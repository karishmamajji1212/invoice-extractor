"""LLM extractor: builds the system prompt, calls the LLM, validates structured output."""
from __future__ import annotations

import json
import logging
from typing import Any, Generator

from openai import OpenAI

from models import InvoiceField

logger = logging.getLogger("invoice_extractor")


SYSTEM_PROMPT = """\
You are a precise utility-invoice data extraction engine. You receive the raw text of a single utility invoice (electricity, gas, or water), which may be written in ANY language (English, Spanish, French, German, etc.).

Your job: extract the following structured fields and return them as a JSON object that strictly matches the provided schema. Do not include any prose, markdown, or commentary — only the JSON object.

Fields to extract (all are mandatory unless explicitly marked optional):
- vendor_name: The name of the utility company / provider. Use the full legal or brand name as printed.
- invoice_date: The date the invoice was issued. Normalize to ISO 8601 (YYYY-MM-DD). If the invoice prints a different date format, convert it.
- service_address: The service / delivery address where the utility is consumed (NOT the billing/mailing address unless that is the only one present). If no service address is printed, return null.
- utility_type: One of "electricity", "gas", "water". Infer from vendor name, usage unit, or line items.
- usage_amount: The numeric consumption value for the billing period, as a plain number (no unit, no thousands separators). Use a period as the decimal separator.
- usage_unit: The unit of consumption, e.g. "kWh", "therms", "gallons", "m³", "ft³". Use the symbol as printed.
- billing_period_start: Start date of the billing period in YYYY-MM-DD. If only a single date is shown, use it for both start and end.
- billing_period_end: End date of the billing period in YYYY-MM-DD.
- detected_language: Detected primary language of the invoice text as a full name (e.g. "English", "Spanish", "French", "German", "Japanese").
- confidence_score: A confidence float between 0.0 and 1.0 (e.g. 0.95) representing how complete, legible, and clear the extraction is.

Rules:
1. Respond ONLY with a JSON object. No markdown fences, no explanations.
2. Every field except service_address is MANDATORY. If a mandatory field is genuinely missing or unreadable in the text, return null for that field — the downstream validator will flag the invoice as incomplete.
3. Normalize all dates to YYYY-MM-DD. If you can only infer a partial date (e.g. "March 2024"), use the first day of the month for start and the last day for end as appropriate.
4. Translate nothing — preserve vendor names and addresses in their original language. Only normalize dates and numeric formats.
5. usage_amount must be a number (int or float), never a string.
6. confidence_score must be a float between 0.0 and 1.0.
7. If the document is not a utility invoice at all, return null for every field.
"""

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": ["string", "null"]},
        "invoice_date": {"type": ["string", "null"]},
        "service_address": {"type": ["string", "null"]},
        "utility_type": {
            "type": ["string", "null"],
            "enum": ["electricity", "gas", "water", None],
        },
        "usage_amount": {"type": ["number", "null"]},
        "usage_unit": {"type": ["string", "null"]},
        "billing_period_start": {"type": ["string", "null"]},
        "billing_period_end": {"type": ["string", "null"]},
        "detected_language": {"type": ["string", "null"]},
        "confidence_score": {"type": ["number", "null"]},
    },
    "required": [
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
    ],
    "additionalProperties": False,
}


class ExtractionError(Exception):
    """Raised when extraction or validation fails."""


def build_client(api_key: str, base_url: str) -> OpenAI:
    if not api_key:
        raise ExtractionError(
            "NVIDIA_API_KEY is not set. Add it to backend/.env before running."
        )
    return OpenAI(base_url=base_url, api_key=api_key)


def parse_json(raw: str) -> dict[str, Any]:
    """Robustly parse JSON from an LLM response that may include stray text/fences."""
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ExtractionError(f"LLM response contained no JSON object: {raw[:200]}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"LLM returned invalid JSON: {exc}") from exc


def extract_invoice_fields(
    invoice_text: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float = 120.0,
) -> InvoiceField:
    """Call the LLM and return validated InvoiceField. Raises ExtractionError on failure."""
    client = build_client(api_key, base_url)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": invoice_text},
            ],
            temperature=0,
            top_p=0.95,
            max_tokens=8192,
            stream=False,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"LLM call failed: {exc}") from exc

    raw_content = (completion.choices[0].message.content or "").strip()
    if not raw_content:
        raise ExtractionError("LLM returned an empty response.")

    data = parse_json(raw_content)

    # Detect the "not an invoice / all missing" sentinel.
    if all(v is None for v in data.values()):
        raise ExtractionError(
            "The document does not appear to be a utility invoice (all fields missing)."
        )

    # Validate with Pydantic; collect missing mandatory fields.
    try:
        return InvoiceField(**data)
    except Exception as exc:  # noqa: BLE001
        # Identify which mandatory fields are missing/null for a helpful message.
        missing: list[str] = []
        for key in (
            "vendor_name",
            "invoice_date",
            "utility_type",
            "usage_amount",
            "usage_unit",
            "billing_period_start",
            "billing_period_end",
        ):
            if data.get(key) is None:
                missing.append(key)
        if missing:
            raise ExtractionError(
                f"Mandatory fields missing from invoice: {', '.join(missing)}."
            ) from exc
        raise ExtractionError(f"LLM output failed validation: {exc}") from exc


def extract_invoice_fields_streaming(
    invoice_text: str,
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float = 120.0,
) -> Generator[dict, None, None]:
    client = build_client(api_key, base_url)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": invoice_text},
            ],
            temperature=0,
            top_p=0.95,
            max_tokens=8192,
            stream=True,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
        
        accumulated_text = ""
        for chunk in completion:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                accumulated_text += content
                yield {"type": "token", "token": content}
                
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "error": f"LLM call failed: {exc}"}
        return

    raw_content = accumulated_text.strip()
    if not raw_content:
        yield {"type": "error", "error": "LLM returned an empty response."}
        return

    try:
        data = parse_json(raw_content)
    except Exception as exc:
        yield {"type": "error", "error": str(exc)}
        return

    # Detect the "not an invoice / all missing" sentinel.
    if all(v is None for v in data.values()):
        yield {"type": "error", "error": "The document does not appear to be a utility invoice (all fields missing)."}
        return

    # Validate with Pydantic; collect missing mandatory fields.
    try:
        field = InvoiceField(**data)
    except Exception as exc:  # noqa: BLE001
        missing: list[str] = []
        for key in (
            "vendor_name",
            "invoice_date",
            "utility_type",
            "usage_amount",
            "usage_unit",
            "billing_period_start",
            "billing_period_end",
        ):
            if data.get(key) is None:
                missing.append(key)
        if missing:
            yield {"type": "error", "error": f"Mandatory fields missing from invoice: {', '.join(missing)}."}
        else:
            yield {"type": "error", "error": f"LLM output failed validation: {exc}"}
        return
        
    yield {"type": "complete", "data": field, "all_fields": data}
