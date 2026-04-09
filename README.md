# Trade Opportunity Analyzer

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=000000)](https://react.dev/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)

FastAPI + Next.js project for analyzing Indian market sectors and returning a structured markdown trade opportunity report. The backend collects live market context, runs Gemini-powered analysis, and exposes a single secured API endpoint. The frontend provides a polished dashboard to run analysis, preview the report, and download it as `.md`.

## Overview

- Backend: FastAPI service with session management, input validation, rate limiting, and Gemini integration
- Frontend: Next.js app with a server-side proxy route so the backend API key is never exposed to the browser
- Output: structured markdown report for sectors like `pharmaceuticals`, `technology`, `agriculture`, `banking`, and `energy`

## Deliverables

- Security features summary: [`SECURITY_FEATURES.md`](./SECURITY_FEATURES.md)
- API documentation: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
- Setup and run instructions: this `README.md`

## Features

- `GET /analyze/{sector}` as the core backend endpoint
- API key authentication using `X-API-Key`
- Signed session cookie handling with in-memory usage tracking
- In-memory rate limiting with `429` support and rate-limit headers
- Sector input validation and normalization
- Live market/news collection from Google News RSS
- Gemini analysis with deterministic fallback mode
- Markdown report generation with watchlist, drivers, risks, and trade ideas
- Next.js dashboard with preview mode, raw markdown mode, copy, and download

## Tech Stack

- Backend: FastAPI, httpx, Pydantic, Starlette SessionMiddleware
- Frontend: Next.js App Router, React 19
- AI: Google Gemini `gemini-2.5-flash`
- Storage: in-memory only
- Testing: pytest

## Project Structure

```text
app/
  api/
    dependencies.py
  core/
    config.py
    logging.py
  schemas/
    market.py
  services/
    analysis.py
    data_collector.py
    memory_store.py
    report_builder.py
    sector_profiles.py
  main.py
frontend/
  app/
  components/
  package.json
tests/
  test_app.py
API_DOCUMENTATION.md
SECURITY_FEATURES.md
README.md
```

## Quick Start

### 1. Backend Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Backend Environment

Create `.env` in the project root:

```env
APP_ENV=development
APP_API_KEYS=demo-trade-key
SESSION_SECRET=change-me-before-production
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
REQUESTS_PER_MINUTE=5
RATE_LIMIT_WINDOW_SECONDS=60
HTTP_TIMEOUT_SECONDS=12
NEWS_RESULTS_LIMIT=6
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Frontend Environment

Create `frontend/.env.local`:

```env
BACKEND_BASE_URL=http://127.0.0.1:8000
BACKEND_API_KEY=demo-trade-key
```

## API Overview

### Backend Endpoint

```http
GET /analyze/{sector}
X-API-Key: demo-trade-key
```

Example:

```bash
curl -X GET "http://127.0.0.1:8000/analyze/pharmaceuticals" \
  -H "X-API-Key: demo-trade-key"
```

Successful responses return `text/markdown`.

### Frontend Proxy Route

```http
POST /api/analyze
Content-Type: application/json
```

Request body:

```json
{
  "sector": "pharmaceuticals"
}
```

## Example Output

```md
# India Sector Trade Opportunity Report: Pharmaceuticals

## Executive Summary
The Indian pharmaceutical sector is projected for growth in FY2026, supported by domestic demand and export-linked catalysts.

**Market Sentiment:** Neutral

**Opportunity Score:** 65/100
```

## Security Highlights

- API key authentication on the FastAPI endpoint
- Signed session cookie management
- In-memory rate limiting per API key fingerprint + session + IP
- Strict input validation for sector names
- Backend secrets loaded from environment variables
- Frontend proxy keeps the backend API key server-side
- `Cache-Control: no-store` on analysis responses

Detailed write-up: [`SECURITY_FEATURES.md`](./SECURITY_FEATURES.md)

## API Docs

- Detailed reference: [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Architecture Notes

- `app/services/data_collector.py`: gathers live market context
- `app/services/analysis.py`: handles Gemini calls and fallback analysis
- `app/services/report_builder.py`: converts analysis into markdown
- `app/services/memory_store.py`: handles sessions and rate limiting
- `frontend/app/api/analyze/route.js`: secure frontend-to-backend proxy
- `frontend/components/analyzer-shell.jsx`: user interface for running and exporting analysis

## Testing

```bash
pytest
```

## Interview Talking Points

- Clean separation between API, collection, analysis, and presentation layers
- Single-endpoint backend that still includes auth, session tracking, and rate limiting
- Graceful fallback mode when external AI calls fail
- Secure frontend proxy pattern that avoids exposing backend credentials to the browser
- Markdown-first response design aligned with the assignment requirement
