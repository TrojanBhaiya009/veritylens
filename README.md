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

### `POST /api/verify`

Request body:

```json
{
  "text": "optional text input",
  "url": "optional article URL"
}
```

Provide either `text` or `url`.

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
