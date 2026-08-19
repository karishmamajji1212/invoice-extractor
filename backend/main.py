"""FastAPI application: SSE streaming endpoint for invoice extraction + CSV download."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import queue
import threading

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from extractor import ExtractionError, extract_invoice_fields, extract_invoice_fields_streaming
from models import ExtractedInvoice, HealthResponse, InvoiceField
from pdf_utils import extract_text

load_dotenv()

logger = logging.getLogger("invoice_extractor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API_KEY = os.getenv("NVIDIA_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL = "thinkingmachines/inkling"

HEARTBEAT_INTERVAL = 3.0  # seconds


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    if not API_KEY:
        logger.warning(
            "NVIDIA_API_KEY is not set. The /extract endpoint will fail until it is added to backend/.env."
        )
    logger.info("Starting invoice extractor — model=%s base_url=%s", MODEL, BASE_URL)
    yield


app = FastAPI(title="Utility Invoice Extractor", lifespan=lifespan)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://invoice-extractor-upaa.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", model=MODEL, base_url=BASE_URL)


def sse(event: str, data: dict) -> bytes:
    """Serialize one Server-Sent Event frame."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def _queue_get_with_timeout(q: queue.Queue, timeout: float) -> Any:
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return "__heartbeat__"


@app.post("/extract")
async def extract(files: list[UploadFile] = File(...)):
    """Process uploaded invoices sequentially, streaming progress via SSE.

    Event types:
      - queue       { filenames: string[], total: int }
      - start       { filename: string, index: int, total: int }
      - heartbeat   (comment frame every 3s while a file is processing)
      - token       { filename: string, index: int, total: int, token: string }
      - success     { filename, index, total, data: InvoiceField, extra_fields: dict }
      - error       { filename, index, total, error: string }
      - done        { total, success_count, error_count }
    """
    if not API_KEY:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "NVIDIA_API_KEY is not configured on the server. Add it to backend/.env and restart."
            },
        )

    filenames = [f.filename or f"file_{i}" for i, f in enumerate(files)]
    total = len(filenames)

    # Read all upload bytes eagerly BEFORE returning the StreamingResponse,
    # because Starlette closes the file handles after the endpoint returns.
    file_bytes_list: list[bytes] = [await f.read() for f in files]

    async def event_stream() -> AsyncGenerator[bytes, None]:
        success_count = 0
        error_count = 0
        results: list[ExtractedInvoice] = []

        try:
            yield sse("queue", {"filenames": filenames, "total": total})

            for idx, (raw_bytes, filename) in enumerate(zip(file_bytes_list, filenames)):
                yield sse("start", {"filename": filename, "index": idx, "total": total})

                loop = asyncio.get_running_loop()

                try:
                    text = await loop.run_in_executor(
                        None, extract_text, raw_bytes, filename
                    )
                except Exception as exc:
                    logger.exception("Failed to extract text from %s", filename)
                    error_count += 1
                    error_msg = f"Text extraction failed: {exc}"
                    yield sse("error", {
                        "filename": filename,
                        "index": idx,
                        "total": total,
                        "error": error_msg,
                    })
                    results.append(ExtractedInvoice(filename=filename, status="error", error=error_msg))
                    continue

                q: queue.Queue = queue.Queue()

                def run_streaming():
                    try:
                        for chunk in extract_invoice_fields_streaming(
                            text, api_key=API_KEY, base_url=BASE_URL, model=MODEL
                        ):
                            q.put(chunk)
                    except Exception as exc:
                        q.put({"type": "error", "error": str(exc)})
                    finally:
                        q.put(None)  # sentinel

                thread = threading.Thread(target=run_streaming, daemon=True)
                thread.start()

                while True:
                    item = await loop.run_in_executor(None, _queue_get_with_timeout, q, HEARTBEAT_INTERVAL)
                    if item == "__heartbeat__":
                        yield b": heartbeat\n\n"
                        continue
                    
                    if item is None:
                        break  # stream finished
                    
                    if item["type"] == "token":
                        yield sse("token", {
                            "filename": filename, "index": idx, "total": total,
                            "token": item["token"]
                        })
                    elif item["type"] == "complete":
                        result = ExtractedInvoice(
                            filename=filename, status="success", data=item["data"]
                        )
                        # Include all_fields (raw dict with extra fields) in the success event
                        yield sse("success", {
                            "filename": filename, "index": idx, "total": total,
                            "data": item["data"].model_dump(),
                            "extra_fields": {k: v for k, v in item["all_fields"].items() 
                                            if k not in InvoiceField.model_fields},
                        })
                        success_count += 1
                        results.append(result)
                    elif item["type"] == "error":
                        result = ExtractedInvoice(
                            filename=filename, status="error", error=item["error"]
                        )
                        yield sse("error", {
                            "filename": filename, "index": idx, "total": total,
                            "error": item["error"],
                        })
                        error_count += 1
                        results.append(result)

        except Exception as exc:
            logger.exception("Unhandled error in SSE event_stream generator")
            error_count += 1
            yield sse("error", {
                "filename": "",
                "index": -1,
                "total": total,
                "error": f"Stream error: {exc}",
            })
        finally:
            # ALWAYS emit the "done" event so the ASGI response completes properly.
            yield sse(
                "done",
                {
                    "total": total,
                    "success_count": success_count,
                    "error_count": error_count,
                },
            )
            # Stash results for the CSV download endpoint via a module-level store.
            LAST_RESULTS["rows"] = results  # type: ignore[assignment]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# Module-level store for the most recent extraction batch (single-user demo).
LAST_RESULTS: dict = {"rows": []}


@app.get("/download")
async def download_csv():
    """Download the most recent extraction batch as a CSV file."""
    rows: list[ExtractedInvoice] = LAST_RESULTS.get("rows", [])
    if not rows:
        return JSONResponse(
            status_code=404,
            content={"detail": "No extraction results available. Run /extract first."},
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "filename",
            "status",
            "vendor_name",
            "invoice_date",
            "service_address",
            "utility_type",
            "usage_amount",
            "usage_unit",
            "billing_period_start",
            "billing_period_end",
            "detected_language",
            "confidence_score",
            "error",
        ]
    )
    for row in rows:
        if row.status == "success" and row.data:
            d = row.data
            conf_str = f"{round(d.confidence_score * 100)}%" if d.confidence_score and d.confidence_score <= 1.0 else f"{d.confidence_score}%" if d.confidence_score else "95%"
            writer.writerow(
                [
                    row.filename,
                    "success",
                    d.vendor_name,
                    d.invoice_date,
                    d.service_address or "",
                    d.utility_type,
                    d.usage_amount,
                    d.usage_unit,
                    d.billing_period_start,
                    d.billing_period_end,
                    d.detected_language or "English",
                    conf_str,
                    "",
                ]
            )
        else:
            writer.writerow(
                [
                    row.filename,
                    "error",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    row.error or "",
                ]
            )

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="extracted_invoices.csv"'
        },
    )
