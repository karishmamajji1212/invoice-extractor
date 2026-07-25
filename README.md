# 📄 Utility Invoice Extractor

A modern, high-performance web application for **multilingual utility invoice data extraction** powered by Large Language Models (LLMs). Upload electricity, gas, or water invoices in PDF or TXT format and watch structured data stream in real-time.

## Live Link: [AI-Powered Multilingual Utility Invoice Extractor](https://invoice-extractor-upaa.vercel.app)

#### Example input files are in `samples` directory. These are invoices with variation in: Format/layout and the Language (English, Spanish, French, etc.)

### Frontend deployed on Vercel
### Backend deployed on Render - as Vercel doesn't support long-lived SSE and often times out.

---

## 🌟 Key Features

- **🌐 Multilingual Extraction**: Supports invoices in English, Spanish, French, German, and other languages without requiring pre-translation.
- **⚡ Real-Time SSE Token Streaming**: Watch the LLM generate structured JSON live in a terminal-style preview window as tokens arrive.
- **🛡️ Resilient Keep-Alive Heartbeats**: Server-Sent Events (SSE) stream includes periodic heartbeat frames (`: heartbeat`) to keep HTTP connections active even during long LLM API calls.
- **📊 Dynamic Field Detection**: Automatically extracts standard utility fields while preserving non-standard extra fields returned by the model.
- **🎯 Language Detection & Confidence Scoring**: Displays primary detected language (`🌐 English`) and confidence percentage (`🛡️ 95% Confidence`) for every extraction.
- **📦 Batch Management & CSV Export**: Processes multiple invoices sequentially, displays progress, and exports batch results to CSV with a single click.

---

### Technology Stack

- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Lucide React Icons.
- **Backend & AI**: Python FastAPI (Uvicorn), Pydantic v2, PyPDF, Server-Sent Events (SSE), NVIDIA LLM API (`openai` SDK).

---

## 🚀 Local Setup & How to Run

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher & `npm`

---

### 1. Backend Setup (FastAPI)

Navigate to the `backend` directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` directory:

```env
NVIDIA_API_KEY=<your_nvidia_api_key_here>
LLM_BASE_URL="https://integrate.api.nvidia.com/v1"
LLM_MODEL="thinkingmachines/inkling"
```

Start the FastAPI development server:

```bash
uvicorn main:app --reload --port 8000
```

The backend server will run at `http://localhost:8000`.

---

### 2. Frontend Setup (React + Vite + TypeScript)

In a separate terminal window, navigate to the project root directory:

```bash
# Ensure you are in the root directory (where package.json lives)
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open your browser and navigate to `http://localhost:5173`.

---

## 🔑 LLM Provider & API Key Configuration

### Default Provider & Model

By default, this repository uses the **NVIDIA API** with the **`thinkingmachines/inkling`** model:
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Default Model**: `thinkingmachines/inkling`

### Using Your Own API Keys & Swapping Models

The backend uses the standard OpenAI-compatible Python client (`openai.OpenAI`). You can easily configure your own API key or swap to any OpenAI-compatible provider:

1. Obtain an API key from NVIDIA Build or another provider.
2. Update `backend/.env`:
   ```env
   NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
   LLM_MODEL=thinkingmachines/inkling
   ```
3. To change the provider or model (e.g. OpenAI, Groq, Together AI, Ollama, etc.), modify `LLM_BASE_URL` and `LLM_MODEL` in `backend/.env`:
   ```env
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_MODEL=gpt-4o-mini
   ```

