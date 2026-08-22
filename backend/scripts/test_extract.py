"""Extracts one document and prints the result."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import extractor

ROOT = Path(__file__).resolve().parent.parent.parent
target = ROOT / "sample_data" / "purchase_orders" / "PO-2026-1000.pdf"

print(f"Reading: {target.name}\n")

doc = extractor.extract(str(target), "PO")

print(f"Document number : {doc.document_number}")
print(f"Vendor          : {doc.vendor_name}")
print(f"Date            : {doc.document_date}")
print(f"Currency        : {doc.currency}")
print(f"Confidence      : {doc.confidence}")
print(f"Was scanned     : {doc.was_scanned}")
print(f"\nLine items ({len(doc.line_items)}):")

for ln in doc.line_items:
    print(f"  {ln.line_number}. {ln.description[:42]:42} "
          f"qty={ln.quantity:>6g}  price={ln.unit_price:>12,.2f}")

print(f"\nGrand total     : {doc.grand_total:,.2f}" if doc.grand_total else "")