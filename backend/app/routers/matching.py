"""Run matches and read results."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, MatchRun, MatchException
from app.schemas import MatchRequest, MatchRunOut, ResolveRequest, ExceptionOut
from app.services import line_matcher, rules_engine

router = APIRouter()


@router.post("", response_model=MatchRunOut)
def create_match(req: MatchRequest, db: Session = Depends(get_db)):
    """Match three already-uploaded documents."""
    po = db.query(Document).get(req.po_doc_id)
    grn = db.query(Document).get(req.grn_doc_id)
    inv = db.query(Document).get(req.invoice_doc_id)

    if not all([po, grn, inv]):
        raise HTTPException(404, "One or more documents not found")

    triplets = line_matcher.match_lines(po.lines, grn.lines, inv.lines)
    exceptions = rules_engine.evaluate(triplets)
    verdict = rules_engine.summarize(exceptions)

    run = MatchRun(
        po_doc_id=po.id, grn_doc_id=grn.id, invoice_doc_id=inv.id,
        status=verdict["status"],
        total_variance=verdict["total_variance"],
        processing_ms=0,
    )
    db.add(run)
    db.flush()

    for exc in exceptions:
        db.add(MatchException(match_run_id=run.id, **exc))

    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[MatchRunOut])
def list_matches(db: Session = Depends(get_db), limit: int = 50):
    return (db.query(MatchRun)
            .order_by(MatchRun.created_at.desc())
            .limit(limit).all())


@router.get("/{run_id}", response_model=MatchRunOut)
def get_match(run_id: int, db: Session = Depends(get_db)):
    run = db.query(MatchRun).get(run_id)
    if not run:
        raise HTTPException(404, "Match run not found")
    return run


@router.patch("/exceptions/{exc_id}", response_model=ExceptionOut)
def resolve_exception(exc_id: int, req: ResolveRequest,
                      db: Session = Depends(get_db)):
    """The human-in-the-loop step: approve, reject, or request a credit note."""
    from datetime import datetime

    valid = ("APPROVED", "REJECTED", "CREDIT_NOTE_REQUESTED", "PENDING")
    if req.resolution not in valid:
        raise HTTPException(400, f"resolution must be one of {valid}")

    exc = db.query(MatchException).get(exc_id)
    if not exc:
        raise HTTPException(404, "Exception not found")

    exc.resolution = req.resolution
    exc.resolved_at = datetime.utcnow() if req.resolution != "PENDING" else None
    db.commit()
    db.refresh(exc)
    return exc