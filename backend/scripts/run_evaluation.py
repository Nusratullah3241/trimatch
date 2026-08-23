"""Runs every cached document set against ground truth and writes docs/evaluation.md.

Produces the numbers for the report:
  - field-level extraction accuracy
  - exception detection precision and recall
  - honest processing time (cold API call vs cached)
  - failure analysis and limitations

Run:  python scripts\\run_evaluation.py
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import extractor, line_matcher, rules_engine

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES = ROOT / "sample_data"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

truth = json.loads((SAMPLES / "ground_truth.json").read_text(encoding="utf-8"))

# ------------------------------------------------------- cold timing
# The disk cache makes repeat runs misleadingly fast. Measure a few sets
# with the cache bypassed so the reported figure reflects real API latency.
COLD_SAMPLES = 3
cold_timings = []

print(f"Measuring cold processing time on {COLD_SAMPLES} sets...")
for t in truth[:COLD_SAMPLES]:
    try:
        t0 = time.time()
        extractor.extract(str(SAMPLES / t["po_file"]), "PO", use_cache=False)
        extractor.extract(str(SAMPLES / t["grn_file"]), "GRN", use_cache=False)
        extractor.extract(str(SAMPLES / t["invoice_file"]), "INVOICE", use_cache=False)
        cold_timings.append((time.time() - t0) * 1000)
    except Exception as e:
        print(f"  cold sample skipped: {str(e)[:60]}")

cold_avg = sum(cold_timings) / len(cold_timings) if cold_timings else 0
if cold_avg:
    print(f"  cold average: {cold_avg:.0f} ms per set\n")
else:
    print("  no cold samples completed (quota) - cached timing only\n")

# ---------------------------------------------------------------- run
results = []
skipped = []
timings = []

print(f"Evaluating {len(truth)} document sets...\n")

for t in truth:
    try:
        t0 = time.time()
        po = extractor.extract(str(SAMPLES / t["po_file"]), "PO")
        grn = extractor.extract(str(SAMPLES / t["grn_file"]), "GRN")
        inv = extractor.extract(str(SAMPLES / t["invoice_file"]), "INVOICE")
        elapsed_ms = int((time.time() - t0) * 1000)
    except Exception as e:
        skipped.append({"set_id": t["set_id"], "reason": str(e)[:80]})
        continue

    triplets = line_matcher.match_lines(po.line_items, grn.line_items, inv.line_items)
    found = rules_engine.evaluate(triplets)
    verdict = rules_engine.summarize(found)

    expected_types = sorted(e["type"] for e in t["expected_exceptions"])
    found_types = sorted(e["exception_type"] for e in found)

    fields = {
        "po_number": po.document_number == t["po_number"],
        "invoice_number": inv.document_number == t["invoice_number"],
        "vendor": (po.vendor_name or "").strip() == t["vendor"].strip(),
        "po_line_count": len(po.line_items) == t["po_line_count"],
        "invoice_line_count": len(inv.line_items) == t["invoice_line_count"],
        "po_total": abs((po.grand_total or 0) - t["po_grand_total"]) < 1.0,
    }

    results.append({
        "set_id": t["set_id"],
        "scenario": t["scenario"],
        "vendor": t["vendor"],
        "expected": expected_types,
        "found": found_types,
        "classification_correct": expected_types == found_types,
        "fields": fields,
        "confidence": round((po.confidence + grn.confidence + inv.confidence) / 3, 3),
        "was_scanned": po.was_scanned or grn.was_scanned or inv.was_scanned,
        "elapsed_ms": elapsed_ms,
        "expected_variance": sum(
            e.get("variance_amount", 0) for e in t["expected_exceptions"]),
        "found_variance": verdict["total_variance"],
    })
    timings.append(elapsed_ms)

n = len(results)
if n == 0:
    print("No cached sets found. Run scripts\\extract_all.py first.")
    sys.exit(1)

# ---------------------------------------------------------- accuracy
correct = sum(r["classification_correct"] for r in results)

field_names = list(results[0]["fields"].keys())
field_acc = {f: sum(r["fields"][f] for r in results) / n * 100 for f in field_names}

tp = fp = fn = 0
for r in results:
    exp = Counter(r["expected"])
    got = Counter(r["found"])
    for kind in set(exp) | set(got):
        hit = min(exp[kind], got[kind])
        tp += hit
        fp += max(0, got[kind] - exp[kind])
        fn += max(0, exp[kind] - got[kind])

precision = tp / (tp + fp) * 100 if (tp + fp) else 0.0
recall = tp / (tp + fn) * 100 if (tp + fn) else 0.0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

by_scenario: dict[str, list] = {}
for r in results:
    by_scenario.setdefault(r["scenario"], []).append(r)

by_vendor: dict[str, list] = {}
for r in results:
    by_vendor.setdefault(r["vendor"], []).append(r)

failures = [r for r in results if not r["classification_correct"]]

avg_ms = sum(timings) / len(timings)
MANUAL_MIN = 12

# ------------------------------------------------------------ report
lines = []
add = lines.append

add("# TriMatch - Evaluation Results\n")
add("Generated automatically by `scripts/run_evaluation.py`.\n")
add(f"Sets evaluated: **{n}** of {len(truth)}"
    + (f" ({len(skipped)} not yet extracted)" if skipped else "") + "\n")

add("\n## 1. Headline\n")
add("| Measure | Result |")
add("|---|---|")
add(f"| Sets classified correctly | {correct}/{n} ({correct/n*100:.1f}%) |")
add(f"| Exception detection precision | {precision:.1f}% |")
add(f"| Exception detection recall | {recall:.1f}% |")
add(f"| F1 score | {f1:.1f}% |")
if cold_avg:
    add(f"| Processing time (live API call) | {cold_avg:.0f} ms per set |")
add(f"| Variance identified | {sum(r['found_variance'] for r in results):,.2f} PKR |")

add("\n**What these figures cover.** All measurements are on "
    f"{n} synthetically generated document sets across four vendor layouts. "
    "Every document was a digital PDF with a clean text layer. Real-world "
    "performance on scanned or photographed invoices would be materially "
    "lower and is not represented here.\n")

add("\n**Recall matters more than precision in this domain.** A missed "
    "overbilling costs real money; a false alarm costs a reviewer about "
    "thirty seconds. The tolerance rules are tuned accordingly.\n")

add("\n## 2. Field-level extraction accuracy\n")
add("Reported per field rather than as one average, since an overall figure "
    "hides weak spots.\n")
add("| Field | Accuracy |")
add("|---|---|")
for f in field_names:
    add(f"| {f.replace('_', ' ')} | {field_acc[f]:.1f}% |")

add("\n## 3. By scenario\n")
add("| Scenario | Sets | Correct |")
add("|---|---|---|")
for sc, rows in sorted(by_scenario.items()):
    ok = sum(r["classification_correct"] for r in rows)
    add(f"| {sc} | {len(rows)} | {ok}/{len(rows)} |")

add("\n**Note on DUPLICATE_INVOICE.** Duplicate detection is implemented in "
    "`match_service.py` and is exercised through the folder watcher and the "
    "API, where database state is available. This offline evaluation runs "
    "without a database, so those sets pass trivially and should not be read "
    "as evidence that the rule works. It is demonstrated separately.\n")

add("\n## 4. By vendor document format\n")
add("Each vendor uses different column headers, date formats, and layout - "
    "one writes \"Qty\", another \"Quantity\", another \"Nos\", another "
    "\"QTY\". This table shows whether format variation affects accuracy, "
    "which is the central argument for using a language model over "
    "hand-written parsing rules.\n")
add("| Vendor | Sets | Correct | Avg confidence |")
add("|---|---|---|---|")
for v, rows in sorted(by_vendor.items()):
    ok = sum(r["classification_correct"] for r in rows)
    conf = sum(r["confidence"] for r in rows) / len(rows)
    add(f"| {v} | {len(rows)} | {ok}/{len(rows)} | {conf:.2f} |")

add("\n## 5. Processing time\n")
manual = n * MANUAL_MIN

if cold_avg:
    system_min = n * cold_avg / 60000
    add("Timing is reported two ways, because a disk cache was added during "
        "development to avoid re-calling the API on unchanged documents. "
        "Repeat runs read from that cache and are not representative.\n")
    add(f"| Condition | Per set | {n} sets |")
    add("|---|---|---|")
    add(f"| Cold - live API call ({len(cold_timings)} sampled) | "
        f"{cold_avg:.0f} ms | {system_min:.1f} min |")
    add(f"| Cached - already extracted | {avg_ms:.0f} ms | "
        f"{n * avg_ms / 60000:.2f} min |")
    add(f"| Manual, at {MANUAL_MIN} min per set | {MANUAL_MIN * 60000:.0f} ms | "
        f"{manual} min |")
    add(f"\nAgainst the cold figure, which is the honest comparison: "
        f"**{manual} minutes reduced to {system_min:.1f} minutes, "
        f"a {(1 - system_min/manual)*100:.1f}% reduction.**\n")
else:
    add(f"- Cached processing: {avg_ms:.0f} ms per set")
    add("- A cold-run measurement could not be taken because the API daily "
        "quota was exhausted. The cached figure reflects disk reads only and "
        "must not be presented as end-to-end system latency.\n")

add(f"- Sets requiring no human involvement: "
    f"**{sum(1 for r in results if not r['found'])}/{n}** "
    f"({sum(1 for r in results if not r['found'])/n*100:.0f}%)\n")

add("\n## 6. Failure analysis\n")
if not failures:
    add("No classification failures on the evaluated sets.\n")
    add("This result should be read narrowly. The test corpus is synthetic, "
        "generated by a script with known values, and every document is a "
        "digital PDF. The evaluation demonstrates that the pipeline handles "
        "format variation and applies its rules correctly; it does not "
        "demonstrate robustness to real-world document quality.\n")
    add("Known untested conditions: scanned or photographed documents, "
        "rotated or skewed pages, handwritten annotations, multi-page "
        "invoices, partial deliveries across several GRNs, and foreign "
        "currency.\n")
else:
    add(f"{len(failures)} set(s) classified incorrectly.\n")
    add("| Set | Scenario | Expected | Found |")
    add("|---|---|---|---|")
    for f in failures:
        add(f"| {f['set_id']} | {f['scenario']} | "
            f"{', '.join(f['expected']) or 'none'} | "
            f"{', '.join(f['found']) or 'none'} |")

if skipped:
    add("\n## 7. Not evaluated\n")
    add(f"{len(skipped)} sets were not extracted and are excluded from every "
        "figure above.\n")

add("\n## Limitations\n")
add("- Test documents are synthetic and digitally generated. Real scanned "
    "invoices with skew, noise, and handwriting would extract less reliably.")
add("- Four vendor layouts were tested. Production would encounter many more.")
add("- Tolerance thresholds (2% price drift, 500 PKR absolute floor) are "
    "assumptions, not derived from any real company's approval policy.")
add("- The manual baseline of 12 minutes per set is an industry estimate, "
    "not a measured comparison against a specific accounts team.")
add("- Duplicate-invoice detection is excluded from these figures, as noted "
    "in section 3.")
add("- The cold timing is sampled from 3 sets, not all of them, because of "
    "API quota limits. It is indicative rather than precise.\n")

out = DOCS / "evaluation.md"
out.write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------ console
print("=" * 62)
print(f"Sets evaluated       : {n}")
print(f"Classified correctly : {correct}/{n}  ({correct/n*100:.1f}%)")
print(f"Precision / Recall   : {precision:.1f}% / {recall:.1f}%")
print(f"F1                   : {f1:.1f}%")
if cold_avg:
    print(f"Cold time per set    : {cold_avg:.0f} ms  (live API)")
print(f"Cached time per set  : {avg_ms:.0f} ms  (disk only)")
print(f"Failures             : {len(failures)}")
print(f"\nWritten: {out}")
print("=" * 62)
