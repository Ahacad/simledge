"""Category rule engine — TOML-based regex/keyword matching for transactions."""

import os
import re
import tomllib

from simledge.log import setup_logging

log = setup_logging("simledge.categorize")

DEFAULT_RULES = [
    # Groceries (top-level)
    {
        "pattern": "SAFEWAY|TRADER JOE|WHOLE FOODS|QFC|KROGER|ALDI|COSTCO|WALMART.*GROCERY|FRED MEYER|WINCO|PUBLIX|H.E.B|WEGMANS|SPROUTS",
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
        "pattern": "BILT|RENT|LEASE.*PAY",
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
        "pattern": "PSE|PUGET SOUND|PG.E|DUKE ENERGY|CON.?ED|NATIONAL GRID|SEATTLE CITY LIGHT",
        "category": "Housing:Utilities",
        "priority": 0,
    },
    # Transport
    {
        "pattern": "SHELL|CHEVRON|ARCO|76|EXXON|MOBIL|BP|SUNOCO|CIRCLE K.*FUEL|COSTCO.*GAS",
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
        "pattern": "SP.*PARKING|PARKMO|METER|IMPARK|LAZ PARKING",
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
        "pattern": "NORDSTROM|UNIQLO|H.M|ZARA|GAP|OLD NAVY|NIKE|REI|PATAGONIA",
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
    {"pattern": "REFUND|RETURN|CREDIT ADJ", "category": "Income:Refund", "priority": 0},
    # Transfer
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
                            "UPDATE transactions SET category = ? WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break
            except re.error:
                if pattern.upper() in description.upper():
                    if not dry_run:
                        conn.execute(
                            "UPDATE transactions SET category = ? WHERE id = ?",
                            (category, txn_id),
                        )
                    count += 1
                    break

    if not dry_run:
        conn.commit()
    log.info("categorized %d transactions (dry_run=%s)", count, dry_run)
    return count
