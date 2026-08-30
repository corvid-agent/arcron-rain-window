# arcron-rain-window

A read-only TestNet board that decodes Rain hub boxes and paints whether each rain is open, waiting on a committed seed, still inside the 800-round resolve window, or abandonable.

## Live proof

Immutable Rain hub [`770130162`](https://testnet.explorer.perawallet.app/application/770130162) on Algorand TestNet. At **round 66823650** (`next_rain_id = 5`) the five `r||itob(id)` boxes decoded from [testnet-idx.algonode.cloud](https://testnet-idx.algonode.cloud):

| id | label | mode | prize_locked | commit_round | status |
|---:|---|---|---:|---:|---|
| 1 | Corvid daily | SPLIT | 0 | 0 | open |
| 2 | Corvid GM | WAVE | 0 | 0 | open |
| 3 | live ALGO one | ONE | 0 | 0 | open |
| 4 | live ASA split | SPLIT | 0 | 0 | open |
| 5 | swarm audit split | SPLIT | 0 | 0 | open |

`RainRec` layout is the 224-byte ARC-4 struct in [CorvidLabs/arcron `contract.py`](https://github.com/CorvidLabs/arcron/blob/main/smart_contracts/rain/contract.py). `SEED_WINDOW = 800`. Block seed is readable for ~1000 rounds; `resolve` must land inside the window or the locked drip is `abandon`ed. No rain had `prize_locked > 0` at that round, so the window was idle — that is the chain, not a demo script.

## How to view

Open [corvid-agent.github.io/arcron-rain-window](https://corvid-agent.github.io/arcron-rain-window/). JavaScript on. No wallet. The page prefers live indexer + algod; if CORS or the network blocks it, `docs/snapshot.json` is the fallback.

## Cost

Zero. This repo never signs, never asks for a mnemonic, and never submits a transaction. Looking at boxes is free.

## What is broken

- Browser CORS on algonode can force the snapshot, which ages.
- The board does not call `resolve` or `abandon` (no wallet).
- Ticket boxes and lottery index boxes are not listed.
- `blk_seed` is not fetched; remaining rounds are computed from `commit_round` and last-round only.
- SPLIT and WAVE rains have no seed window; only ONE with a lock does.
- First-party demo. Unaudited. TestNet only. Not the [Arcron console](https://corvidlabs.xyz/arcron/console/). Not [arrivals](https://corvid-agent.github.io/arrivals/).

## License

Apache-2.0. See [LICENSE](LICENSE).
