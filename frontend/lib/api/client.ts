import type {
  ApiError,
  ChangeRecord,
  ComparisonHistoryResponse,
  ComparisonResult,
  ComparisonSummary,
  ParsedDocument,
} from "@/lib/types/api";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: init?.signal ?? AbortSignal.timeout(180_000),
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "TimeoutError") {
      throw new ApiRequestError("The analysis is taking longer than expected. You can retry the comparison.", 408, "REQUEST_TIMEOUT");
    }
    throw new ApiRequestError(
      "Unable to connect to the analysis service. Check that the backend is running, then try again.",
      0,
      "NETWORK_ERROR",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const apiError = isApiError(payload) ? payload : null;
    throw new ApiRequestError(
      apiError?.message ?? `The request failed with status ${response.status}.`,
      response.status,
      apiError?.error,
    );
  }
  return payload as T;
}

function isApiError(value: unknown): value is ApiError {
  return (
    typeof value === "object" &&
    value !== null &&
    "message" in value &&
    typeof value.message === "string" &&
    "error" in value &&
    typeof value.error === "string"
  );
}

export function createComparison(oldFile: File, newFile: File): Promise<ComparisonResult> {
  const form = new FormData();
  form.append("old_file", oldFile);
  form.append("new_file", newFile);
  return request<unknown>("/api/v1/comparisons", { method: "POST", body: form }).then((payload) => {
    if (!isComparisonResult(payload)) throw malformedResponse();
    return payload;
  });
}

export function getComparison(id: string): Promise<ComparisonResult> {
  return request<unknown>(`/api/v1/comparisons/${encodeURIComponent(id)}`).then((payload) => {
    if (!isComparisonResult(payload)) throw malformedResponse();
    return payload;
  });
}

export function getChanges(id: string, includeUnchanged = true): Promise<ChangeRecord[]> {
  return request<unknown>(
    `/api/v1/comparisons/${encodeURIComponent(id)}/changes?include_unchanged=${includeUnchanged}`,
  ).then((payload) => {
    if (!Array.isArray(payload) || !payload.every(isChangeRecord)) throw malformedResponse();
    return payload;
  });
}

export function getSummary(id: string): Promise<ComparisonSummary> {
  return request<unknown>(`/api/v1/comparisons/${encodeURIComponent(id)}/summary`).then((payload) => {
    if (!isSummary(payload)) throw malformedResponse();
    return payload;
  });
}

export function getHistory(limit = 20, offset = 0): Promise<ComparisonHistoryResponse> {
  return request<ComparisonHistoryResponse>(`/api/v1/comparisons?limit=${limit}&offset=${offset}`);
}

export function parseDocument(file: File): Promise<ParsedDocument> {
  const form = new FormData();
  form.append("file", file);
  return request<ParsedDocument>("/api/v1/documents/parse", { method: "POST", body: form });
}

export const configuredUploadLimitMb = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB || 50);

function malformedResponse() {
  return new ApiRequestError("The analysis service returned an incomplete response. Please retry.", 502, "INVALID_RESPONSE");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSummary(value: unknown): value is ComparisonSummary {
  if (!isRecord(value)) return false;
  return ["total_changes", "additions", "deletions", "modifications", "numerical_changes", "temporal_changes", "entity_changes", "contradictions", "refinements", "unchanged"].every((key) => typeof value[key] === "number");
}

function isDocumentMeta(value: unknown): boolean {
  return isRecord(value) && typeof value.filename === "string" && typeof value.pages === "number";
}

function isChangeRecord(value: unknown): value is ChangeRecord {
  return isRecord(value) && typeof value.id === "string" && typeof value.type === "string" && typeof value.confidence === "number" && typeof value.explanation === "string" && isRecord(value.details);
}

function isComparisonResult(value: unknown): value is ComparisonResult {
  return isRecord(value) && typeof value.comparison_id === "string" && typeof value.created_at === "string" && isDocumentMeta(value.old_document) && isDocumentMeta(value.new_document) && isSummary(value.summary) && Array.isArray(value.changes) && value.changes.every(isChangeRecord);
}
