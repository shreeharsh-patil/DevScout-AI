import type { ReactNode } from "react";

// ─── Research types (single source of truth) ─────────────────────────────────
export type ResearchType =
  | "developer"
  | "startup"
  | "email"
  | "youtube"
  | "reddit"
  | "idea"
  | "social"
  | "linkedin"
  | "npm"
  | "hackernews"
  | "github-repo";

export type ResearchStatus = "idle" | "loading" | "success" | "error" | "rate_limited";

// ─── Detection result ────────────────────────────────────────────────────────
export interface DetectionResult {
  type: ResearchType;
  label: string;
  confidence: string;
  icon: ReactNode;
  color: string;
}

// ─── API response shapes ─────────────────────────────────────────────────────
export interface ResearchJob {
  job_id: string;
  status: string;
}

export interface ResearchReport {
  job_id: string;
  status: string;
  research_type?: string;
  report?: string;
  raw_data?: {
    analysis?: Record<string, unknown>;
    researcher?: Record<string, unknown>;
  };
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

export interface FullReport {
  job_id: string;
  query: string;
  research_type: string;
  status: string;
  report?: string;
  report_markdown?: string;
  error?: string;
  created_at: string;
}

// ─── Metadata maps ───────────────────────────────────────────────────────────
export interface TypeMeta {
  label: string;
  icon: ReactNode;
  color: string;
  bg: string;
}

export interface StatusMeta {
  label: string;
  icon: ReactNode;
  color: string;
}
