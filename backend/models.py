"""Pydantic models for LLM request/response validation and API contracts."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvoiceField(BaseModel):
    """A single extracted invoice field, validated by the LLM structured output."""
    model_config = ConfigDict(extra="allow")

    vendor_name: str = Field(..., description="Name of the utility vendor/provider")
    invoice_date: str = Field(..., description="Invoice issue date in YYYY-MM-DD format")
    service_address: Optional[str] = Field(
        None, description="Service address where utility is delivered, if available"
    )
    utility_type: Literal["electricity", "gas", "water"] = Field(
        ..., description="Type of utility: electricity, gas, or water"
    )
    usage_amount: float = Field(..., description="Numeric usage amount consumed")
    usage_unit: str = Field(..., description="Unit of usage, e.g. kWh, therms, gallons")
    billing_period_start: str = Field(
        ..., description="Billing period start date in YYYY-MM-DD format"
    )
    billing_period_end: str = Field(
        ..., description="Billing period end date in YYYY-MM-DD format"
    )
    detected_language: Optional[str] = Field(
        "English", description="Detected primary language of the invoice (e.g. English, Spanish, French)"
    )
    confidence_score: Optional[float] = Field(
        0.95, description="Extraction confidence score between 0.0 and 1.0 (or percentage 0-100)"
    )

    @field_validator("vendor_name", "usage_unit")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("field is required and cannot be empty")
        return v

    @field_validator("invoice_date", "billing_period_start", "billing_period_end")
    @classmethod
    def normalize_date(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("date is required and cannot be empty")
        return v


class ExtractedInvoice(BaseModel):
    """Wrapper for one invoice extraction result with status metadata."""

    filename: str
    status: Literal["success", "error"]
    data: Optional[InvoiceField] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    model: str
    base_url: str
