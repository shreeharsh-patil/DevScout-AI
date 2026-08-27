/**
 * Centralized API client for DevScout AI.
 *
 * All backend requests go through this module so the base URL is configured
 * exactly once via the NEXT_PUBLIC_API_URL environment variable.
 *
 * Safety: NEXT_PUBLIC_* vars are embedded into the client bundle at build
 * time. Only non-secret values (like an API base URL) should use this prefix.
 */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Default timeout for every request (ms). */
const DEFAULT_TIMEOUT_MS = 30_000;

/** Timeout for long-polling status checks (ms). */
const POLL_TIMEOUT_MS = 10_000;

// ---------------------------------------------------------------------------
// Custom error types
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  /** HTTP status code (0 when the request never reached the server). */
  status: number;
  /** Parsed body when available. */
  body: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export class ApiTimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiTimeoutError";
  }
}

export class ApiNetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiNetworkError";
  }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Fetch with an AbortController-based timeout.
 */
async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(input, { ...init, signal: controller.signal });
    return response;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiTimeoutError(
        `Request timed out after ${Math.round(timeoutMs / 1000)}s`,
      );
    }
    // TypeError is what fetch throws when the network is unreachable
    if (err instanceof TypeError) {
      throw new ApiNetworkError(
        "Could not reach the backend. Please check your connection and try again.",
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Parse the response body. Returns `null` when the body is empty or
 * malformed instead of throwing, so callers can handle it gracefully.
 */
async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    // Malformed JSON — return raw text wrapped in an object so callers
    // can still inspect it without crashing.
    return { _raw: text };
  }
}

/**
 * Low-level request helper that wraps fetchWithTimeout, handles non-2xx
 * responses (including 429 rate-limit detection), and parses JSON.
 */
async function request<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchInit } = options;
  const url = `${API_BASE_URL}${path}`;

  let res: Response;
  try {
    res = await fetchWithTimeout(url, fetchInit, timeoutMs);
  } catch (err) {
    // Re-throw our custom errors as-is
    if (
      err instanceof ApiTimeoutError ||
      err instanceof ApiNetworkError
    ) {
      throw err;
    }
    throw new ApiNetworkError(
      "Could not reach the backend. Please check your connection and try again.",
    );
  }

  // Handle non-OK responses
  if (!res.ok) {
    const body = await parseBody(res);

    // Rate-limit (429)
    if (res.status === 429) {
      throw new ApiError(
        "Rate limited by the server. Please wait a moment before trying again.",
        429,
        body,
      );
    }

    // Try to extract a human-readable message from common error shapes
    const detail =
      (body as Record<string, unknown>)?.detail ??
      (body as Record<string, unknown>)?.message ??
      (body as Record<string, unknown>)?.error;

    const message =
      typeof detail === "string"
        ? detail
        : `Server returned ${res.status}: ${res.statusText}`;

    throw new ApiError(message, res.status, body);
  }

  const body = await parseBody(res);

  // Validate that the body is an object/array (malformed response guard)
  if (body !== null && typeof body !== "object") {
    throw new ApiError("Received unexpected response format from server.", 500, body);
  }

  return body as T;
}

// ---------------------------------------------------------------------------
// Typed API functions
// ---------------------------------------------------------------------------

export interface ResearchRequest {
  query: string;
  type: string;
  depth?: string;
}

export interface ResearchResponse {
  job_id: string;
  status: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  report?: string;
  report_markdown?: string;
  raw_data?: Record<string, unknown>;
  research_type?: string;
  error?: string;
  message?: string;
}

export interface HistoryItem {
  job_id: string;
  query: string;
  research_type: string;
  status: string;
  created_at: string;
}

export interface ReportResponse {
  job_id: string;
  query: string;
  research_type: string;
  status: string;
  report_markdown?: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Health-check the backend. */
export async function checkHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/v1/health");
}

/** Submit a new research job. */
export async function startResearch(
  payload: ResearchRequest,
): Promise<ResearchResponse> {
  return request<ResearchResponse>("/api/v1/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Poll the status of a running research job. */
export async function getJobStatus(
  jobId: string,
): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(
    `/api/v1/research/status/${encodeURIComponent(jobId)}`,
    { timeoutMs: POLL_TIMEOUT_MS },
  );
}

/** Fetch the last 20 research jobs. */
export async function getHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/api/v1/history");
}

/** Fetch the full report for a single job. */
export async function getReport(jobId: string): Promise<ReportResponse> {
  return request<ReportResponse>(
    `/api/v1/research/report/${encodeURIComponent(jobId)}`,
  );
}

/** Delete a research job. */
export async function deleteJob(
  jobId: string,
): Promise<{ deleted: boolean; job_id: string }> {
  return request<{ deleted: boolean; job_id: string }>(
    `/api/v1/research/${encodeURIComponent(jobId)}`,
    { method: "DELETE" },
  );
}
