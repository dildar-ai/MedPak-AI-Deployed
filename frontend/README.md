# MedPak AI — Frontend

React + Vite + TailwindCSS frontend for **MedPak AI**, a bilingual (English + Urdu)
medicine information assistant for Pakistan.

## Features

- 🔍 **Medicine search** — by brand, salt, or strength, with one-tap examples
- 💰 **Live prices** — scraped from Pakistani pharmacies (never outdated DB prices)
- 💊 **Alternatives** — same salt set, same dosage form, compared per unit
- 📷 **Box scanning** — camera / upload → OCR → instant search
- 🤖 **AI chat** — English, Urdu script, and Roman Urdu
- 🔐 **JWT authentication** — register / login

## Development

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api to localhost:8000)
```

## Production build

```bash
npm run build      # outputs to dist/
```

Set `VITE_API_BASE_URL` (e.g. `https://<your-space>.hf.space/api`) when the
backend is not on localhost — see the root `DEPLOYMENT.md`.

## Tech

React 19 · Vite 8 · TailwindCSS 3 · Axios · Lucide icons · react-markdown ·
Noto Nastaliq Urdu font for اردو text.
