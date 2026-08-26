"""Orchestrates a complete three-way match and saves it to the database."""
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Document, LineItem, MatchRun, MatchException
from app.services import extractor, line_matcher, rules_engine, tolerance_service

DOC_TYPE_PREFIXES = {
    "PO": ("PO",),
    "GRN": ("GRN",),
    "INVOICE": ("INV", "INVOICE", "BILL"),
}


class DocumentTypeMismatch(ValueError):
    """The document does not look like the type it was uploaded as."""


def _verify_doc_type(document_number: str | None, declared: str, filename: str):
    """
    Cheap sanity check on the extracted document number.

    Only rejects when the number clearly belongs to a DIFFERENT known type.
    An unrecognised or missing number is allowed through - being strict there
    would reject valid documents from vendors with unusual numbering.
    """
    if not document_number:
        return

    prefix = document_number.strip().upper()

    for doc_type, prefixes in DOC_TYPE_PREFIXES.items():
        if doc_type == declared:
            continue
        if any(prefix.startswith(p) for p in prefixes):
            raise DocumentTypeMismatch(
                f"'{filename}' was uploaded as {declared}, but its document "
                f"number '{document_number}' identifies it as a {doc_type}. "
                f"Check the upload slots."
            )


def _save_document(db: Session, file_path: str, doc_type: str,
                   source: str = "UPLOAD") -> Document:
    """Extracts one PDF and stores it with its line items."""
    data = extractor.extract(file_path, doc_type)

    _verify_doc_type(data.document_number, doc_type, Path(file_path).name)

    doc = Document(
        doc_type=doc_type,
        filename=Path(file_path).name,
        file_path=str(file_path),
        document_number=data.document_number or "",
        reference_po_number=data.reference_po_number or "",
        vendor_name=data.vendor_name or "",
        grand_total=data.grand_total or 0,
        raw_text=data.raw_text[:20000],
        was_scanned=data.was_scanned,
        extraction_confidence=data.confidence,
        source=source,
    )
    db.add(doc)
    db.flush()

    for i, ln in enumerate(data.line_items, 1):
        db.add(LineItem(
            document_id=doc.id,
            line_number=ln.line_number or i,
            description=ln.description,
            item_code=ln.item_code or "",
            quantity=ln.quantity or 0,
            unit_price=ln.unit_price or 0,
            line_total=ln.line_total or 0,
        ))

    db.flush()
    return doc


def _is_duplicate(db: Session, invoice: Document) -> bool:
    """
    Has this exact invoice already been processed?

    Paying the same invoice twice is one of the most common and expensive
    errors in accounts payable.
    """
    if not invoice.document_number:
        return False

    existing = (
        db.query(Document)
        .filter(Document.doc_type == "INVOICE")
        .filter(Document.document_number == invoice.document_number)
        .filter(Document.vendor_name == invoice.vendor_name)
        .filter(Document.id != invoice.id)
        .first()
    )
    return existing is not None


def run_match(db: Session, po_path: str, grn_path: str, invoice_path: str,
              source: str = "UPLOAD") -> MatchRun:
    """The complete pipeline: read three PDFs, compare them, save the verdict."""
    started = time.time()

    po_doc = _save_document(db, po_path, "PO", source)
    grn_doc = _save_document(db, grn_path, "GRN", source)
    inv_doc = _save_document(db, invoice_path, "INVOICE", source)

    tolerances = tolerance_service.get_tolerances(db)

    triplets = line_matcher.match_lines(po_doc.lines, grn_doc.lines, inv_doc.lines)
    exceptions = rules_engine.evaluate(triplets, tolerances)

    # Duplicate check needs database state, so it lives here rather than
    # in the pure rules engine.
    if _is_duplicate(db, inv_doc):
        exceptions.append({
            "exception_type": "DUPLICATE_INVOICE",
            "severity": "HIGH",
            "line_description": f"Invoice {inv_doc.document_number}",
            "expected_value": "not previously processed",
            "actual_value": "already exists in system",
            "variance_amount": float(inv_doc.grand_total or 0),
            "variance_pct": 100.0,
        })

    verdict = rules_engine.summarize(exceptions)
    elapsed_ms = int((time.time() - started) * 1000)

    run = MatchRun(
        po_doc_id=po_doc.id,
        grn_doc_id=grn_doc.id,
        invoice_doc_id=inv_doc.id,
        status=verdict["status"],
        total_variance=verdict["total_variance"],
        processing_ms=elapsed_ms,
        applied_price_tolerance_pct=tolerances.price_pct,
        applied_absolute_tolerance=tolerances.absolute_amount,
    )
    db.add(run)
    db.flush()

    for exc in exceptions:
        db.add(MatchException(match_run_id=run.id, **exc))

    db.commit()
    db.refresh(run)
    return run