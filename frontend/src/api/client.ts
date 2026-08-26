import type { Document, MatchRun, MatchException, Stats } from "../types";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) message = body.detail;
    } catch {
      // response wasn't JSON - keep the status text
    }
    throw new Error(message);
  }
  return res.json();
}

export function uploadDocument(file: File, docType: string): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("doc_type", docType);
  return req<Document>("/api/documents/upload", { method: "POST", body: form });
}

export function listDocuments(): Promise<Document[]> {
  return req<Document[]>("/api/documents");
}

export function getDocument(id: number): Promise<Document> {
  return req<Document>(`/api/documents/${id}`);
}

export function runMatch(poId: number, grnId: number, invoiceId: number): Promise<MatchRun> {
  return req<MatchRun>("/api/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ po_doc_id: poId, grn_doc_id: grnId, invoice_doc_id: invoiceId }),
  });
}

export function listMatches(): Promise<MatchRun[]> {
  return req<MatchRun[]>("/api/match");
}

export function getMatch(id: number): Promise<MatchRun> {
  return req<MatchRun>(`/api/match/${id}`);
}

export function resolveException(id: number, resolution: string): Promise<MatchException> {
  return req<MatchException>(`/api/match/exceptions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolution }),
  });
}

export function getStats(): Promise<Stats> {
  return req<Stats>("/api/stats");
}

export function money(n: number): string {
  return new Intl.NumberFormat("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n || 0);
}