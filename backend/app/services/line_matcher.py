"""Pairs up line items across PO, GRN, and Invoice."""
from rapidfuzz import fuzz

SIMILARITY_THRESHOLD = 70   # 0-100. Below this, items are considered different.


def similarity(a: str, b: str) -> float:
    """
    token_sort_ratio ignores word order, so
    'Dell Latitude 5540 i7' and 'LAT-5540 Dell (i7)' still score high.
    """
    return fuzz.token_sort_ratio((a or "").lower(), (b or "").lower())


def _find_best(source, candidates, already_used: set):
    """
    Finds the candidate line that best matches `source`.
    Returns (index, line) or (None, None) if nothing is close enough.
    """
    best_idx = None
    best_score = 0.0

    for idx, cand in enumerate(candidates):
        if idx in already_used:
            continue

        # An exact item code beats fuzzy text every time
        src_code = (source.item_code or "").strip()
        cand_code = (cand.item_code or "").strip()
        if src_code and src_code == cand_code:
            return idx, cand

        score = similarity(source.description, cand.description)
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is not None and best_score >= SIMILARITY_THRESHOLD:
        return best_idx, candidates[best_idx]

    return None, None


def match_lines(po_lines, grn_lines, inv_lines) -> list[dict]:
    """
    Returns a list of triplets: {"po": ..., "grn": ..., "invoice": ...}

    Any of the three can be None. A None IS meaningful:
      - invoice present, po missing  -> item was never ordered
      - po present, invoice missing  -> ordered but not billed
    """
    triplets = []
    used_grn: set = set()
    used_inv: set = set()

    for po in po_lines:
        grn_idx, grn = _find_best(po, grn_lines, used_grn)
        inv_idx, inv = _find_best(po, inv_lines, used_inv)

        if grn_idx is not None:
            used_grn.add(grn_idx)
        if inv_idx is not None:
            used_inv.add(inv_idx)

        triplets.append({"po": po, "grn": grn, "invoice": inv})

    # Invoice lines that matched no PO line = unauthorized items
    for idx, inv in enumerate(inv_lines):
        if idx in used_inv:
            continue

        grn_idx, grn = _find_best(inv, grn_lines, used_grn)
        if grn_idx is not None:
            used_grn.add(grn_idx)

        triplets.append({"po": None, "grn": grn, "invoice": inv})

    return triplets