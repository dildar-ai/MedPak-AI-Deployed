---
title: MedPak AI Backend
emoji: 💊
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# MedPak AI — Backend API

FastAPI backend for **MedPak AI**, a bilingual (English + Urdu) medicine
assistant for Pakistan:

- 🔍 Search 23,000+ Pakistani medicine brands / 1,956 generics
- 💰 **Live prices** scraped from Pakistani pharmacies (Dvago + SERP), cached in 3 tiers
- 💊 Cheaper alternatives matched by **salt set + dosage form + per-unit price**
- 🤖 RAG chat (ChromaDB + Groq GPT-OSS) in English, Urdu and Roman Urdu
- 📷 OCR medicine-box scanning (EasyOCR)
- 🔐 JWT auth, rate limiting, strict information-only guardrails

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health/` | Health check + DB stats |
| POST | `/api/auth/register` `/api/auth/login` | JWT auth |
| GET | `/api/medicine/search?q=` | Search medicines |
| POST | `/api/medicine/scan` | OCR scan + search |
| GET | `/api/medicine/{id}` | Drug details + full salt set |
| GET | `/api/medicine/{id}/alternatives` | Live-priced alternatives |
| POST | `/api/chat/message` | Bilingual AI chat |

Full docs at `/docs` (Swagger UI).

## Secrets (Settings → Variables and secrets)

| Name | Value |
|---|---|
| `GROQ_API_KEY` | Groq API key — [console.groq.com/keys](https://console.groq.com/keys) |
| `SECRET_KEY` | Long random string (JWT signing) |
| `CORS_ORIGINS` | `["*"]` |
| `DEBUG` | `false` |

---

*Smart Medicine Information, Better Health*
