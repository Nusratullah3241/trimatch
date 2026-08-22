"""
Generates 40 sets of sample documents (Purchase Order, GRN, Invoice) as PDFs,
plus a ground_truth.json file recording the correct answer for each set.

Run once:  python scripts\\generate_sample_data.py
"""
import json
import random
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

# --- where to write -----------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "sample_data"
(OUT / "purchase_orders").mkdir(parents=True, exist_ok=True)
(OUT / "grns").mkdir(parents=True, exist_ok=True)
(OUT / "invoices").mkdir(parents=True, exist_ok=True)

random.seed(42)  # same output every run - important for reproducible testing

# --- vendors, each with a DIFFERENT document layout ---------------------
# This is deliberate. If all documents look identical, your accuracy
# score is meaningless because you never tested format variation.
VENDORS = [
    {
        "name": "Zenith Computer Traders",
        "address": "Plot 24, I-9 Industrial Area, Islamabad",
        "qty_label": "Qty",
        "price_label": "Unit Price",
        "total_label": "Amount",
        "date_format": "{d:02d}/{m:02d}/{y}",
        "currency": "PKR",
        "show_item_code": True,
    },
    {
        "name": "Falcon Office Supplies (Pvt) Ltd",
        "address": "Suite 12, Clifton Block 5, Karachi",
        "qty_label": "Quantity",
        "price_label": "Rate",
        "total_label": "Total Value",
        "date_format": "{y}-{m:02d}-{d:02d}",
        "currency": "PKR",
        "show_item_code": False,
    },
    {
        "name": "Meridian Tech Distribution",
        "address": "31-A Gulberg III, Lahore",
        "qty_label": "Nos",
        "price_label": "Price/Unit",
        "total_label": "Line Total",
        "date_format": "{d:02d}-{mn}-{y}",
        "currency": "Rs.",
        "show_item_code": True,
    },
    {
        "name": "Apex Industrial Equipment",
        "address": "Sector 23, Korangi, Karachi",
        "qty_label": "QTY",
        "price_label": "UNIT COST",
        "total_label": "EXT. COST",
        "date_format": "{mn} {d}, {y}",
        "currency": "PKR",
        "show_item_code": False,
    },
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CATALOG = [
    ("LAP-DL5540", "Dell Latitude 5540 i7 16GB 512GB SSD", 185000),
    ("LAP-HP840", "HP EliteBook 840 G10 i5 16GB", 172000),
    ("MON-DL24", "Dell P2422H 24 inch IPS Monitor", 38500),
    ("PRN-HP477", "HP LaserJet Pro MFP M477fdw", 96000),
    ("UPS-APC15", "APC Smart-UPS 1500VA", 78000),
    ("KEY-LOGMX", "Logitech MX Keys Wireless Keyboard", 24500),
    ("NAS-SYN4B", "Synology DS923+ 4-Bay NAS", 215000),
    ("SWT-CIS24", "Cisco CBS250 24-Port Gigabit Switch", 142000),
    ("CHR-ERGO1", "Ergonomic Mesh Office Chair", 32000),
    ("DSK-ADJ160", "Height Adjustable Desk 160cm", 58000),
    ("SSD-SAM2TB", "Samsung 990 PRO 2TB NVMe SSD", 46000),
    ("DOC-THDR4", "Thunderbolt 4 Docking Station", 54000),
]

# --- how the invoice differs from the PO in each scenario ---------------
SCENARIOS = (
    ["PERFECT"] * 16
    + ["PRICE_VARIANCE"] * 8
    + ["QUANTITY_VARIANCE"] * 6
    + ["UNAUTHORIZED_ITEM"] * 4
    + ["WITHIN_TOLERANCE"] * 3
    + ["DUPLICATE_INVOICE"] * 2
    + ["MISSING_ON_INVOICE"] * 1
)

styles = getSampleStyleSheet()
TITLE = ParagraphStyle("t", parent=styles["Heading1"], fontSize=16, spaceAfter=2)
SUB = ParagraphStyle("s", parent=styles["Normal"], fontSize=9,
                     textColor=colors.HexColor("#555555"))
BODY = ParagraphStyle("b", parent=styles["Normal"], fontSize=9.5, leading=13)


def fmt_date(vendor, d, m, y):
    return vendor["date_format"].format(d=d, m=m, y=y, mn=MONTHS[m - 1])


def money(vendor, amount):
    return f"{vendor['currency']} {amount:,.2f}"


def build_pdf(path, vendor, doc_title, header_rows, table_head, table_rows,
              totals_rows, footer_note):
    """Shared PDF builder. Layout differs per vendor via the labels passed in."""
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    flow = []

    flow.append(Paragraph(vendor["name"], TITLE))
    flow.append(Paragraph(vendor["address"], SUB))
    flow.append(Spacer(1, 10))

    flow.append(Paragraph(f"<b>{doc_title}</b>", styles["Heading2"]))
    flow.append(Spacer(1, 4))

    meta = Table(header_rows, colWidths=[38 * mm, 60 * mm])
    meta.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(meta)
    flow.append(Spacer(1, 12))

    ncols = len(table_head)
    widths = [14 * mm] + [None] * (ncols - 1)
    data = [table_head] + table_rows
    t = Table(data, colWidths=[14 * mm, 70 * mm] + [None] * (ncols - 2),
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E6E1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 10))

    if totals_rows:
        tot = Table(totals_rows, colWidths=[None, 40 * mm], hAlign="RIGHT")
        tot.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.black),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        flow.append(tot)

    if footer_note:
        flow.append(Spacer(1, 14))
        flow.append(Paragraph(footer_note, SUB))

    doc.build(flow)


