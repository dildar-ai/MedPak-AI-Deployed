# MedPak AI — Complete Project Report
### Intelligent Bilingual Medicine Assistant for Pakistan
**Version:** 1.1.0 | **Date:** September 2026

---

## Table of Contents
1. Project Overview
2. Problem Statement & Objectives
3. System Architecture
4. Technology Stack
5. Database Design
6. Backend — Module-by-Module Breakdown
7. Frontend — Component-by-Component Breakdown
8. RAG Pipeline (AI Search)
9. LLM Integration (Groq + GPT-OSS)
10. OCR System (Medicine Box Scanning)
11. Key Features Summary
12. API Endpoints Reference
13. How to Run the Project
14. Future Enhancements

---

## 1. Project Overview

**MedPak AI** is a full-stack web application that serves as an intelligent, bilingual (English + Urdu) medicine information system tailored specifically for Pakistan. It allows users to:

- **Search** for any medicine by brand name, generic/salt name, or by scanning a medicine box image
- **View** comprehensive drug profiles including uses, side effects, dosage by age group, and cheaper alternatives with prices in PKR
- **Chat** with an AI-powered medical assistant that understands English, Urdu script, and Roman Urdu

The system combines a traditional relational database (SQLite) with modern AI technologies including **Retrieval Augmented Generation (RAG)**, **Large Language Models (LLMs)**, and **Optical Character Recognition (OCR)**.

---

## 2. Problem Statement & Objectives

### Problem
In Pakistan, patients often lack access to reliable, understandable medicine information in their own language. Existing resources are English-only, fragmented across websites, and don't provide price comparisons or cheaper alternatives — critical for a price-sensitive market.

