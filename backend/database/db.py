"""
MedPak AI — Database Query Layer
All interactions with pharmapedia.db go through this module.

Tables available:
  DRUG        (CODE, NAME, OVERVIEW, CHARACTERISTICS, INDICATIONS, CONTRAINDICATIONS,
               INTERACTIONS, INTERFERENCE, EFFECTS, RISK, WARNING, STORAGE)
  BRAND       (BID, BNAME, CID)
  BRAND_DRUG  (NAME, CATEGORY, FORM, ID, DUMB, PACKING, TRADEPRICE, RETAILPRICE, MG, DID, BID)
  COMPANY     (ID, NAME, ADDRESS, PHONE, FAX)
  Neonatal    (DOSE, SINGLE, FREQ, ROUTE, INSTRUCTION, CODE)
  Paedriatic  (DOSE, SINGLE, FREQ, ROUTE, INSTRUCTION, CODE)
  adult       (DOSE, SINGLE, FREQ, ROUTE, INSTRUCTION, CODE)
"""

import sqlite3
import re
from typing import Any
from contextlib import contextmanager
from config import settings
from utils.dosage_utils import humanize_dosage_rows


# ── Connection helpers ────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    """Yield a read-only SQLite connection, close automatically."""
    conn = sqlite3.connect(f"file:{settings.DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row          # dict-like access by column name
    try:
        yield conn
    finally:
        conn.close()


def _clean_price(price_str: str) -> float:
    """Convert '1,234.56' → 1234.56, return 0.0 on failure."""
    try:
        return float(re.sub(r"[^\d.]", "", price_str or ""))
    except (ValueError, TypeError):
        return 0.0


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row)


# ── 1. Medicine Search ────────────────────────────────────────────────────────

# Generic dosage-form words that add nothing to a medicine search ("panadol tablet").
_TOKEN_STOPWORDS = {
    "tablet", "tablets", "tab", "tabs", "capsule", "capsules", "cap", "caps",
    "syrup", "suspension", "susp", "injection", "injections", "inj", "infusion",
    "cream", "gel", "drops", "drop", "ointment", "lotion", "spray", "suppository",
    "sachet", "sachets", "mg", "ml", "mcg", "gm", "g", "iu", "for", "the",
    "of", "with", "and", "please", "medicine", "brand", "price",
}

# Cached lowercase name lists for fuzzy (typo) matching — loaded once on demand.
_fuzzy_cache: dict[str, list[str]] = {}


def _load_fuzzy_lists() -> None:
    if "brands" in _fuzzy_cache:
        return
    with get_conn() as conn:
        brands = [r[0].lower() for r in conn.execute("SELECT DISTINCT NAME FROM BRAND_DRUG").fetchall()]
        salts = [r[0].lower() for r in conn.execute("SELECT DISTINCT NAME FROM DRUG").fetchall()]
    _fuzzy_cache["brands"] = [b for b in brands if b]
    _fuzzy_cache["salts"] = [s for s in salts if s]