> 💡 **Free API Key Directory**:
> If you are looking for free LLM API providers, check out the curated provider directory:  
> 👉 [awesome-freellm-apis Provider Directory](https://github.com/open-free-llm-api/awesome-freellm-apis#provider-directory)

---

## 🧪 Testing Criteria & Validation

The application was validated using a multi-tiered testing strategy combining manual visual inspection, automated ground truth benchmarking against a 30-invoice dataset, and strict edge-case exception handling.

### 1. Manual & Visual Eyeball Testing
- **Prompt Verification**: Iteratively tested custom system prompts against varied invoice layouts to ensure JSON mode compliance.
- **Visual Inspection**: Verified live token streaming in the UI dark code preview box, confirming real-time SSE token delivery with 1.5s response pacing.
- **Field Matching & Language Accuracy**: Manually verified 100% field match and accurate primary language detection (`detected_language`) across initial sample invoices (English, Spanish, French, German).

---

### 2. Ground Truth Benchmark Evaluation (30 Invoices Dataset)
- **Dataset**: Evaluated against a comprehensive dataset of 30 utility invoices (`samples/utility-invoices/`) and `ground_truth.xlsx` covering 5 languages (English, Spanish, French, German, Portuguese) and multiple utility types (Electricity, Gas, Water).
- **Execution Script**: Run the automated evaluation benchmark:
  ```bash
  python scripts/evaluate_service.py
  ```
- **Benchmark Results**:

| Field | Accuracy % | Match Ratio | Status |
| :--- | :---: | :---: | :---: |
| **Vendor Name** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Invoice Date** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Service Address** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Utility Type** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Usage Amount** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Billing Period Start** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Billing Period End** | **100.0%** | 21 / 21 | 🟢 Perfect Match |
| **Usage Unit** | **85.7%** | 18 / 21 | 🟡 High Accuracy |
| **Overall Accuracy** | **98.2%** | **165 / 168** | 🏆 **Passed** |

> 📊 **Detailed Interactive Report**:  
> View the complete interactive HTML evaluation report locally in your browser:  
> 👉 [evaluation_report.html](evaluation_report.html)

---

### 3. Edge Case Testing & Exception Handling

- **Non-Utility Document Detection**:
  - *Scenario*: Uploading a generic document, agreement, or non-utility invoice where no utility fields match.
  - *Handling*: The system detects that mandatory fields evaluate to `null` and returns an explicit error message:  
    `"The document does not appear to be a utility invoice (all fields missing)."` — **Verified & Working**.
- **Missing Mandatory Fields**:
  - *Scenario*: Uploading a partial invoice missing mandatory fields (e.g. missing consumption amount or billing dates).
  - *Handling*: Pydantic validation identifies missing mandatory attributes and presents a clear error message to the user:  
    `"Mandatory fields missing from invoice: <field_names>."` — **Verified & Working**.
- **Server & Network Error Resilience**:
  - *Scenario*: HTTP 4xx/5xx errors, rate limits (429), missing API key, or connection failure.
  - *Handling*: The SSE client catches the error, displays a global red alert banner, and updates all queued/processing files in the batch to "Error" state.

---

## 📡 API Endpoint Reference

### 1. `POST /extract` — Batch Extraction Stream (SSE)
- **Request**: `multipart/form-data` with `files` (array of PDF or TXT files).
- **Response**: `text/event-stream` (Server-Sent Events streaming `queue`, `start`, `token`, `success`, `error`, `done`).

### 2. `GET /download` — CSV Export
- **Response**: `text/csv` attachment (`extracted_invoices.csv`).

### 3. `GET /health` — Health Check
- **Response**: `application/json` status and model metadata.

---

## 🧠 Server-Sent Events (SSE) Architecture

### How SSE is Achieved in this Application

1. **FastAPI StreamingResponse**: The `/extract` endpoint returns a Starlette `StreamingResponse` wrapping an asynchronous Python generator (`event_stream`).
2. **Non-Blocking Queue Worker Thread**: LLM streaming calls run inside a background daemon thread that feeds chunks into a thread-safe `queue.Queue`.
3. **Heartbeat Interleaving**: The async generator polls the queue with a 3-second timeout (`HEARTBEAT_INTERVAL`). If no token arrives within 3 seconds, a heartbeat comment frame (`: heartbeat\n\n`) is yielded, keeping the HTTP socket open.

## 💡 Assumptions & Future Roadmap

- **Supported Formats**: Assumes input documents are text-selectable PDFs or text files.
- **Model Choice Rationale**: Chosen for its open Apache license and 900B+ parameter architecture for high accuracy.
- **Multimodal Capabilities**: Supports native image-text multimodal extraction for future visual invoice processing.
- **Future OCR & Robustness**: Given more time, full OCR integration and broader image/file handling would be implemented for enhanced robustness.

---

## 🛠️ Project Structure

```
invoice-extractor/
├── backend/
│   ├── extractor.py    # LLM integration, prompt engineering, streaming token generator
│   ├── main.py         # FastAPI app, SSE endpoint, heartbeat loop, CSV exporter
│   ├── models.py       # Pydantic data schemas & dynamic extra field configuration
│   ├── pdf_utils.py    # PyPDF text extraction utility
│   ├── requirements.txt
│   └── .env            # Environment variables (NVIDIA_API_KEY)
├── scripts/
│   └── evaluate_service.py # Benchmark testing & HTML report generator script
├── src/
│   ├── components/
│   │   └── Dropzone.tsx  # Upload area, live terminal stream box, dynamic grid results
│   ├── App.tsx          # Main React application & batch state manager
│   ├── sseClient.ts     # SSE stream parser & HTTP error handling
│   ├── types.ts         # TypeScript interfaces & event definitions
│   └── index.css        # TailwindCSS styles
├── evaluation_report.html # Stand-alone benchmark HTML report
├── index.html           # Main HTML with inline SVG favicon
└── package.json
```

---

## 📜 License

MIT License — feel free to use and modify for your own applications!
