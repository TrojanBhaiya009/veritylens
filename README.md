# VerityLens

AI-driven verification engine that extracts factual claims from text or URLs, retrieves real-world evidence, and produces an explainable accuracy report.

## Features

- Claim extraction from plain text or article URLs.
- Evidence retrieval using DuckDuckGo Search.
- Per-claim verdict classification:
  - True
  - False
  - Partially True
  - Unverifiable
- Confidence scoring and rationale per claim.
- Explicit source citations for each claim.
- Conflicting evidence detection.
- AI-generated text probability estimator (bonus).

## Architecture

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python
- LLM: Own LLM Engine (DuckDuckGo Chat multi-model + enhanced NLP)
- Search: DuckDuckGo Search API

Pipeline:

1. Extract claims from input content.
2. Formulate search retrieval for each claim.
3. Compare claim vs evidence using LLM.
4. Render interactive Accuracy Report.

## Project Structure

```text
fact-claim-verifier/
  backend/
    app/
      config.py
      main.py
      models/schemas.py
      routers/verify.py
      services/
        detector_service.py
        llm_service.py
        scraper_service.py
        search_service.py
        verification_service.py
    requirements.txt
  frontend/
    src/
      api/client.ts
      components/ClaimCard.tsx
      components/PipelineStatus.tsx
      types/report.ts
      App.tsx
      styles.css
    package.json
  docs/
    presentation-outline.md
  .env.example
```

## Setup

### 1. Configure environment

No API keys required! The system uses free DuckDuckGo Chat and enhanced local NLP.

### 2. Run backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL: `http://127.0.0.1:8000`

### 3. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://127.0.0.1:5173`

## API

### `POST /api/analyze`

Request body:

```json
{
  "text": "optional text input",
  "url": "optional article URL"
}
```

Provide either `text` or `url`.

### `GET /api/health`

Health endpoint for deployment checks.

## Deployment (Render + Vercel)

### 1. Deploy backend on Render

Service settings:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`

Backend environment variables:

- `CORS_ORIGINS` = comma-separated origins (example: `https://your-app.vercel.app,http://localhost:5173`)
- `CORS_ORIGIN_REGEX` = optional regex for dynamic preview domains (default allows `*.vercel.app`)
- `URL_FETCH_VERIFY_SSL` = `true` (recommended default)

### 2. Deploy frontend on Vercel

Project settings:

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`

Vercel environment variable:

- `VITE_API_BASE` = your Render backend URL (example: `https://your-backend.onrender.com`)

### 3. Verify deployment

1. Open `https://<render-service>.onrender.com/api/health`
2. Open your Vercel frontend URL
3. Submit sample text and confirm streaming results arrive

## Security Notes

- Keep all API keys in `backend/.env` only.
- Do not commit secrets.
- Rotate leaked keys immediately.
- Enable outbound request allowlists and rate limiting for production.

## 10-Minute Demo Plan

Use the script in `docs/presentation-outline.md`.

Recommended 3 scenarios:

1. Mostly true article.
2. Mixed factual and misleading claims.
3. Conflicting source landscape (recent or disputed topic).

## GitHub Publishing

1. Create a new GitHub repository.
2. Push this project root.
3. Add screenshots/GIF in README for stronger presentation.
4. Share the public repository link as the deliverable.

## Known Limitations

- DuckDuckGo results can be shallow for niche or rapidly changing topics.
- AI-generated detector is heuristic, not forensic grade.
- Verification quality depends on source quality and timeliness.
