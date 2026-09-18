"""
MedPak AI — Guard Unit Tests
Tests the pre-LLM input guardrails (check_query_guards) to ensure:
  - Legitimate medicine questions pass through to the LLM
  - Suggestion/diagnosis/emergency/off-topic requests are blocked
  - Greetings receive a friendly welcome
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from llm.guard import check_query_guards


# ── Allowed queries (should return None → forwarded to LLM) ──────────────────

ALLOWED_QUERIES = [
    "What is Panadol used for?",
    "Panadol ke side effects kya hain?",
    "Is it safe to take Panadol with Aspirin?",
    "What is the difference between Brufen and Panadol?",
    "What does extended release mean?",
    "How is paracetamol metabolized?",
    "What is the price of Brufen?",
    "hi, what is panadol used for?",       # greeting + real question → LLM
]

@pytest.mark.parametrize("query", ALLOWED_QUERIES)
def test_allowed_queries_pass_through(query):
    """Legitimate medicine questions must NOT be blocked."""
    result = check_query_guards(query)
    assert result is None, f"Query was wrongly blocked: {query!r} → reason={result.get('reason')}"


# ── Blocked: medicine suggestion requests ─────────────────────────────────────

SUGGESTION_QUERIES = [
    "Which medicine should I take for fever?",
    "What medicine can I take for headache?",
    "konsi dawa lun bukhaar ke liye?",
    "Suggest me a medicine for cough",
    "Can you prescribe something for pain?",
]

@pytest.mark.parametrize("query", SUGGESTION_QUERIES)
def test_suggestion_requests_blocked(query):
    result = check_query_guards(query)
    assert result is not None, f"Suggestion query was NOT blocked: {query!r}"
    assert result["reason"] == "suggestion"


# ── Blocked: diagnosis requests ───────────────────────────────────────────────

DIAGNOSIS_QUERIES = [
    "What illness do I have? I have fever.",
    "Diagnose me please",
    "mujhe kya hua hai?",
]

@pytest.mark.parametrize("query", DIAGNOSIS_QUERIES)
def test_diagnosis_requests_blocked(query):
    result = check_query_guards(query)
    assert result is not None, f"Diagnosis query was NOT blocked: {query!r}"
    assert result["reason"] == "diagnosis"


# ── Blocked: emergencies ──────────────────────────────────────────────────────

EMERGENCY_QUERIES = [
    "I took 20 tablets of Panadol, what do I do?",
    "I want to kill myself",
]

@pytest.mark.parametrize("query", EMERGENCY_QUERIES)
def test_emergency_requests_caught(query):
    result = check_query_guards(query)
    assert result is not None, f"Emergency query was NOT caught: {query!r}"
    assert result["reason"] == "emergency"


# ── Blocked: off-topic ────────────────────────────────────────────────────────

OFF_TOPIC_QUERIES = [
    "Write a poem about the ocean.",
    "Can you write me a short story?",
    "Tell me a joke",
    "koi shayari sunao",
]

@pytest.mark.parametrize("query", OFF_TOPIC_QUERIES)
def test_off_topic_requests_blocked(query):
    result = check_query_guards(query)
    assert result is not None, f"Off-topic query was NOT blocked: {query!r}"
    assert result["reason"] == "off_topic"


# ── Blocked: greetings → friendly welcome ─────────────────────────────────────

GREETING_QUERIES = [
    "hi",
    "Hello!",
    "salam sir",
    "Assalam o Alaikum",
]

@pytest.mark.parametrize("query", GREETING_QUERIES)
def test_greetings_return_welcome(query):
    result = check_query_guards(query)
    assert result is not None, f"Greeting was NOT caught: {query!r}"
    assert result["reason"] == "greeting"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_string_passes():
    assert check_query_guards("") is None

def test_whitespace_only_passes():
    assert check_query_guards("   ") is None

def test_none_passes():
    assert check_query_guards(None) is None
