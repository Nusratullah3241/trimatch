"""Reads and writes the tolerance thresholds stored in the database.

Kept separate from rules_engine.py deliberately - the rules engine stays
pure and testable, and this module is the only place that knows the
thresholds live in a database row.
"""
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Tolerance
from app.services.rules_engine import Tolerances

SINGLETON_ID = 1


def get_row(db: Session) -> Tolerance:
    """
    Returns the tolerance row, creating it from .env defaults on first use.

    A single row (id=1) rather than a key-value table: these three values
    always change together, and a policy review sets all of them at once.
    """
    row = db.get(Tolerance, SINGLETON_ID)

    if row is None:
        row = Tolerance(
            id=SINGLETON_ID,
            price_tolerance_pct=settings.price_tolerance_pct,
            absolute_tolerance_amount=settings.absolute_tolerance_amount,
            quantity_tolerance_pct=settings.quantity_tolerance_pct,
            updated_by="system (initial defaults from .env)",
        )
        db.add(row)
        db.commit()
        db.refresh(row)

    return row


def get_tolerances(db: Session) -> Tolerances:
    """The immutable value object the rules engine consumes."""
    row = get_row(db)
    return Tolerances(
        price_pct=row.price_tolerance_pct,
        absolute_amount=row.absolute_tolerance_amount,
        quantity_pct=row.quantity_tolerance_pct,
    )


def update(db: Session, price_pct: float, absolute_amount: float,
           quantity_pct: float, updated_by: str = "user") -> Tolerance:
    """
    Updates the thresholds after validating them.

    Validation matters here: a negative tolerance is meaningless, and a
    price tolerance of 100% would silently disable the rule entirely.
    Someone adjusting a threshold should not be able to switch off a
    financial control by typing the wrong number.
    """
    if not 0 <= price_pct <= 50:
        raise ValueError(
            "Price tolerance must be between 0 and 50 percent. "
            "A higher value would effectively disable the price check."
        )
    if absolute_amount < 0:
        raise ValueError("Minimum amount cannot be negative.")
    if not 0 <= quantity_pct <= 20:
        raise ValueError(
            "Quantity tolerance must be between 0 and 20 percent. "
            "Being billed for goods that did not arrive is not a rounding error."
        )

    row = get_row(db)
    row.price_tolerance_pct = price_pct
    row.absolute_tolerance_amount = absolute_amount
    row.quantity_tolerance_pct = quantity_pct
    row.updated_by = updated_by

    db.commit()
    db.refresh(row)
    return row


def reset(db: Session) -> Tolerance:
    """Restores the values from .env."""
    return update(
        db,
        price_pct=settings.price_tolerance_pct,
        absolute_amount=settings.absolute_tolerance_amount,
        quantity_pct=settings.quantity_tolerance_pct,
        updated_by="reset to defaults",
    )