# 💊 MedPak AI

**Smart Medicine Information, Better Health** — a bilingual (English + Urdu) AI-powered
medicine assistant built for Pakistan. Search 23,000+ medicine brands, compare **live
pharmacy prices**, discover **cheaper alternatives with the same salts**, scan medicine
boxes with OCR, and chat with an AI assistant in English, Urdu or Roman Urdu.

> ⚠️ **Disclaimer:** MedPak AI provides medicine *information only*. It does not diagnose,
> prescribe, or replace a licensed doctor or pharmacist.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔍 **Instant Medicine Search** | 23,332 Pakistani medicine brands / 1,956 generics, typo-tolerant fuzzy matching |
| 🧪 **Fixed-Dose Combination Aware** | Multi-salt products (e.g. Panadol CF) show their *complete* salt composition, and alternatives match the *exact same salt set* |
| 💰 **Live Price Scraping** | Real-time prices from Pakistani pharmacies (Dvago + search-engine fallback), 3-tier cached (memory → SQLite → live) |
| 📉 **Cheaper Alternatives (Apples-to-Apples)** | Strictly compares medicines of the *exact same dosage form* (Gel vs Gel) to prevent misleading savings, ranked by per-unit price. |
| 📷 **Scan Medicine Box** | Fast OCR (EasyOCR) reads a medicine box photo and finds it in the database. Auto-downscales high-res photos for speed. |
| 🤖 **Bilingual AI Chat** | RAG (ChromaDB) + Groq GPT-OSS 120B with strict information-only guardrails — answers in English, Urdu and Roman Urdu. |
| 🔐 **Secure by Design** | JWT auth, bcrypt password hashing, rate limiting, deterministic pre-LLM guardrails |

## 🏗️ Architecture

```
┌─────────────────────┐         ┌──────────────────────────────┐
│  React + Vite +     │  HTTP   │  FastAPI Backend             │
│  Tailwind CSS       │ ──────► │  ├── Auth (JWT + bcrypt)     │
│  (frontend/)        │  /api   │  ├── Medicine Search / RAG   │
└─────────────────────┘         │  ├── Live Price Scraper      │
                                │  ├── OCR Scanner (EasyOCR)   │
                                │  └── SQLite (pharmapedia.db) │
                                └──────────────┬───────────────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │  Groq GPT-OSS 120B  │
                                    │  (20B fallback)     │
                                    └─────────────────────┘
```

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (use source .venv/bin/activate on Linux/Mac)
pip install -r requirements.txt

copy .env.example .env          # then fill in the two required values:
```

| Variable | Where to get it |
|---|---|
| `GROQ_API_KEY` | Free key: [console.groq.com/keys](https://console.groq.com/keys) |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |

```bash
python main.py                  # API on http://127.0.0.1:8000 (docs at /docs)
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                     # app on http://localhost:5173
```

> The dev server proxies `/api` to the backend automatically. For production builds,
> set `VITE_API_BASE_URL` (see `frontend/.env.example`).

## 📁 Repository Layout

```
backend/    FastAPI app — routers, auth, RAG, OCR, price scrapers, pharmapedia.db
frontend/   React (Vite + Tailwind) SPA — search, details, alternatives, chat
DEPLOYMENT.md           Full deployment guide (Hugging Face Spaces + Vercel)
MedPak_AI_Project_Report.md    Detailed project report
```

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLite, ChromaDB, sentence-transformers, EasyOCR, httpx
- **LLM:** Groq (OpenAI-compatible) — GPT-OSS 120B primary, GPT-OSS 20B fallback
- **Frontend:** React 19, Vite, Tailwind CSS, lucide-react, react-markdown
- **Security:** JWT, bcrypt, slowapi rate limiting, deterministic guardrails

## 📜 License & Attribution

Medicine data derived from publicly available Pakistani pharmaceutical databases.
Prices are scraped from public pharmacy websites and may vary — always confirm at
the pharmacy.

---

*Built for a hackathon — feedback welcome!*