def make_po(path, vendor, po_no, date, lines):
    head = ["#", "Description"]
    if vendor["show_item_code"]:
        head.append("Item Code")
    head += [vendor["qty_label"], vendor["price_label"], vendor["total_label"]]

    rows = []
    for i, ln in enumerate(lines, 1):
        r = [str(i), ln["description"]]
        if vendor["show_item_code"]:
            r.append(ln["item_code"])
        r += [f"{ln['quantity']:g}",
              f"{ln['unit_price']:,.2f}",
              f"{ln['quantity'] * ln['unit_price']:,.2f}"]
        rows.append(r)

    subtotal = sum(l["quantity"] * l["unit_price"] for l in lines)
    build_pdf(
        path, vendor, "PURCHASE ORDER",
        [["PO Number:", po_no], ["Date:", date], ["Buyer:", "Ali Traders (Pvt) Ltd"]],
        head, rows,
        [["Subtotal:", money(vendor, subtotal)],
         ["Grand Total:", money(vendor, subtotal)]],
        "This purchase order is subject to agreed rates. Any price revision requires written approval.",
    )


def make_grn(path, vendor, grn_no, po_no, date, lines):
    # A GRN records what physically arrived - no prices.
    head = ["#", "Description"]
    if vendor["show_item_code"]:
        head.append("Item Code")
    head += [vendor["qty_label"] + " Received", "Condition"]

    rows = []
    for i, ln in enumerate(lines, 1):
        r = [str(i), ln["description"]]
        if vendor["show_item_code"]:
            r.append(ln["item_code"])
        r += [f"{ln['qty_received']:g}", "Good"]
        rows.append(r)

    build_pdf(
        path, vendor, "GOODS RECEIVED NOTE",
        [["GRN Number:", grn_no], ["Against PO:", po_no],
         ["Received Date:", date], ["Warehouse:", "Main Store, Karachi"]],
        head, rows, None,
        "Goods inspected on receipt. Quantities above reflect physical count.",
    )


def make_invoice(path, vendor, inv_no, po_no, date, lines):
    head = ["#", "Description"]
    if vendor["show_item_code"]:
        head.append("Item Code")
    head += [vendor["qty_label"], vendor["price_label"], vendor["total_label"]]

    rows = []
    for i, ln in enumerate(lines, 1):
        r = [str(i), ln["description"]]
        if vendor["show_item_code"]:
            r.append(ln["item_code"])
        r += [f"{ln['quantity']:g}",
              f"{ln['unit_price']:,.2f}",
              f"{ln['quantity'] * ln['unit_price']:,.2f}"]
        rows.append(r)

    subtotal = sum(l["quantity"] * l["unit_price"] for l in lines)
    tax = round(subtotal * 0.18, 2)
    build_pdf(
        path, vendor, "TAX INVOICE",
        [["Invoice No:", inv_no], ["Against PO:", po_no],
         ["Invoice Date:", date], ["Payment Terms:", "Net 30 days"]],
        head, rows,
        [["Subtotal:", money(vendor, subtotal)],
         ["Sales Tax @ 18%:", money(vendor, tax)],
         ["Grand Total:", money(vendor, subtotal + tax)]],
        "Please quote the invoice number with payment. Late payment surcharge applies after 30 days.",
    )


