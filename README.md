# TriMatch

AI-powered three-way match for accounts payable. Compares a purchase order,
a goods received note, and an invoice, then flags discrepancies for review.

Built as an individual university automation project.

## The problem

Before paying a supplier invoice, someone has to check it against what was
ordered and what actually arrived. It takes 10-15 minutes per invoice, it is
repetitive, and tired reviewers miss things - a rate quietly raised, items
billed that never showed up, the same invoice paid twice.

## What it does

1. A PDF lands in the inbox folder - no human action required
2. Gemini reads it and returns structured data, whatever layout the vendor uses
3. Line items are matched across all three documents using fuzzy matching
4. Business rules apply configurable tolerances
5. Clean sets are approved automatically; problems are raised as exceptions
   with the amount at stake, for a human to decide

## Results

Measured on 40 synthetic document sets across four different vendor layouts:

- 40/40 correctly classified
- 100% precision and recall on exception detection
- 5.0 seconds per set against a 12-minute manual baseline
- 21/40 sets required no human involvement
- 2,742,284.94 PKR of discrepancies identified

These figures are on digitally generated PDFs with clean text layers.
Performance on genuinely scanned documents would be lower and is not
represented. Full breakdown, including limitations, in `docs/evaluation.md`.

## Rules

| Rule | Trigger |
|---|---|
| PRICE_VARIANCE | Invoiced rate above the PO rate beyond tolerance |
| QUANTITY_VARIANCE | Invoiced quantity above quantity received |
| UNAUTHORIZED_ITEM | Invoice line matching no PO line |
| MISSING_ON_INVOICE | Received but not billed |
| DUPLICATE_INVOICE | Same invoice number and vendor already processed |
| EXTRACTION_FAILURE | A price could not be read - flagged as unreadable, not as a variance |

The price rule requires BOTH a percentage breach and an absolute amount
breach before raising an exception. A 5% rise on a 100-rupee item is 5
rupees; flagging it costs more reviewer attention than it protects. A
system that flags everything is one nobody reads.

Thresholds are editable at runtime from the Tolerances page, with validation
that prevents a control being switched off by setting it absurdly high.

## Tests

    cd backend
    pytest -v

25 unit tests covering every rule, both tolerance boundaries, null and zero
values, missing documents, and regressions for two defects found during
demonstration testing.

## Stack

Backend: Python 3.11, FastAPI, SQLAlchemy, SQLite, Pydantic, Google Gemini,
watchdog, RapidFuzz, pytest.
Frontend: React 18, TypeScript, Vite, Tailwind CSS, Recharts.

## Running it

Backend:

    cd backend
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env        # add your GEMINI_API_KEY
    python scripts\init_db.py
    uvicorn app.main:app --reload --port 8000

Frontend:

    cd frontend
    npm install
    npm run dev

Folder watcher - the automatic trigger:

    cd backend
    python -m app.services.watcher

Generate test documents and evaluate:

    python scripts\generate_sample_data.py
    python scripts\extract_all.py
    python scripts\run_evaluation.py

API documentation at http://localhost:8000/docs

## Known limitations

- No authentication. Anyone with the URL can resolve exceptions.
- Resolutions are recorded but trigger no downstream action.
- The folder watcher is local; production would use email ingestion.
- Tested only on digital PDFs, not scanned or photographed documents.
- Single-page invoices only; partial deliveries across multiple GRNs are
  not modelled.
