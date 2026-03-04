# tests/test_sync.py
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest


SAMPLE_RESPONSE = {
    "accounts": [
        {
            "org": {"domain": "chase.com", "name": "Chase", "id": "chase-org-1"},
            "id": "acct-checking-1",
            "name": "TOTAL CHECKING",
            "currency": "USD",
            "balance": "4230.50",
            "available-balance": "4200.00",
            "balance-date": 1740873600,
            "transactions": [
                {
                    "id": "txn-1",
                    "posted": 1740787200,
                    "amount": "-47.32",
                    "description": "WHOLE FOODS MKT #10234",
                    "pending": False,
                },
                {
                    "id": "txn-2",
                    "posted": 1740700800,
                    "amount": "4225.00",
                    "description": "PAYROLL AMAZON",
                    "pending": False,
                },
            ],
        }
    ]
}


def test_parse_simplefin_response():
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(SAMPLE_RESPONSE)

    assert len(institutions) == 1
    assert institutions[0]["id"] == "chase-org-1"
    assert institutions[0]["name"] == "Chase"

    assert len(accounts) == 1
    assert accounts[0]["id"] == "acct-checking-1"
    assert accounts[0]["name"] == "TOTAL CHECKING"
    assert accounts[0]["institution_id"] == "chase-org-1"

    assert len(balances) == 1
    assert balances[0]["balance"] == 4230.50

    assert len(transactions) == 2
    assert transactions[0]["amount"] == -47.32
    assert transactions[1]["amount"] == 4225.00


def test_parse_handles_missing_org():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [],
            }
        ]
    }
    from simledge.sync import parse_response
    institutions, accounts, balances, transactions = parse_response(response)
    assert len(institutions) == 0
    assert accounts[0]["institution_id"] is None


def test_parse_handles_pending_transactions():
    response = {
        "accounts": [
            {
                "id": "acct-1",
                "name": "Account",
                "currency": "USD",
                "balance": "100.00",
                "balance-date": 1740873600,
                "transactions": [
                    {
                        "id": "txn-pending",
                        "posted": 1740787200,
                        "amount": "-10.00",
                        "description": "PENDING CHARGE",
                        "pending": True,
                    }
                ],
            }
        ]
    }
    from simledge.sync import parse_response
    _, _, _, transactions = parse_response(response)
    assert transactions[0]["pending"] is True


def test_run_sync_quiet_returns_result_and_no_print(tmp_path, capsys):
    """run_sync(quiet=True) returns result dict without printing."""
    from simledge.sync import run_sync

    db_path = tmp_path / "test.db"
    config_path = tmp_path / "config.toml"
    config_path.write_text('[simplefin]\naccess_url = "https://fake.simplefin.org/test"\n')

    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("simledge.sync.load_access_url", return_value="https://fake.simplefin.org/test"), \
         patch("simledge.sync.DB_PATH", db_path), \
         patch("simledge.sync.fetch_accounts", new_callable=AsyncMock, return_value=SAMPLE_RESPONSE):
        result = asyncio.run(run_sync(quiet=True))

    assert result["status"] == "success"
    assert result["accounts"] == 1
    assert result["transactions"] == 2
    captured = capsys.readouterr()
    assert captured.out == ""


def test_sync_is_stale_after_24h(tmp_path):
    from datetime import datetime, timedelta
    from simledge.db import init_db, get_last_sync
    conn = init_db(str(tmp_path / "test.db"))
    # Log a sync 25 hours ago
    old_time = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO sync_log (synced_at, accounts_updated, transactions_added, status)"
        " VALUES (?, 1, 10, 'success')",
        (old_time,),
    )
    conn.commit()
    last = get_last_sync(conn)
    last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
    assert (datetime.now() - last_dt).total_seconds() > 86400
    conn.close()


def test_sync_is_fresh_within_24h(tmp_path):
    from datetime import datetime
    from simledge.db import init_db, log_sync, get_last_sync
    conn = init_db(str(tmp_path / "test.db"))
    log_sync(conn, 1, 10)  # logs "now"
    last = get_last_sync(conn)
    last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
    assert (datetime.now() - last_dt).total_seconds() < 86400
    conn.close()


def test_run_sync_quiet_error_returns_dict(capsys):
    """run_sync(quiet=True) returns error dict without printing on missing config."""
    from simledge.sync import run_sync

    with patch("simledge.sync.load_access_url", return_value=None):
        result = asyncio.run(run_sync(quiet=True))

    assert result["status"].startswith("error:")
    assert result["accounts"] == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_sync_retries_once_on_network_error(tmp_path):
    """Sync should retry exactly once on network error, not more."""
    from simledge.sync import run_sync
    from simledge.db import init_db

    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("connection refused")

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    with patch("simledge.sync.fetch_accounts", side_effect=mock_fetch), \
         patch("simledge.sync.load_access_url", return_value="https://fake.url"), \
         patch("simledge.sync.DB_PATH", db_path), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = asyncio.run(run_sync(quiet=True))

    assert result["status"].startswith("error:")
    assert "internet connection" in result["status"].lower()
    assert call_count == 2  # initial + 1 retry


def test_sync_succeeds_on_retry(tmp_path):
    """Sync should succeed if retry works."""
    from simledge.sync import run_sync
    from simledge.db import init_db

    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("temporary failure")
        return SAMPLE_RESPONSE

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    with patch("simledge.sync.fetch_accounts", side_effect=mock_fetch), \
         patch("simledge.sync.load_access_url", return_value="https://fake.url"), \
         patch("simledge.sync.DB_PATH", db_path), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = asyncio.run(run_sync(quiet=True))

    assert result["status"] == "success"
    assert call_count == 2
