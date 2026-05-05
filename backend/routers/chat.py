"""
MedPak AI — Chat API Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from rag.retriever import retrieve_context, build_context_string
from llm.groq_client import call_llm
from llm.memory import add_turn, get_history, load_session_from_db, get_all_sessions
from database.db import enrich_drugs_for_cards

router = APIRouter(prefix="/api/chat", tags=["Chat"])


from typing import Optional

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@router.post("/message")
def send_message(req: ChatRequest):
    """
    Main chat endpoint.
    1. Retrieves RAG context for the query.
    2. Fetches chat history for the session.
    3. Calls Groq LLM (Qwen3).
    4. Saves the interaction to history.
    """
    session_id = req.session_id or str(uuid.uuid4())
    
    # 1. RAG Retrieval
    context_data = retrieve_context(req.message)
    context_text = build_context_string(context_data)
    
    # 2. History
    # If it's a new request but has an existing session ID, ensure it's loaded in memory
    history = get_history(session_id)
    if not history:
        load_session_from_db(session_id)
        history = get_history(session_id)
        
    # 3. LLM Call
    try:
        result = call_llm(
            user_query=req.message,
            context_text=context_text,
            history=history
        )
    except Exception as e:
        print(f"[ERROR] LLM Call Failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to the AI model. Please try again.")
    
    # 4. Save to history
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
def list_sessions():
    """List all previous session IDs."""
    return {"sessions": get_all_sessions()}


@router.get("/history/{session_id}")
def get_session_history(session_id: str):
    """Get the full message history for a session."""
    load_session_from_db(session_id, limit=50) # Load up to last 50
    history = get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return {"session_id": session_id, "history": history}