def build_set(idx, scenario):
    vendor = VENDORS[idx % len(VENDORS)]
    po_no = f"PO-2026-{1000 + idx}"
    grn_no = f"GRN-2026-{5000 + idx}"
    inv_no = f"INV-{vendor['name'][:3].upper()}-{9000 + idx}"

    day, month, year = random.randint(1, 28), random.randint(1, 8), 2026
    po_date = fmt_date(vendor, day, month, year)
    grn_date = fmt_date(vendor, min(day + 5, 28), month, year)
    inv_date = fmt_date(vendor, min(day + 6, 28), month, year)

    # 2-4 items per document
    picked = random.sample(CATALOG, random.randint(2, 4))
    po_lines = [
        {"item_code": c, "description": d, "quantity": random.randint(2, 15),
         "unit_price": float(p)}
        for c, d, p in picked
    ]

    grn_lines = [
        {"item_code": l["item_code"], "description": l["description"],
         "qty_received": l["quantity"]}
        for l in po_lines
    ]
    inv_lines = [dict(l) for l in po_lines]

    expected = []

    if scenario == "PRICE_VARIANCE":
        t = inv_lines[0]
        old = t["unit_price"]
        t["unit_price"] = round(old * random.uniform(1.06, 1.18), 2)
        expected.append({
            "type": "PRICE_VARIANCE",
            "line": t["description"],
            "po_price": old,
            "invoice_price": t["unit_price"],
            "variance_amount": round((t["unit_price"] - old) * t["quantity"], 2),
        })

    elif scenario == "WITHIN_TOLERANCE":
        t = inv_lines[0]
        old = t["unit_price"]
        t["unit_price"] = round(old * 1.008, 2)  # 0.8% - under the 2% limit
        expected = []  # should NOT be flagged

    elif scenario == "QUANTITY_VARIANCE":
        short = random.randint(1, 3)
        grn_lines[0]["qty_received"] = max(1, po_lines[0]["quantity"] - short)
        expected.append({
            "type": "QUANTITY_VARIANCE",
            "line": po_lines[0]["description"],
            "ordered": po_lines[0]["quantity"],
            "received": grn_lines[0]["qty_received"],
            "billed": inv_lines[0]["quantity"],
            "variance_amount": round(
                (inv_lines[0]["quantity"] - grn_lines[0]["qty_received"])
                * inv_lines[0]["unit_price"], 2),
        })

    elif scenario == "UNAUTHORIZED_ITEM":
        extra_pool = [c for c in CATALOG if c[0] not in [l["item_code"] for l in po_lines]]
        c, d, p = random.choice(extra_pool)
        qty = random.randint(1, 5)
        extra = {"item_code": c, "description": d, "quantity": qty,
                 "unit_price": float(p)}
        inv_lines.append(extra)
        grn_lines.append({"item_code": c, "description": d, "qty_received": qty})
        expected.append({
            "type": "UNAUTHORIZED_ITEM",
            "line": d,
            "variance_amount": round(qty * p, 2),
        })

    elif scenario == "MISSING_ON_INVOICE":
        dropped = inv_lines.pop()
        expected.append({
            "type": "MISSING_ON_INVOICE",
            "line": dropped["description"],
            "variance_amount": 0,
        })

    # DUPLICATE_INVOICE and PERFECT need no line changes

    make_po(OUT / "purchase_orders" / f"{po_no}.pdf", vendor, po_no, po_date, po_lines)
    make_grn(OUT / "grns" / f"{grn_no}.pdf", vendor, grn_no, po_no, grn_date, grn_lines)
    make_invoice(OUT / "invoices" / f"{inv_no}.pdf", vendor, inv_no, po_no, inv_date, inv_lines)

    return {
        "set_id": idx,
        "scenario": scenario,
        "vendor": vendor["name"],
        "po_number": po_no,
        "grn_number": grn_no,
        "invoice_number": inv_no,
        "po_file": f"purchase_orders/{po_no}.pdf",
        "grn_file": f"grns/{grn_no}.pdf",
        "invoice_file": f"invoices/{inv_no}.pdf",
        "po_line_count": len(po_lines),
        "invoice_line_count": len(inv_lines),
        "po_grand_total": round(sum(l["quantity"] * l["unit_price"] for l in po_lines), 2),
        "invoice_subtotal": round(sum(l["quantity"] * l["unit_price"] for l in inv_lines), 2),
        "expected_exceptions": expected,
        "should_auto_approve": len(expected) == 0,
    }


def main():
    scenarios = SCENARIOS[:]
    random.shuffle(scenarios)

    truth = []
    for i, sc in enumerate(scenarios):
        truth.append(build_set(i, sc))
        print(f"  [{i + 1:2d}/{len(scenarios)}]  {sc}")

    (OUT / "ground_truth.json").write_text(
        json.dumps(truth, indent=2), encoding="utf-8")

    total_exc = sum(len(t["expected_exceptions"]) for t in truth)
    auto = sum(1 for t in truth if t["should_auto_approve"])

    print("\n" + "=" * 55)
    print(f"Generated {len(truth)} document sets ({len(truth) * 3} PDFs)")
    print(f"Should auto-approve : {auto}")
    print(f"Should be flagged   : {len(truth) - auto}")
    print(f"Total exceptions    : {total_exc}")
    print(f"Ground truth        : {OUT / 'ground_truth.json'}")
    print("=" * 55)


if __name__ == "__main__":
    main()