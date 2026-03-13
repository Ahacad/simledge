"""SimpleFIN API client and data sync."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx

from simledge.config import CONFIG_PATH, DB_PATH
from simledge.db import (
    get_last_sync,
    init_db,
    log_sync,
    snapshot_balance,
    upsert_account,
    upsert_institution,
    upsert_transaction,
)
from simledge.log import setup_logging

log = setup_logging("simledge.sync")

CC_NAME_HINTS = {"credit", "card", "visa", "mastercard", "amex", "discover", "citi"}


def _infer_account_type(name):
    """Best-effort account type from name keywords."""
    lower = name.lower()
    for hint in CC_NAME_HINTS:
        if hint in lower:
            return "credit"
    if "checking" in lower:
        return "checking"
    if "saving" in lower:
        return "savings"
    return None


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
                institutions.append(
                    {
                        "id": institution_id,
                        "name": org.get("name", ""),
                        "domain": org.get("domain"),
                    }
                )
                seen_orgs.add(institution_id)

        accounts.append(
            {
                "id": acct["id"],
                "institution_id": institution_id,
                "name": acct["name"],
                "currency": acct.get("currency", "USD"),
                "type": _infer_account_type(acct["name"]),
            }
        )

        balance_ts = acct.get("balance-date", 0)
        balance_date = datetime.fromtimestamp(balance_ts, tz=UTC).strftime("%Y-%m-%d")
        balances.append(
            {
                "account_id": acct["id"],
                "date": balance_date,
                "balance": float(acct.get("balance", 0)),
                "available_balance": float(acct["available-balance"])
                if "available-balance" in acct
                else None,
            }
        )

        for txn in acct.get("transactions", []):
            posted_ts = txn.get("posted", 0)
            if posted_ts and posted_ts > 0:
                posted_date = datetime.fromtimestamp(posted_ts, tz=UTC).strftime("%Y-%m-%d")
            else:
                posted_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
            transactions.append(
                {
                    "id": txn["id"],
                    "account_id": acct["id"],
                    "posted": posted_date,
                    "amount": float(txn.get("amount", 0)),
                    "description": txn.get("description", ""),
                    "pending": txn.get("pending", False),
                    "raw_json": json.dumps(txn),
                }
            )

    return institutions, accounts, balances, transactions


async def fetch_accounts(access_url, start_date=None):
    """Fetch account data from SimpleFIN."""
    params = {"pending": "1"}
    if start_date:
        dt = datetime.fromisoformat(start_date).replace(tzinfo=UTC)
        params["start-date"] = str(int(dt.timestamp()))
    else:
        # No start date means fetch max history (5 years back)
        epoch = datetime(2020, 1, 1, tzinfo=UTC)
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


def _sync_error_message(error):
    """Return user-friendly error message with actionable guidance."""
    if isinstance(error, httpx.ConnectError):
        return "Cannot reach SimpleFIN. Check your internet connection."
    if isinstance(error, httpx.TimeoutException):
        return "SimpleFIN request timed out. Try again later."
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status in (401, 403):
            return "SimpleFIN access denied. Your token may have expired. Run: simledge setup"
        if status == 429:
            return "SimpleFIN rate limit hit. Wait a few minutes before syncing again."
        if status >= 500:
            return f"SimpleFIN server error ({status}). Try again later."
    return f"Sync failed: {error}"


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
        last_sync = None if full else get_last_sync(conn)
        if last_sync:
            # Look back 14 days from last sync to catch retroactively-posted
            # transactions (credit cards can take days to post). Duplicates
            # are harmless thanks to upsert.
            dt = datetime.fromisoformat(last_sync).replace(tzinfo=UTC)
            start_date = (dt - timedelta(days=14)).strftime("%Y-%m-%d")
        else:
            start_date = None

    log.info("syncing from SimpleFIN (start_date=%s, full=%s)", start_date, full)
    data = None
    last_error = None
    for attempt in range(2):
        try:
            data = await fetch_accounts(access_url, start_date)
            break
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code in (401, 403, 429):
                break
            if attempt == 0:
                log.warning("sync attempt 1 failed: %s, retrying in 2s", e)
                await asyncio.sleep(2)
            else:
                log.error("sync retry failed: %s", e)
        except httpx.HTTPError as e:
            last_error = e
            if attempt == 0:
                log.warning("sync attempt 1 failed: %s, retrying in 2s", e)
                await asyncio.sleep(2)
            else:
                log.error("sync retry failed: %s", e)

    if data is None:
        error_msg = _sync_error_message(last_error)
        log_sync(conn, 0, 0, status=f"error: {last_error}")
        if not quiet:
            print(f"Sync failed: {error_msg}")
        conn.close()
        return {"accounts": 0, "transactions": 0, "status": f"error: {error_msg}"}

    institutions, accounts, balances, transactions = parse_response(data)

    for inst in institutions:
        upsert_institution(conn, inst["id"], inst["name"], inst.get("domain"))
    for acct in accounts:
        upsert_account(
            conn,
            acct["id"],
            acct["institution_id"],
            acct["name"],
            acct["currency"],
            acct.get("type"),
        )
    for bal in balances:
        snapshot_balance(
            conn, bal["account_id"], bal["date"], bal["balance"], bal.get("available_balance")
        )

    txn_count = 0
    for txn in transactions:
        upsert_transaction(
            conn,
            txn["id"],
            txn["account_id"],
            txn["posted"],
            txn["amount"],
            txn["description"],
            pending=txn["pending"],
            raw_json=txn["raw_json"],
        )
        txn_count += 1

    log_sync(conn, len(accounts), txn_count)

    # Auto-apply category rules from TOML
    from simledge.categorize import apply_rules, detect_cc_payments, load_rules
    from simledge.config import RULES_PATH

    rules = load_rules(RULES_PATH)
    if rules:
        cat_count = apply_rules(rules, conn)
        if cat_count and not quiet:
            print(f"Auto-categorized {cat_count} transactions")

    cc_count = detect_cc_payments(conn)
    if cc_count and not quiet:
        print(f"Detected {cc_count} credit card payment transfers")

    if not quiet:
        print(f"Synced {len(accounts)} accounts, {txn_count} transactions")
    conn.close()
    return {"accounts": len(accounts), "transactions": txn_count, "status": "success"}