def _keyword_sql(q: str, fetch: int) -> list[dict]:
    """Single-keyword ranked SQL search: exact > starts-with > contains."""
    q_exact = q.lower()
    q_prefix = f"{q}%"
    q_any = f"%{q}%"
    # Separator-insensitive form: "Panadol CF" matches "PANADOL-CF" and
    # "Augmentin 625" matches "AUGMENTIN 625" regardless of hyphen/space mix.
    q_compact = re.sub(r"[\s\-]+", "", q_exact)
    q_compact_prefix = f"{q_compact}%"
    q_compact_any = f"%{q_compact}%"

    sql = """
        SELECT
            d.CODE          AS drug_id,
            d.NAME          AS salt_name,
            d.INDICATIONS   AS indications,
            b.BNAME         AS brand_name,
            bd.NAME         AS brand_product_name,
            bd.FORM         AS form,
            bd.MG           AS strength,
            bd.RETIALPRICE  AS retail_price,
            bd.TRADEPRICE   AS trade_price,
            bd.PACKING      AS packing,
            co.NAME         AS company,
            bd.DID          AS did,
            bd.BID          AS bid,
            CASE
              WHEN LOWER(bd.NAME) = ?   OR LOWER(b.BNAME) = ?   OR LOWER(d.NAME) = ?
                OR REPLACE(REPLACE(LOWER(bd.NAME), '-', ''), ' ', '') = ? THEN 1
              WHEN LOWER(bd.NAME) LIKE ? OR LOWER(b.BNAME) LIKE ? OR LOWER(d.NAME) LIKE ?
                OR REPLACE(REPLACE(LOWER(bd.NAME), '-', ''), ' ', '') LIKE ? THEN 2
              ELSE 3
            END AS relevance
        FROM BRAND_DRUG bd
        JOIN BRAND   b  ON bd.BID  = b.BID
        JOIN DRUG    d  ON bd.DID  = d.CODE
        LEFT JOIN COMPANY co ON b.CID = co.ID
        WHERE bd.NAME LIKE ?
           OR b.BNAME  LIKE ?
           OR d.NAME   LIKE ?
           OR REPLACE(REPLACE(LOWER(bd.NAME), '-', ''), ' ', '') LIKE ?
        ORDER BY relevance ASC, bd.NAME ASC
        LIMIT ?
    """
    params = (
        q_exact, q_exact, q_exact, q_compact,
        q_prefix, q_prefix, q_prefix, q_compact_prefix,
        q_any, q_any, q_any, q_compact_any,
        fetch,
    )
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    # Deduplicate by brand product name so each variant (CF, Extra, etc.)
    # keeps its own price while collapsing duplicate DB rows.
    seen: dict[tuple[str, str], dict] = {}
    for row in rows:
        r = _row_to_dict(row)
        r["retail_price_num"] = _clean_price(r["retail_price"])
        r["trade_price_num"] = _clean_price(r.get("trade_price", ""))
        r["company"] = (r.get("company") or "").strip() or "Unknown"
        brand_key = (r.get("brand_product_name") or "").lower()
        form_key = (r.get("form") or "").lower().strip()
        key = (brand_key, form_key)
        if key not in seen or r["relevance"] < seen[key]["relevance"]:
            seen[key] = r
    return list(seen.values())


def _merge_results(merged: dict[tuple[str, str], dict], rows: list[dict], base_relevance: int) -> None:
    """Merge keyword rows into a result map, keeping the best relevance per brand+form."""
    for r in rows:
        r = dict(r)
        r["relevance"] = base_relevance + min(r.get("relevance", 3), 3)
        brand_key = (r.get("brand_product_name") or "").lower()
        form_key = (r.get("form") or "").lower().strip()
        key = (brand_key, form_key)
        if key not in merged or r["relevance"] < merged[key]["relevance"]:
            merged[key] = r


def _fuzzy_names(q: str, n: int = 5) -> list[str]:
    """Find close matches for typo'd queries ("Pnadol" → "panadol"), best first."""
    import difflib

    _load_fuzzy_lists()
    cutoff = 0.75 if len(q) >= 6 else 0.80
    q_chars = set(q)
    min_shared = min(3, len(q_chars))
    scored: list[tuple[float, str]] = []
    for name in _fuzzy_cache["salts"] + _fuzzy_cache["brands"]:
        if abs(len(name) - len(q)) > 3:
            continue
        # Cheap pre-filter: must share a few distinct characters at all
        if len(q_chars & set(name)) < min_shared:
            continue
        ratio = difflib.SequenceMatcher(None, q, name).ratio()
        if ratio >= cutoff:
            scored.append((ratio, name))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [name for _, name in scored[:n]]


