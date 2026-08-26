"""Unit tests for the rules engine.

The rules engine is deliberately pure - no database, no network, no file
access - so it can be tested in isolation with hand-built line items.
This is the layer that decides whether money is paid, so it is the layer
that most needs testing.

These tests cover cases the 40-set evaluation corpus never generated:
tolerance boundaries, zero and null values, missing documents, and
several rules firing on one line.

Run:  pytest tests/test_rules_engine.py -v
"""
from dataclasses import dataclass

import pytest

from app.services import rules_engine


# --------------------------------------------------------------- helpers

@dataclass
class Line:
    """Stands in for a LineItem. Only the fields the rules engine reads."""
    description: str
    quantity: float = 0
    unit_price: float = 0
    line_total: float = 0
    item_code: str = ""


def triplet(po=None, grn=None, invoice=None):
    return {"po": po, "grn": grn, "invoice": invoice}


def kinds(exceptions):
    """Sorted list of exception types, for readable assertions."""
    return sorted(e["exception_type"] for e in exceptions)


# ------------------------------------------------------ the happy path

def test_perfect_match_raises_nothing():
    """Everything agrees. The reviewer should never see this document."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell Latitude 5540", 10, 185000, 1850000),
            grn=Line("Dell Latitude 5540", 10),
            invoice=Line("Dell Latitude 5540", 10, 185000, 1850000),
        )
    ])
    assert kinds(result) == []


def test_perfect_match_summarises_as_auto_approve():
    verdict = rules_engine.summarize([])
    assert verdict["status"] == "MATCHED"
    assert verdict["auto_approve"] is True
    assert verdict["total_variance"] == 0


# ---------------------------------------------------- price variance

def test_price_above_agreed_rate_is_flagged():
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell Latitude 5540", 10, 185000),
            grn=Line("Dell Latitude 5540", 10),
            invoice=Line("Dell Latitude 5540", 10, 199000),
        )
    ])
    assert kinds(result) == ["PRICE_VARIANCE"]
    # 14,000 per unit over 10 units
    assert result[0]["variance_amount"] == 140000.0


def test_price_variance_under_ten_percent_is_medium():
    """185,000 -> 199,000 is 7.57%. Real, but not alarming."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=Line("Dell", 10, 199000),
        )
    ])
    assert result[0]["severity"] == "MEDIUM"


def test_price_variance_over_ten_percent_is_high():
    """100,000 -> 130,000 is 30%. That needs attention now."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Server", 5, 100000),
            grn=Line("Server", 5),
            invoice=Line("Server", 5, 130000),
        )
    ])
    assert result[0]["severity"] == "HIGH"


def test_undercharge_is_also_flagged():
    """
    A supplier charging LESS than agreed is still a deviation from the
    purchase order and still needs a human to look at it. Silently
    accepting favourable errors is how ledgers drift out of alignment.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=Line("Dell", 10, 170000),
        )
    ])
    assert kinds(result) == ["PRICE_VARIANCE"]


# ------------------------------------------- the dual tolerance rule
#
# The price rule requires BOTH a percentage breach AND an absolute
# breach. These four tests are the reason that design exists.

def test_percentage_breached_but_amount_trivial_stays_silent():
    """
    3% on a 100-rupee pen is 3 rupees. Raising an exception costs a
    reviewer thirty seconds. Flagging this wastes more than it protects.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Ballpoint pen", 1, 100),
            grn=Line("Ballpoint pen", 1),
            invoice=Line("Ballpoint pen", 1, 103),
        )
    ])
    assert kinds(result) == []


def test_amount_large_but_percentage_trivial_stays_silent():
    """
    10,000 rupees sounds like a lot, but on a million-rupee server it is
    1% - well within normal freight and rounding adjustments.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Rack server", 1, 1000000),
            grn=Line("Rack server", 1),
            invoice=Line("Rack server", 1, 1010000),
        )
    ])
    assert kinds(result) == []


def test_exactly_at_the_tolerance_boundary_stays_silent():
    """The rule is 'greater than 2%', not 'greater than or equal to'."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Monitor", 10, 100000),
            grn=Line("Monitor", 10),
            invoice=Line("Monitor", 10, 102000),   # exactly 2.0%
        )
    ])
    assert kinds(result) == []


def test_just_over_the_boundary_is_flagged():
    result = rules_engine.evaluate([
        triplet(
            po=Line("Monitor", 10, 100000),
            grn=Line("Monitor", 10),
            invoice=Line("Monitor", 10, 102100),   # 2.1%
        )
    ])
    assert kinds(result) == ["PRICE_VARIANCE"]


# ------------------------------------------------- quantity variance

def test_billed_for_more_than_arrived():
    """Ordered 10, received 7, billed 10. Three units do not exist."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 7),
            invoice=Line("Dell", 10, 185000),
        )
    ])
    assert kinds(result) == ["QUANTITY_VARIANCE"]
    assert result[0]["variance_amount"] == 555000.0   # 3 x 185,000
    assert result[0]["severity"] == "HIGH"


