/* Rain resolve window. Read-only. No wallet. TestNet hub 770130162. */
(() => {
  const HUB = 770130162;
  const INDEXER = "https://testnet-idx.algonode.cloud";
  const ALGOD = "https://testnet-api.algonode.cloud";
  const EXPLORER = "https://testnet.explorer.perawallet.app/application/" + HUB;
  const SEED_WINDOW = 800;
  const REFRESH_MS = 30000;
  const MODES = { 0: "SPLIT", 1: "ONE", 2: "WAVE" };

  function b64ToBytes(b64) {
    const bin = atob(String(b64).replace(/-/g, "+").replace(/_/g, "/"));
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  function bytesToB64(bytes) {
    let s = "";
    for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
    return btoa(s);
  }

  function u64(dv, off) {
    return dv.getUint32(off) * 0x100000000 + dv.getUint32(off + 4);
  }

  function rainNameB64(id) {
    const raw = new Uint8Array(9);
    raw[0] = 0x72; // b"r"
    const dv = new DataView(raw.buffer);
    const hi = Math.floor(id / 0x100000000);
    const lo = id >>> 0;
    dv.setUint32(1, hi);
    dv.setUint32(5, lo);
    return bytesToB64(raw);
  }

  function labelOf(bytes) {
    const slice = bytes.subarray(64, 96);
    let out = "";
    for (let i = 0; i < slice.length; i++) {
      if (slice[i] === 0) break;
      out += String.fromCharCode(slice[i]);
    }
    return out;
  }

  // RainRec: Address, Address, Label[32], then 16× UInt64. 224 bytes.
  function decodeRainRec(id, bytes) {
    if (bytes.length < 224) throw new Error("short RainRec " + id + " len=" + bytes.length);
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    return {
      id,
      label: labelOf(bytes),
      prize_asset: u64(dv, 96),
      drip: u64(dv, 104),
      interval_rounds: u64(dv, 112),
      last_rain_round: u64(dv, 120),
      pot: u64(dv, 128),
      tickets: u64(dv, 136),
      draw_id: u64(dv, 144),
      cumulative: u64(dv, 152),
      mode: u64(dv, 160),
      wave_cap: u64(dv, 168),
      wave_count: u64(dv, 176),
      last_share: u64(dv, 184),
      last_wave_id: u64(dv, 192),
      wave_unclaimed: u64(dv, 200),
      commit_round: u64(dv, 208),
      prize_locked: u64(dv, 216),
    };
  }

  function statusOf(r, round) {
    if (r.mode === 1 && r.prize_locked > 0) {
      if (round <= r.commit_round) return "drawn-waiting-resolve";
      if (round <= r.commit_round + SEED_WINDOW) return "resolve-window remaining";
      return "abandonable";
    }
    return "open";
  }

  function flapWord(status) {
    if (status === "drawn-waiting-resolve") return "WAIT";
    if (status === "resolve-window remaining") return "RESOLVE";
    if (status === "abandonable") return "ABANDON";
    return "OPEN";
  }

  function remainingRounds(r, round) {
    if (r.mode !== 1 || r.prize_locked === 0) return null;
    const close = r.commit_round + SEED_WINDOW;
    if (round <= r.commit_round) return { phase: "wait", n: r.commit_round - round, close };
    if (round <= close) return { phase: "window", n: close - round, close };
    return { phase: "closed", n: 0, close };
  }

  function globalU64(app, key) {
    const want = btoa(key);
    const state = (app.params && app.params["global-state"]) ||
      (app.application && app.application.params && app.application.params["global-state"]) ||
      [];
    for (const item of state) {
      if (item.key === want || item.key === key) return item.value.uint;
    }
    // indexer keys are b64
    const rawWant = new TextEncoder().encode(key);
    for (const item of state) {
      try {
        const raw = b64ToBytes(item.key);
        if (raw.length === rawWant.length && raw.every((b, i) => b === rawWant[i])) {
          return item.value.uint;
        }
      } catch {
        /* ignore */
      }
    }
    return 0;
  }

  async function fetchJson(url) {
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(url + " " + res.status);
    return res.json();
  }

  async function fetchBox(nameB64) {
    const q = "b64:" + nameB64;
    try {
      return await fetchJson(INDEXER + "/v2/applications/" + HUB + "/box?name=" + encodeURIComponent(q));
    } catch {
      return await fetchJson(ALGOD + "/v2/applications/" + HUB + "/box?name=" + encodeURIComponent(q));
    }
  }

  async function fetchLive() {
    let last_round = 0;
    let roundNote = "";
    try {
      const st = await fetchJson(ALGOD + "/v2/status");
      last_round = st["last-round"];
      roundNote = "algod last-round";
    } catch {
      roundNote = "indexer current-round";
    }
    let app;
    try {
      app = await fetchJson(INDEXER + "/v2/applications/" + HUB);
    } catch {
      app = await fetchJson(ALGOD + "/v2/applications/" + HUB);
    }
    if (!last_round) last_round = app["current-round"] || 0;
    const next = globalU64(app, "next_rain_id") || 5;
    const rains = [];
    for (let id = 1; id <= next; id++) {
      const box = await fetchBox(rainNameB64(id));
      const rec = decodeRainRec(id, b64ToBytes(box.value));
      rains.push(rec);
    }
    return {
      last_round,
      rains,
      next_rain_id: next,
      mode: "live",
      note: "indexer + " + roundNote,
    };
  }

  async function fetchSnapshot() {
    const snap = await fetchJson("snapshot.json");
    const rains = (snap.rains || []).map((r) => {
      if (r.value_b64) return decodeRainRec(r.id, b64ToBytes(r.value_b64));
      return r;
    });
    return {
      last_round: snap.last_round,
      rains,
      next_rain_id: snap.next_rain_id,
      mode: "fallback",
      note: "snapshot " + (snap.generated_at || "") + " · live fetch failed",
      generated_at: snap.generated_at,
    };
  }

  function flaps(text) {
    const wrap = document.createElement("span");
    wrap.className = "flaps";
    const s = String(text);
    for (let i = 0; i < s.length; i++) {
      const cell = document.createElement("span");
      cell.className = "flap";
      cell.style.setProperty("--d", i * 32 + "ms");
      cell.textContent = s[i] === " " ? "\u00a0" : s[i];
      wrap.appendChild(cell);
    }
    return wrap;
  }

  function metaCell(k, v) {
    const d = document.createElement("div");
    const lab = document.createElement("span");
    lab.textContent = k;
    const b = document.createElement("b");
    b.textContent = v;
    d.append(lab, b);
    return d;
  }

  function render(frame) {
    const round = frame.last_round;
    document.getElementById("round").textContent = String(round);
    document.getElementById("decoded").textContent = String(frame.rains.length);
    const feed = document.getElementById("feed");
    feed.textContent = frame.mode === "live" ? "LIVE" : frame.mode === "fallback" ? "SNAPSHOT" : "SEEKING";
    feed.style.color = frame.mode === "live" ? "var(--phosphor)" : frame.mode === "fallback" ? "var(--wait)" : "var(--mute)";
    document.getElementById("feed-note").textContent = frame.note || "";

    const host = document.getElementById("columns");
    host.replaceChildren();
    document.getElementById("empty").classList.toggle("hidden", frame.rains.length > 0);

    frame.rains.forEach((r) => {
      const st = statusOf(r, round);
      const rem = remainingRounds(r, round);
      const card = document.createElement("article");
      card.className = "gauge";
      card.dataset.status = st;

      const idRow = document.createElement("div");
      idRow.className = "id-row";
      idRow.appendChild(flaps("R-" + String(r.id).padStart(3, "0")));

      const lab = document.createElement("div");
      lab.className = "label";
      lab.textContent = (r.label || "—") + " · " + (MODES[r.mode] || r.mode);

      const stFlaps = document.createElement("div");
      stFlaps.className = "status-flaps";
      stFlaps.appendChild(flaps(flapWord(st)));

      const phrase = document.createElement("div");
      phrase.className = "status-phrase";
      phrase.textContent = st;

      const cyl = document.createElement("div");
      cyl.className = "cylinder";
      const water = document.createElement("div");
      water.className = "water";
      const ticks = document.createElement("div");
      ticks.className = "ticks";
      const read = document.createElement("div");
      read.className = "cyl-read";
      if (rem && rem.phase === "window") {
        const pct = Math.max(0, Math.min(100, (rem.n / SEED_WINDOW) * 100));
        water.style.height = pct + "%";
        read.textContent = rem.n + " r left";
      } else if (rem && rem.phase === "wait") {
        water.style.height = "100%";
        water.style.opacity = "0.35";
        read.textContent = "opens in " + rem.n + " r";
      } else if (rem && rem.phase === "closed") {
        water.style.height = "4%";
        water.style.background = "linear-gradient(180deg, #ff5a8a, #4a1020)";
        read.textContent = "window closed";
      } else {
        water.classList.add("dry");
        read.textContent = "no lock";
      }
      cyl.append(water, ticks, read);

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.append(
        metaCell("DRIP", String(r.drip)),
        metaCell("TICKETS", String(r.tickets)),
        metaCell("POT", String(r.pot)),
        metaCell("DRAW", String(r.draw_id)),
        metaCell("COMMIT", String(r.commit_round)),
        metaCell("LOCKED", String(r.prize_locked)),
      );

      const link = document.createElement("a");
      link.className = "explore";
      link.href = EXPLORER;
      link.textContent = "EXPLORER · " + HUB;
      link.title = "Rain " + r.id + " is box r||itob(" + r.id + ") on hub " + HUB;

      card.append(idRow, lab, stFlaps, phrase, cyl, meta, link);
      host.appendChild(card);
    });

    const stamp = document.getElementById("stamp");
    const when = frame.generated_at ? " snapshot " + frame.generated_at : " painted " + new Date().toISOString();
    stamp.textContent = "hub " + HUB + " · last-round " + round + " · rains " + frame.rains.length + " ·" + when + " · chain is source of truth.";
  }

  async function tick() {
    try {
      render(await fetchLive());
    } catch (err) {
      console.warn("live fetch failed", err);
      try {
        render(await fetchSnapshot());
      } catch (err2) {
        document.getElementById("feed").textContent = "FAIL";
        document.getElementById("feed-note").textContent = "live and snapshot both failed";
        console.error(err2);
      }
    }
  }

  tick();
  setInterval(tick, REFRESH_MS);
})();