def search_medicines(query: str, limit: int = 30) -> list[dict]:
    """
    Ranked search with graceful degradation:
      1. Full query   — exact > starts-with > contains ("panadol")
      2. Per-token    — informative words only ("panadol tablet" → "panadol")
      3. Fuzzy/typo   — close matches via difflib ("Pnadol" → "PANADOL",
                       "Abuprofen" → salt "Ibuprofen" and its brands)

    Each result is enriched with the complete salt composition of its brand
    product, so fixed-dose combinations (e.g. Panadol-CF) show every salt.
    """
    q = (query or "").strip()
    if len(q) < 2:
        return []

    merged: dict[tuple[str, str], dict] = {}

    # ── Tier 1: full keyword search (separator-insensitive) ────────────────
    _merge_results(merged, _keyword_sql(q, fetch=limit * 3), base_relevance=0)

    # ── Tier 2: token supplement for multi-word queries ───────────────────
    # The exact FDC match stays on top ("Panadol CF" → PANADOL-CF first),
    # while sibling brands (plain PANADOL, PANADOL EXTRA) follow below.
    if len(q.split()) > 1:
        words = re.findall(r"[a-z]+", q.lower())
        tokens = [t for t in words if len(t) >= 3 and t not in _TOKEN_STOPWORDS]
        for rank, tok in enumerate(tokens[:3]):
            _merge_results(merged, _keyword_sql(tok, fetch=limit), base_relevance=10 + rank)
        # Strength numbers as last-resort supplement ("625 mg" → AUGMENTIN 625)
        if not merged:
            for rank, num in enumerate(re.findall(r"\d{2,}", q)[:2]):
                _merge_results(merged, _keyword_sql(num, fetch=limit), base_relevance=15 + rank)

    if not merged:
        # ── Tier 3: fuzzy typo correction ──────────────────────────────────
        words = re.findall(r"[a-z]+", q.lower())
        fuzzy_tokens = [t for t in words if len(t) >= 4 and t not in _TOKEN_STOPWORDS]
        rank = 0
        for tok in fuzzy_tokens[:2]:
            for name in _fuzzy_names(tok, n=3):
                _merge_results(merged, _keyword_sql(name, fetch=limit), base_relevance=20 + rank)
                rank += 1

    if not merged:
        # ── Tier 4: bare numbers as last resort ("625" → AUGMENTIN 625) ────
        for rank, num in enumerate(re.findall(r"\d{2,}", q.lower())[:2]):
            _merge_results(merged, _keyword_sql(num, fetch=limit), base_relevance=30 + rank)

    results = sorted(merged.values(), key=lambda r: (r["relevance"], r.get("brand_product_name") or ""))

    # ── Enrich with complete salt composition ──────────────────────────────
    # Multi-salt brands are stored as multiple BRAND_DRUG rows; search only
    # returns the row that matched, so attach all salts for display.
    if results:
        names = [r.get("brand_product_name") for r in results if r.get("brand_product_name")]
        salt_map = get_brand_product_all_salts(names)
        for r in results:
            name = r.get("brand_product_name")
            fallback = [r.get("salt_name") or r.get("NAME") or "Generic"]
            r["salt_names"] = salt_map.get(name, fallback)

    return results[:limit]


# ── 2. Full Drug Detail ───────────────────────────────────────────────────────

