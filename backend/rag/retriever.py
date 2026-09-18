"""
MedPak AI — RAG Retriever
Combines vector search (ChromaDB) + keyword fallback (SQLite)
to find the most relevant drug context for a user query.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
from rag.vectorstore import query_index
from database.db import get_drug_by_id, get_brand_variants, get_dosage, search_medicines
from database.prices_db import get_stored_prices


# ── Relevance threshold ───────────────────────────────────────────────────────
# Cosine similarity ≥ this → use vector result; below → add keyword fallback
VECTOR_THRESHOLD = 0.45

# Queries shorter than this that don't match a known drug name are rejected
_NON_MEDICAL_PATTERNS = re.compile(
    r'^\s*(hi|hello|hey|salam|ok|yes|no|thanks|bye|lol|haha|hmm|'
    r'what|who|how are you|kya|kon|theek|shukriya|khuda hafiz)\s*[!?.]*$',
    re.IGNORECASE,
)


def _is_non_medical_query(query: str) -> bool:
    """Return True for greetings, single chars, and obvious non-medicine text."""
    q = query.strip()
    if len(q) < 2:
        return True
    if _NON_MEDICAL_PATTERNS.match(q):
        return True
    return False


def retrieve_context(query: str, n: int = 3) -> dict:
    """
    Main retrieval function. Returns a structured context dict.
    """
    _empty = {
        "drugs": [], "top_drug": None, "brands": [],
        "dosage": {}, "query_type": "none",
    }

    # Fast-reject obvious greetings/gibberish
    if _is_non_medical_query(query):
        return _empty

    # ── Step 1: ALWAYS Keyword search first (exact matches) ───────────────────
    keyword_hits = search_medicines(query, limit=n)
    keyword_drug_ids = list({h["drug_id"] for h in keyword_hits})

    # ── Step 2: ALWAYS Vector search (semantic matches) ───────────────────────
    vector_results = query_index(query, n_results=n)
    strong_results = [r for r in vector_results if r["score"] >= VECTOR_THRESHOLD]

    if not keyword_drug_ids and not strong_results:
        query_type = "none"
    elif keyword_drug_ids and not strong_results:
        query_type = "keyword"
    elif strong_results and not keyword_drug_ids:
        query_type = "vector"
    else:
        query_type = "mixed"

    # ── Step 3: Collect candidate drug IDs (keyword first, then vector) ───────
    seen_ids = set()
    candidate_ids = []
    
    for did in keyword_drug_ids:
        if did not in seen_ids:
            candidate_ids.append(did)
            seen_ids.add(did)
            
    for r in strong_results:
        if r["drug_id"] not in seen_ids:
            candidate_ids.append(r["drug_id"])
            seen_ids.add(r["drug_id"])

    # ── Step 4: Fetch full drug details ──────────────────────────────────────
    drugs = []
    for did in candidate_ids[:n]:
        drug = get_drug_by_id(did)
        if drug:
            drugs.append(drug)

    top_drug = drugs[0] if drugs else None

    # ── Step 5: Fetch brands + dosage for the top drug only ─────────────────
    brands, dosage = [], {}
    if top_drug:
        brands = get_brand_variants(top_drug["CODE"])
        dosage = get_dosage(top_drug["CODE"])

    return {
        "drugs":      drugs,
        "top_drug":   top_drug,
        "brands":     brands,
        "dosage":     dosage,
        "query_type": query_type,
    }


def build_context_string(context: dict, max_chars: int = 3000) -> str:
    """
    Format retrieved context into a clean text block to inject into the LLM prompt.
    Keeps it under max_chars to respect token limits.
    """
    lines = []

    for drug in context["drugs"][:3]:
        lines.append(f"## Drug: {drug['NAME']}")
        lines.append(f"Indications: {(drug.get('INDICATIONS') or '')[:400]}")
        lines.append(f"Side Effects: {(drug.get('EFFECTS') or '')[:300]}")
        lines.append(f"Contraindications: {(drug.get('CONTRAINDICATIONS') or '')[:200]}")
        lines.append(f"Warnings: {(drug.get('warnings') or '')[:200]}")
        lines.append("")

    if context["brands"]:
        top_brands = context["brands"][:5]
        lines.append("## Pakistani Brands & Prices")
        for b in top_brands:
            # Check for live price first, fall back to DB retail price
            brand_label = b['brand_product_name']
            live_results = get_stored_prices(brand_label, max_age_hours=72)
            if live_results:
                live_price = min(r['price_pkr'] for r in live_results if r.get('price_pkr') and 10 < r['price_pkr'] < 50000)
                price_str = f"Rs.{live_price} PKR (live)"
            else:
                price_str = f"{b['retail_price']} PKR" if b["retail_price_num"] > 0 else "N/A"
            lines.append(
                f"- {brand_label} ({b['form']}, {b['strength']}, "
                f"Packing: {b['packing']}) -> Retail: {price_str} | {b['company']}"
            )
        lines.append("")

    if context["dosage"]:
        lines.append("## Dosage")
        for group, rows in context["dosage"].items():
            for row in rows[:1]:
                if row.get("DOSE", "").strip():
                    lines.append(
                        f"- {group.title()}: {row['DOSE']} | {row['FREQ']} | {row['ROUTE']}"
                    )
        lines.append("")

    result = "\n".join(lines)
    return result[:max_chars]


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    queries = [
        "Panadol",
        "fever and headache tablet",
        "bukhaar ki dawa",           # Roman Urdu: medicine for fever
        "sugar ka ilaj",             # Roman Urdu: diabetes treatment
        "بخار کی دوا",               # Urdu script: fever medicine
    ]

    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        ctx = retrieve_context(q)
        print(f"Query type: {ctx['query_type']}")
        print(f"Top drug: {ctx['top_drug']['NAME'] if ctx['top_drug'] else 'None'}")
        if ctx["drugs"]:
            print(f"All matches: {[d['NAME'] for d in ctx['drugs']]}")
        if ctx["brands"]:
            b = ctx["brands"][0]
            print(f"First brand: {b['brand_product_name']} - {b['retail_price']} PKR")
