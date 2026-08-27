import type { ReactNode } from "react";

// ─── Research types (single source of truth) ─────────────────────────────────
export type ResearchType =
  | "developer"
  | "startup"
  | "email"
  | "email_intelligence"
  | "youtube"
  | "reddit"
  | "idea"
  | "social"
  | "linkedin"
  | "npm"
  | "hackernews"
  | "github-repo"
  | "repository";


export type ResearchStatus = "idle" | "loading" | "success" | "error" | "rate_limited";

// ─── Detection result ────────────────────────────────────────────────────────
export interface DetectionResult {
  type: ResearchType;
  label: string;
  confidence: string;
  icon: ReactNode;
  color: string;
}

// ─── Source / Evidence Verification ──────────────────────────────────────────
export interface ResearchSource {
  source_id: string;
  title: string;
  url: string;
  platform: string;
  retrieved_at: string;
  source_type: string;
  snippet?: string;
  metadata?: Record<string, unknown>;
}

// ─── API response shapes ─────────────────────────────────────────────────────
export interface ResearchJob {
  job_id: string;
  status: string;
}

export interface ResearchReport {
  job_id: string;
  status: string;
  query?: string;
  stage?: string;
  custom_title?: string;

  is_saved?: boolean;
  tags?: string[];
  research_type?: string;
  report?: string;
  report_markdown?: string;
  sources?: ResearchSource[];
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
  stage?: string;
  report?: string;
  report_markdown?: string;
  sources?: ResearchSource[];
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
