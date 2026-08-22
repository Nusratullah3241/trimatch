"""Upload and list documents."""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Document
from app.schemas import DocumentOut
from app.services.match_service import _save_document

router = APIRouter()

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db),
):
    """Upload one PDF, extract it, store it."""
    doc_type = doc_type.upper()
    if doc_type not in ("PO", "GRN", "INVOICE"):
        raise HTTPException(400, "doc_type must be PO, GRN or INVOICE")

    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        doc = _save_document(db, str(dest), doc_type, source="UPLOAD")
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Extraction failed: {e}")


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), limit: int = 50):
    return (db.query(Document)
            .order_by(Document.uploaded_at.desc())
            .limit(limit).all())


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc