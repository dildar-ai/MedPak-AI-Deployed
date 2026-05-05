"""
MedPak AI — Groq LLM Client
Handles:
  - Prompt engineering for medical context (bilingual Urdu/English)
  - Qwen3-32B as primary model (best Urdu + Roman Urdu + English)
  - LLaMA 3.3 70B as automatic fallback on rate-limit
  - Conversation memory injection
  - Safety disclaimer enforcement
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from groq import RateLimitError, APIStatusError
from typing import Optional
import re
from config import settings


# ── Client ────────────────────────────────────────────────────────────────────

_THINK_RE = re.compile(r'<think>.*?</think>\s*', re.DOTALL)

_client: Optional[Groq] = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are MedPak AI — an expert medicine assistant for Pakistan.

LANGUAGE RULES (most important rule):
- For the INITIAL response about a medicine, you MUST provide the information in BOTH English and Urdu script (اردو). 
- Do not translate the medicine names, keep them in English letters or transliterated, but the uses and side effects must be in both languages.
- AFTER the initial response, mirror the user's exact language (if they ask in Roman Urdu, reply in Roman Urdu; if English, reply in English).

YOUR ROLE:
- Answer questions about medicines: uses, dosage, side effects, prices, Pakistani brands, alternatives.
- Use ONLY the provided drug context when answering specific medicine questions.
- If a question is outside your knowledge base, say so clearly in the user's language.

ALWAYS INCLUDE this safety disclaimer at the end of every medicine-related answer:
⚠️ Disclaimer: یہ معلومات صرف آگاہی کے لیے ہے / This is for informational purposes only. Always consult a licensed doctor or pharmacist before taking any medicine.

FORMATTING:
- Use bullet points and clear headings for medicine information.
- Keep answers concise but complete.
- For prices, always mention "PKR" currency.
- For dosage, always mention age group (neonatal/paediatric/adult).
"""


# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_messages(
    user_query: str,
    context_text: str = "",
    history: Optional[list] = None,
) -> list:
    """
    Build the full messages array for the Groq API call.
    history: list of {"role": "user"|"assistant", "content": "..."}
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject retrieved medicine context as a hidden system message
    if context_text.strip():
        messages.append({
            "role": "system",
            "content": (
                "RETRIEVED MEDICINE DATABASE CONTEXT (use this to answer):\n\n"
                + context_text
            ),
        })

    # Add conversation history (last N turns for memory)
    if history:
        # Only last MAX_HISTORY_TURNS exchanges
        tail = history[-(settings.MAX_HISTORY_TURNS * 2):]
        messages.extend(tail)

    # Add current user message
    messages.append({"role": "user", "content": user_query})

    return messages


# ── Main LLM Call ─────────────────────────────────────────────────────────────

def call_llm(
    user_query: str,
    context_text: str = "",
    history: Optional[list] = None,
    model: Optional[str] = None,
) -> dict:
    """
    Call Groq API with the given query + context + history.
    Returns: {"answer": str, "model_used": str, "tokens": int}
    Automatically falls back to LLaMA 3.3 70B if Qwen3 is rate-limited.
    """
    if not (settings.GROQ_API_KEY or "").strip():
        return {
            "answer": (
                "This server is not configured with a GROQ_API_KEY. "
                "Add your key to backend/.env (see .env.example), then restart the API."
            ),
            "model_used": "none",
            "tokens": 0,
        }

    client = _get_client()
    messages = build_messages(user_query, context_text, history or [])
    primary_model = model or settings.GROQ_MODEL

    def _messages_for_api(model_id: str) -> list:
        """Do not mutate shared `messages`; Qwen uses /no_think, other models get raw query."""
        use_no_think = "qwen" in model_id.lower()
        out: list = []
        for i, m in enumerate(messages):
            if i == len(messages) - 1 and m.get("role") == "user":
                text = user_query + (" /no_think" if use_no_think else "")
                out.append({**m, "content": text})
            else:
                out.append(dict(m))
        return out

    def _call(model_id: str) -> dict:
        response = client.chat.completions.create(
            model=model_id,
            messages=_messages_for_api(model_id),
            max_tokens=settings.GROQ_MAX_TOKENS,
            temperature=settings.GROQ_TEMPERATURE,
        )
        answer = response.choices[0].message.content
        # Strip Qwen3 reasoning blocks before returning to the user
        answer = _THINK_RE.sub('', answer).strip()
        tokens = response.usage.total_tokens if response.usage else 0
        return {"answer": answer, "model_used": model_id, "tokens": tokens}

    # Try primary model (Qwen3-32B)
    try:
        return _call(primary_model)
    except RateLimitError:
        print(f"[LLM] Rate limit on {primary_model}, falling back to {settings.GROQ_FALLBACK_MODEL}")
    except APIStatusError as e:
        print(f"[LLM] API error on {primary_model}: {e}, falling back")

    # Fallback to LLaMA 3.3 70B
    try:
        return _call(settings.GROQ_FALLBACK_MODEL)
    except Exception as e:
        print(f"[LLM] Fallback model failed: {e}")
        return {
            "answer": "Sorry, the AI service is temporarily unavailable. Please try again in a moment.",
            "model_used": "none",
            "tokens": 0,
        }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    test_cases = [
        # (query, context, description)
        ("What is Panadol used for?",         "",                      "English query"),
        ("Panadol kis liye use hoti hai?",    "",                      "Roman Urdu query"),
        ("پیناڈول کس لیے استعمال ہوتی ہے؟", "",                      "Urdu script query"),
        ("bukhaar mein konsi dawa leni chahiye?", "",                  "Roman Urdu general"),
        ("Is it safe to take Panadol with Aspirin?", "",               "Drug interaction English"),
    ]

    history = []
    print("=== LLM Self-Test (Qwen3-32B) ===\n")

    for query, context, desc in test_cases:
        print(f"[{desc}]")
        print(f"User: {query}")
        result = call_llm(query, context_text=context, history=history)
        print(f"Model: {result['model_used']} | Tokens: {result['tokens']}")
        print(f"Answer: {result['answer'][:300]}...")
        print()

        # Build memory for multi-turn
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": result["answer"]})

    print("=== All LLM tests complete! ===")
