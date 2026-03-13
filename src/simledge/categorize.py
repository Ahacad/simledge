"""Category rule engine — TOML-based regex/keyword matching for transactions."""

import os
import re
import tomllib
from datetime import date, timedelta

from simledge.log import setup_logging

log = setup_logging("simledge.categorize")

DEFAULT_RULES = [
    # Groceries (top-level)
    {
        "pattern": "SAFEWAY|TRADER JOE|WHOLE FOODS|QFC|KROGER|ALDI|COSTCO|WALMART.*GROCERY|FRED MEYER|WINCO|PUBLIX|H-?E-?B\\b|WEGMANS|SPROUTS",
        "category": "Groceries",
        "priority": 0,
    },
    # Food
    {
        "pattern": "DOORDASH|GRUBHUB|UBER EATS|CHIPOTLE|MCDONALD|STARBUCKS|SUBWAY|TACO BELL|CHICK-FIL|PANDA EXPRESS|PANERA|WENDY|BURGER KING|DOMINO|PIZZA HUT|FIVE GUYS|SHAKE SHACK|IN.N.OUT|POPEYES|WINGSTOP|JACK IN THE BOX",
        "category": "Food:Dining",
        "priority": 0,
    },
    {
        "pattern": "STARBUCKS|DUTCH BROS|PEET.*COFFEE|DUNKIN",
        "category": "Food:Coffee",
        "priority": 5,
    },
    # Housing
    {
        "pattern": "\\bBILT\\b|\\bRENT\\b|LEASE.*PAY",
        "category": "Housing:Rent",
        "priority": 0,
    },
    {
        "pattern": "COMCAST|XFINITY|SPECTRUM|AT.T.*INTERNET|VERIZON.*FIOS|CENTURYLINK|T-MOBILE.*HOME",
        "category": "Housing:Internet",
        "priority": 0,
    },
    {
        "pattern": "T-MOBILE|VERIZON.*WIRELESS|AT.T.*WIRELESS|MINT MOBILE|VISIBLE|GOOGLE FI",
        "category": "Housing:Phone",
        "priority": 0,
    },
    {
        "pattern": "\\bPSE\\b|PUGET SOUND|PG&E|PG\\&E|DUKE ENERGY|CON\\s*ED|NATIONAL GRID|SEATTLE CITY LIGHT",
        "category": "Housing:Utilities",
        "priority": 0,
    },
    # Transport
    {
        "pattern": "\\bSHELL\\b|CHEVRON|\\bARCO\\b|\\b76\\b|EXXON|\\bMOBIL\\b|\\bBP\\b|SUNOCO|CIRCLE K.*FUEL|COSTCO.*GAS",
        "category": "Transport:Gas",
        "priority": 0,
    },
    {"pattern": "UBER(?!.*EATS)|LYFT", "category": "Transport:Rideshare", "priority": 5},
    {
        "pattern": "GEICO|STATE FARM|ALLSTATE|PROGRESSIVE|USAA.*AUTO|LIBERTY MUTUAL",
        "category": "Transport:Auto Insurance",
        "priority": 0,
    },
    {
        "pattern": "SP\\+.*PARKING|PARKMO|PARK.*METER|IMPARK|LAZ PARKING",
        "category": "Transport:Parking",
        "priority": 0,
    },
    # Shopping
    {"pattern": "AMAZON\\.COM|AMZN", "category": "Shopping:General", "priority": 0},
    {"pattern": "TARGET|WALMART(?!.*GROCERY)", "category": "Shopping:General", "priority": 0},
    {
        "pattern": "BEST BUY|APPLE\\.COM|NEWEGG|B.H PHOTO|MICRO CENTER",
        "category": "Shopping:Electronics",
        "priority": 0,
    },
    {
        "pattern": "NORDSTROM|UNIQLO|H&M|H\\s*&\\s*M|ZARA|\\bGAP\\b|OLD NAVY|\\bNIKE\\b|\\bREI\\b|PATAGONIA",
        "category": "Shopping:Clothing",
        "priority": 0,
    },
    {
        "pattern": "IKEA|HOME DEPOT|LOWES|BED BATH|WAYFAIR|POTTERY BARN|CRATE.BARREL",
        "category": "Shopping:Home",
        "priority": 0,
    },
    # Entertainment
    {
        "pattern": "NETFLIX|HULU|DISNEY.*PLUS|HBO|PARAMOUNT|PEACOCK|APPLE.*TV|YOUTUBE.*PREMIUM|SPOTIFY|APPLE.*MUSIC|CRUNCHYROLL",
        "category": "Entertainment:Streaming",
        "priority": 0,
    },
    {
        "pattern": "STEAM|PLAYSTATION|XBOX|NINTENDO|EPIC GAMES|RIOT GAMES|BLIZZARD",
        "category": "Entertainment:Games",
        "priority": 0,
    },
    {
        "pattern": "TICKETMASTER|STUBHUB|LIVE NATION|AMC|REGAL|CINEMARK|FANDANGO",
        "category": "Entertainment:Events",
        "priority": 0,
    },
    # Health
    {"pattern": "CVS|WALGREENS|RITE AID|PHARMACY", "category": "Health:Pharmacy", "priority": 0},
    {
        "pattern": "PLANET FITNESS|ANYTIME FITNESS|24 HOUR|GOLD.S GYM|EQUINOX|LA FITNESS|YMCA|CRUNCH",
        "category": "Health:Gym",
        "priority": 0,
    },
    # Travel
    {
        "pattern": "UNITED AIR|DELTA AIR|AMERICAN AIR|SOUTHWEST|ALASKA AIR|JETBLUE|SPIRIT AIR|FRONTIER AIR",
        "category": "Travel:Flights",
        "priority": 0,
    },
    {
        "pattern": "MARRIOTT|HILTON|HYATT|IHG|BEST WESTERN|AIRBNB|VRBO|BOOKING\\.COM",
        "category": "Travel:Hotels",
        "priority": 0,
    },
    # Personal
    {
        "pattern": "GREAT CLIPS|SUPERCUTS|SPORT CLIPS|BARBER",
        "category": "Personal:Haircut",
        "priority": 0,
    },
    # Finance
    {"pattern": "ATM.*WITHDRAW|ATM.*W/D", "category": "Finance:ATM", "priority": 0},
    {
        "pattern": "INTEREST CHARGE|FINANCE CHARGE|LATE FEE|ANNUAL FEE|MONTHLY FEE|SERVICE FEE",
        "category": "Finance:Fees",
        "priority": 0,
    },
    {"pattern": "INTEREST PAID|INTEREST EARN|APY", "category": "Finance:Interest", "priority": 0},
    # Income
    {
        "pattern": "PAYROLL|DIRECT DEP|DIR DEP|ACH.*SALARY|EMPLOYER",
        "category": "Income:Salary",
        "priority": 0,
    },
    {"pattern": "REFUND|\\bRETURN\\b|CREDIT ADJ", "category": "Income:Refund", "priority": 0},
    # Transfer — credit card payments
    {
        "pattern": "AUTOPAY|AUTO\\s*PAY|PAYMENT\\s*-?\\s*THANK\\s*YOU|BILL\\s+PAY",
        "category": "Transfer:Credit Card Payment",
        "priority": 10,
    },
    # Transfer — general
    {
        "pattern": "TRANSFER|XFER|ZELLE|VENMO|PAYPAL.*TRANSFER|CASH APP",
        "category": "Transfer",
        "priority": 0,
    },
]


