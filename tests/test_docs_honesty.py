"""Static honesty: rain-window Pages board stays TestNet-shaped and offline-checkable."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SNAPSHOT = json.loads((DOCS / "snapshot.json").read_text())
README = (ROOT / "README.md").read_text()
REFRESH = (ROOT / "scripts" / "refresh_snapshot.py").read_text()
APP_JS = (DOCS / "app.js").read_text()
INDEX = (DOCS / "index.html").read_text()

RAIN_KEYS = {
    "id",
    "label",
    "mode",
    "mode_name",
    "prize_asset",
    "drip",
    "interval_rounds",
    "last_rain_round",
    "pot",
    "tickets",
    "draw_id",
    "cumulative",
    "wave_cap",
    "wave_count",
    "last_share",
    "last_wave_id",
    "wave_unclaimed",
    "commit_round",
    "prize_locked",
    "status",
}


def test_docs_board_files_exist() -> None:
    assert (DOCS / "index.html").is_file()
    assert (DOCS / "app.js").is_file()
    assert (DOCS / "style.css").is_file()
    assert (DOCS / "snapshot.json").is_file()
    assert (ROOT / "scripts" / "refresh_snapshot.py").is_file()
    assert (ROOT / "LICENSE").is_file()


def test_snapshot_testnet_only() -> None:
    for key in (
        "generated_at",
        "network",
        "hub",
        "last_round",
        "seed_window",
        "rains",
        "source",
    ):
        assert key in SNAPSHOT
    assert SNAPSHOT["network"] == "testnet"
    assert int(SNAPSHOT["hub"]) == 770130162
    assert int(SNAPSHOT["last_round"]) > 0
    assert int(SNAPSHOT["seed_window"]) == 800
    assert SNAPSHOT.get("immutable") is True
    src = SNAPSHOT["source"]
    assert "testnet" in str(src.get("indexer", "")).lower()
    assert "testnet" in str(src.get("algod", "")).lower()
    blob = json.dumps(SNAPSHOT).lower()
    assert "mainnet" not in blob
    # LocalNet / dockernet ids must never land in the Pages snapshot
    assert "dockernet" not in blob
    assert "localhost" not in blob
    assert SNAPSHOT["hub"] not in (1001, 1002, 1003, 1004, 1005)


def test_rains_shape() -> None:
    rains = SNAPSHOT["rains"]
    assert isinstance(rains, list)
    assert len(rains) >= 1
    for rain in rains:
        missing = RAIN_KEYS - set(rain)
        assert not missing, f"rain {rain.get('id')} missing {missing}"
        assert int(rain["id"]) > 0
        assert rain["status"] in {
            "open",
            "drawn-waiting-resolve",
            "resolve-window remaining",
            "abandonable",
        }


def test_board_js_is_read_only_testnet() -> None:
    assert "770130162" in APP_JS
    assert "testnet-idx.algonode.cloud" in APP_JS
    assert "testnet-api.algonode.cloud" in APP_JS
    assert "mainnet" not in APP_JS.lower()
    # explorer host is fine; no wallet connect / signing surface
    for needle in ("mnemonic", "WalletConnect", "MyAlgo", "connectWallet", "signTxn"):
        assert needle.lower() not in APP_JS.lower()


def test_refresh_script_is_read_only() -> None:
    assert "770130162" in REFRESH
    assert "testnet" in REFRESH.lower()
    assert "mainnet" not in REFRESH.lower()
    # docstring may say "no mnemonic"; must not load or print one
    assert "load_mnemonic" not in REFRESH.lower()
    assert "mnemonic =" not in REFRESH.lower()
    assert "private_key" not in REFRESH.lower()
    assert "AtomicTransactionComposer" not in REFRESH
    assert "sign_transaction" not in REFRESH


def test_readme_and_index_honesty() -> None:
    assert "770130162" in README
    assert "TestNet" in README or "testnet" in README.lower()
    assert "Apache-2.0" in README or "Apache" in (ROOT / "LICENSE").read_text()
    assert "770130162" in INDEX
    assert "TESTNET" in INDEX.upper()
