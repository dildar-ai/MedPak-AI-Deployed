"""
MedPak AI — Medicine API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import uuid

from database.db import (
    search_medicines,
    get_drug_by_id,
    get_brand_variants,
    get_alternatives,
    get_cheapest_alternative,
    get_dosage,
    check_interaction_between,
    enrich_drugs_for_cards,
)
from ocr.scanner import scan_medicine_image
from rag.retriever import retrieve_context, build_context_string
from llm.groq_client import call_llm
from llm.memory import add_turn, get_history
from config import settings


router = APIRouter(prefix="/api/medicine", tags=["Medicine"])


@router.get("/search")
def search(q: str = Query(..., min_length=2, description="Search query for brand or salt")):
    """
    Ranked keyword search (exact → prefix → contains).
    Much faster and more accurate than RAG for named medicine lookups.
    """
    results = search_medicines(q, limit=30)
    return {"results": results, "count": len(results)}


class MedicineChatRequest(BaseModel):
    message: str
    drug_id: int
    session_id: Optional[str] = None


@router.post("/chat")
def medicine_chat(req: MedicineChatRequest):
    """
    Context-aware chat about a specific medicine.
    Pre-loads the full drug profile as context before calling the LLM.
    """
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
            dosage_lines.append(f"  [{group}] {d.get('DOSE','')} — {d.get('FREQ','')} — {d.get('ROUTE','')}")
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
async def scan_and_search(file: UploadFile = File(...)):
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
        scanned_text = scan_medicine_image(image_bytes)
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
def get_drug_details(drug_id: int):
    """Get full details, brands, and dosage for a specific drug ID."""
    drug = get_drug_by_id(drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    brands = get_brand_variants(drug_id)
    dosage = get_dosage(drug_id)

    return {
        "drug": drug,
        "dosage": dosage,
        "brands": brands,
    }


@router.get("/{drug_id}/alternatives")
def get_drug_alternatives(drug_id: int, limit: int = 15):
    """Find cheaper alternatives for a specific drug ID."""
    drug = get_drug_by_id(drug_id)
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    alternatives = get_alternatives(drug_id, limit=limit)
    cheapest = get_cheapest_alternative(drug_id)

    return {
        "salt_name": drug["NAME"],
        "cheapest_alternative": cheapest,
        "alternatives": alternatives,
    }


@router.get("/interactions/{drug_id_1}/{drug_id_2}")
def check_interactions(drug_id_1: int, drug_id_2: int):
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
