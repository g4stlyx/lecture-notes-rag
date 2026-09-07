export type DocumentStatus = "discovered" | "processing" | "ready" | "failed" | "stale";

export interface DocumentSummary {
  id: string;
  displayName: string;
  sourcePath: string;
  extension: string;
  semester: number | null;
  course: string | null;
  pageCount: number | null;
  extractionMethod: string | null;
  extractionQuality: number | null;
  status: DocumentStatus;
  errorCode: string | null;
  indexedAt: string | null;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface SourceCitation {
  label: string;
  documentId: string;
  title: string;
  sourcePath: string;
  semester: number | null;
  course: string | null;
  pageStart: number;
  pageEnd: number;
  excerpt: string;
  score: number;
  openUrl: string;
}

export interface ChatRequest {
  question: string;
  semester?: number;
  course?: string;
  documentIds?: string[];
  conversationId?: string;
}

export interface ChatResponse {
  conversationId: string;
  answer: string;
  sources: SourceCitation[];
  grounded: boolean;
  model: string | null;
  latencyMs: number;
}

export interface IngestionJob {
  id: string;
  status: "queued" | "running" | "paused" | "interrupted" | "completed" | "failed";
  discoveredCount: number;
  processedCount: number;
  skippedCount: number;
  failedCount: number;
  startedAt: string | null;
  completedAt: string | null;
  errorSummary: string | null;
}
