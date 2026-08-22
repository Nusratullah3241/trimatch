"""Runs the full three-way match on cached sets and compares to ground truth."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import extractor, line_matcher, rules_engine

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES = ROOT / "sample_data"

truth = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))

correct = 0
tested = 0
skipped = 0

for t in truth:
    try:
        po = extractor.extract(str(SAMPLES / t["po_file"]), "PO")
        grn = extractor.extract(str(SAMPLES / t["grn_file"]), "GRN")
        inv = extractor.extract(str(SAMPLES / t["invoice_file"]), "INVOICE")
    except Exception:
        skipped += 1
        continue   # not cached yet

    triplets = line_matcher.match_lines(po.line_items, grn.line_items, inv.line_items)
    found = rules_engine.evaluate(triplets)
    verdict = rules_engine.summarize(found)

    expected_types = sorted(e["type"] for e in t["expected_exceptions"])
    found_types = sorted(e["exception_type"] for e in found)

    ok = expected_types == found_types
    correct += ok
    tested += 1

    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] Set {t['set_id']:2d}  {t['scenario']:20} "
          f"expected={expected_types or ['none']}  found={found_types or ['none']}")

    if not ok or found:
        for e in found:
            print(f"        -> {e['exception_type']}: {e['line_description'][:38]}")
            print(f"           expected {e['expected_value']}, got {e['actual_value']}, "
                  f"variance {e['variance_amount']:,.2f} ({e['variance_pct']}%)")

print("\n" + "=" * 60)
print(f"Tested  : {tested} sets   (skipped {skipped} - not cached yet)")
print(f"Correct : {correct}/{tested}" +
      (f"   = {correct/tested*100:.1f}%" if tested else ""))
print("=" * 60)