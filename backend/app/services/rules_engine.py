"""Applies business rules to matched triplets and produces exceptions.

Deliberately pure: no database, no API calls, no file access.
That makes the business logic easy to unit test - which matters,
because this is the layer that decides whether money is paid.
"""
from decimal import Decimal

from app.config import settings


def _d(value) -> Decimal:
    """Safe conversion to Decimal. Never use float for money."""
    if value is None:
        return Decimal(0)
    return Decimal(str(value))


def _exception(exc_type, severity, description, expected, actual,
               variance_amount, variance_pct):
    return {
        "exception_type": exc_type,
        "severity": severity,
        "line_description": description,
        "expected_value": str(expected),
        "actual_value": str(actual),
        "variance_amount": float(variance_amount),
        "variance_pct": round(float(variance_pct), 2),
    }


def evaluate(triplets: list[dict]) -> list[dict]:
    """Returns a list of exceptions. Empty list means everything matched."""
    exceptions = []

    for t in triplets:
        po, grn, inv = t.get("po"), t.get("grn"), t.get("invoice")

        # RULE 1 - billed for something never ordered
        if inv is not None and po is None:
            amount = _d(inv.line_total) or (_d(inv.quantity) * _d(inv.unit_price))
            exceptions.append(_exception(
                "UNAUTHORIZED_ITEM", "HIGH", inv.description,
                "not on purchase order", f"billed {inv.quantity} units",
                amount, 100.0))
            continue

        # RULE 2 - ordered and received, but not billed (informational)
        if po is not None and inv is None:
            exceptions.append(_exception(
                "MISSING_ON_INVOICE", "LOW", po.description,
                f"{po.quantity} units ordered", "not billed",
                Decimal(0), 0.0))
            continue

        if po is None or inv is None:
            continue

        po_price = _d(po.unit_price)
        inv_price = _d(inv.unit_price)
        inv_qty = _d(inv.quantity)

        # RULE 0 - extraction sanity check, runs BEFORE the price rule.
        #
        # A unit price of zero on an invoice line is almost never real - an
        # invoice exists to charge for something. It nearly always means the
        # price could not be read from the document.
        #
        # Treating it as a price variance produces a confident, wrong finding:
        # "actual 0.00, 100% variance". The system would be reporting an
        # overcharge that does not exist while hiding a genuine failure.
        #
        # Knowing when it does not know is more valuable here than guessing.
        if inv_price <= 0 and po_price > 0:
            exceptions.append(_exception(
                "EXTRACTION_FAILURE", "HIGH", inv.description,
                f"a unit price (PO shows {po_price:,.2f})",
                "no price could be read from the invoice",
                Decimal(0), 0.0))
            continue

        # RULE 3 - price variance
        if po_price > 0:
            diff = inv_price - po_price
            if diff != 0:
                pct = abs(diff) / po_price * 100
                amount = abs(diff) * inv_qty

                over_pct = pct > _d(settings.price_tolerance_pct)
                over_abs = amount > _d(settings.absolute_tolerance_amount)

                # BOTH must be breached. A 5% rise on a 100-rupee item is
                # 5 rupees - not worth a reviewer's attention.
                if over_pct and over_abs:
                    exceptions.append(_exception(
                        "PRICE_VARIANCE",
                        "HIGH" if pct > 10 else "MEDIUM",
                        po.description,
                        f"{po_price:,.2f}", f"{inv_price:,.2f}",
                        amount, pct))

        # RULE 4 - billed for more than actually arrived
        received = _d(grn.quantity) if grn is not None else Decimal(0)
        if inv_qty > received:
            over_qty = inv_qty - received
            amount = over_qty * inv_price
            pct = (over_qty / inv_qty * 100) if inv_qty else Decimal(0)
            exceptions.append(_exception(
                "QUANTITY_VARIANCE", "HIGH", po.description,
                f"{received:g} received", f"{inv_qty:g} billed",
                amount, pct))

    return exceptions


def summarize(exceptions: list[dict]) -> dict:
    """Overall verdict for a match run."""
    total = sum(e["variance_amount"] for e in exceptions)
    high = [e for e in exceptions if e["severity"] == "HIGH"]
    needs_verification = [
        e for e in exceptions if e["exception_type"] == "EXTRACTION_FAILURE"
    ]

    return {
        "status": "MATCHED" if not exceptions else "EXCEPTION",
        "exception_count": len(exceptions),
        "high_severity_count": len(high),
        "extraction_failures": len(needs_verification),
        "total_variance": round(total, 2),
        "auto_approve": len(exceptions) == 0,
    }