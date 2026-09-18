"""
MedPak AI — Chat API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import uuid

from rag.retriever import retrieve_context, build_context_string
from llm.llm_client import call_llm
from llm.guard import check_query_guards
from llm.memory import add_turn, get_history, load_session_from_db, get_all_sessions
from database.db import enrich_drugs_for_cards
from auth.dependencies import get_current_user
from ratelimit import limiter

router = APIRouter(prefix="/api/chat", tags=["Chat"])


from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/message")
@limiter.limit("10/minute")
def send_message(request: Request, req: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Main chat endpoint.
    1. Checks deterministic guardrails (refuses suggestions/diagnoses
       requests BEFORE hitting the LLM).
    2. Retrieves RAG context for the query.
    3. Fetches chat history for the session.
    4. Calls the LLM (Groq GPT-OSS 120B) under a strict
       information-only system prompt.
    5. Saves the interaction to history.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # 1. Pre-LLM guardrails — blatant violations never cost tokens
    #    (greetings get a friendly welcome; refusals/emergencies are instant)
    guard_result = check_query_guards(req.message)
    if guard_result:
        add_turn(session_id, req.message, guard_result["answer"])
        return {
            "session_id": session_id,
            "answer": guard_result["answer"],
            "model_used": "guard",
            "guarded": guard_result["reason"] != "greeting",
            "guard_reason": guard_result["reason"],
            "rag_context": {
                "query_type": "guarded",
                "top_drug": None,
                "drugs_found": 0,
                "drugs": [],
            },
        }

    # 2. RAG Retrieval
    context_data = retrieve_context(req.message)
    context_text = build_context_string(context_data)

    # 3. History
    # If it's a new request but has an existing session ID, ensure it's loaded in memory
    history = get_history(session_id)
    if not history:
        load_session_from_db(session_id)
        history = get_history(session_id)

    # 4. LLM Call
    try:
        result = call_llm(
            user_query=req.message,
            context_text=context_text,
            history=history
        )
    except Exception as e:
        print(f"[ERROR] LLM Call Failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to the AI model. Please try again.")

    # 5. Save to history
    add_turn(session_id, req.message, result["answer"])

    drugs_ui = enrich_drugs_for_cards(context_data["drugs"])

    return {
        "session_id": session_id,
        "answer": result["answer"],
        "model_used": result["model_used"],
        "rag_context": {
            "query_type": context_data["query_type"],
            "top_drug": context_data["top_drug"]["NAME"] if context_data["top_drug"] else None,
            "drugs_found": len(context_data["drugs"]),
            "drugs": drugs_ui,
        }
    }


@router.get("/sessions")
def list_sessions(user: dict = Depends(get_current_user)):
    """List all previous session IDs."""
    return {"sessions": get_all_sessions()}


@router.get("/history/{session_id}")
def get_session_history(session_id: str, user: dict = Depends(get_current_user)):
    """Get the full message history for a session."""
    load_session_from_db(session_id, limit=50) # Load up to last 50
    history = get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return {"session_id": session_id, "history": history}
