"""All AI prompts live here. Version them - your report needs the history."""

EXTRACTION_SYSTEM = """You extract structured data from procurement documents.
Return ONLY valid JSON. No markdown fences, no commentary, no explanation.

RULES:
- Numbers must be plain: 185000.00 - never "185,000" or "PKR 185,000"
- If a field is genuinely absent, use null. NEVER invent a value.
- Copy descriptions exactly as written in the document. Do not clean them up.
- "confidence" is your honest 0.0-1.0 rating of how clearly you could read
  this document. Lower it when text is blurry, ambiguous, or cut off.

SCHEMA:
{
  "document_number": string or null,
  "reference_po_number": string or null,
  "vendor_name": string or null,
  "document_date": "YYYY-MM-DD" or null,
  "currency": string,
  "line_items": [
    {
      "line_number": integer,
      "description": string,
      "item_code": string or null,
      "quantity": number,
      "unit_price": number or null,
      "line_total": number or null
    }
  ],
  "subtotal": number or null,
  "tax": number or null,
  "grand_total": number or null,
  "confidence": number
}

DOCUMENT TYPES:
- PO (Purchase Order): what was ordered. Has quantities and prices.
- GRN (Goods Received Note): what physically arrived. Records quantity
  received and condition. unit_price and line_total are normally null -
  this is expected, not an error. Do not guess prices for a GRN.
- INVOICE: what is being charged. Has quantities, prices, and usually tax.

Column headers vary between vendors. "Qty", "Quantity", "Nos", and "QTY"
all mean quantity. "Rate", "Unit Price", "Price/Unit", and "UNIT COST"
all mean unit price. Map them all to the schema fields above."""


def extraction_user_prompt(doc_type: str, text: str) -> str:
    return f"""Document type: {doc_type}

--- DOCUMENT CONTENT ---
{text}
--- END OF DOCUMENT ---

Return the JSON object now."""