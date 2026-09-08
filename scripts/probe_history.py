#!/usr/bin/env python3
"""Append one rain-window sample into docs/history.json + docs/history.sqlite.

Reads current docs/snapshot.json by default (honest TestNet hub 770130162).
Pass --refresh to run refresh_snapshot.py first. Never submits, no mnemonic,
TestNet only. Demo hub 770130162 only — never product 770746178.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SNAP_PATH = DOCS / "snapshot.json"
HIST_JSON = DOCS / "history.json"
HIST_DB = DOCS / "history.sqlite"
DEMO_HUB = 770130162

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
  t TEXT,
  round INTEGER,
  listed INTEGER,
  open INTEGER,
  waiting INTEGER,
  resolve_window INTEGER,
  abandonable INTEGER,
  pot_micro INTEGER,
  prize_locked_micro INTEGER,
  tickets INTEGER,
  source TEXT
)
"""


def sample_from_snapshot(snap: dict, source: str) -> dict:
    rains = snap.get("rains") or []
    counts = {
        "open": 0,
        "drawn-waiting-resolve": 0,
        "resolve-window remaining": 0,
        "abandonable": 0,
    }
    pot = 0
    locked = 0
    tickets = 0
    for r in rains:
        st = r.get("status") or "open"
        counts[st] = counts.get(st, 0) + 1
        pot += int(r.get("pot") or 0)
        locked += int(r.get("prize_locked") or 0)
        tickets += int(r.get("tickets") or 0)
    return {
        "t": snap.get("generated_at") or "",
        "round": int(snap["last_round"]),
        "listed": len(rains),
        "open": counts.get("open", 0),
        "waiting": counts.get("drawn-waiting-resolve", 0),
        "resolve_window": counts.get("resolve-window remaining", 0),
        "abandonable": counts.get("abandonable", 0),
        "pot_micro": pot,
        "prize_locked_micro": locked,
        "tickets": tickets,
        "source": source,
    }


def load_history() -> list[dict]:
    if not HIST_JSON.exists():
        return []
    data = json.loads(HIST_JSON.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def rewrite_sqlite(rows: list[dict]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    if HIST_DB.exists():
        HIST_DB.unlink()
    con = sqlite3.connect(HIST_DB)
    con.execute(SCHEMA)
    con.executemany(
        "INSERT INTO samples VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                r.get("t"),
                r.get("round"),
                r.get("listed"),
                r.get("open"),
                r.get("waiting"),
                r.get("resolve_window"),
                r.get("abandonable"),
                r.get("pot_micro"),
                r.get("prize_locked_micro"),
                r.get("tickets"),
                r.get("source"),
            )
            for r in rows
        ],
    )
    con.commit()
    con.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="run scripts/refresh_snapshot.py before sampling snapshot.json",
    )
    args = ap.parse_args()

    if args.refresh:
        refresh = ROOT / "scripts" / "refresh_snapshot.py"
        print("running refresh_snapshot.py …", file=sys.stderr)
        rc = subprocess.call([sys.executable, str(refresh)])
        if rc != 0:
            print(f"refresh_snapshot failed rc={rc}", file=sys.stderr)
            return rc

    if not SNAP_PATH.is_file():
        print(f"missing {SNAP_PATH}", file=sys.stderr)
        return 1

    snap = json.loads(SNAP_PATH.read_text(encoding="utf-8"))
    if snap.get("network") != "testnet":
        print("refuse: snapshot.json network is not testnet", file=sys.stderr)
        return 1
    hub = int(snap.get("hub") or 0)
    if hub != DEMO_HUB:
        print(f"refuse: hub {hub} is not demo hub {DEMO_HUB}", file=sys.stderr)
        return 1

    sample = sample_from_snapshot(snap, source="probe_history.py from docs/snapshot.json")
    hist = load_history()
    if any(int(h.get("round") or 0) == sample["round"] for h in hist):
        print(json.dumps({"skipped_duplicate": True, "round": sample["round"], "points": len(hist)}))
        rewrite_sqlite(hist)
        return 0

    hist.append(sample)
    hist.sort(key=lambda h: (int(h.get("round") or 0), str(h.get("t") or "")))
    HIST_JSON.write_text(json.dumps(hist, indent=2) + "\n", encoding="utf-8")
    rewrite_sqlite(hist)
    print(json.dumps({"appended": True, "round": sample["round"], "points": len(hist), "sample": sample}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
