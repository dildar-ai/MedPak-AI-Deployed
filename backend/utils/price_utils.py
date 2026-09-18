"""
MedPak AI — Price Utility Functions
Helpers for parsing pack sizes, calculating per-unit costs, and savings.
"""

import re


def parse_pack_quantity(packing: str) -> int:
    """
    Extract the numeric unit count from a packing string.

    Examples:
        "10's"        -> 10
        "100ml"       -> 100
        "30 Tablets"  -> 30
        "1 Strip"     -> 1
        "6x10's"      -> 60  (sub-packs x units)
        "3 Blister"   -> 3
        ""            -> 1   (fallback)

    Returns 1 if parsing fails — prevents division by zero.
    """
    if not packing:
        return 1

    p = packing.strip().lower()

    # Multi-pack: "6x10's", "3 x 10", "2x100ml"
    m = re.match(r"(\d+)\s*x\s*(\d+)", p)
    if m:
        return int(m.group(1)) * int(m.group(2))

    # Leading number: "10's", "100ml", "30 tablets", "5 ampoules"
    m = re.match(r"(\d+)", p)
    if m:
        val = int(m.group(1))
        return val if val > 0 else 1

    return 1


def parse_strength_mg(strength: str) -> float | None:
    """
    Parse a DB strength string into milligrams (used to prefer scraped
    listings that match the variant being viewed).

    "20 MG" -> 20.0, "0.5mg" -> 0.5, "500 MCG" -> 0.5, "1 G" -> 1000.0
    Multi-part strengths ("500 MG 125 MG") return the FIRST number.
    """
    if not strength:
        return None
    s = str(strength).strip().upper()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(MCG|MG|G|GM)?\b", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2) or "MG"
    if unit == "MCG":
        return val / 1000
    if unit in ("G", "GM"):
        return val * 1000
    return val


def calculate_savings(current_price: float, alt_price: float) -> dict:
    """
    Calculate how much a user saves by switching to an alternative.

    Returns:
        {
            "save_pkr": float,     # Amount saved (positive = cheaper)
            "save_pct": float,     # Percentage saved (positive = cheaper)
            "is_cheaper": bool     # True if alternative costs less
        }
    """
    if not current_price or current_price <= 0:
        return {"save_pkr": 0.0, "save_pct": 0.0, "is_cheaper": False}
    if not alt_price or alt_price <= 0:
        return {"save_pkr": 0.0, "save_pct": 0.0, "is_cheaper": False}

    save_pkr = round(current_price - alt_price, 2)
    save_pct = round((save_pkr / current_price) * 100, 1)

    return {
        "save_pkr": save_pkr,
        "save_pct": save_pct,
        "is_cheaper": alt_price < current_price,
    }


def format_price_pkr(price: float) -> str:
    """Format a float price as 'Rs. 123.50' string."""
    if price is None or price <= 0:
        return "N/A"
    if price == int(price):
        return f"Rs. {int(price)}"
    return f"Rs. {price:.2f}"
