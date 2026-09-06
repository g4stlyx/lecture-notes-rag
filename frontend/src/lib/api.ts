import type {
  ChatRequest,
  ChatResponse,
  DocumentListResponse,
  IngestionJob,
} from "../types/api";

const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const message = isDetailResponse(body) ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}

export function listDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>("/documents?pageSize=100");
}

export function createIngestionJob(force = false): Promise<IngestionJob> {
  return request<IngestionJob>("/ingestion/jobs", {
    method: "POST",
    body: JSON.stringify({ force }),
  });
}

export function getIngestionJob(jobId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/ingestion/jobs/${jobId}`);
}

export function askQuestion(payload: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(payload) });
}

function isDetailResponse(value: unknown): value is { detail: string } {
  return typeof value === "object" && value !== null && "detail" in value && typeof value.detail === "string";
}