### Objectives
1. Build a searchable database of Pakistani medicines with brands, prices, and companies
2. Provide bilingual information (English + Urdu) for accessibility
3. Use AI to enable natural-language queries ("bukhaar ki dawa" → fever medicines)
4. Allow scanning medicine boxes via camera/upload to identify medicines
5. Offer an AI chatbot for interactive medical guidance
6. Show cheaper alternatives to help patients save money

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)               │
│  ┌──────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Home │  │ SearchBar │  │ Chatbot  │  │ Medicine  │  │
│  │      │  │ + OCR     │  │ (AI)     │  │ Detail    │  │
│  └──┬───┘  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  │
│     └────────────┴─────────────┴───────────────┘        │
│                        │ Axios HTTP                      │
└────────────────────────┼────────────────────────────────┘
                         │ /api/*
┌────────────────────────┼────────────────────────────────┐
│              BACKEND (FastAPI + Python)                   │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ Medicine     │  │ Chat       │  │ Health           │  │
│  │ Router       │  │ Router     │  │ Router           │  │
│  └──────┬──────┘  └─────┬──────┘  └──────────────────┘  │
│         │               │                                │
│  ┌──────┴──────┐  ┌─────┴──────┐  ┌──────────────────┐  │
│  │ RAG         │  │ LLM Client │  │ OCR Scanner      │  │
│  │ Retriever   │  │ (Groq)     │  │ (EasyOCR)        │  │
│  └──────┬──────┘  └─────┬──────┘  └──────────────────┘  │
│         │               │                                │
│  ┌──────┴──────┐  ┌─────┴──────┐                        │
│  │ ChromaDB    │  │ Memory     │                        │
│  │ VectorStore │  │ (SQLite)   │                        │
│  └──────┬──────┘  └────────────┘                        │
│         │                                                │
│  ┌──────┴──────────────────────────────────────────┐    │
│  │           SQLite Database (pharmapedia.db)        │    │
│  │  DRUG | BRAND | BRAND_DRUG | COMPANY | Dosage    │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. User types a query or uploads an image on the frontend
2. Frontend sends HTTP request to FastAPI backend via Axios
3. Backend processes through the appropriate pipeline (Search/Chat/OCR)
4. Results are returned as JSON and rendered in the React UI

---

## 4. Technology Stack

### Backend
| Technology | Purpose | Version |
|---|---|---|
| **Python** | Core language | 3.10+ |
| **FastAPI** | REST API framework | ≥0.115 |
| **Uvicorn** | ASGI server | ≥0.34 |
| **SQLite** | Relational database | Built-in |
| **ChromaDB** | Vector database for RAG | 1.0.7 |
| **Sentence-Transformers** | Text embeddings | ≥3.0 |
| **OpenAI SDK** | Groq LLM API client | ≥1.0 |
| **EasyOCR** | Optical Character Recognition | ≥1.7 |
| **Pillow** | Image processing | ≥10.0 |
| **Pydantic** | Data validation | ≥2.11 |

### Frontend
| Technology | Purpose | Version |
|---|---|---|
| **React** | UI framework | 19.2 |
| **Vite** | Build tool / dev server | 8.0 |
| **TailwindCSS** | Utility-first CSS | 3.4 |
| **Axios** | HTTP client | 1.15 |
| **Lucide React** | Icon library | 1.14 |
| **React Markdown** | Markdown rendering in chat | 10.1 |
| **Noto Nastaliq Urdu** | Google Font for Urdu text | — |

### AI Models
| Model | Provider | Purpose |
|---|---|---|
| **GPT-OSS 120B** | Groq (free tier) | Primary LLM (strong multilingual + reasoning) |
| **GPT-OSS 20B** | Groq (free tier) | Fallback LLM (faster) |
| **all-MiniLM-L6-v2** | HuggingFace (local) | Sentence embeddings for RAG |
| **EasyOCR CRAFT** | Local | Text detection in images |

---

## 5. Database Design

The SQLite database `pharmapedia.db` contains **7 tables**:

### DRUG Table (Generic/Salt Information)
| Column | Description |
|---|---|
| CODE (PK) | Unique drug identifier |
| NAME | Generic/salt name (e.g., "Paracetamol") |
| OVERVIEW | General description |
| INDICATIONS | What the drug is used for |
| CONTRAINDICATIONS | When NOT to use |
| INTERACTIONS | Drug-drug interactions |
| EFFECTS | Side effects |
| WARNINING | Safety warnings |
| STORAGE | Storage instructions |

### BRAND Table
| Column | Description |
|---|---|
| BID (PK) | Brand ID |
| BNAME | Brand company name |
| CID (FK) | Links to COMPANY table |

### BRAND_DRUG Table (Product Variants)
| Column | Description |
|---|---|
| NAME | Product name (e.g., "Panadol Extra") |
| FORM | Tablet, Syrup, Injection, etc. |
| PACKING | Pack size (e.g., "10's", "100ml") |
| TRADEPRICE | Wholesale price |
| RETAILPRICE | Consumer price in PKR |
| MG | Strength (e.g., "500mg") |
| DID (FK) | Links to DRUG.CODE |
| BID (FK) | Links to BRAND.BID |

### COMPANY Table
| Column | Description |
|---|---|
| ID (PK) | Company ID |
| NAME | Pharmaceutical company name |
| ADDRESS, PHONE, FAX | Contact details |

### Dosage Tables (3 tables: Neonatal, Paedriatic, adult)
| Column | Description |
|---|---|
| DOSE | Recommended dosage |
| SINGLE | Maximum single dose |
| FREQ | Frequency (e.g., "3 times daily") |
| ROUTE | Administration route (Oral, IV, etc.) |
| INSTRUCTION | Special instructions |
| CODE (FK) | Links to DRUG.CODE |

### Relationships
```
DRUG (1) ←──→ (N) BRAND_DRUG ←──→ (1) BRAND ←──→ (1) COMPANY
DRUG (1) ←──→ (N) Neonatal / Paedriatic / adult
```

---

## 6. Backend — Module-by-Module Breakdown

### 6.1 `main.py` — Application Entry Point
- Creates the FastAPI app instance with CORS middleware
- Registers four routers: `/api/health`, `/api/auth`, `/api/medicine`, `/api/chat`
- CORS is configured to accept requests from all common Vite dev ports (5173, 5174, 5175, 4173)

### 6.2 `config.py` — Configuration Management
- Uses **Pydantic Settings** to load environment variables from `.env` file
- Defines all configurable parameters: database paths, API keys, model names, temperature, token limits
- Supports `GROQ_API_KEY` for LLM authentication (Groq free tier)
- Configurable `OCR_USE_GPU` flag (defaults to False for CPU-only machines)

### 6.3 `database/db.py` — Database Query Layer
**Major functions:**

| Function | Purpose |
|---|---|
| `search_medicines(query)` | SQL LIKE search across BRAND_DRUG, BRAND, and DRUG tables |
| `get_drug_by_id(drug_id)` | Full drug profile by CODE |
| `get_drug_by_name(name)` | Partial match on drug NAME |
| `get_brand_variants(drug_id)` | All Pakistani brands for a generic drug |
| `get_alternatives(drug_id)` | Cheaper alternative brands, sorted by price |
| `get_cheapest_alternative(drug_id)` | Single cheapest option |
| `enrich_drugs_for_cards(drugs)` | Merges DRUG data with brand data for frontend cards |
| `get_dosage(drug_id)` | Dosage split by age group (neonatal/paediatric/adult) |
| `get_db_stats()` | Record counts for health check |
| `get_brand_product_salts(name)` | All salts in a combination product (e.g. Panadol CF) |
| `get_brand_variants_multi(ids)` | Brand variants across multiple salts |

**Key design decisions:**
- Database is opened in **read-only** mode (`?mode=ro`) for safety
- Prices are cleaned from string format ("1,234.56") to float using regex
- `enrich_drugs_for_cards()` creates a unified data shape that the frontend can always rely on
- Fixed-dose combinations (e.g. Panadol CF) are stored as one row per salt — helpers resolve the full salt set so search cards and alternatives compare like-for-like

### 6.4 `routers/medicine.py` — Medicine REST API

| Endpoint | Method | Description |
|---|---|---|
| `/api/medicine/search?q=` | GET | Hybrid RAG search (AI + keyword) |
| `/api/medicine/scan` | POST | Upload image → OCR → search |
| `/api/medicine/{drug_id}` | GET | Full drug details + brands + dosage |
| `/api/medicine/{drug_id}/alternatives` | GET | Cheaper alternatives list |
| `/api/medicine/interactions/{id1}/{id2}` | GET | Drug interaction check |
| `/api/medicine/live-price?brand=&strength=` | GET | Live price for one brand |
| `/api/medicine/prices/refresh` | POST | Force a fresh price scrape |
| `/api/auth/register` / `/api/auth/login` | POST | JWT authentication |

**Search Flow:**
1. User query goes to `retrieve_context()` (RAG retriever)
2. RAG combines vector search + keyword search results
3. Results are enriched via `enrich_drugs_for_cards()` for card display
4. Returns JSON with `results[]` array

**Scan Flow:**
1. Image is validated (must be image/*, ≤10MB)
2. Passed to EasyOCR for text extraction
3. Largest text block is used as search query
4. Results go through the same RAG + enrich pipeline

### 6.5 `routers/chat.py` — Chat API

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat/message` | POST | Send message, get AI response |
| `/api/chat/sessions` | GET | List all past sessions |
| `/api/chat/history/{id}` | GET | Get full session history |

**Chat Flow:**
1. User message is received with optional `session_id`
2. RAG retriever finds relevant drug context
3. Context is formatted into a text block
4. Chat history is loaded from memory
5. Everything is sent to Groq (GPT-OSS 120B)
6. Response is saved to history and returned

### 6.6 `llm/llm_client.py` — LLM Integration (Groq)

**System Prompt** instructs the AI to:
- Provide initial medicine answers in BOTH English and Urdu script
- After initial response, mirror the user's language
- Always include a safety disclaimer
- Use bullet points, PKR currency, age groups for dosage
- Only use provided drug context for medicine-specific answers

**API:** Uses the OpenAI SDK with Groq's OpenAI-compatible endpoint. The layer is provider-agnostic — pointing base URL/model/key at any compatible provider (e.g. Alibaba Cloud DashScope) requires no code changes.

**Fallback Strategy:**
```
User Query → GPT-OSS 120B (Primary, Groq)
                 ↓ (if rate-limited)
             GPT-OSS 20B (Fallback, Groq)
                 ↓ (if also fails)
             Graceful error message
```

**`<think>` Tag Handling:**
GPT-OSS models may output internal reasoning in `<think>...</think>` blocks. These are stripped using a regex before the response reaches the user.

### 6.7 `llm/memory.py` — Conversation Memory (126 lines)
- **In-memory store**: Dictionary of session_id → message list
- **SQLite persistence**: `history.db` stores all conversations permanently
- **Auto-trimming**: Only last N turns (configurable, default 5) are sent to the LLM to manage token limits
- **Thread-safe**: Uses `threading.Lock` for concurrent access

### 6.8 `rag/vectorstore.py` — Vector Database (167 lines)
- Uses **ChromaDB** (persistent storage) to store drug embeddings
- **Embedding model**: `all-MiniLM-L6-v2` (runs locally, no API needed)
- Each drug's NAME + INDICATIONS + EFFECTS are concatenated into a single text, then embedded as a 384-dimensional vector
- **Cosine similarity** search finds semantically similar drugs

### 6.9 `rag/retriever.py` — Hybrid RAG Retriever (165 lines)

**The core intelligence of the search system.** Combines two search strategies:

| Strategy | How It Works | Good For |
|---|---|---|
| **Keyword Search** | SQL `LIKE '%query%'` on brand/drug/salt names | Exact matches ("Panadol") |
| **Vector Search** | Cosine similarity on embeddings | Semantic queries ("fever tablet") |

**Smart Query Rejection:**
- Greetings ("Hi", "Hello", "Salam") are detected via regex and instantly rejected — returning 0 results instead of irrelevant medicines
- Queries shorter than 2 characters are rejected
- Vector results below a **0.45 similarity threshold** are filtered out

**Pipeline:**
```
Query → Non-medical check → Keyword Search → Vector Search
          ↓ (reject)              ↓                ↓
        0 results          Exact matches    Semantic matches
                                  ↓                ↓
                           Merge & Deduplicate (keyword priority)
                                       ↓
                              Fetch full drug details
                                       ↓
                              Return context dict
```

### 6.10 `ocr/scanner.py` — Medicine Box Scanner (90 lines)
- Uses **EasyOCR** with English language model
- First run downloads ~200MB model weights (cached permanently)
- **Heuristic**: Sorts detected text blocks by bounding box area — largest text is assumed to be the medicine brand name
- Handles Windows terminal encoding issues (`UnicodeEncodeError` fix)
- Falls back to CPU if GPU initialization fails

---

## 7. Frontend — Component-by-Component Breakdown

### 7.1 Application Structure
```
src/
├── main.jsx          # React entry point
├── App.jsx           # Root component with mode routing
├── index.css         # Global styles, Tailwind, Urdu font
├── lib/
│   └── api.js        # Axios HTTP client (all API calls)
└── components/
    ├── Header.jsx    # Sticky header with clickable logo
    ├── Auth.jsx      # Login / signup screen (JWT)
    ├── Home.jsx      # Landing page with feature highlights
    ├── SearchBar.jsx # Search input + one-tap examples + OCR buttons
    ├── MedicineCard.jsx  # Grid card for search results (full salt composition)
    ├── MedicineDetail.jsx # Full drug profile with tabs
    └── Chatbot.jsx   # Full-screen AI chat interface
```

### 7.2 `App.jsx` — Root Component & State Manager
- Manages three **modes**: `home`, `search`, `chat`
- Holds all search state (results, loading flags, selected drug)
- `goHome()` resets all state and returns to landing page
- `handleSearch()` calls `/api/medicine/search` → populates grid
- `handleScan()` calls `/api/medicine/scan` → shows scanned text banner + results
- `handleCardClick()` navigates to drug detail view

### 7.3 `Home.jsx` — Landing Page
- Two large interactive cards: "Search Medicine" and "Chat with AI"
- "Powered by AI • پاکستان کے لیے" badge
- Hover animations with glow effects
- Footer medical disclaimer in English + Urdu

### 7.4 `SearchBar.jsx` — Search & OCR Interface
- Text input with search icon and clear button
- Two OCR buttons below a divider: **"Take Photo"** (opens camera) and **"Upload Image"** (file picker)
- Scanning indicator: "Scanning image... This may take a moment on first use"
- Auto-focus on mount

### 7.5 `MedicineCard.jsx` — Result Card
- Displays: brand name, salt name, form, strength, packing, company, price in PKR
- Hover effect with card lift animation
- "View full details →" call-to-action
- Defensive data access — never shows "undefined"

### 7.6 `MedicineDetail.jsx` — Drug Profile (Tabbed)
**Four tabs:**

| Tab | Content |
|---|---|
| **Information** | Overview, Uses/Indications, Side Effects, Contraindications, Warnings, Storage |
| **Dosage** | Split by age: Neonatal (purple), Paediatric (blue), Adult (green) |
| **Alternatives** | Live price comparison — same salt set, same dosage form, per-unit savings |
| **Ask AI** | Inline RAG chat about this specific medicine |

- Every section header is **bilingual**: "Overview / جائزہ", "Side Effects / مضر اثرات"
- Empty states have Urdu messages
- Color-coded dosage cards by age group

### 7.7 `Chatbot.jsx` — AI Chat Interface
- Full-screen conversational UI with gradient header
- Welcome message in English + Urdu
- User messages appear right-aligned (green), AI messages left-aligned (white)
- AI responses rendered as **Markdown** (supports bold, bullets, headings)
- Urdu text detected automatically and rendered with `Noto Nastaliq Urdu` font
- Client-side `<think>` tag stripping as safety net
- Auto-scroll to latest message
- Shows actual server error details instead of generic messages

### 7.8 `lib/api.js` — API Client
- Uses **Vite proxy** in development (`/api` → `http://127.0.0.1:8000/api`)
- Eliminates CORS issues during development
- Exports `medicineApi` (search, scan, getDetails, getAlternatives, checkInteractions)
- Exports `chatApi` (sendMessage, getHistory, getSessions)

### 7.9 Styling (`index.css` + `tailwind.config.js`)
- **Google Fonts**: Inter (UI) + Noto Nastaliq Urdu (Urdu text)
- **Custom components**: `.glass-card`, `.btn-primary`, `.input-search`, `.badge`, `.font-urdu`
- **Color system**: Green primary palette (medical/health theme)
- **Animations**: `fadeIn`, `slideUp`, `pulse-slow`
- **Custom scrollbar**: 8px wide, slate-colored, visible track

---

## 8. RAG Pipeline — Detailed Explanation

**RAG (Retrieval Augmented Generation)** is the technique that makes the search intelligent.

### Why RAG?
Without RAG, searching "fever medicine" would return nothing because no medicine is literally named "fever medicine". RAG solves this by understanding the *meaning* behind words.

### How It Works

**Step 1: Indexing (One-time setup)**
```
All drugs from SQLite → Concatenate (Name + Indications + Effects)
    → Sentence-Transformers encodes each → 384-dim vector
        → Stored in ChromaDB collection
```

**Step 2: Query Time**
```
User types "bukhaar ki dawa" (Roman Urdu for "fever medicine")
    → Sentence-Transformers encodes query → 384-dim vector
        → ChromaDB finds nearest neighbors by cosine similarity
            → Returns drug IDs with scores
```

**Step 3: Hybrid Merge**
```
Keyword results (SQL LIKE) + Vector results (ChromaDB)
    → Deduplicate → Keyword results get priority
        → Fetch full drug details from SQLite
            → Return enriched context
```

### Threshold System
- Vector similarity score ≥ **0.45** → result is accepted
- Below 0.45 → result is filtered out (prevents "Hi" → "Thiyomine")

---

## 9. LLM Integration — How the AI Chat Works

### Request Flow
```
User: "Panadol kis liye use hoti hai?"
    ↓
1. RAG Retriever finds Paracetamol drug data
    ↓
2. Context formatted: "Drug: Paracetamol, Indications: ..., Brands: Panadol 500mg Rs.15..."
    ↓
3. System prompt + context + chat history + user message assembled
    ↓
4. Sent to Groq API → GPT-OSS 120B processes
    ↓
5. Response stripped of <think> tags
    ↓
6. Saved to memory → Returned to frontend
```

### Why GPT-OSS on Groq?
- **Free tier** — generous limits, perfect for demos and hackathons
- **Fast inference** — Groq's LPU serving keeps chat responses snappy
- Handles code-switching (mixing English + Urdu in one sentence)
- Understands Urdu script (اردو), Roman Urdu, and English equally well
- **OpenAI-compatible API** — provider-agnostic: switch to Alibaba Cloud DashScope or any compatible endpoint via 3 env vars

### Fallback Chain
If GPT-OSS 120B is rate-limited → automatically falls back to GPT-OSS 20B → if that also fails → returns a graceful error message.

### Live Price Integration
When the RAG retriever builds context for the LLM, it now checks for **live scraped prices** from Pakistani pharmacy websites. If a live price is available (less than 72 hours old), it is included in the context alongside or instead of the database price. This means the AI chatbot always has access to current market prices when answering medicine questions.

---

## 10. OCR System — Medicine Box Scanning

### Flow
```
User captures/uploads photo
    ↓
Frontend sends as multipart/form-data
    ↓
Backend validates (must be image, ≤10MB)
    ↓
EasyOCR detects all text regions in image
    ↓
Heuristic: sort text blocks by bounding box AREA
    ↓
Largest text = likely brand name (e.g., "PANADOL")
    ↓
Feed into RAG search pipeline
    ↓
Return results + scanned text info
```

### First-Run Behavior
EasyOCR downloads ~200MB of detection + recognition models on first use. This is a one-time download cached at `~/.EasyOCR/`.

---

## 11. Key Features Summary

| Feature | Description |
|---|---|
| **Hybrid AI Search** | Keyword + Vector semantic search combined |
| **Medicine Box Scanner** | Camera or upload → OCR → auto-search |
| **AI Chatbot** | RAG-powered, bilingual, session memory |
| **Pakistani Focus** | PKR prices, local brands, local companies |
| **Bilingual UI** | English + Urdu script (Noto Nastaliq font) |
| **Dosage by Age** | Neonatal / Paediatric / Adult dosage info |
| **Price Comparison** | Live-priced alternatives matched by salt set & dosage form |
| **Live Price Scraping** | 3-tier cache (memory → DB → web) with 72hr persistence |
| **Smart Rejection** | Greetings/gibberish don't return random medicines |
| **Groq GPT-OSS AI** | GPT-OSS 120B/20B via Groq (free tier) |
| **Safety Disclaimers** | Every AI response includes medical disclaimer |

---

## 12. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Health check + DB stats |
| GET | `/api/medicine/search?q=` | Search medicines |
| POST | `/api/medicine/scan` | OCR scan + search |
| GET | `/api/medicine/{id}` | Drug details |
| GET | `/api/medicine/{id}/alternatives` | Cheaper alternatives |
| GET | `/api/medicine/interactions/{id1}/{id2}` | Drug interaction check |
| GET | `/api/medicine/live-price?brand=&strength=` | Live price for one brand |
| POST | `/api/medicine/prices/refresh` | Force a fresh price scrape |
| POST | `/api/auth/register` | Create account (JWT) |
| POST | `/api/auth/login` | Log in (JWT) |
| POST | `/api/chat/message` | Send chat message |
| GET | `/api/chat/sessions` | List chat sessions |
| GET | `/api/chat/history/{id}` | Session history |

---

## 13. How to Run the Project

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API Key (free at console.groq.com/keys)

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Create .env file with: GROQ_API_KEY=your_key_here
# Get free key from: https://console.groq.com/keys
python rag/vectorstore.py      # Build RAG index (first time)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### First-Time RAG Index Build
```bash
cd backend
python rag/vectorstore.py
```

### Cloud Deployment
Backend → Hugging Face Spaces (Docker) · Frontend → Vercel. Full step-by-step guide in `DEPLOYMENT.md`.

---

## 14. Future Enhancements

1. **Personal Medicine Lists** — saved lists per user (JWT auth already shipped)
2. **Drug Interaction Checker UI** — Select two medicines and check conflicts
3. **Voice Input** — Speak medicine names in Urdu
4. **Mobile App** — React Native wrapper
5. **Prescription Scanner** — OCR for doctor prescriptions
6. **Price Alerts** — Notify when a medicine's live price drops
7. **Notification System** — Medicine reminders

---

*This document covers the complete MedPak AI project architecture, implementation, and technical decisions. Good luck with your evaluation! 🎓*
