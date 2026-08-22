"""Shapes of the data going in and out of the API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_number: int
    description: str
    item_code: str
    quantity: float
    unit_price: float
    line_total: float


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    filename: str
    document_number: str
    vendor_name: str
    grand_total: float
    was_scanned: bool
    extraction_confidence: float
    source: str
    uploaded_at: datetime
    lines: list[LineItemOut] = []


class ExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exception_type: str
    severity: str
    line_description: str
    expected_value: str
    actual_value: str
    variance_amount: float
    variance_pct: float
    ai_explanation: str
    resolution: str


class MatchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_variance: float
    processing_ms: int
    created_at: datetime
    exceptions: list[ExceptionOut] = []


class MatchRequest(BaseModel):
    po_doc_id: int
    grn_doc_id: int
    invoice_doc_id: int


class ResolveRequest(BaseModel):
    resolution: str   # APPROVED | REJECTED | CREDIT_NOTE_REQUESTED