def test_quantity_has_no_tolerance():
    """
    Even one unit over is flagged. Being billed for goods that did not
    arrive is never acceptable at any magnitude, so quantity tolerance
    is zero by design.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Cable", 100, 500),
            grn=Line("Cable", 99),
            invoice=Line("Cable", 100, 500),
        )
    ])
    assert kinds(result) == ["QUANTITY_VARIANCE"]


def test_billed_for_less_than_arrived_is_fine():
    """Under-billing is the supplier's loss, not a control failure."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=Line("Dell", 8, 185000),
        )
    ])
    assert kinds(result) == []


def test_missing_grn_means_nothing_was_received():
    """
    No GRN matched at all. From the system's point of view nothing
    arrived, so the entire invoiced quantity is unsupported.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=None,
            invoice=Line("Dell", 10, 185000),
        )
    ])
    assert kinds(result) == ["QUANTITY_VARIANCE"]


# ------------------------------------------------- unauthorized items

def test_item_on_invoice_but_not_on_purchase_order():
    result = rules_engine.evaluate([
        triplet(po=None, grn=None, invoice=Line("Laptop bag", 5, 4500, 22500))
    ])
    assert kinds(result) == ["UNAUTHORIZED_ITEM"]
    assert result[0]["variance_amount"] == 22500.0
    assert result[0]["severity"] == "HIGH"


def test_unauthorized_item_falls_back_to_qty_times_price():
    """When line_total is missing, the amount is still computed."""
    result = rules_engine.evaluate([
        triplet(po=None, grn=None, invoice=Line("Laptop bag", 5, 4500, 0))
    ])
    assert result[0]["variance_amount"] == 22500.0


# ------------------------------------------------ missing on invoice

def test_received_but_not_billed_is_informational_only():
    """
    The company has goods it has not been charged for. Worth noting,
    but nothing is at risk, so severity is LOW and variance is zero.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=None,
        )
    ])
    assert kinds(result) == ["MISSING_ON_INVOICE"]
    assert result[0]["severity"] == "LOW"
    assert result[0]["variance_amount"] == 0.0


# --------------------------------------------- extraction failure
#
# These are the regression tests for the defect found during demo
# testing: a zero unit price was being reported as a 100% price
# variance, which is a fabricated finding.

def test_zero_invoice_price_is_an_extraction_failure_not_a_variance():
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=Line("Dell", 10, 0),
        )
    ])
    assert kinds(result) == ["EXTRACTION_FAILURE"]
    assert "PRICE_VARIANCE" not in kinds(result)


def test_extraction_failure_reports_no_money_at_stake():
    """
    Nothing is financially at risk - the system simply could not read
    the document. Inventing a variance figure here would be the same
    error in a different form.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 10),
            invoice=Line("Dell", 10, 0),
        )
    ])
    assert result[0]["variance_amount"] == 0.0


def test_a_genuinely_free_line_on_both_documents_is_not_flagged():
    """
    A promotional item priced at zero on BOTH the PO and the invoice is
    consistent, not a failure. The guard only fires when the PO has a
    price and the invoice does not.
    """
    result = rules_engine.evaluate([
        triplet(
            po=Line("Free carry case", 1, 0),
            grn=Line("Free carry case", 1),
            invoice=Line("Free carry case", 1, 0),
        )
    ])
    assert kinds(result) == []


# --------------------------------------------------- multiple rules

def test_price_and_quantity_can_both_fire_on_one_line():
    """Overcharged AND billed for undelivered units."""
    result = rules_engine.evaluate([
        triplet(
            po=Line("Dell", 10, 185000),
            grn=Line("Dell", 7),
            invoice=Line("Dell", 10, 199000),
        )
    ])
    assert kinds(result) == ["PRICE_VARIANCE", "QUANTITY_VARIANCE"]


def test_several_lines_produce_several_exceptions():
    result = rules_engine.evaluate([
        triplet(Line("Good", 5, 1000), Line("Good", 5), Line("Good", 5, 1000)),
        triplet(Line("Bad", 5, 100000), Line("Bad", 5), Line("Bad", 5, 130000)),
        triplet(None, None, Line("Sneaky", 2, 50000, 100000)),
    ])
    assert kinds(result) == ["PRICE_VARIANCE", "UNAUTHORIZED_ITEM"]


# ------------------------------------------------------- summarize

def test_summary_counts_and_totals():
    exceptions = rules_engine.evaluate([
        triplet(Line("A", 10, 100000), Line("A", 10), Line("A", 10, 130000)),
        triplet(None, None, Line("B", 1, 50000, 50000)),
    ])
    verdict = rules_engine.summarize(exceptions)

    assert verdict["status"] == "EXCEPTION"
    assert verdict["auto_approve"] is False
    assert verdict["exception_count"] == 2
    assert verdict["high_severity_count"] == 2
    assert verdict["total_variance"] == 350000.0   # 300,000 + 50,000


def test_summary_counts_extraction_failures_separately():
    exceptions = rules_engine.evaluate([
        triplet(Line("A", 10, 185000), Line("A", 10), Line("A", 10, 0)),
    ])
    verdict = rules_engine.summarize(exceptions)
    assert verdict["extraction_failures"] == 1


# ----------------------------------------------------- empty input

def test_no_triplets_produces_no_exceptions():
    assert rules_engine.evaluate([]) == []
