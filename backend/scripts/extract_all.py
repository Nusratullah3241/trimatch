"""Extracts all 120 sample documents and reports on the results."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import extractor

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES = ROOT / "sample_data"

truth = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))

jobs = []
for t in truth:
    jobs.append((t["po_file"], "PO", t))
    jobs.append((t["grn_file"], "GRN", t))
    jobs.append((t["invoice_file"], "INVOICE", t))

print(f"Extracting {len(jobs)} documents...\n")

results = []
failures = []
started = time.time()

for i, (rel_path, doc_type, meta) in enumerate(jobs, 1):
    path = SAMPLES / rel_path
    try:
        t0 = time.time()
        doc = extractor.extract(str(path), doc_type)
        ms = int((time.time() - t0) * 1000)

        results.append({
            "file": rel_path,
            "doc_type": doc_type,
            "set_id": meta["set_id"],
            "vendor": meta["vendor"],
            "extracted_number": doc.document_number,
            "line_count": len(doc.line_items),
            "confidence": doc.confidence,
            "ms": ms,
        })
        status = "ok"
    except Exception as e:
        failures.append({"file": rel_path, "error": str(e)[:120]})
        status = f"FAILED - {str(e)[:60]}"

    if i % 10 == 0 or status != "ok":
        print(f"  [{i:3d}/{len(jobs)}]  {rel_path:45} {status}")

elapsed = time.time() - started

# --- report -----------------------------------------------------------
print("\n" + "=" * 60)
print(f"Extracted        : {len(results)}/{len(jobs)}")
print(f"Failed           : {len(failures)}")
print(f"Total time       : {elapsed:.1f}s")
if results:
    avg = sum(r["ms"] for r in results) / len(results)
    print(f"Avg per document : {avg:.0f} ms")
    lowconf = [r for r in results if r["confidence"] < 0.8]
    print(f"Low confidence   : {len(lowconf)}")

print("\nBy vendor:")
vendors = {}
for r in results:
    vendors.setdefault(r["vendor"], []).append(r)
for v, rows in sorted(vendors.items()):
    conf = sum(x["confidence"] for x in rows) / len(rows)
    print(f"  {v:38} {len(rows):3d} docs   avg conf {conf:.2f}")

if failures:
    print("\nFailures:")
    for f in failures:
        print(f"  {f['file']}: {f['error']}")

out = SAMPLES / "extraction_results.json"
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nSaved: {out}")
print("=" * 60)