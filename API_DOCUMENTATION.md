# API Documentation

## Overview

The backend exposes one main FastAPI endpoint for sector analysis:

- `GET /analyze/{sector}`

The endpoint collects live market context, runs AI analysis using Gemini when available, and returns a structured markdown report.

## Base URL

Local backend:

```text
http://127.0.0.1:8000
```

## Authentication

All backend requests require an API key in the `X-API-Key` header.

Example:

```http
X-API-Key: demo-trade-key
```

## Endpoint

### `GET /analyze/{sector}`

Analyzes a sector and returns a markdown report.

### Path Parameter

- `sector`:
  - Type: `string`
  - Example: `pharmaceuticals`
  - Allowed characters: letters, spaces, ampersands, hyphens
  - Length: 2 to 40 characters

### Example Request

```bash
curl -X GET "http://127.0.0.1:8000/analyze/pharmaceuticals" \
  -H "X-API-Key: demo-trade-key"
```

### Successful Response

- Status: `200 OK`
- Content-Type: `text/markdown`

### Example Response

```md
# India Sector Trade Opportunity Report: Pharmaceuticals

## Request Metadata
- Generated At: 2026-04-09 12:18:08 UTC
- Session ID: `6cf204fc-2ebb-4b68-bedc-c11b3cbc8984`
- Requests In Session: 1
- Scenario: Base

## Executive Summary
The Indian pharmaceutical sector is projected for growth in FY2026, supported by domestic demand and export-linked catalysts.

**Market Sentiment:** Neutral

**Opportunity Score:** 65/100
```

## Response Headers

Successful responses include:

- `Cache-Control: no-store`
- `X-Session-ID`
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

Rate-limited responses include:

- `Retry-After`

## Error Responses

### `401 Unauthorized`

Returned when the API key is missing or invalid.

Example:

```json
{
  "detail": "Missing or invalid API key."
}
```

### `422 Unprocessable Entity`

Returned when the sector value fails validation.

Example:

```json
{
  "detail": "Sector must contain only letters, spaces, or ampersands."
}
```

### `429 Too Many Requests`

Returned when the session/user exceeds the in-memory rate limit window.

Example:

```json
{
  "detail": "Rate limit exceeded. Please retry after the reset window.",
  "retry_after_seconds": 43
}
```

### `503 Service Unavailable`

Returned when an external dependency cannot be reached and the request cannot be completed normally.

Example:

```json
{
  "detail": "Failed to reach an external dependency: ConnectError"
}
```

## Interactive FastAPI Docs

FastAPI automatically exposes:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Frontend Proxy API

The Next.js frontend includes a server-side proxy route:

- `POST /api/analyze`

### Purpose

- Accepts a JSON body like:

```json
{
  "sector": "pharmaceuticals"
}
```

- Validates the input
- Calls the FastAPI backend on the server side
- Keeps the backend API key hidden from the browser

### Example Frontend Response

```json
{
  "report": "# India Sector Trade Opportunity Report: Pharmaceuticals\n...",
  "meta": {
    "sessionId": "6cf204fc-2ebb-4b68-bedc-c11b3cbc8984",
    "rateLimit": {
      "limit": "5",
      "remaining": "4",
      "reset": "60"
    }
  }
}
```

