"""Read and update the business rule thresholds."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ToleranceOut, ToleranceUpdate
from app.services import tolerance_service

router = APIRouter()


@router.get("", response_model=ToleranceOut)
def read_tolerances(db: Session = Depends(get_db)):
    return tolerance_service.get_row(db)


@router.put("", response_model=ToleranceOut)
def update_tolerances(req: ToleranceUpdate, db: Session = Depends(get_db)):
    """
    Changing a threshold does NOT re-evaluate past runs. Each run records
    the tolerances it was judged under, so historical decisions stay
    explainable after a policy change.
    """
    try:
        return tolerance_service.update(
            db,
            price_pct=req.price_tolerance_pct,
            absolute_amount=req.absolute_tolerance_amount,
            quantity_pct=req.quantity_tolerance_pct,
            updated_by="user",
        )
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/reset", response_model=ToleranceOut)
def reset_tolerances(db: Session = Depends(get_db)):
    return tolerance_service.reset(db)