"""
MedPak AI — API Integration Tests
Tests core API endpoints using FastAPI's TestClient.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


# ── Helper: register + login and return auth headers ──────────────────────────

_test_user_counter = 0
_cached_auth_headers = None

def _auth_headers() -> dict:
    """Register a fresh test user, login, cache, and return Authorization headers."""
    global _test_user_counter, _cached_auth_headers
    if _cached_auth_headers:
        return _cached_auth_headers
        
    _test_user_counter += 1
    email = f"test{_test_user_counter}@medpak.test"
    password = "TestPass123!"
    username = f"tester{_test_user_counter}"

    # Register (ignore if already exists)
    client.post("/api/auth/register", json={
        "email": email, "username": username, "password": password,
    })
    # Login
    resp = client.post("/api/auth/login", json={
        "email": email, "password": password,
    })
    data = resp.json()
    token = data.get("access_token") or data.get("token", "")
    _cached_auth_headers = {"Authorization": f"Bearer {token}"}
    return _cached_auth_headers


# ── Health endpoint (public) ──────────────────────────────────────────────────

def test_health_endpoint():
    resp = client.get("/api/health/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "database" in data


# ── Auth endpoints ────────────────────────────────────────────────────────────

def test_register_and_login():
    import time
    unique = int(time.time() * 1000)
    email = f"integration{unique}@medpak.test"
    password = "SecurePass123!"

    # Register
    resp = client.post("/api/auth/register", json={
        "email": email, "username": f"integ_{unique}", "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data or "token" in data

    # Login
    resp = client.post("/api/auth/login", json={
        "email": email, "password": password,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data or "token" in data


def test_login_wrong_password():
    resp = client.post("/api/auth/login", json={
        "email": "nonexistent@medpak.test", "password": "wrong",
    })
    assert resp.status_code in (401, 404)


# ── Protected endpoints require auth ─────────────────────────────────────────

def test_search_requires_auth():
    resp = client.get("/api/medicine/search?q=panadol")
    assert resp.status_code in (401, 403)


def test_search_with_auth():
    headers = _auth_headers()
    resp = client.get("/api/medicine/search?q=panadol", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] > 0


def test_search_short_query():
    headers = _auth_headers()
    resp = client.get("/api/medicine/search?q=a", headers=headers)
    # FastAPI validation: min_length=2
    assert resp.status_code == 422


def test_drug_detail_with_auth():
    headers = _auth_headers()
    # First search to get a drug_id
    search = client.get("/api/medicine/search?q=paracetamol", headers=headers)
    results = search.json().get("results", [])
    if results:
        drug_id = results[0]["drug_id"]
        resp = client.get(f"/api/medicine/{drug_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "drug" in data
        assert "dosage" in data
        assert "brands" in data


def test_drug_detail_not_found():
    headers = _auth_headers()
    resp = client.get("/api/medicine/999999", headers=headers)
    assert resp.status_code == 404


def test_alternatives_with_auth():
    headers = _auth_headers()
    search = client.get("/api/medicine/search?q=paracetamol", headers=headers)
    results = search.json().get("results", [])
    if results:
        drug_id = results[0]["drug_id"]
        form = results[0].get("form", "")
        strength = results[0].get("strength", "")
        brand = results[0].get("brand_product_name", "")
        url = f"/api/medicine/{drug_id}/alternatives?brand={brand}&form={form}&strength={strength}"
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "alternatives" in data
        assert "salt_name" in data
        assert "price_coverage" in data
