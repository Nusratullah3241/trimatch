"""Aggregate numbers for the dashboard and metrics page."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, MatchRun, MatchException

router = APIRouter()

MINUTES_SAVED_PER_MATCH = 12   # conservative manual-processing estimate


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    total_docs = db.query(func.count(Document.id)).scalar() or 0
    total_runs = db.query(func.count(MatchRun.id)).scalar() or 0
    matched = db.query(func.count(MatchRun.id)).filter(
        MatchRun.status == "MATCHED").scalar() or 0

    total_variance = db.query(func.sum(MatchException.variance_amount)).scalar() or 0
    avg_ms = db.query(func.avg(MatchRun.processing_ms)).scalar() or 0

    by_type = dict(
        db.query(MatchException.exception_type, func.count(MatchException.id))
        .group_by(MatchException.exception_type).all()
    )

    pending = db.query(func.count(MatchException.id)).filter(
        MatchException.resolution == "PENDING").scalar() or 0

    return {
        "total_documents": total_docs,
        "total_match_runs": total_runs,
        "auto_approved": matched,
        "auto_approval_rate": round(matched / total_runs * 100, 1) if total_runs else 0,
        "total_variance_caught": round(float(total_variance), 2),
        "avg_processing_ms": round(float(avg_ms)),
        "exceptions_by_type": by_type,
        "pending_review": pending,
        "estimated_minutes_saved": total_runs * MINUTES_SAVED_PER_MATCH,
    }