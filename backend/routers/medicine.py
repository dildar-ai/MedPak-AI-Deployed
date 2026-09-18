"""
MedPak AI — Medicine API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import Optional
import uuid

from database.db import (
    search_medicines,
    get_drug_by_id,
    get_brand_variants,
    get_brand_variants_multi,
    get_brand_product_salts,
    get_salt_sets_for_brands,
    get_alternatives,
    get_cheapest_alternative,
    get_dosage,
    check_interaction_between,
    enrich_drugs_for_cards,
)
from ocr.scanner import scan_medicine_image
from rag.retriever import retrieve_context, build_context_string
from llm.llm_client import call_llm
from llm.memory import add_turn, get_history
from config import settings
from auth.dependencies import get_current_user
from ratelimit import limiter

from scrapers.price_cache import (
    clear_cache,
    get_cache_stats,
    get_or_fetch_price,
    get_best_result,
    get_saved_prices_batch,
    pending_scrape_brands,
    register_scrape_job,
    get_scrape_status,
    bulk_scrape_brands,
    select_best_result,
)
from scrapers.price_scraper import scrape_live_price
from database.prices_db import save_prices
from utils.price_utils import parse_strength_mg, calculate_savings


router = APIRouter(prefix="/api/medicine", tags=["Medicine"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query for brand or salt"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: dict = Depends(get_current_user),
):
    """
    Ranked keyword search (exact → prefix → contains).
    Much faster and more accurate than RAG for named medicine lookups.

    Responds instantly with any SAVED live prices attached (memory/DB — never
    scrapes in-request). A background job then scrapes the brands that have
    no price yet, so the next request finds them.
    """
    results = search_medicines(q, limit=30)

    # Attach saved live prices (instant — never blocks the response).
    # NOTE: DB prices are deliberately NOT surfaced — they are outdated.
    brand_names: list[str] = []
    strength_map: dict[str, str] = {}
    for r in results:
        brand = r.get("brand_product_name") or r.get("brand_name") or ""
        if not brand:
            continue
        brand_names.append(brand)
        strength_map.setdefault(brand, r.get("strength") or "")
        best = get_best_result(brand, strength_mg=parse_strength_mg(r.get("strength") or ""), form_name=r.get("form"))
        if best:
            qty = best.get("pack_qty")
            r["live_price_pkr"] = best["price_pkr"]
            r["price_source"] = "live"
            r["pack_qty"] = qty
            r["pack_desc"] = best.get("pack_desc")
            # Per-unit is only meaningful when derived from the SCRAPED pack,
            # never from a guessed DB packing string.
            r["price_per_unit"] = round(best["price_pkr"] / qty, 2) if qty else None
        else:
            r["live_price_pkr"] = None
            r["price_source"] = "pending"
            r["pack_qty"] = None
            r["pack_desc"] = None
            r["price_per_unit"] = None

    # Fire-and-forget: scrape all unpriced brands from this search in parallel
    if brand_names:
        pending = pending_scrape_brands(brand_names)
        if pending:
            job_key = f"search:{q.strip().lower()}"
            if not (get_scrape_status(job_key) or {}).get("running"):
                register_scrape_job(job_key, len(pending))
                background_tasks.add_task(
                    bulk_scrape_brands, job_key, brand_names, strengths=strength_map
                )

    return {"results": results, "count": len(results)}


@router.delete("/price-cache")
def clear_price_cache(user: dict = Depends(get_current_user)):
    """Flush all cached live prices (admin/debug endpoint)."""
    removed = clear_cache()
    return {"cleared": removed, "message": f"Removed {removed} cached price entries"}


@router.get("/price-cache/stats")
def price_cache_stats(user: dict = Depends(get_current_user)):
    """Return current price cache statistics."""
    return get_cache_stats()


@router.post("/prices/refresh")
@limiter.limit("10/minute")
async def refresh_prices(request: Request, user: dict = Depends(get_current_user)):
    """
    Force-refresh live prices for a brand — bypasses all caches,
    re-scrapes from the web, saves the results, and returns them.
    """
    import json
    try:
        body = json.loads(await request.body())
        brand = str(body.get("brand", "")).strip()
        strength = str(body.get("strength", "")).strip() or None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if len(brand) < 2:
        raise HTTPException(status_code=400, detail="Brand name too short.")

    results = await scrape_live_price(brand, strength)
    if results:
        valid = [r for r in results if r.get("price_pkr") and 15 <= r["price_pkr"] <= 30000]
        if valid:
            save_prices(brand, valid)
            return {
                "brand": brand,
                "live_price_pkr": min(r["price_pkr"] for r in valid),
                "all_prices": valid[:5],
                "found": True,
                "refreshed": True,
            }

    return {"brand": brand, "live_price_pkr": None, "all_prices": [], "found": False, "refreshed": True}


@router.get("/live-price")
async def get_live_price(
    brand: str = Query(..., min_length=2, description="Brand name to fetch live price for"),
    strength: Optional[str] = Query(
        None, description="Formulation strength from the DB (e.g. '20 MG') — sharpens the live search"
    ),
    form: Optional[str] = Query(None, description="Formulation (e.g. 'Tablet', 'Injection')"),
    user: dict = Depends(get_current_user),
):
    """
    Fetch (or return cached) live price for a specific brand name.
    This is called by the detail view to show live prices.
    Unlike the /search endpoint, this WILL wait for the scraper to finish.
    """
    results = await get_or_fetch_price(brand, strength)
    if results:
        best = select_best_result(results, strength_mg=parse_strength_mg(strength or ""), form_name=form)
        if best:
            qty = best.get("pack_qty")
            return {
                "brand": brand,
                "live_price_pkr": best["price_pkr"],
                "all_prices": results[:5],
                "pack_qty": qty,
                "pack_desc": best.get("pack_desc"),
                "price_title": best.get("title"),
                "price_per_unit": round(best["price_pkr"] / qty, 2) if qty else None,
                "found": True,
            }
    return {"brand": brand, "live_price_pkr": None, "all_prices": [], "found": False}


class MedicineChatRequest(BaseModel):
    message: str
    drug_id: int
    session_id: Optional[str] = None


@router.post("/chat")
@limiter.limit("10/minute")
def medicine_chat(request: Request, req: MedicineChatRequest, user: dict = Depends(get_current_user)):
    """
    Context-aware chat about a specific medicine.
    Pre-loads the full drug profile as context before calling the LLM.
    """
    from llm.guard import check_query_guards

    guard_result = check_query_guards(req.message)
    if guard_result:
        session_id = req.session_id or str(uuid.uuid4())
        add_turn(session_id, req.message, guard_result["answer"])
        drug = get_drug_by_id(req.drug_id)
        return {
            "session_id": session_id,
            "answer": guard_result["answer"],
            "drug_name": drug.get("NAME") if drug else None,
            "guarded": True,
        }

    drug = get_drug_by_id(req.drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    brands = get_brand_variants(req.drug_id)
    dosage  = get_dosage(req.drug_id)

    # Build a rich context string about this specific drug
    brand_names = ", ".join(
        b.get("brand_product_name", "") for b in brands[:8] if b.get("brand_product_name")
    )
    dosage_lines = []
    for group in ["adult", "paediatric", "neonatal"]:
        for d in (dosage.get(group) or [])[:2]:
            freq = d.get("freq_human") or d.get("FREQ", "")
            route = d.get("route_human") or d.get("ROUTE", "")
            dosage_lines.append(f"  [{group}] {d.get('DOSE','')} — {freq} — {route}")
    dosage_text = "\n".join(dosage_lines) or "Not specified"

    context_text = f"""
MEDICINE PROFILE — {drug.get('NAME', 'Unknown')}
=================================================
Generic/Salt Name : {drug.get('NAME', '')}
Pakistani Brands  : {brand_names or 'Unknown'}
Overview          : {(drug.get('OVERVIEW') or '')[:400]}
Uses/Indications  : {(drug.get('INDICATIONS') or '')[:400]}
Side Effects      : {(drug.get('EFFECTS') or '')[:300]}
Contraindications : {(drug.get('CONTRAINDICATIONS') or '')[:300]}
Warnings          : {(drug.get('warnings') or '')[:200]}
Storage           : {(drug.get('STORAGE') or '')[:150]}
Dosage by Age:
{dosage_text}
""".strip()

    session_id = req.session_id or str(uuid.uuid4())
    history = get_history(session_id)

    try:
        result = call_llm(
            user_query=req.message,
            context_text=context_text,
            history=history,
        )
    except Exception as e:
        print(f"[ERROR] Medicine Chat LLM Failed: {e}")
        raise HTTPException(status_code=500, detail="AI model failed. Please try again.")

    add_turn(session_id, req.message, result["answer"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "drug_name": drug.get("NAME"),
    }


@router.post("/scan")
@limiter.limit("5/minute")
async def scan_and_search(request: Request, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload an image of a medicine to extract the name and search the database."""
    ctype = file.content_type or ""
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    max_bytes = max(1, settings.MAX_UPLOAD_IMAGE_MB) * 1024 * 1024
    image_bytes = await file.read()
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum size is {settings.MAX_UPLOAD_IMAGE_MB} MB.",
        )

    try:
        scanned_text = await scan_medicine_image(image_bytes)
    except Exception:
        import traceback
        print("[ERROR] OCR Scan Crashed:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="OCR processing failed. Try a clearer photo or a smaller image.",
        )

    if not scanned_text:
        return {"scanned_text": "", "results": [], "count": 0, "message": "Could not read any text from the image."}

    main_word = scanned_text.split()[0] if len(scanned_text.split()) > 1 else scanned_text

    results = search_medicines(main_word, limit=20)
    return {
        "scanned_text": scanned_text,
        "search_used": main_word,
        "results": results,
        "count": len(results),
    }


