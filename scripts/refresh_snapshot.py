#!/usr/bin/env python3
"""Refresh docs/snapshot.json from TestNet rain hub 770130162. Read-only. No mnemonic."""
from __future__ import annotations

import base64
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from algosdk.encoding import encode_address

HUB = 770130162
INDEXER = "https://testnet-idx.algonode.cloud"
ALGOD = "https://testnet-api.algonode.cloud"
SEED_WINDOW = 800
COMMIT_DELAY = 8
MODES = {0: "SPLIT", 1: "ONE", 2: "WAVE"}
OUT = Path(__file__).resolve().parents[1] / "docs" / "snapshot.json"


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "arcron-rain-window-refresh"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def u64(raw: bytes, off: int) -> int:
    return int.from_bytes(raw[off : off + 8], "big")


def rain_label(raw: bytes) -> str:
    chunk = raw[64:96]
    end = chunk.find(b"\x00")
    if end == -1:
        end = len(chunk)
    return chunk[:end].decode("ascii", "replace").strip()


def hub_state(app_json: dict) -> dict:
    params = (app_json.get("application") or {}).get("params") or app_json.get("params") or {}
    state = {}
    for kv in params.get("global-state") or []:
        key = base64.b64decode(kv["key"]).decode("ascii", "replace")
        val = kv.get("value") or {}
        if val.get("type") == 2:
            state[key] = val.get("uint", 0)
        elif val.get("type") == 1:
            state[key] = val.get("bytes", "")
    return state


def status_of(r: dict, round_: int) -> tuple[str, dict | None]:
    if r["mode"] == 1 and r["prize_locked"] > 0:
        close = r["commit_round"] + SEED_WINDOW
        if round_ <= r["commit_round"]:
            return "drawn-waiting-resolve", {"phase": "wait", "n": r["commit_round"] - round_, "close": close}
        if round_ <= close:
            return "resolve-window remaining", {"phase": "window", "n": close - round_, "close": close}
        return "abandonable", {"phase": "closed", "n": 0, "close": close}
    return "open", None


def decode_rain(rid: int, raw: bytes, round_: int) -> dict:
    if len(raw) < 224:
        raise ValueError(f"short RainRec {rid} len={len(raw)}")
    rec = {
        "id": rid,
        "creator": encode_address(raw[0:32]),
        "gate_creator": encode_address(raw[32:64]),
        "label": rain_label(raw),
        "prize_asset": u64(raw, 96),
        "drip": u64(raw, 104),
        "interval_rounds": u64(raw, 112),
        "last_rain_round": u64(raw, 120),
        "pot": u64(raw, 128),
        "tickets": u64(raw, 136),
        "draw_id": u64(raw, 144),
        "cumulative": u64(raw, 152),
        "mode": u64(raw, 160),
        "wave_cap": u64(raw, 168),
        "wave_count": u64(raw, 176),
        "last_share": u64(raw, 184),
        "last_wave_id": u64(raw, 192),
        "wave_unclaimed": u64(raw, 200),
        "commit_round": u64(raw, 208),
        "prize_locked": u64(raw, 216),
        "value_b64": base64.b64encode(raw).decode("ascii"),
        "name_b64": base64.b64encode(b"r" + rid.to_bytes(8, "big")).decode("ascii"),
    }
    rec["mode_name"] = MODES.get(rec["mode"], str(rec["mode"]))
    status, window = status_of(rec, round_)
    rec["status"] = status
    rec["window"] = window
    return rec


def main() -> None:
    status = get(f"{ALGOD}/v2/status")
    last_round = int(status["last-round"])
    rain_app = get(f"{INDEXER}/v2/applications/{HUB}")
    hs = hub_state(rain_app)
    next_id = int(hs.get("next_rain_id") or 0)
    rains = []
    for rid in range(1, next_id + 1):
        name = base64.b64encode(b"r" + rid.to_bytes(8, "big")).decode("ascii")
        box = get(f"{INDEXER}/v2/applications/{HUB}/box?name=b64:{name}")
        raw = base64.b64decode(box["value"])
        rains.append(decode_rain(rid, raw, last_round))
    snapshot = {
        "network": "testnet",
        "hub": HUB,
        "immutable": True,
        "seed_window": SEED_WINDOW,
        "commit_delay": COMMIT_DELAY,
        "last_round": last_round,
        "box_round": last_round,
        "next_rain_id": next_id,
        "cursor": hs.get("cursor", 0),
        "bootstrapped": hs.get("bootstrapped", 0),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "indexer": INDEXER,
            "algod": ALGOD,
            "layout": "https://github.com/CorvidLabs/arcron/blob/main/smart_contracts/rain/contract.py",
            "struct": "RainRec",
        },
        "rains": rains,
    }
    OUT.write_text(json.dumps(snapshot, indent=2) + "\n")
    statuses = ", ".join(f"{r['id']}:{r['status']}" for r in rains)
    print(f"wrote {OUT} last_round={last_round} rains={len(rains)} {statuses}")


if __name__ == "__main__":
    main()
