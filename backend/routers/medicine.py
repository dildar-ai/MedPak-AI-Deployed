"""
MedPak AI — Medicine API Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
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
from rag.retriever import retrieve_context
from config import settings


router = APIRouter(prefix="/api/medicine", tags=["Medicine"])


@router.get("/search")
def search(q: str = Query(..., min_length=2, description="Search query for brand or salt")):
    """Search for medicines using Hybrid RAG (AI + Keyword)."""
    context = retrieve_context(q, n=15)
    results = enrich_drugs_for_cards(context["drugs"])
    return {"results": results, "count": len(results)}


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
        
    # Use the scanned text to search our database
    # Sometimes OCR returns "PANADOL 500mg" - we take the first word as a safe guess for search
    main_word = scanned_text.split()[0] if len(scanned_text.split()) > 1 else scanned_text
    
    context = retrieve_context(main_word, n=15)
    results = enrich_drugs_for_cards(context["drugs"])
    return {
        "scanned_text": scanned_text,
        "search_used": main_word,
        "results": results,
        "count": len(results)
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
        "alternatives": alternatives
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
        "details": details.strip() or "No severe interactions found in database."
    }
