"""SimpleFIN API client and data sync."""

import json
from base64 import b64decode
from datetime import datetime, timezone

import httpx

from simledge.config import DB_PATH, CONFIG_PATH
from simledge.db import (
    init_db, upsert_institution, upsert_account, snapshot_balance,
    upsert_transaction, log_sync, get_last_sync,
)
from simledge.log import setup_logging

log = setup_logging("simledge.sync")


def parse_response(data):
    """Parse SimpleFIN JSON response into normalized records."""
    institutions = []
    accounts = []
    balances = []
    transactions = []
    seen_orgs = set()

    for acct in data.get("accounts", []):
        org = acct.get("org")
        institution_id = None

        if org and org.get("id"):
            institution_id = org["id"]
            if institution_id not in seen_orgs:
                institutions.append({
                    "id": institution_id,
                    "name": org.get("name", ""),
                    "domain": org.get("domain"),
                })
                seen_orgs.add(institution_id)

        accounts.append({
            "id": acct["id"],
            "institution_id": institution_id,
            "name": acct["name"],
            "currency": acct.get("currency", "USD"),
        })

        balance_ts = acct.get("balance-date", 0)
        balance_date = datetime.fromtimestamp(balance_ts, tz=timezone.utc).strftime("%Y-%m-%d")
        balances.append({
            "account_id": acct["id"],
            "date": balance_date,
            "balance": float(acct.get("balance", 0)),
            "available_balance": float(acct["available-balance"]) if "available-balance" in acct else None,
        })

        for txn in acct.get("transactions", []):
            posted_ts = txn.get("posted", 0)
            if posted_ts and posted_ts > 0:
                posted_date = datetime.fromtimestamp(posted_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            else:
                posted_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            transactions.append({
                "id": txn["id"],
                "account_id": acct["id"],
                "posted": posted_date,
                "amount": float(txn.get("amount", 0)),
                "description": txn.get("description", ""),
                "pending": txn.get("pending", False),
                "raw_json": json.dumps(txn),
            })

    return institutions, accounts, balances, transactions


async def fetch_accounts(access_url, start_date=None):
    """Fetch account data from SimpleFIN."""
    params = {"pending": "1"}
    if start_date:
        dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        params["start-date"] = str(int(dt.timestamp()))
    else:
        # No start date means fetch max history (5 years back)
        epoch = datetime(2020, 1, 1, tzinfo=timezone.utc)
        params["start-date"] = str(int(epoch.timestamp()))

    # access_url is the base; SimpleFIN API requires /accounts endpoint
    url = access_url.rstrip("/") + "/accounts"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()


def load_access_url():
    """Read SimpleFIN access URL from config."""
    import tomllib
    try:
        with open(CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
        return config["simplefin"]["access_url"]
    except (FileNotFoundError, KeyError) as e:
        log.error("config not found or missing simplefin.access_url: %s", e)
        return None


async def run_sync(full=False, start_date=None, quiet=False):
    """Main sync: fetch from SimpleFIN, update local DB.

    When quiet=True, suppresses print output and returns a result dict.
    """
    access_url = load_access_url()
    if not access_url:
        if not quiet:
            print("No SimpleFIN access URL configured. Run: simledge setup")
        return {"accounts": 0, "transactions": 0, "status": "error: no access URL configured"}

    conn = init_db(DB_PATH)
    if not start_date:
        start_date = None if full else get_last_sync(conn)

    log.info("syncing from SimpleFIN (start_date=%s, full=%s)", start_date, full)
    try:
        data = await fetch_accounts(access_url, start_date)
    except httpx.HTTPError as e:
        log.error("SimpleFIN request failed: %s", e)
        log_sync(conn, 0, 0, status=f"error: {e}")
        if not quiet:
            print(f"Sync failed: {e}")
        conn.close()
        return {"accounts": 0, "transactions": 0, "status": f"error: {e}"}

    institutions, accounts, balances, transactions = parse_response(data)

    for inst in institutions:
        upsert_institution(conn, inst["id"], inst["name"], inst.get("domain"))
    for acct in accounts:
        upsert_account(conn, acct["id"], acct["institution_id"], acct["name"], acct["currency"])
    for bal in balances:
        snapshot_balance(conn, bal["account_id"], bal["date"], bal["balance"], bal.get("available_balance"))

    txn_count = 0
    for txn in transactions:
        upsert_transaction(
            conn, txn["id"], txn["account_id"], txn["posted"], txn["amount"],
            txn["description"], pending=txn["pending"], raw_json=txn["raw_json"],
        )
        txn_count += 1

    log_sync(conn, len(accounts), txn_count)
    if not quiet:
        print(f"Synced {len(accounts)} accounts, {txn_count} transactions")
    conn.close()
    return {"accounts": len(accounts), "transactions": txn_count, "status": "success"}
