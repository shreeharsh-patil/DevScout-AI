/**
 * Centralized API client for DevScout AI SaaS.
 *
 * All backend requests go through this module so the base URL and Auth headers
 * are configured consistently across all pages and components.
 */

import type { ResearchSource } from "@/types/research";

const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 30_000;
const POLL_TIMEOUT_MS = 10_000;

// Token storage key
const TOKEN_STORAGE_KEY = "devscout_auth_token";
const WORKSPACE_STORAGE_KEY = "devscout_active_workspace";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getStoredWorkspace(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(WORKSPACE_STORAGE_KEY);
}

export function setStoredWorkspace(wsId: string | null): void {
  if (typeof window === "undefined") return;
  if (wsId) {
    localStorage.setItem(WORKSPACE_STORAGE_KEY, wsId);
  } else {
    localStorage.removeItem(WORKSPACE_STORAGE_KEY);
  }
}

// ---------------------------------------------------------------------------
// Custom error types
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  status: number;
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
// Internal request helper with Auth & Workspace headers
// ---------------------------------------------------------------------------

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

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { _raw: text };
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers: customHeaders, ...fetchInit } = options;
  const url = `${API_BASE_URL}${path}`;

  // Attach token and active workspace headers if present
  const headers = new Headers(customHeaders || {});
  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const activeWorkspace = getStoredWorkspace();
  if (activeWorkspace && !headers.has("X-Workspace-Id")) {
    headers.set("X-Workspace-Id", activeWorkspace);
  }

  let res: Response;
  try {
    res = await fetchWithTimeout(url, { ...fetchInit, headers }, timeoutMs);
  } catch (err) {
    if (err instanceof ApiTimeoutError || err instanceof ApiNetworkError) {
      throw err;
    }
    throw new ApiNetworkError(
      "Could not reach the backend. Please check your connection and try again.",
    );
  }

  if (!res.ok) {
    const body = await parseBody(res);

    if (res.status === 429) {
      throw new ApiError(
        "Rate limited by the server. Please wait a moment before trying again.",
        429,
        body,
      );
    }

    if (res.status === 402) {
      throw new ApiError(
        "Monthly workspace credit limit exceeded. Upgrade to continue.",
        402,
        body,
      );
    }

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
  if (body !== null && typeof body !== "object") {
    throw new ApiError("Received unexpected response format from server.", 500, body);
  }

  return body as T;
}

// ---------------------------------------------------------------------------
// TypeScript Interfaces
// ---------------------------------------------------------------------------

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: string;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  monthly_credit_limit: number;
  credits_used: number;
  credits_remaining?: number;
  is_active?: boolean;
  is_owner?: boolean;
}

export interface AuthMeResponse {
  user: UserProfile;
  workspace: WorkspaceInfo;
  workspaces: WorkspaceInfo[];
  stats: {
    total_research_jobs: number;
    saved_reports: number;
    credits_used: number;
    credit_limit: number;
  };
}

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
  user_id?: string;
  workspace_id?: string;
  status: string;
  stage?: string;
  custom_title?: string;
  is_saved?: boolean;
  tags?: string[];
  report?: string;
  report_markdown?: string;
  raw_data?: Record<string, unknown>;
  sources?: ResearchSource[];
  research_type?: string;
  error?: string;
  message?: string;
  created_at?: string;
  updated_at?: string;
}

export interface HistoryItem {
  job_id: string;
  query: string;
  custom_title?: string;
  research_type: string;
  is_saved?: boolean;
  status: string;
  stage?: string;
  created_at: string;
  updated_at?: string;
}

export interface ReportResponse {
  job_id: string;
  query: string;
  custom_title?: string;
  is_saved?: boolean;
  research_type: string;
  status: string;
  stage?: string;
  report_markdown?: string;
  sources?: ResearchSource[];
  created_at: string;
}

export interface UsageLogItem {
  id: string;
  action: string;
  job_id?: string;
  credits_deducted: number;
  created_at: string;
}

export interface WorkspaceUsageResponse {
  workspace_id: string;
  plan_tier: string;
  monthly_credit_limit: number;
  credits_used: number;
  credits_remaining: number;
  usage_logs: UsageLogItem[];
}

// ---------------------------------------------------------------------------
// Public SaaS API Methods
// ---------------------------------------------------------------------------

/** Health check */
export async function checkHealth(): Promise<{ status: string }> {
  return request<{ status: string }>("/api/v1/health");
}

/** Get authenticated user profile, workspace, and usage */
export async function getMe(): Promise<AuthMeResponse> {
  return request<AuthMeResponse>("/api/v1/auth/me");
}

/** Generate a JWT token / Login */
export async function loginWithEmail(
  email: string,
  name?: string,
  workspaceName?: string
): Promise<{ access_token: string; user_id: string; workspace_id: string }> {
  const data = await request<{ access_token: string; user_id: string; workspace_id: string }>(
    "/api/v1/auth/token",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name, workspace_name: workspaceName }),
    }
  );
  setStoredToken(data.access_token);
  if (data.workspace_id) {
    setStoredWorkspace(data.workspace_id);
  }
  return data;
}

/** List all accessible workspaces */
export async function listWorkspaces(): Promise<WorkspaceInfo[]> {
  return request<WorkspaceInfo[]>("/api/v1/workspaces");
}

/** Create a new workspace */
export async function createWorkspace(
  name: string,
  slug?: string
): Promise<WorkspaceInfo> {
  return request<WorkspaceInfo>("/api/v1/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, slug }),
  });
}

/** Get workspace credit usage and logs */
export async function getWorkspaceUsage(
  workspaceId: string
): Promise<WorkspaceUsageResponse> {
  return request<WorkspaceUsageResponse>(
    `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/usage`
  );
}

/** Submit a new research job */
export async function startResearch(
  payload: ResearchRequest,
): Promise<ResearchResponse> {
  return request<ResearchResponse>("/api/v1/research", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** Poll status of a research job */
export async function getJobStatus(
  jobId: string,
): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(
    `/api/v1/research/status/${encodeURIComponent(jobId)}`,
    { timeoutMs: POLL_TIMEOUT_MS },
  );
}

/** Fetch workspace history */
export async function getHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/api/v1/history");
}

/** Fetch bookmarked/saved reports */
export async function getSavedReports(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/api/v1/reports/saved");
}

/** Fetch full report */
export async function getReport(jobId: string): Promise<ReportResponse> {
  return request<ReportResponse>(
    `/api/v1/research/report/${encodeURIComponent(jobId)}`,
  );
}

/** Update report (rename, save bookmark, tags) */
export async function updateReport(
  jobId: string,
  updates: { custom_title?: string; is_saved?: boolean; tags?: string[] }
): Promise<{ job_id: string; custom_title?: string; is_saved?: boolean }> {
  return request<{ job_id: string; custom_title?: string; is_saved?: boolean }>(
    `/api/v1/reports/${encodeURIComponent(jobId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    }
  );
}

/** Delete a research job */
export async function deleteJob(
  jobId: string,
): Promise<{ message: string; job_id: string }> {
  return request<{ message: string; job_id: string }>(
    `/api/v1/reports/${encodeURIComponent(jobId)}`,
    { method: "DELETE" },
  );
}