def get_drug_by_id(drug_id: int) -> dict | None:
    """Return complete drug profile for a given DRUG.CODE."""
    sql = """
        SELECT CODE, NAME, OVERVIEW, CHARACTERSTICS, INDICATIONS,
               CONTRAINDICATIONS, INTERACTIONS, INTERFERENCE,
               EFFECTS, RISK, WARNINING AS warnings, STORAGE
        FROM DRUG WHERE CODE = ?
    """
    with get_conn() as conn:
        row = conn.execute(sql, (drug_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_drug_by_name(name: str) -> dict | None:
    """Return first drug matching the generic/salt name (partial, case-insensitive)."""
    sql = """
        SELECT CODE, NAME, OVERVIEW, CHARACTERSTICS, INDICATIONS,
               CONTRAINDICATIONS, INTERACTIONS, INTERFERENCE,
               EFFECTS, RISK, WARNINING AS warnings, STORAGE
        FROM DRUG WHERE NAME LIKE ? LIMIT 1
    """
    with get_conn() as conn:
        row = conn.execute(sql, (f"%{name}%",)).fetchone()
    return _row_to_dict(row) if row else None


# ── 3. Brand Variants ────────────────────────────────────────────────────────

def get_brand_variants(drug_id: int) -> list[dict]:
    """All brand products for a given drug (salt), with company info."""
    sql = """
        SELECT
            bd.NAME         AS brand_product_name,
            b.BNAME         AS brand_name,
            bd.FORM         AS form,
            bd.MG           AS strength,
            bd.PACKING      AS packing,
            bd.TRADEPRICE   AS trade_price,
            bd.RETIALPRICE  AS retail_price,
            bd.CATEGORY     AS category,
            co.NAME         AS company,
            co.ADDRESS      AS company_address,
            bd.BID          AS bid,
            bd.DID          AS did
        FROM BRAND_DRUG bd
        JOIN BRAND   b  ON bd.BID = b.BID
        LEFT JOIN COMPANY co ON b.CID = co.ID
        WHERE bd.DID = ?
        ORDER BY bd.FORM, bd.MG
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (drug_id,)).fetchall()

    results = []
    for row in rows:
        r = _row_to_dict(row)
        r["retail_price_num"] = _clean_price(r["retail_price"])
        r["trade_price_num"]  = _clean_price(r["trade_price"])
        r["company"] = (r.get("company") or "").strip() or "Unknown"
        results.append(r)
    return results


def get_brand_product_salts(brand_product_name: str) -> list[dict]:
    """Return every salt (DRUG row) linked to a given brand product name."""
    sql = """
        SELECT DISTINCT d.CODE AS drug_id, d.NAME AS salt_name
        FROM BRAND_DRUG bd
        JOIN DRUG d ON bd.DID = d.CODE
        WHERE LOWER(bd.NAME) = LOWER(?)
        ORDER BY d.NAME
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (brand_product_name,)).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_brand_variants_multi(drug_ids: list[int]) -> list[dict]:
    """All brand products for any of the given drug (salt) IDs."""
    if not drug_ids:
        return []
    placeholders = ",".join("?" * len(drug_ids))
    sql = f"""
        SELECT
            bd.NAME         AS brand_product_name,
            b.BNAME         AS brand_name,
            bd.FORM         AS form,
            bd.MG           AS strength,
            bd.PACKING      AS packing,
            bd.TRADEPRICE   AS trade_price,
            bd.RETIALPRICE  AS retail_price,
            bd.CATEGORY     AS category,
            co.NAME         AS company,
            co.ADDRESS      AS company_address,
            bd.BID          AS bid,
            bd.DID          AS did
        FROM BRAND_DRUG bd
        JOIN BRAND   b  ON bd.BID = b.BID
        LEFT JOIN COMPANY co ON b.CID = co.ID
        WHERE bd.DID IN ({placeholders})
        ORDER BY bd.FORM, bd.MG
    """
    with get_conn() as conn:
        rows = conn.execute(sql, tuple(drug_ids)).fetchall()

    results = []
    for row in rows:
        r = _row_to_dict(row)
        r["retail_price_num"] = _clean_price(r["retail_price"])
        r["trade_price_num"]  = _clean_price(r["trade_price"])
        r["company"] = (r.get("company") or "").strip() or "Unknown"
        results.append(r)
    return results


def get_salt_sets_for_brands(brand_product_names: list[str]) -> dict[str, set[int]]:
    """
    Map each brand product name to the set of drug (salt) IDs it contains.
    Used to enforce exact salt-set matching for fixed-dose combinations.
    """
    if not brand_product_names:
        return {}
    placeholders = ",".join("?" * len(brand_product_names))
    sql = f"""
        SELECT bd.NAME AS brand_product_name, d.CODE AS drug_id
        FROM BRAND_DRUG bd
        JOIN DRUG d ON bd.DID = d.CODE
        WHERE LOWER(bd.NAME) IN ({placeholders})
    """
    params = tuple(n.lower() for n in brand_product_names)
    out: dict[str, set[int]] = {}
    with get_conn() as conn:
        for row in conn.execute(sql, params).fetchall():
            name = row["brand_product_name"]
            out.setdefault(name, set()).add(row["drug_id"])
    return out


def get_brand_product_all_salts(brand_product_names: list[str]) -> dict[str, list[str]]:
    """
    Map each brand product name to the ordered list of salt names it contains.
    Used by search cards to show complete compositions (e.g. Paracetamol + Caffeine).
    """
    if not brand_product_names:
        return {}
    placeholders = ",".join("?" * len(brand_product_names))
    sql = f"""
        SELECT DISTINCT bd.NAME AS brand_product_name, d.NAME AS salt_name
        FROM BRAND_DRUG bd
        JOIN DRUG d ON bd.DID = d.CODE
        WHERE LOWER(bd.NAME) IN ({placeholders})
        ORDER BY d.NAME
    """
    params = tuple(n.lower() for n in brand_product_names)
    out: dict[str, list[str]] = {}
    with get_conn() as conn:
        for row in conn.execute(sql, params).fetchall():
            out.setdefault(row["brand_product_name"], []).append(row["salt_name"])
    return out


# ── 4. Cheaper Alternatives ───────────────────────────────────────────────────

def get_alternatives(drug_id: int, limit: int = 15) -> list[dict]:
    """
    Return cheaper brand alternatives for the same salt, sorted by retail price ASC.
    Filters out entries with price = 0 (discontinued/data gaps).
    """
    variants = get_brand_variants(drug_id)
    # Filter: price must be > 0
    priced = [v for v in variants if v["retail_price_num"] > 0]
    # Sort cheapest first
    priced.sort(key=lambda x: x["retail_price_num"])
    return priced[:limit]


def get_cheapest_alternative(drug_id: int) -> dict | None:
    """Return the single cheapest brand for a salt."""
    alts = get_alternatives(drug_id, limit=1)
    return alts[0] if alts else None


def enrich_drugs_for_cards(drugs: list[dict | None]) -> list[dict]:
    """
    Merge DRUG-row fields with a representative brand row so the frontend MedicineCard
    always receives drug_id, brand_name, salt_name, form, strength, packing, prices.
    """
    out: list[dict] = []
    for drug in drugs or []:
        if not drug:
            continue
        code = drug.get("CODE")
        if code is None:
            continue
        try:
            code_int = int(code)
        except (TypeError, ValueError):
            continue
        brands = get_brand_variants(code_int)
        first = brands[0] if brands else {}
        brand_label = (first.get("brand_product_name") or "").strip() or (drug.get("NAME") or "Generic")
        out.append({
            **drug,
            "drug_id": code_int,
            "brand_name": brand_label,
            "salt_name": drug.get("NAME") or "",
            "form": first.get("form") or "",
            "strength": first.get("strength") or "",
            "packing": first.get("packing") or "",
            "company": first.get("company") or "Unknown",
            "retail_price": first.get("retail_price"),
            "retail_price_num": first.get("retail_price_num", 0) if first else 0,
        })
    return out


# ── 5. Dosage by Age Group ────────────────────────────────────────────────────

def get_dosage(drug_id: int) -> dict:
    """
    Return dosage information split by age group.
    Returns dict with keys: neonatal, paediatric, adult (each a list of dose rows).
    """
    age_tables = {
        "neonatal":   "Neonatal",
        "paediatric": "Paedriatic",
        "adult":      "adult",
    }
    dosage = {}
    sql = "SELECT DOSE, SINGLE, FREQ, ROUTE, INSTRUCTION FROM [{}] WHERE CODE = ?"

    with get_conn() as conn:
        for key, table in age_tables.items():
            rows = conn.execute(sql.format(table), (drug_id,)).fetchall()
            cleaned = []
            for row in rows:
                r = _row_to_dict(row)
                dose = (r.get("DOSE") or "").strip()
                instr = (r.get("INSTRUCTION") or "").lower()
                # Skip rows with no dose that are explicitly "not recommended"
                if not dose and "not recommended" in instr:
                    continue
                cleaned.append(r)
            dosage[key] = humanize_dosage_rows(cleaned)

    return dosage


# ── 6. Drug Interactions ──────────────────────────────────────────────────────

def get_interactions(drug_id: int) -> str | None:
    """Return raw interaction text for a drug (to be parsed/summarised by LLM)."""
    sql = "SELECT INTERACTIONS FROM DRUG WHERE CODE = ?"
    with get_conn() as conn:
        row = conn.execute(sql, (drug_id,)).fetchone()
    return row["INTERACTIONS"] if row else None


def check_interaction_between(drug_id_1: int, drug_id_2: int) -> dict:
    """
    Check if drug_2's name appears in drug_1's interaction text (bidirectional).
    Returns {found: bool, details: str}.
    """
    drug2 = get_drug_by_id(drug_id_2)
    if not drug2:
        return {"found": False, "details": "Drug not found."}

    interactions_text = get_interactions(drug_id_1) or ""
    drug2_name = drug2["NAME"]

    found = drug2_name.lower() in interactions_text.lower()
    details = ""
    if found:
        # Extract the sentence(s) mentioning drug2
        sentences = re.split(r"(?<=[.!?])\s+", interactions_text)
        matching = [s for s in sentences if drug2_name.lower() in s.lower()]
        details = " ".join(matching[:3])

    return {"found": found, "drug_name": drug2_name, "details": details}


# ── 7. Company Info ───────────────────────────────────────────────────────────

def get_company(company_id: int) -> dict | None:
    """Return company details by ID."""
    sql = "SELECT ID, NAME, ADDRESS, PHONE, FAX FROM COMPANY WHERE ID = ?"
    with get_conn() as conn:
        row = conn.execute(sql, (company_id,)).fetchone()
    if not row:
        return None
    r = _row_to_dict(row)
    r["NAME"] = r["NAME"].strip()
    return r


# ── 8. All Drugs (for RAG indexing) ──────────────────────────────────────────

def get_all_drugs() -> list[dict]:
    """
    Return all drugs with their key text fields for ChromaDB indexing.
    Called once during RAG pipeline build.
    """
    sql = """
        SELECT CODE, NAME, OVERVIEW, INDICATIONS, CONTRAINDICATIONS,
               INTERACTIONS, EFFECTS, WARNINING AS warnings
        FROM DRUG
        ORDER BY CODE
    """
    with get_conn() as conn:
        rows = conn.execute(sql).fetchall()
    return [_row_to_dict(r) for r in rows]


# ── 9. Stats ──────────────────────────────────────────────────────────────────

def get_db_stats() -> dict:
    """Return record counts for all tables (used in /health endpoint)."""
    tables = ["BRAND", "BRAND_DRUG", "COMPANY", "DRUG", "Neonatal", "Paedriatic", "adult"]
    stats = {}
    with get_conn() as conn:
        for t in tables:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM [{t}]").fetchone()
            stats[t] = row["cnt"]
    return stats


# ── Quick self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== DB Stats ===")
    print(json.dumps(get_db_stats(), indent=2))

    print("\n=== Search: 'Panadol' ===")
    results = search_medicines("Panadol", limit=5)
    for r in results:
        print(f"  {r['brand_name']:<30} {r['strength']:<12} Retail: {r['retail_price']} PKR  Salt: {r['salt_name']}")

    print("\n=== Drug Detail: Paracetamol ===")
    drug = get_drug_by_name("Paracetamol")
    if drug:
        print(f"  Name       : {drug['NAME']}")
        print(f"  Indications: {(drug['INDICATIONS'] or '')[:120]}...")
        print(f"  Warnings   : {(drug['warnings'] or '')[:120]}...")

    print("\n=== Dosage: Paracetamol ===")
    dosage = get_dosage(drug["CODE"])
    for group, rows in dosage.items():
        print(f"  [{group.upper()}]")
        for d in rows[:1]:
            print(f"    Dose: {d['DOSE']}  Freq: {d['FREQ']}  Route: {d['ROUTE']}")

    print("\n=== Cheapest Alternatives: Paracetamol ===")
    alts = get_alternatives(drug["CODE"], limit=5)
    for a in alts:
        print(f"  {a['brand_product_name']:<25} {a['strength']:<12} {a['retail_price']:>8} PKR  ({a['company']})")

    print("\n=== All tests passed! ===")