def init_rules(path):
    """Write default rules to path. Does nothing if file already exists."""
    if os.path.exists(path):
        log.debug("rules file already exists at %s, skipping init", path)
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_rules(path, DEFAULT_RULES)
    log.info("initialized default rules at %s", path)
    return True


def load_rules(path):
    """Load rules from a TOML file. Returns list of dicts, empty if file missing."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        log.debug("rules file not found at %s", path)
        return []

    raw = data.get("rules", [])
    rules = []
    for r in raw:
        if "pattern" not in r or "category" not in r:
            continue
        rules.append(
            {
                "pattern": r["pattern"],
                "category": r["category"],
                "priority": r.get("priority", 0),
            }
        )
    return rules


def save_rules(path, rules):
    """Write rules list to a TOML file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# SimpLedge category rules",
        "# Edit this file to customize how transactions are categorized.",
        "# Each rule matches transaction descriptions against a regex pattern.",
        '# Categories use colon-delimited hierarchy: "Parent:Child"',
        "# Higher priority rules match first. Regex falls back to substring match.",
        "",
    ]
    for r in rules:
        lines.append("[[rules]]")
        lines.append(f'pattern = "{_escape_toml(r["pattern"])}"')
        lines.append(f'category = "{_escape_toml(r["category"])}"')
        priority = r.get("priority", 0)
        if priority != 0:
            lines.append(f"priority = {priority}")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))