@router.get("/{drug_id}")
async def get_drug_details(
    drug_id: int,
    brand: Optional[str] = Query(None, description="Brand product the user clicked — used to show its exact salt composition"),
    user: dict = Depends(get_current_user),
):
    """Get full details, brands, dosage, and the complete salt set for a drug ID."""
    drug = get_drug_by_id(drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    brands = get_brand_variants(drug_id)
    dosage = get_dosage(drug_id)

    # Combination products (e.g. Panadol-CF, Tonoplex-P) appear once per salt
    # in BRAND_DRUG. Surface every salt for the clicked brand so the header is
    # medically accurate instead of showing only the single salt of this DID.
    salts = []
    target_brand = ""
    if brand and isinstance(brand, str):
        target_brand = brand.strip()
    elif brands:
        target_brand = brands[0].get("brand_product_name", "")
    if target_brand:
        salts = get_brand_product_salts(target_brand)

    # Enrich first brand with saved live price (instant cache/DB check only)
    if brands:
        first_brand = brands[0].get("brand_product_name", "")
        if first_brand:
            best = get_best_result(
                first_brand,
                strength_mg=parse_strength_mg(brands[0].get("strength") or ""),
            )
            if best:
                qty = best.get("pack_qty")
                brands[0]["live_price_pkr"] = best["price_pkr"]
                brands[0]["price_source"] = "live"
                brands[0]["pack_qty"] = qty
                brands[0]["pack_desc"] = best.get("pack_desc")
                brands[0]["price_per_unit"] = (
                    round(best["price_pkr"] / qty, 2) if qty else None
                )

    return {
        "drug": drug,
        "salts": salts,
        "dosage": dosage,
        "brands": brands,
    }


@router.get("/{drug_id}/alternatives")
async def get_drug_alternatives(
    drug_id: int,
    limit: int = 20,
    brand: Optional[str] = Query(None, description="Brand the user clicked — used as the price reference"),
    form: Optional[str] = Query(None, description="Dosage form of the clicked brand (e.g. 'Tablets') — ensures correct form filtering"),
    strength: Optional[str] = Query(None, description="Strength of the clicked brand (e.g. '500 MG') — sharpens form matching"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: dict = Depends(get_current_user),
):
    """
    Find cheaper alternatives with LIVE prices.

    Responds INSTANTLY with whatever prices are already saved (memory/DB).
    If some brands have no price yet, a background job scrapes ALL of them
    simultaneously and persists the results for future use — the frontend
    polls this endpoint while `scraping.in_progress` is true and watches the
    table fill up. Savings are calculated against the clicked brand
    (`brand` param); alternatives in the same form/strength as the clicked
    brand are prioritized.
    """
    drug = get_drug_by_id(drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    # Get all brand variants for this salt
    variants = get_brand_variants(drug_id)

    # ── Reference brand: the product the user actually clicked ──────────────
    ref_variant = None
    ref_brand_name = ""
    if brand and isinstance(brand, str):
        b = brand.strip().lower()
        ref_variant = next(
            (v for v in variants if (v.get("brand_product_name") or "").strip().lower() == b),
            None,
        )
        ref_brand_name = ref_variant.get("brand_product_name", "") if ref_variant else ""

    # ── Fixed-dose combinations: match the FULL salt set ────────────────────
    # Many brands have multiple salts (Panadol-CF = Paracetamol + Pseudoephedrine
    # + Chlorpheniramine). Fetching variants for only the clicked DID would
    # compare against products containing just one of those salts. Instead,
    # resolve every salt of the reference brand and keep only brands whose
    # salt set is identical.
    ref_salt_ids = {drug_id}
    ref_salt_names = [drug["NAME"]]
    if ref_brand_name:
        ref_salts = get_brand_product_salts(ref_brand_name)
        if ref_salts:
            ref_salt_ids = {s["drug_id"] for s in ref_salts}
            ref_salt_names = [s["salt_name"] for s in ref_salts]

        if len(ref_salt_ids) > 1:
            variants = get_brand_variants_multi(list(ref_salt_ids))
            candidate_names = [
                v.get("brand_product_name") for v in variants if v.get("brand_product_name")
            ]
            salt_sets = get_salt_sets_for_brands(candidate_names)
            variants = [
                v for v in variants
                if salt_sets.get(v.get("brand_product_name", ""), set()) == ref_salt_ids
            ]
            ref_variant = next(
                (v for v in variants
                 if (v.get("brand_product_name") or "").strip().lower() == ref_brand_name.strip().lower()),
                None,
            )

    if not variants:
        return {
            "salt_name": drug["NAME"],
            "salt_names": ref_salt_names,
            "current_brand": None,
            "alternatives": [],
            "cheapest": None,
            "price_coverage": {"total": 0, "with_live": 0, "no_live_price": 0},
            "scraping": {"in_progress": False, "brands_total": 0, "brands_done": 0},
        }

    # ── Pre-sort by DB price (cheapest first) using trade_price ───────────
    # Use trade_price as primary (retail_price is a placeholder in this DB).
    # Variants with no price sink to the bottom.
    def _db_price(v):
        return (v.get("trade_price_num") or v.get("retail_price_num") or 0)

    variants.sort(key=_db_price)

    # ── Prioritize same form/strength as the clicked brand ────────────────
    # Comparing a 500mg capsule against a pediatric syrup is noise.
    # Use the explicitly-passed form/strength from the frontend when available
    # (they come straight from the card the user clicked and are always correct).
    # Fall back to the ref_variant lookup only when the frontend doesn't send them.
    ref_form = ""
    ref_str = ""
    if form and isinstance(form, str) and form.strip():
        ref_form = form.strip().lower()
    elif ref_variant:
        ref_form = (ref_variant.get("form") or "").strip().lower()
    if strength and isinstance(strength, str) and strength.strip():
        ref_str = strength.strip().lower()
    elif ref_variant:
        ref_str = (ref_variant.get("strength") or "").strip().lower()

    if ref_form:
        def _form_rank(v):
            same_form = (v.get("form") or "").strip().lower() == ref_form
            same_str = bool(ref_str) and (v.get("strength") or "").strip().lower() == ref_str
            return 0 if (same_form and same_str) else (1 if same_form else 2)

        variants.sort(key=_form_rank)  # stable sort → price order kept within groups

    # ── Deduplicate by brand name ──────────────────────────────────────────
    # BRAND_DRUG keeps one row per packing (20s / 100s / 10x10s) but live
    # prices are per brand — collapse packings into a single row each.
    _seen_names: set[str] = set()
    unique_variants = []
    for v in variants:
        key = (v.get("brand_product_name") or "").strip().lower()
        if key and key not in _seen_names:
            _seen_names.add(key)
            unique_variants.append(v)
    variants = unique_variants

    # Every brand of this salt — the background job scrapes them ALL,
    # so there is no scrape cap anymore.
    all_names = [v.get("brand_product_name") for v in variants if v.get("brand_product_name")]
    # brand_name → DB strength, so each scrape searches the right formulation
    strength_map = {
        v["brand_product_name"]: v.get("strength") or ""
        for v in variants
        if v.get("brand_product_name")
    }

    # ── Instant: saved prices only (memory + DB — never scrapes) ──────────
    saved = get_saved_prices_batch(all_names)

    # ── Kick off ONE background bulk scrape for every unpriced brand ──────
    # All brands are scraped simultaneously (bounded concurrency) and the
    # results are persisted to live_prices.db for future requests. The
    # reference brand goes first so its price arrives earliest.
    job_key = f"alternatives:{drug_id}"
    pending = pending_scrape_brands(all_names)
    status = get_scrape_status(job_key)
    if pending and not (status and status.get("running")):
        ordered = list(all_names)
        if ref_variant and ref_variant.get("brand_product_name"):
            ref_name_first = ref_variant["brand_product_name"]
            ordered = [ref_name_first] + [n for n in ordered if n != ref_name_first]
        register_scrape_job(job_key, len(pending))
        background_tasks.add_task(
            bulk_scrape_brands, job_key, ordered, strengths=strength_map
        )
        status = get_scrape_status(job_key)

    # ── Enrich each variant with SAVED live prices only ───────────────────
    # DB prices are outdated and must never be shown to users. Brands we
    # can't price online are listed without a price instead of a wrong one.
    # The price says WHAT it covers via pack_qty / pack_desc / price_title.
    enriched = []
    with_live = 0

    for v in variants:
        name = v.get("brand_product_name", "")
        strength_mg = parse_strength_mg(v.get("strength") or "")
        results = saved.get(name)
        best = select_best_result(results, strength_mg=strength_mg, form_name=v.get("form")) if results else None

        per_unit = None
        if best and best.get("pack_qty"):
            per_unit = round(best["price_pkr"] / best["pack_qty"], 2)

        if best:
            with_live += 1

        sources = []
        if results:
            for r in results[:3]:
                if r.get("price_pkr"):
                    sources.append({
                        "name": r.get("source", ""),
                        "price": r["price_pkr"],
                        "pack_desc": r.get("pack_desc"),
                    })

        enriched.append({
            "brand_product_name": name,
            "brand_name": v.get("brand_name", ""),
            "form": v.get("form", ""),
            "strength": v.get("strength", ""),
            "packing": v.get("packing") or "",
            "company": v.get("company", "Unknown"),
            "live_price": best["price_pkr"] if best else None,
            "best_price": best["price_pkr"] if best else None,   # live only — no DB fallback
            "price_source": "live" if best else "none",
            "price_title": best.get("title") if best else None,  # listing the price came from
            "pack_qty": best.get("pack_qty") if best else None,
            "pack_desc": best.get("pack_desc") if best else None,
            "price_per_unit": per_unit,
            "sources": sources,
            "scraped_at": best.get("scraped_at") if best else None,
        })

    # ── Reference: the brand the user clicked ─────────────────────────────
    ref_name = (ref_variant or {}).get("brand_product_name") or (all_names[0] if all_names else "")
    ref_entry = next((e for e in enriched if e["brand_product_name"] == ref_name), None)
    # ref_form is already set earlier from explicit query params or ref_variant

    # Rank: First prioritize exact dosage form matches (0), then other forms (1).
    # Within each group, rank by PER-UNIT price when the pack is known — a fair 
    # comparison across pack sizes. Fall back to pack price when no pack info exists.
    def _rank(e):
        is_same_form = e.get("form", "").strip().lower() == ref_form if ref_form else False
        form_priority = 0 if is_same_form else 1

        if e["price_per_unit"] is not None:
            return (form_priority, 0, e["price_per_unit"])
        if e["best_price"] is not None:
            return (form_priority, 1, e["best_price"])
        return (form_priority, 2, 0)

    # Only compare alternatives of the SAME DOSAGE FORM as the clicked brand.
    # Tablet vs suspension vs injection are different dosage forms and
    # comparing their prices (per tablet vs per ml vs per ampoule) is
    # meaningless. We include all alternatives even if they don't have a live
    # price yet, so the user can watch them populate as the background scrape finishes.
    comparable = (
        [e for e in enriched if e["form"].strip().lower() == ref_form]
        if ref_form else enriched
    )

    priced = sorted(comparable, key=_rank)[:limit]

    # Always show the user's own brand row (even if unpriced) so they can
    # see what they're comparing against.
    if ref_entry and ref_entry not in priced:
        priced.append(ref_entry)

    # ── Savings — only meaningful when BOTH sides have live prices ────────
    # Compare PER UNIT only when BOTH packs are known — mixing bases
    # (ref's per-unit price vs alt's pack price) would be nonsense. Fall
    # back to pack-price comparison for alts without pack info.
    for alt in priced:
        per_unit_ok = bool(
            ref_entry
            and ref_entry["price_per_unit"] is not None
            and alt["price_per_unit"] is not None
        )
        ref_basis = (
            ref_entry["price_per_unit"] if per_unit_ok
            else (ref_entry["best_price"] if ref_entry else None)
        )
        alt_basis = alt["price_per_unit"] if per_unit_ok else alt["best_price"]
        alt["savings"] = (
            calculate_savings(ref_basis, alt_basis)
            if ref_basis and alt["best_price"] else None
        )
        alt["savings_basis"] = "per_unit" if per_unit_ok else "pack"

    # ── Build current brand info ──────────────────────────────────────────
    current_brand = None
    if ref_entry:
        current_brand = {
            "name": ref_entry["brand_product_name"],
            "live_price": ref_entry["live_price"],
            "best_price": ref_entry["best_price"],
            "price_source": ref_entry["price_source"],
            "pack_qty": ref_entry["pack_qty"],
            "pack_desc": ref_entry["pack_desc"],
            "price_per_unit": ref_entry["price_per_unit"],
        }

    cheapest = priced[0] if priced else None

    return {
        "salt_name": drug["NAME"],
        "salt_names": ref_salt_names,
        "current_brand": current_brand,
        "alternatives": priced,
        "cheapest": cheapest,
        "price_coverage": {
            "total": len(enriched),
            "with_live": with_live,
            "no_live_price": len(enriched) - with_live,
        },
        "scraping": {
            "in_progress": bool(status and status.get("running")),
            "brands_total": (status or {}).get("total", 0),
            "brands_done": (status or {}).get("done", 0),
        },
    }


@router.get("/interactions/{drug_id_1}/{drug_id_2}")
def check_interactions(drug_id_1: int, drug_id_2: int, user: dict = Depends(get_current_user)):
    """Check if two drugs have known interactions."""
    interaction_1 = check_interaction_between(drug_id_1, drug_id_2)
    interaction_2 = check_interaction_between(drug_id_2, drug_id_1)

    found = interaction_1["found"] or interaction_2["found"]
    details = ""
    if interaction_1["found"]:
        details += interaction_1["details"] + " "
    if interaction_2["found"]:
        details += interaction_2["details"]

    return {
        "interaction_found": found,
        "details": details.strip() or "No severe interactions found in database.",
    }
