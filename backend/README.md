# Utility Invoice Extractor — Backend

FastAPI service that extracts structured data from utility invoices (electricity, gas, water) using an LLM via the OpenAI SDK (pointed at NVIDIA NIM by default), validates the output with Pydantic, and streams per-file progress to the frontend via Server-Sent Events.

## Stack

- **FastAPI** — async web framework
- **OpenAI SDK** — LLM client (compatible with NVIDIA NIM / any OpenAI-compatible endpoint)
- **Pydantic v2** — request/response validation
- **pypdf** — text extraction from PDFs
- **python-dotenv** — environment configuration
- **SSE (Server-Sent Events)** — real-time progress streaming with 3-second heartbeats

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your API key:

```bash
cp .env.example .env
```

| Variable           | Description                              | Default                                |
| ------------------ | ---------------------------------------- | -------------------------------------- |
| `NVIDIA_API_KEY`   | API key for the LLM endpoint             | _(required)_                           |
| `LLM_BASE_URL`     | OpenAI-compatible base URL               | `https://integrate.api.nvidia.com/v1`  |
| `LLM_MODEL`        | Model name                               | `meta/llama-3.3-70b-instruct`          |
| `HOST` / `PORT`    | Server bind address                      | `0.0.0.0:8000`                         |

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Endpoints

### `GET /health`
Returns server status and the configured model.

### `POST /extract`
Upload one or more invoice files (PDF or TXT). Returns an SSE stream.

**Events:**
- `queue` — `{ filenames, total }` sent once at the start
- `start` — `{ filename, index, total }` when a file begins processing
- `success` — `{ filename, index, total, data }` with the validated invoice fields
- `error` — `{ filename, index, total, error }` if extraction or validation fails
- `done` — `{ total, success_count, error_count }` when all files are processed

Heartbeat comment frames (`: heartbeat`) are sent every 3 seconds during processing to keep the connection alive.

### `GET /download`
Downloads the most recent extraction batch as a CSV file.

## How it works

1. **Ingest** — files are uploaded via multipart form data
2. **Extract text** — pypdf extracts text from PDFs; TXT files are read directly
3. **LLM parse** — the system prompt instructs the LLM to return a JSON object matching the schema, handling any input language
4. **Validate** — Pydantic validates the LLM output; missing mandatory fields are reported as errors
5. **Output** — results are collected and downloadable as CSV

## Mandatory fields

If any of these are missing or null in the LLM output, the file is marked as an error with the specific missing fields listed:

- `vendor_name`
- `invoice_date`
- `utility_type`
- `usage_amount`
- `usage_unit`
- `billing_period_start`
- `billing_period_end`

`service_address` is optional.

## Sample invoices

Five sample invoices are in `../samples/` covering electricity, gas, and water in English, Spanish, and French with varied layouts.