def _escape_toml(s):
    """Escape backslashes and double quotes for TOML string values."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def apply_rules(rules, conn, dry_run=False):
    """Apply rules to uncategorized transactions. Returns count matched."""
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    uncategorized = conn.execute(
        "SELECT id, description FROM transactions WHERE category IS NULL"
    ).fetchall()

    count = 0
    for txn_id, description in uncategorized:
        for rule in sorted_rules:
            pattern = rule["pattern"]
            category = rule["category"]
            try:
                if re.search(pattern, description, re.IGNORECASE):
                    if not dry_run:
                        conn.execute(
                            "UPDATE transactions SET category = ?, category_source = 'rule'"
                            " WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break
            except re.error:
                if pattern.upper() in description.upper():
                    if not dry_run:
                        conn.execute(
                            "UPDATE transactions SET category = ?, category_source = 'rule'"
                            " WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break

    if not dry_run:
        conn.commit()
    log.info("categorized %d transactions (dry_run=%s)", count, dry_run)
    return count


CC_PAYMENT_PATTERNS = re.compile(
    r"AUTOPAY|AUTO\s*PAY|PAYMENT\s*-?\s*THANK\s*YOU|ONLINE\s+PAYMENT"
    r"|MOBILE\s+PAYMENT|AUTOMATIC\s+PAYMENT|PAYMENT\s+RECEIVED"
    r"|BILL\s+PAY|ACH\s+PAYMENT|CARD\s+PAYMENT|PAYMENT\s+TO\s+.*CARD",
    re.IGNORECASE,
)

CC_ACCOUNT_TYPES = {"credit", "credit_card"}
_KNOWN_NON_CC_TYPES = {"checking", "savings"}

# How many days apart the two sides of a CC payment can post.
# Banks often post the checking debit and the credit card payment credit
# on different days (e.g., checking posts Monday, CC posts Wednesday).
CC_PAYMENT_DATE_WINDOW = 5


def detect_cc_payments(conn, verbose=False):
    """Detect credit card payment transfer pairs and categorize them.

    Matching strategy (all conditions must hold for a pair):
      1. Same absolute amount (rounded to cents).
      2. Posted dates within CC_PAYMENT_DATE_WINDOW days of each other.
         Banks don't always post both sides on the same day — the checking
         debit and CC payment credit can land days apart.
      3. Opposite signs (one negative outflow, one positive inflow).
      4. Exactly one side is a credit card account. This prevents matching
         two checking-to-checking transfers or two CC-to-CC movements.
      5. At least one side's description matches CC_PAYMENT_PATTERNS
         (e.g., "AUTOPAY", "PAYMENT THANK YOU"). This gates the match so
         we don't pair unrelated same-amount transactions that happen to
         cross a CC boundary.

    Transactions already categorized are left untouched. Matched
    uncategorized transactions are tagged "Transfer:Credit Card Payment".
    """
    rows = conn.execute(
        "SELECT t.id, t.posted, t.amount, t.description, t.account_id, a.type, t.category"
        " FROM transactions t"
        " JOIN accounts a ON t.account_id = a.id"
    ).fetchall()

    if verbose:
        type_counts = {}
        for *_, acct_type, _ in rows:
            type_counts[acct_type or "NULL"] = type_counts.get(acct_type or "NULL", 0) + 1
        print(f"  Accounts by type: {type_counts}")
        print(f"  Total transactions: {len(rows)}")

    # Group by absolute amount only. Date matching happens per-pair below,
    # because the two sides can post on different days.
    from collections import defaultdict

    by_amount = defaultdict(list)
    for tid, posted, amount, desc, _acct_id, acct_type, category in rows:
        by_amount[round(abs(amount), 2)].append(
            {
                "id": tid,
                "posted": date.fromisoformat(posted) if isinstance(posted, str) else posted,
                "amount": amount,
                "description": desc,
                "type": acct_type,
                "category": category,
            }
        )

    count = 0
    tagged = set()
    pairs_found = 0
    rejected_no_cc = 0
    rejected_date = 0
    window = timedelta(days=CC_PAYMENT_DATE_WINDOW)

    for abs_amt, txns in by_amount.items():
        if len(txns) < 2 or abs_amt == 0:
            continue

        negatives = [t for t in txns if t["amount"] < 0]
        positives = [t for t in txns if t["amount"] > 0]

        for neg in negatives:
            for pos in positives:
                pairs_found += 1

                # Date gate: both sides must post within the window
                if abs(neg["posted"] - pos["posted"]) > window:
                    rejected_date += 1
                    continue

                # Account type gate: exactly one side must be a CC account
                neg_is_cc = neg["type"] in CC_ACCOUNT_TYPES
                pos_is_cc = pos["type"] in CC_ACCOUNT_TYPES

                # Account type + description gate:
                # - Clear case: one side is explicitly CC, the other isn't.
                #   No description check needed — account types are unambiguous.
                # - Ambiguous case: one side has NULL type. Require description
                #   match to confirm it's actually a CC payment.
                # - Two non-CC accounts: never match.
                if neg_is_cc ^ pos_is_cc:
                    pass  # clear signal: one CC, one non-CC
                elif (
                    neg["type"] in _KNOWN_NON_CC_TYPES
                    and pos["type"] is None
                    and (
                        CC_PAYMENT_PATTERNS.search(neg["description"])
                        or CC_PAYMENT_PATTERNS.search(pos["description"])
                    )
                ):
                    pass  # known non-CC + unknown type, description confirms CC payment
                else:
                    rejected_no_cc += 1
                    continue

                for t in (neg, pos):
                    if t["id"] not in tagged and t["category"] is None:
                        conn.execute(
                            "UPDATE transactions SET category = ?,"
                            " category_source = 'cc_detect' WHERE id = ?",
                            ("Transfer:Credit Card Payment", t["id"]),
                        )
                        tagged.add(t["id"])
                        count += 1

    if verbose:
        print(f"  Amount-matched pairs evaluated: {pairs_found}")
        print(f"  Rejected (dates too far apart): {rejected_date}")
        print(f"  Rejected (no CC account on exactly one side): {rejected_no_cc}")
        print(f"  Tagged: {count}")

    conn.commit()
    log.info("detected %d credit card payment transactions", count)
    return count
