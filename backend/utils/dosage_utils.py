"""
MedPak AI — Dosage Field Humanizer

The pharmapedia database stores dosage rows with terse clinical codes that
mean nothing to patients:

    FREQ   "24 hourly"   → how often to take it
    ROUTE  "PO"          → how it enters the body
    SINGLE "30 (30)"     → maximum single dose in mg

These helpers expand them into plain language. Unknown values pass through
unchanged so no information is ever lost.
"""

from __future__ import annotations

import re


# ── Frequency ────────────────────────────────────────────────────────────────

FREQ_MAP = {
    "24 HOURLY": "Once daily",
    "24HOURLY": "Once daily",
    "12 HOURLY": "Every 12 hours",
    "8 HOURLY": "Every 8 hours",
    "6 HOURLY": "Every 6 hours",
    "4 HOURLY": "Every 4 hours",
    "3 HOURLY": "Every 3 hours",
    "2 HOURLY": "Every 2 hours",
    "48 HOURLY": "Every other day",
    "72 HOURLY": "Every 3 days",
    "WEEKLY": "Once a week",
    "ONCE": "Single dose",
    "ONCE ONLY": "Single dose",
    "STAT": "Immediately (single dose)",
    "OD": "Once daily",
    "BD": "Twice daily",
    "BID": "Twice daily",
    "TDS": "Three times daily",
    "TID": "Three times daily",
    "QID": "Four times daily",
    "QDS": "Four times daily",
    "Q4H": "Every 4 hours",
    "Q6H": "Every 6 hours",
    "Q8H": "Every 8 hours",
    "Q12H": "Every 12 hours",
    "HS": "At bedtime",
    "PRN": "As needed",
    "AS REQUIRED": "As needed",
    "AS RECOMMENDED": "As recommended by your doctor",
    "AS RECOMMENDED.": "As recommended by your doctor",
}


# ── Route ────────────────────────────────────────────────────────────────────

ROUTE_MAP = {
    "PO": "By mouth (swallow)",
    "ORAL": "By mouth (swallow)",
    "IV": "Injection into a vein",
    "IV INF": "Drip into a vein (infusion)",
    "IVINF": "Drip into a vein (infusion)",
    "IM": "Injection into a muscle",
    "SC": "Injection under the skin",
    "S/C": "Injection under the skin",
    "SQ": "Injection under the skin",
    "TOPICAL": "Apply on the skin",
    "OPHTHALMIC": "Into the eye",
    "OTIC": "Into the ear",
    "NASAL": "Into the nose",
    "INHALATION": "Inhaled (breathed in)",
    "SLOW IV": "Slow injection into a vein",
    "PR": "Into the rectum",
    "RECTAL": "Into the rectum",
    "SL": "Under the tongue",
    "SUBLINGUAL": "Under the tongue",
    "BUCCAL": "Against the cheek (inside mouth)",
    "VAGINAL": "Into the vagina",
    "INTRATHECAL": "Injection into the spine",
    "EPIDURAL": "Injection into the lower back",
    "INTRAVENOUS": "Injection into a vein",
    "INTRAMUSCULAR": "Injection into a muscle",
    "SUBCUTANEOUS": "Injection under the skin",
    "TRANSDERMAL": "Patch on the skin",
}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


def humanize_freq(value: str) -> str:
    """'24 hourly' → 'Once daily'; unknown patterns pass through cleaned."""
    raw = (value or "").strip()
    if not raw:
        return ""
    key = _norm(raw)
    if key in FREQ_MAP:
        return FREQ_MAP[key]
    m = re.fullmatch(r"(\d+)\s*HOURLY", key)
    if m:
        return f"Every {m.group(1)} hours"
    # Mixed-case originals like "As recommended." keep their own wording
    return raw.rstrip(".").strip() or raw


def humanize_route(value: str) -> str:
    """'PO' → 'By mouth (swallow)'; combos like 'PO/IV' → 'By mouth or injection…'."""
    raw = (value or "").strip()
    if not raw:
        return ""
    parts = [p.strip() for p in re.split(r"[/,+]", raw) if p.strip()]
    translated = [ROUTE_MAP.get(_norm(p), p.strip()) for p in parts]
    if not translated:
        return raw
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered = [t for t in translated if not (t.lower() in seen or seen.add(t.lower()))]
    return " or ".join(ordered)


def humanize_single(value: str) -> str:
    """'30 (30)' → 'Max single dose: 30 mg' (maximum amount per single dose)."""
    raw = (value or "").strip()
    if not raw:
        return ""
    m = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not m:
        return raw
    val = float(m.group(1))
    val = int(val) if val == int(val) else val
    return f"Max single dose: {val} mg"


def humanize_dosage_rows(rows: list[dict]) -> list[dict]:
    """
    Add human-readable twins of the coded dosage fields to every row.
    Raw values are kept untouched; new keys: freq_human, route_human, single_human.
    """
    for r in rows or []:
        r["freq_human"] = humanize_freq(r.get("FREQ") or "")
        r["route_human"] = humanize_route(r.get("ROUTE") or "")
        r["single_human"] = humanize_single(r.get("SINGLE") or "")
    return rows or []
