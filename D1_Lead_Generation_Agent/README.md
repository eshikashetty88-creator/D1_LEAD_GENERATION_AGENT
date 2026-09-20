# D1 – Autonomous Lead Generation & Qualification Agent

A hackathon-ready multi-agent pipeline for:

ICP intake → discovery → robots.txt compliance → enrichment → deduplication → scoring → CSV/HubSpot export → refresh.

## Agents
1. Discovery Agent – searches public sources using Serper.
2. Enrichment Agent – extracts firmographic signals with Gemini from pages that passed robots.txt.
3. Deduplication Agent – deterministic Pandas-based company/email/domain normalization.
4. Qualification/Scoring Agent – applies a transparent 100-point ICP rubric.
5. Export Agent – writes CRM-ready CSV files.

## Compliance
- Only public business information is used.
- The app checks robots.txt with Python `urllib.robotparser` before fetching a page.
- Disallowed URLs are skipped and logged.
- Unknown information is never fabricated.
- Personal contact information is not scraped from private sources.
- A mock-data mode is included for demo reliability.

## Run locally

### 1. Create and activate a virtual environment
Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure keys
Copy `.env.example` to `.env` and add:
- `GEMINI_API_KEY`
- `SERPER_API_KEY`

Never commit `.env`.

### 4. Run Streamlit
```bash
streamlit run frontend/app.py
```

### 5. Optional FastAPI API
In another terminal:
```bash
uvicorn backend.main:app --reload
```
Open the API docs at `http://127.0.0.1:8000/docs`.

## Demo fallback
If keys are missing or live sources fail, the Streamlit app can run in Mock Demo mode using `data/mock_leads.json`.

## Suggested demo ICP
- Industry: B2B SaaS
- Company size: 50–500
- Geography: India
- Signals: Hiring / Growth
- Target roles: Founder, CEO, CTO, Head of Security
- Leads: 10

## Evaluation mapping
- Relevance → ICP-based search queries
- Enrichment → source URLs + confidence
- Scoring → 100-point rubric + per-lead reasoning
- Dedup/export → deterministic normalization + CSV/HubSpot fields
- Compliance → robots.txt gate before HTTP fetch
- Refresh → repeatable pipeline with SQLite cache

## Streamlit Community Cloud deployment

1. Push this folder to GitHub.
2. Create a Streamlit app pointing to `frontend/app.py`.
3. In the app's Secrets settings, add:
```toml
GEMINI_API_KEY = "your-key"
SERPER_API_KEY = "your-key"
GEMINI_MODEL = "gemini-3.8-flash"
```
4. Reboot the app.

If you do not have live API keys, keep Mock/demo mode enabled for the presentation.
