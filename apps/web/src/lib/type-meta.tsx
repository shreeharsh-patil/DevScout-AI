"use client";

import React from "react";
import {
  GitBranch,
  Globe,
  Mail,
  PlayCircle,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Package,
  FileText,
} from "lucide-react";
import type { TypeMeta, StatusMeta } from "@/types/research";

// LinkedIn icon (not in this lucide-react version)
function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

export const TYPE_META: Record<string, TypeMeta> = {
  developer: {
    label: "Developer Intel",
    icon: <GitBranch className="w-3 h-3" />,
    color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
    bg: "bg-emerald-500/10",
  },
  startup: {
    label: "Startup Research",
    icon: <Globe className="w-3 h-3" />,
    color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
    bg: "bg-indigo-500/10",
  },
  email: {
    label: "Email OSINT",
    icon: <Mail className="w-3 h-3" />,
    color: "text-orange-400 border-orange-500/30 bg-orange-500/5",
    bg: "bg-orange-500/10",
  },
  youtube: {
    label: "YouTube Analysis",
    icon: <PlayCircle className="w-3 h-3" />,
    color: "text-red-400 border-red-500/30 bg-red-500/5",
    bg: "bg-red-500/10",
  },
  reddit: {
    label: "Reddit Insights",
    icon: <MessageSquare className="w-3 h-3" />,
    color: "text-orange-500 border-orange-500/30 bg-orange-500/5",
    bg: "bg-orange-500/10",
  },
  idea: {
    label: "Idea Validator",
    icon: <ShieldCheck className="w-3 h-3" />,
    color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
    bg: "bg-cyan-500/10",
  },
  social: {
    label: "Social Tracker",
    icon: <TrendingUp className="w-3 h-3" />,
    color: "text-blue-400 border-blue-500/30 bg-blue-500/5",
    bg: "bg-blue-500/10",
  },
  linkedin: {
    label: "LinkedIn Intel",
    icon: <LinkedinIcon className="w-3 h-3" />,
    color: "text-sky-400 border-sky-500/30 bg-sky-500/5",
    bg: "bg-sky-500/10",
  },
  npm: {
    label: "npm Analyzer",
    icon: <Package className="w-3 h-3" />,
    color: "text-rose-400 border-rose-500/30 bg-rose-500/5",
    bg: "bg-rose-500/10",
  },
  repository: {
    label: "Repository Intelligence",
    icon: <GitBranch className="w-3 h-3" />,
    color: "text-violet-400 border-violet-500/30 bg-violet-500/5",
    bg: "bg-violet-500/10",
  },
};

export const STATUS_META: Record<string, StatusMeta> = {
  completed: {
    label: "Completed",
    icon: (
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
    color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
  },
  failed: {
    label: "Failed",
    icon: (
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
    color: "text-red-400 border-red-500/30 bg-red-500/5",
  },
  pending: {
    label: "Pending",
    icon: (
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    color: "text-amber-400 border-amber-500/30 bg-amber-500/5",
  },
  running: {
    label: "Running",
    icon: (
      <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
      </svg>
    ),
    color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
  },
};

/** Get a fallback TypeMeta for unknown research types. */
export function getTypeMetaFallback(type: string): TypeMeta {
  return {
    label: type,
    icon: <FileText className="w-3 h-3" />,
    color: "text-neutral-400 border-neutral-700 bg-neutral-800/30",
    bg: "bg-neutral-800/30",
  };
}

/** Get a fallback StatusMeta for unknown statuses. */
export function getStatusMetaFallback(status: string): StatusMeta {
  return {
    label: status,
    icon: (
      <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    color: "text-neutral-400 border-neutral-700 bg-neutral-800/30",
  };
}

/** All research type values for select dropdowns. */
export const ALL_RESEARCH_TYPES = [
  { value: "auto", label: "⚡ Auto-Detect" },
  { value: "developer", label: "Developer Intel" },
  { value: "github-repo", label: "Repo Analyzer" },
  { value: "startup", label: "Startup Research" },
  { value: "email", label: "Identity Intel (Email)" },
  { value: "youtube", label: "YouTube Analysis" },
  { value: "reddit", label: "Reddit Insights" },
  { value: "hackernews", label: "HackerNews Intel" },
  { value: "idea", label: "Idea Validator" },
  { value: "social", label: "Social Tracker" },
  { value: "linkedin", label: "LinkedIn Intel" },
  { value: "npm", label: "npm Analyzer" },
  { value: "repository", label: "Repository Intelligence" },
] as const;
