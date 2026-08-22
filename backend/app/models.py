from datetime import datetime

from sqlalchemy import (String, Integer, Numeric, DateTime,
                        ForeignKey, Text, Float, Boolean)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    """One PDF - a PO, a GRN, or an Invoice."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(20))       # PO | GRN | INVOICE
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))

    document_number: Mapped[str] = mapped_column(String(100), default="")
    reference_po_number: Mapped[str] = mapped_column(String(100), default="")
    vendor_name: Mapped[str] = mapped_column(String(255), default="")
    grand_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    raw_text: Mapped[str] = mapped_column(Text, default="")
    was_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="UPLOAD")  # UPLOAD | WATCHER
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lines: Mapped[list["LineItem"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class LineItem(Base):
    """One row from any document. Same shape for all three types."""
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    line_number: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(500))
    item_code: Mapped[str] = mapped_column(String(100), default="")
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    document: Mapped["Document"] = relationship(back_populates="lines")


class MatchRun(Base):
    """One three-way comparison."""
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    grn_doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    invoice_doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))

    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    total_variance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    processing_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exceptions: Mapped[list["MatchException"]] = relationship(
        back_populates="match_run", cascade="all, delete-orphan"
    )


class MatchException(Base):
    """One problem found during matching."""
    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_run_id: Mapped[int] = mapped_column(ForeignKey("match_runs.id"))

    exception_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    line_description: Mapped[str] = mapped_column(String(500), default="")
    expected_value: Mapped[str] = mapped_column(String(200), default="")
    actual_value: Mapped[str] = mapped_column(String(200), default="")
    variance_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    variance_pct: Mapped[float] = mapped_column(Float, default=0)
    ai_explanation: Mapped[str] = mapped_column(Text, default="")

    resolution: Mapped[str] = mapped_column(String(30), default="PENDING")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    match_run: Mapped["MatchRun"] = relationship(back_populates="exceptions")