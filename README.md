# arcron-rain-window

A read-only TestNet board that decodes Rain hub boxes and paints whether each rain is open, waiting on a committed seed, still inside the 800-round resolve window, or abandonable.

## Live proof

Immutable Rain hub [`770130162`](https://testnet.explorer.perawallet.app/application/770130162) on Algorand TestNet. At **round 67117616** (`next_rain_id = 5`) the five `r||itob(id)` boxes decoded from [testnet-idx.algonode.cloud](https://testnet-idx.algonode.cloud):

| id | label | mode | prize_locked | commit_round | status |
|---:|---|---|---:|---:|---|
| 1 | Corvid daily | SPLIT | 0 | 0 | open |
| 2 | Corvid GM | WAVE | 0 | 0 | open |
| 3 | live ALGO one | ONE | 50000 | 66831694 | abandonable |
| 4 | live ASA split | SPLIT | 0 | 0 | open |
| 5 | swarm audit split | SPLIT | 0 | 0 | open |

`RainRec` is 224 bytes including `prize_locked`. Hub `770130162` matches that layout **without** the #213 enter-while-locked assert, and it cannot be updated ([#232](https://github.com/CorvidLabs/arcron/issues/232)). Not product rain — product rain is CorvidLabs/arcron-rain hub [`770746178`](https://testnet.explorer.perawallet.app/application/770746178). Do not copy this app id into `arcron-rain`. `SEED_WINDOW = 800`. Rain 3 is past the window with `prize_locked = 50000` — abandonable on chain. The board does not call `abandon`.

## How to view

Open [corvid-agent.github.io/arcron-rain-window](https://corvid-agent.github.io/arcron-rain-window/). JavaScript on. No wallet. The page prefers live indexer + algod; if CORS or the network blocks it, `docs/snapshot.json` is the fallback.

```bash
python3 scripts/refresh_snapshot.py   # writes docs/snapshot.json from TestNet, no key
python3 scripts/probe_history.py      # append docs/history.json + history.sqlite from snapshot
```

Phosphor graphs on the Pages board read append-only `docs/history.json` / `docs/history.sqlite` via in-page sql.js (same spirit as arcron-status-page).

## Cost

Zero. This repo never signs, never asks for a mnemonic, and never submits a transaction. Looking at boxes is free.

## What is broken

- Browser CORS on algonode can force the snapshot, which ages.
- The live hub is pre-#213: tickets can still be bought while a ONE draw is open. Immutable, so that guard will never land on 770130162.
- The board does not call `resolve` or `abandon` (no wallet).
- Ticket boxes and lottery index boxes are not listed.
- `blk_seed` is not fetched; remaining rounds are computed from `commit_round` and last-round only.
- SPLIT and WAVE rains have no seed window; only ONE with a lock does.
- First-party demo. Unaudited. TestNet only. Not the [Arcron console](https://corvidlabs.xyz/arcron/console/). Not [arrivals](https://corvid-agent.github.io/arrivals/).

## License

Apache-2.0. See [LICENSE](LICENSE).
