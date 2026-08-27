import type { ResearchType } from "@/types/research";

// ─── Detection result without JSX ────────────────────────────────────────────
// Components can map type → icon themselves. This keeps the detector pure.
export interface DetectionMeta {
  type: ResearchType;
  label: string;
  confidence: string;
  color: string;
}

const LINKEDIN_COLOR = "text-sky-400 border-sky-500/30 bg-sky-500/5";
const NPM_COLOR = "text-rose-400 border-rose-500/30 bg-rose-500/5";
const REPO_COLOR = "text-violet-400 border-violet-500/30 bg-violet-500/5";
const DEVELOPER_COLOR = "text-emerald-400 border-emerald-500/30 bg-emerald-500/5";
const YOUTUBE_COLOR = "text-red-400 border-red-500/30 bg-red-500/5";
const EMAIL_COLOR = "text-orange-400 border-orange-500/30 bg-orange-500/5";
const REDDIT_COLOR = "text-orange-500 border-orange-500/30 bg-orange-500/5";
const STARTUP_COLOR = "text-indigo-400 border-indigo-500/30 bg-indigo-500/5";
const HACKERNEWS_COLOR = "text-amber-400 border-amber-500/30 bg-amber-500/5";
const SOCIAL_COLOR = "text-blue-400 border-blue-500/30 bg-blue-500/5";
const IDEA_COLOR = "text-cyan-400 border-cyan-500/30 bg-cyan-500/5";

/**
 * Detect the research type from a raw query string.
 * Returns null when the query is empty.
 */
export function detectQueryType(raw: string): DetectionMeta | null {
  const q = raw.trim().toLowerCase();
  if (!q) return null;

  // LinkedIn profile URL
  if (/linkedin\.com\/in\//i.test(q)) {
    return {
      type: "linkedin",
      label: "LinkedIn Intel",
      confidence: "LinkedIn Profile Detected",
      color: LINKEDIN_COLOR,
    };
  }

  // npm package URL
  if (/npmjs\.com\/package\//i.test(q)) {
    return {
      type: "npm",
      label: "npm Analyzer",
      confidence: "npm Package URL Detected",
      color: NPM_COLOR,
    };
  }

  // GitHub repo: owner/repo pattern or full github.com URL with a slash
  if (
    /github\.com\/[a-z0-9_-]+\/[a-z0-9_.-]+/i.test(q) ||
    /^[a-z0-9_-]+\/[a-z0-9_.-]{1,100}$/.test(q)
  ) {
    return {
      type: "github-repo",
      label: "Repo Analyzer",
      confidence: "GitHub Repository Detected",
      color: REPO_COLOR,
    };
  }

  // GitHub profile URL or @handle (comes AFTER repo check)
  if (
    /github\.com\/[a-z0-9_-]+\/?$/i.test(q) ||
    (/^@?[a-z0-9_-]{1,39}$/.test(q) && !q.includes("."))
  ) {
    return {
      type: "developer",
      label: "Developer Intel",
      confidence: "GitHub Profile Detected",
      color: DEVELOPER_COLOR,
    };
  }

  // npm package name heuristic
  if (
    /^[a-z0-9@][a-z0-9_-]{0,213}$/.test(q) &&
    !q.includes(".") &&
    !q.includes("/") &&
    q.length >= 2 &&
    q.length <= 214
  ) {
    if (
      /^(@[a-z0-9_-]+\/)?[a-z0-9][a-z0-9_-]*$/.test(q) &&
      !q.includes(" ") &&
      q.split("-").length > 1
    ) {
      return {
        type: "npm",
        label: "npm Analyzer",
        confidence: "npm Package Name Detected",
        color: NPM_COLOR,
      };
    }
  }

  // YouTube URL
  if (/youtube\.com\/watch|youtu\.be\//i.test(q)) {
    return {
      type: "youtube",
      label: "YouTube Analysis",
      confidence: "YouTube URL Detected",
      color: YOUTUBE_COLOR,
    };
  }

  // Email address
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(q)) {
    return {
      type: "email",
      label: "Identity Intelligence",
      confidence: "Email Address Detected",
      color: EMAIL_COLOR,
    };
  }

  // Reddit URL or "reddit" keyword
  if (/reddit\.com/i.test(q) || q.startsWith("reddit:")) {
    return {
      type: "reddit",
      label: "Reddit Insights",
      confidence: "Reddit Source Detected",
      color: REDDIT_COLOR,
    };
  }

  // Any other website URL → startup research
  if (
    /^https?:\/\//i.test(q) ||
    /^www\./i.test(q) ||
    /\.(com|io|co|ai|dev|app|net|org)(\/|$)/i.test(q)
  ) {
    return {
      type: "startup",
      label: "Startup Research",
      confidence: "Company URL Detected",
      color: STARTUP_COLOR,
    };
  }

  // HackerNews keyword
  if (/\bhacker\s?news\b|\bhn\b|show hn|ask hn/i.test(q)) {
    return {
      type: "hackernews",
      label: "HackerNews Intel",
      confidence: "HackerNews Query Detected",
      color: HACKERNEWS_COLOR,
    };
  }

  // Multi-word comparison phrases → social tracker
  if (/\bvs\b|\bcompare\b|\btrack\b|\bsentiment\b|\btrend/i.test(q)) {
    return {
      type: "social",
      label: "Social Tracker",
      confidence: "Comparison Query Detected",
      color: SOCIAL_COLOR,
    };
  }

  // Default: idea validator
  return {
    type: "idea",
    label: "Idea Validator",
    confidence: "Keyword / Concept Detected",
    color: IDEA_COLOR,
  };
}
