# 📄 Utility Invoice Extractor

A modern, high-performance web application for **multilingual utility invoice data extraction** powered by Large Language Models (LLMs). Upload electricity, gas, or water invoices in PDF or TXT format and watch structured data stream in real-time.

---

## 🌟 Key Features

- **🌐 Multilingual Extraction**: Supports invoices in English, Spanish, French, German, and other languages without requiring pre-translation.
- **⚡ Real-Time SSE Token Streaming**: Watch the LLM generate structured JSON live in a terminal-style preview window as tokens arrive.
- **📊 Dynamic Field Detection**: Automatically extracts standard utility fields while preserving non-standard extra fields returned by the model.
- **📦 Batch Management & CSV Export**: Processes multiple invoices sequentially, displays progress, and exports batch results to CSV with a single click.

### Technology stacks

#### Frontend: React 18, TypeScript, Vite, TailwindCSS, and Lucide React Icons.

#### Backend & AI: Python FastAPI (Uvicorn), Pydantic v2, PyPDF, Server-Sent Events (SSE), and NVIDIA LLM API (openai SDK).

---

## 🚀 Local Setup & How to Run

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher & `npm`

---

### Clone the repo to start with.

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
   ```
3. To change the provider or model (e.g. OpenAI, Groq, Together AI, Ollama, etc.), modify `BASE_URL` and `MODEL` in `backend/main.py`:
   ```python
   BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
   MODEL = "gpt-4o-mini"
   ```

> 💡 **Free API Key Directory**:
> If you are looking for free LLM API providers, check out the curated provider directory:  
> 👉 [awesome-freellm-apis Provider Directory](https://github.com/open-free-llm-api/awesome-freellm-apis#provider-directory)

---

## 📡 API Endpoint Reference

### 1. `POST /extract` — Batch Extraction Stream (SSE)

### 2. `GET /download` — CSV Export

### 3. `GET /health` — Health Check

---

## 🧠 Server-Sent Events (SSE) Architecture

### How SSE is Achieved in this Application

1. **FastAPI StreamingResponse**: The `/extract` endpoint returns a Starlette `StreamingResponse` wrapping an asynchronous Python generator (`event_stream`).
2. **Non-Blocking Queue Worker Thread**: LLM streaming calls run inside a background daemon thread that feeds chunks into a thread-safe `queue.Queue`.
3. **Heartbeat Interleaving**: The async generator polls the queue with a 3-second timeout (`HEARTBEAT_INTERVAL`). If no token arrives within 3 seconds, a heartbeat comment frame (`: heartbeat\n\n`) is yielded, keeping the HTTP socket open.

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
├── src/
│   ├── components/
│   │   └── Dropzone.tsx  # Upload area, live terminal stream box, dynamic grid results
│   ├── App.tsx          # Main React application & batch state manager
│   ├── sseClient.ts     # SSE stream parser & HTTP error handling
│   ├── types.ts         # TypeScript interfaces & event definitions
│   └── index.css        # TailwindCSS styles
├── index.html           # Main HTML with inline SVG favicon
└── package.json
```

---

## 📜 License

For personal use only — feel free to use and modify for your own applications!
