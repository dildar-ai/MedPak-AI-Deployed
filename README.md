# MedPak AI 🇵🇰💊
### Intelligent Bilingual Medicine Assistant for Pakistan

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?style=flat&logo=fastapi)
![React](https://img.shields.io/badge/React-19.2-61DAFB?style=flat&logo=react)
![Groq](https://img.shields.io/badge/LLM-Groq%20Qwen3--32B-orange?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

MedPak AI is a full-stack AI-powered medicine information system built specifically for Pakistan. Search any medicine by name or scan its box with your camera — get instant information about uses, side effects, dosages, Pakistani brands, prices in PKR, and cheaper alternatives. Chat with an AI assistant in English, Urdu, or Roman Urdu.

🌐 **Live Demo:** [medpak-ai.vercel.app](https://medpak-ai.vercel.app)

---

## 📸 Features

- 🔍 **Hybrid AI Search** — Keyword + vector semantic search combined. Understands "bukhaar ki dawa" → fever medicines
- 📸 **Medicine Box Scanner** — Photograph any medicine strip or box, OCR extracts the name and searches automatically
- 💬 **Bilingual AI Chatbot** — RAG-powered assistant with full session memory, responds in English, Urdu script, and Roman Urdu
- 🇵🇰 **Pakistan-Specific Data** — PKR prices, local brands, local pharmaceutical companies
- 💊 **Dosage by Age Group** — Neonatal, Paediatric, and Adult dosage information
- 💰 **Price Comparison** — Cheaper alternatives sorted by price to help patients save money
- 🧠 **Smart Rejection** — Greetings and gibberish don't return random medicine results
- ⚡ **LLM Fallback Chain** — Auto-switches from Qwen3-32B to LLaMA 3.3 70B if rate-limited
- 🔒 **Safety Disclaimers** — Every AI response includes a medical disclaimer

---

## 🏗️ System Architecture
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
│              BACKEND (FastAPI + Python)                  │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ Medicine     │  │ Chat       │  │ Health           │ │
│  │ Router       │  │ Router     │  │ Router           │ │
│  └──────┬───────┘  └─────┬──────┘  └──────────────────┘ │
│         │                │                               │
│  ┌──────┴───────┐  ┌─────┴──────┐  ┌──────────────────┐ │
│  │ RAG          │  │ LLM Client │  │ OCR Scanner      │ │
│  │ Retriever    │  │ (Groq)     │  │ (EasyOCR)        │ │
│  └──────┬───────┘  └─────┬──────┘  └──────────────────┘ │
│         │                │                               │
│  ┌──────┴───────┐  ┌─────┴──────┐                       │
│  │ ChromaDB     │  │ Memory     │                       │
│  │ VectorStore  │  │ (SQLite)   │                       │
│  └──────┬───────┘  └────────────┘                       │
│         │                                               │
│  ┌──────┴──────────────────────────────────────────┐   │
│  │         SQLite Database (pharmapedia.db)          │   │
│  │  DRUG | BRAND | BRAND_DRUG | COMPANY | Dosage    │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose | Version |
|---|---|---|
| Python | Core language | 3.10+ |
| FastAPI | REST API framework | ≥0.115 |
| SQLite | Relational database | Built-in |
| ChromaDB | Vector database for RAG | 1.0.7 |
| Sentence-Transformers | Text embeddings | ≥3.0 |
| Groq SDK | LLM API client | ≥0.28 |
| EasyOCR | Optical Character Recognition | ≥1.7 |
| Pydantic | Data validation | ≥2.11 |

### Frontend
| Technology | Purpose | Version |
|---|---|---|
| React | UI framework | 19.2 |
| Vite | Build tool | 8.0 |
| TailwindCSS | Styling | 3.4 |
| Axios | HTTP client | 1.15 |
| React Markdown | Markdown rendering in chat | 10.1 |
| Noto Nastaliq Urdu | Google Font for Urdu text | — |

### AI Models
| Model | Provider | Purpose |
|---|---|---|
| Qwen3-32B | Groq Cloud | Primary LLM — best Urdu support |
| LLaMA 3.3 70B | Groq Cloud | Fallback LLM |
| all-MiniLM-L6-v2 | HuggingFace (local) | Sentence embeddings for RAG |
| EasyOCR CRAFT | Local | Text detection in images |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API Key — free at [console.groq.com](https://console.groq.com)

### 1. Clone the Repository
```bash
git clone https://github.com/dildar-ai/medpak-ai.git
cd medpak-ai
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:
GROQ_API_KEY=your_groq_api_key_here

Build the RAG vector index (one-time):
```bash
python rag/vectorstore.py
```

Start the backend server:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Backend runs at: `http://localhost:8000`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Health check + database stats |
| GET | `/api/medicine/search?q=` | Search medicines by name or salt |
| POST | `/api/medicine/scan` | OCR scan image + search |
| GET | `/api/medicine/{id}` | Full drug profile |
| GET | `/api/medicine/{id}/alternatives` | Cheaper alternatives sorted by price |
| GET | `/api/medicine/interactions/{id1}/{id2}` | Drug interaction check |
| POST | `/api/chat/message` | Send message to AI chatbot |
| GET | `/api/chat/sessions` | List all chat sessions |
| GET | `/api/chat/history/{id}` | Get session conversation history |

---

## 🧠 How RAG Works

Without RAG, searching "fever medicine" returns nothing because no medicine is literally named that. RAG solves this by understanding meaning:
User types "bukhaar ki dawa"
→ Sentence-Transformers encodes query to 384-dim vector
→ ChromaDB finds nearest drug vectors by cosine similarity
→ Merged with keyword SQL results
→ Enriched drug data returned to LLM as context
→ LLM answers naturally in user's language

Similarity threshold: **≥ 0.45** — below this, results are filtered out to prevent irrelevant matches.

---

## 📁 Project Structure
medpak-ai/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Environment & settings
│   ├── requirements.txt
│   ├── pharmapedia.db        # SQLite medicine database
│   ├── database/
│   │   └── db.py             # All database query functions
│   ├── rag/
│   │   └── vectorstore.py    # ChromaDB vector index builder
│   ├── llm/
│   │   └── groq_client.py    # Groq API + fallback chain
│   ├── ocr/
│   │   └── scanner.py        # EasyOCR medicine scanner
│   └── routers/
│       ├── medicine.py       # Medicine search/scan endpoints
│       ├── chat.py           # Chatbot endpoints
│       └── health.py         # Health check endpoint
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── MedicineCard.jsx
│   │   │   ├── MedicineDetail.jsx
│   │   │   └── Chatbot.jsx
│   │   └── lib/
│   │       └── api.js        # Axios API client
│   ├── package.json
│   └── vite.config.js
└── README.md

---

## 🔮 Future Enhancements

- [ ] User authentication — save personal medicine lists
- [ ] Voice input — speak medicine names in Urdu
- [ ] Mobile app — React Native wrapper
- [ ] Prescription scanner — OCR for handwritten prescriptions
- [ ] Medicine reminders — notification system
- [ ] Drug interaction checker UI — select two medicines and check conflicts

---

## ⚠️ Disclaimer

MedPak AI is for **informational purposes only**. Always consult a qualified doctor or pharmacist before taking any medicine. Do not use this app as a substitute for professional medical advice.

---

## 👨‍💻 Author

**Dildar Hassan**
B.S. Artificial Intelligence — Superior University Faisalabad
- GitHub: [@dildar-ai](https://github.com/dildar-ai)
- LinkedIn: [dildar-hussain-51214d](https://linkedin.com/in/dildar-hussain-51214d)

---

## 📄 License

This project is licensed under the MIT License.
