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

def search_medicines(query: str, limit: int = 20) -> list[dict]:
    """
    Search by brand name OR generic/salt name (case-insensitive, fuzzy).
    Returns combined results deduplicated by drug code.
    """
    q = f"%{query.strip()}%"
    sql = """
        SELECT DISTINCT
            d.CODE          AS drug_id,
            d.NAME          AS salt_name,
            d.INDICATIONS   AS indications,
            b.BNAME         AS brand_name,
            bd.FORM         AS form,
            bd.MG           AS strength,
            bd.RETIALPRICE  AS retail_price,
            bd.TRADEPRICE   AS trade_price,
            bd.PACKING      AS packing,
            co.NAME         AS company,
            bd.DID          AS did,
            bd.BID          AS bid
        FROM BRAND_DRUG bd
        JOIN BRAND   b  ON bd.BID  = b.BID
        JOIN DRUG    d  ON bd.DID  = d.CODE
        LEFT JOIN COMPANY co ON b.CID = co.ID
        WHERE bd.NAME LIKE ?
           OR b.BNAME  LIKE ?
           OR d.NAME   LIKE ?
        ORDER BY bd.NAME
        LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(sql, (q, q, q, limit)).fetchall()

    results = []
    for row in rows:
        r = _row_to_dict(row)
        r["retail_price_num"] = _clean_price(r["retail_price"])
        r["company"] = (r.get("company") or "").strip() or "Unknown"
        results.append(r)
    return results


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
            dosage[key] = cleaned

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
