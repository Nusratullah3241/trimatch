export interface LineItem {
  id: number;
  line_number: number;
  description: string;
  item_code: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface Document {
  id: number;
  doc_type: "PO" | "GRN" | "INVOICE";
  filename: string;
  document_number: string;
  vendor_name: string;
  grand_total: number;
  was_scanned: boolean;
  extraction_confidence: number;
  source: string;
  uploaded_at: string;
  lines: LineItem[];
}

export interface MatchException {
  id: number;
  exception_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  line_description: string;
  expected_value: string;
  actual_value: string;
  variance_amount: number;
  variance_pct: number;
  ai_explanation: string;
  resolution: string;
}

export interface MatchRun {
  id: number;
  status: string;
  total_variance: number;
  processing_ms: number;
  created_at: string;
  po_doc_id: number;
  grn_doc_id: number;
  invoice_doc_id: number;
  applied_price_tolerance_pct: number;
  applied_absolute_tolerance: number;
  exceptions: MatchException[];
}

export interface Stats {
  total_documents: number;
  total_match_runs: number;
  auto_approved: number;
  auto_approval_rate: number;
  total_variance_caught: number;
  avg_processing_ms: number;
  exceptions_by_type: Record<string, number>;
  pending_review: number;
  estimated_minutes_saved: number;
}

export interface Tolerances {
  price_tolerance_pct: number;
  absolute_tolerance_amount: number;
  quantity_tolerance_pct: number;
  updated_at: string;
  updated_by: string;
}