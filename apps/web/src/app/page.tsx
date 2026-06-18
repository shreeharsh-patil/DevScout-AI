"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Cpu,
  Globe,
  GitBranch,
  X,
  PlayCircle,
  MessageSquare,
  Mail,
  ShieldCheck,
  Zap,
  ArrowRight,
  TrendingUp,
  LayoutDashboard,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  ChevronDown,
  Download,
  Package,
  Clock,
  History,
} from "lucide-react";

// LinkedIn icon (not in this lucide-react version)
function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

// ─── Types ────────────────────────────────────────────────────────────────────
type ResearchType =
  | "developer"
  | "startup"
  | "email"
  | "youtube"
  | "reddit"
  | "idea"
  | "social"
  | "linkedin"
  | "npm";

interface DetectionResult {
  type: ResearchType;
  label: string;
  confidence: string;
  icon: React.ReactNode;
  color: string;
}

// ─── Smart type detection ─────────────────────────────────────────────────────
function detectQueryType(raw: string): DetectionResult {
  const q = raw.trim().toLowerCase();

  // LinkedIn profile URL
  if (/linkedin\.com\/in\//i.test(q)) {
    return {
      type: "linkedin",
      label: "LinkedIn Intel",
      confidence: "LinkedIn Profile Detected",
      icon: <LinkedinIcon className="w-4 h-4" />,
      color: "text-sky-400 border-sky-500/30 bg-sky-500/5",
    };
  }

  // npm package URL
  if (/npmjs\.com\/package\//i.test(q)) {
    return {
      type: "npm",
      label: "npm Analyzer",
      confidence: "npm Package URL Detected",
      icon: <Package className="w-4 h-4" />,
      color: "text-rose-400 border-rose-500/30 bg-rose-500/5",
    };
  }

  // GitHub profile URL or @handle
  if (
    /github\.com\/[a-z0-9_-]+\/?$/i.test(q) ||
    (/^@?[a-z0-9_-]{1,39}$/.test(q) && !q.includes("."))
  ) {
    return {
      type: "developer",
      label: "Developer Intel",
      confidence: "GitHub Profile Detected",
      icon: <GitBranch className="w-4 h-4" />,
      color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
    };
  }

  // npm package name: no spaces, no dots, no slashes, reasonable length
  if (/^[a-z0-9@][a-z0-9_-]{0,213}$/.test(q) && !q.includes(".") && !q.includes("/") && q.length >= 2 && q.length <= 214) {
    // Only trigger npm if it looks like a package name (not a single word idea)
    // Heuristic: if it's a known npm-style name pattern (lowercase, hyphens, @scope)
    if (/^(@[a-z0-9_-]+\/)?[a-z0-9][a-z0-9_-]*$/.test(q) && !q.includes(" ") && q.split("-").length > 1) {
      return {
        type: "npm",
        label: "npm Analyzer",
        confidence: "npm Package Name Detected",
        icon: <Package className="w-4 h-4" />,
        color: "text-rose-400 border-rose-500/30 bg-rose-500/5",
      };
    }
  }

  // YouTube URL
  if (/youtube\.com\/watch|youtu\.be\//i.test(q)) {
    return {
      type: "youtube",
      label: "YouTube Analysis",
      confidence: "YouTube URL Detected",
      icon: <PlayCircle className="w-4 h-4" />,
      color: "text-red-400 border-red-500/30 bg-red-500/5",
    };
  }

  // Email address
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(q)) {
    return {
      type: "email",
      label: "Email OSINT",
      confidence: "Email Address Detected",
      icon: <Mail className="w-4 h-4" />,
      color: "text-orange-400 border-orange-500/30 bg-orange-500/5",
    };
  }

  // Reddit URL or "reddit" keyword
  if (/reddit\.com/i.test(q) || q.startsWith("reddit:")) {
    return {
      type: "reddit",
      label: "Reddit Insights",
      confidence: "Reddit Source Detected",
      icon: <MessageSquare className="w-4 h-4" />,
      color: "text-orange-500 border-orange-500/30 bg-orange-500/5",
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
      icon: <Globe className="w-4 h-4" />,
      color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
    };
  }

  // Multi-word phrase with "vs", "compare", "track" → social tracker
  if (/\bvs\b|\bcompare\b|\btrack\b|\bsentiment\b|\btrend/i.test(q)) {
    return {
      type: "social",
      label: "Social Tracker",
      confidence: "Comparison Query Detected",
      icon: <TrendingUp className="w-4 h-4" />,
      color: "text-blue-400 border-blue-500/30 bg-blue-500/5",
    };
  }

  // Default: idea validator for free-form queries
  return {
    type: "idea",
    label: "Idea Validator",
    confidence: "Keyword / Concept Detected",
    icon: <ShieldCheck className="w-4 h-4" />,
    color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
  };
}

// ─── Placeholder cycling hook ─────────────────────────────────────────────────
const PLACEHOLDERS = [
  "github.com/torvalds",
  "stripe.com",
  "someone@gmail.com",
  "youtu.be/dQw4w9WgXcQ",
  "AI meeting notes app",
  "react vs vue",
  "linkedin.com/in/satyanadella",
  "lodash-es",
];

function useCyclingPlaceholder(active: boolean) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setIdx((i) => (i + 1) % PLACEHOLDERS.length), 3000);
    return () => clearInterval(id);
  }, [active]);
  return PLACEHOLDERS[idx];
}

// ─── Score Ring Component ─────────────────────────────────────────────────────
function ScoreRing({ score, label }: { score: number; label: string }) {
  const [animated, setAnimated] = useState(0);
  const r = 54;
  const circ = 2 * Math.PI * r;

  useEffect(() => {
    // Animate from 0 to score
    let start: number | null = null;
    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / 1200, 1);
      setAnimated(Math.round(progress * score));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [score]);

  const color =
    score <= 40
      ? "#ef4444"
      : score <= 70
      ? "#f59e0b"
      : "#10b981";

  const dashOffset = circ - (animated / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-3 py-6">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#1f2937" strokeWidth="12" />
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circ}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.05s linear" }}
        />
      </svg>
      <div className="flex flex-col items-center -mt-[120px] mb-[80px] pointer-events-none select-none">
        <span className="text-4xl font-extrabold text-white">{animated}</span>
        <span className="text-xs text-neutral-500 font-mono">/100</span>
        <span className="text-[10px] uppercase tracking-widest text-neutral-600 mt-1">{label}</span>
      </div>
    </div>
  );
}

// ─── Parse score from markdown ────────────────────────────────────────────────
function parseScore(markdown: string): number | null {
  const match = markdown.match(/##\s+(?:Developer|Idea Viability)\s+Score:\s*(\d+)\s*\/\s*100/i);
  if (match) return parseInt(match[1], 10);
  // fallback: look for "Score: 85/100" anywhere
  const loose = markdown.match(/Score:\s*(\d+)\s*\/\s*100/i);
  if (loose) return parseInt(loose[1], 10);
  return null;
}

// ─── Parse SWOT from markdown ─────────────────────────────────────────────────
function parseSwot(markdown: string) {
  const extract = (keyword: string): string[] => {
    const regex = new RegExp(
      `\\*\\*${keyword}:?\\*\\*([\\s\\S]*?)(?=\\*\\*(?:Strengths|Weaknesses|Opportunities|Threats):?\\*\\*|$)`,
      "i"
    );
    const match = markdown.match(regex);
    if (!match) return [];
    return match[1]
      .split("\n")
      .map((l) => l.replace(/^[-*•]\s*/, "").trim())
      .filter((l) => l.length > 0);
  };
  return {
    strengths: extract("Strengths"),
    weaknesses: extract("Weaknesses"),
    opportunities: extract("Opportunities"),
    threats: extract("Threats"),
  };
}

// ─── SWOT 2×2 Grid ────────────────────────────────────────────────────────────
function SwotGrid({ markdown }: { markdown: string }) {
  const { strengths, weaknesses, opportunities, threats } = parseSwot(markdown);
  if (!strengths.length && !weaknesses.length && !opportunities.length && !threats.length) {
    return null;
  }

  const quadrant = (
    title: string,
    items: string[],
    bg: string,
    textColor: string,
    borderColor: string
  ) => (
    <div className={`rounded-xl p-4 border ${bg} ${borderColor}`}>
      <p className={`text-xs font-bold uppercase tracking-widest mb-3 ${textColor}`}>{title}</p>
      <ul className="space-y-1">
        {items.slice(0, 6).map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-neutral-300">
            <span className={`mt-0.5 shrink-0 ${textColor}`}>•</span>
            <span>{item}</span>
          </li>
        ))}
        {items.length === 0 && <li className="text-xs text-neutral-600 italic">None detected</li>}
      </ul>
    </div>
  );

  return (
    <div className="mb-8">
      <p className="text-xs uppercase tracking-widest text-neutral-500 mb-4">SWOT Analysis</p>
      <div className="grid grid-cols-2 gap-3">
        {quadrant("Strengths", strengths, "bg-emerald-950/40", "text-emerald-400", "border-emerald-800/40")}
        {quadrant("Weaknesses", weaknesses, "bg-red-950/40", "text-red-400", "border-red-800/40")}
        {quadrant("Opportunities", opportunities, "bg-blue-950/40", "text-blue-400", "border-blue-800/40")}
        {quadrant("Threats", threats, "bg-amber-950/40", "text-amber-400", "border-amber-800/40")}
      </div>
    </div>
  );
}

// ─── Markdown renderer with styled components ─────────────────────────────────
function MarkdownReport({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-semibold text-indigo-400 mt-8 mb-4">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-medium text-emerald-400 mt-6 mb-2">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-base font-medium text-neutral-300 mt-4 mb-2">{children}</h4>
        ),
        p: ({ children }) => (
          <p className="text-neutral-300 mb-3 leading-relaxed">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-4 space-y-1 ml-2">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-4 space-y-1 ml-4 list-decimal">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="flex gap-2 text-neutral-300">
            <span className="text-indigo-400 shrink-0 mt-0.5">•</span>
            <span>{children}</span>
          </li>
        ),
        strong: ({ children }) => (
          <strong className="text-white font-semibold">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="text-neutral-400 italic">{children}</em>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-400 hover:underline"
          >
            {children}
          </a>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-indigo-500 pl-4 my-4 text-neutral-400 italic">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto my-6">
            <table className="w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-neutral-900 text-neutral-400 text-xs uppercase">{children}</thead>
        ),
        tbody: ({ children }) => <tbody className="divide-y divide-neutral-800">{children}</tbody>,
        tr: ({ children }) => <tr className="hover:bg-neutral-900/50">{children}</tr>,
        th: ({ children }) => (
          <th className="px-4 py-2 text-left font-medium text-neutral-400">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-4 py-3 text-neutral-300">{children}</td>
        ),
        code: ({ className, children, ...props }) => {
          const isBlock = className?.includes("language-");
          return isBlock ? (
            <code
              className="block bg-neutral-900 border border-neutral-800 rounded-lg p-4 text-sm font-mono text-emerald-300 overflow-x-auto my-4"
              {...props}
            >
              {children}
            </code>
          ) : (
            <code
              className="bg-neutral-900 text-emerald-300 px-1.5 py-0.5 rounded text-xs font-mono"
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="not-prose">{children}</pre>,
        hr: () => <hr className="border-neutral-800 my-6" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

// ─── Download helper ──────────────────────────────────────────────────────────
function downloadMarkdown(content: string, type: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `devscout-report-${type}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Rate limit countdown ─────────────────────────────────────────────────────
function RateLimitAlert({ onRetry }: { onRetry: () => void }) {
  const [seconds, setSeconds] = useState(60);
  useEffect(() => {
    if (seconds <= 0) return;
    const id = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(id);
  }, [seconds]);
  return (
    <Alert className="bg-amber-950/30 border-amber-700 text-amber-400 py-6 flex flex-col items-center gap-3">
      <Clock className="w-10 h-10" />
      <div className="text-center">
        <AlertTitle className="text-base font-bold">⏳ Free Tier Rate Limit Hit</AlertTitle>
        <AlertDescription className="mt-2 text-amber-300/80">
          Wait about 60 seconds and try again.
          {seconds > 0 ? (
            <span className="block mt-2 font-mono text-2xl font-bold text-amber-400">
              {seconds}s
            </span>
          ) : (
            <Button
              onClick={onRetry}
              size="sm"
              className="mt-3 bg-amber-600 hover:bg-amber-700 text-black font-bold"
            >
              Try Again
            </Button>
          )}
        </AlertDescription>
      </div>
    </Alert>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function OnePageApp() {
  const [query, setQuery] = useState("");
  const [manualType, setManualType] = useState<ResearchType | "auto">("auto");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error" | "rate_limited">(
    "idle"
  );
  const [report, setReport] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [scrolled, setScrolled] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Animated placeholder — only cycle when query is empty
  const placeholder = useCyclingPlaceholder(query.trim() === "");

  // Live detection as user types
  const detection = query.trim() ? detectQueryType(query) : null;
  const activeType: ResearchType =
    (manualType !== "auto" ? manualType : detection?.type) ?? "idea";

  const startResearch = useCallback(async () => {
    if (!query.trim()) return;

    // Clear any existing poll
    if (pollRef.current) clearInterval(pollRef.current);

    const dashboard = document.getElementById("dashboard");
    dashboard?.scrollIntoView({ behavior: "smooth" });

    setStatus("loading");
    setReport(null);
    setErrorMessage("");

    try {
      const res = await fetch("http://localhost:8000/api/v1/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), type: activeType, depth: "standard" }),
      });
      const data = await res.json();

      let pollCount = 0;
      const MAX_POLLS = 30; // 30 × 2s = 60s timeout

      pollRef.current = setInterval(async () => {
        pollCount++;

        if (pollCount >= MAX_POLLS) {
          clearInterval(pollRef.current!);
          setStatus("error");
          setErrorMessage("Request timed out after 60 seconds. Please try again.");
          return;
        }

        try {
          const statusRes = await fetch(
            `http://localhost:8000/api/v1/research/status/${data.job_id}`
          );
          const statusData = await statusRes.json();

          if (statusData.status === "rate_limited") {
            clearInterval(pollRef.current!);
            setStatus("rate_limited");
            return;
          }

          if (statusData.status === "completed" || statusData.status === "failed") {
            clearInterval(pollRef.current!);
            if (statusData.status === "completed") {
              setStatus("success");
              setReport(statusData);
            } else {
              setStatus("error");
              setErrorMessage(
                statusData.error || statusData.message || "The agents encountered an error."
              );
              setReport(statusData);
            }
          }
        } catch (pollErr) {
          console.error("Poll error:", pollErr);
        }
      }, 2000);
    } catch (e) {
      console.error(e);
      setStatus("error");
      setErrorMessage("Network error — could not reach the backend.");
    }
  }, [query, activeType]);

  // Cleanup poll on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const features = [
    {
      icon: <GitBranch className="w-5 h-5 text-emerald-400" />,
      title: "Developer Intel",
      desc: "Paste a GitHub URL or handle. Get tech stack, impact score & AI insights.",
      example: "github.com/torvalds",
    },
    {
      icon: <Globe className="w-5 h-5 text-indigo-400" />,
      title: "Startup Research",
      desc: "Paste any company URL. Get automated SWOT + competitor analysis.",
      example: "stripe.com",
    },
    {
      icon: <TrendingUp className="w-5 h-5 text-blue-400" />,
      title: "Social Tracker",
      desc: "Type a keyword or topic. Get cross-platform sentiment comparison.",
      example: "react vs vue",
    },
    {
      icon: <Mail className="w-5 h-5 text-orange-400" />,
      title: "Email OSINT",
      desc: "Paste an email. Find public developer footprints automatically.",
      example: "someone@gmail.com",
    },
    {
      icon: <PlayCircle className="w-5 h-5 text-red-400" />,
      title: "YouTube Analysis",
      desc: "Paste a YouTube URL. Extract metadata, audience & deep insights.",
      example: "youtu.be/dQw4w9WgXcQ",
    },
    {
      icon: <ShieldCheck className="w-5 h-5 text-cyan-400" />,
      title: "Idea Validator",
      desc: "Type your SaaS idea. Validate it against live market data.",
      example: "AI meeting notes app",
    },
    {
      icon: <LinkedinIcon className="w-5 h-5 text-sky-400" />,
      title: "LinkedIn Intel",
      desc: "Paste a LinkedIn profile URL. Get professional background & insights.",
      example: "linkedin.com/in/satyanadella",
    },
    {
      icon: <Package className="w-5 h-5 text-rose-400" />,
      title: "npm Analyzer",
      desc: "Paste an npm package name or URL. Get downloads, maintainers & health.",
      example: "react-query",
    },
  ];

  // Score for developer / idea reports
  const score =
    report?.report && (activeType === "developer" || activeType === "idea")
      ? parseScore(report.report)
      : null;

  return (
    <div className="flex flex-col min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30">

      {/* Header */}
      <header
        className={`fixed top-0 w-full z-50 transition-all duration-300 ${
          scrolled
            ? "bg-black/80 backdrop-blur-md border-b border-neutral-800 py-3"
            : "bg-transparent py-6"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-emerald-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white fill-current" />
            </div>
            <h1 className="text-xl font-bold tracking-tighter">DevScout AI</h1>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <a
              href="#features"
              className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
            >
              Features
            </a>
            <a
              href="#dashboard"
              className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
            >
              Console
            </a>
            <Link
              href="/history"
              className="text-sm font-medium text-neutral-400 hover:text-white transition-colors flex items-center gap-1.5"
            >
              <History className="w-4 h-4" />
              History
            </Link>
            <Button
              variant="outline"
              className="border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-white"
            >
              Launch Console
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <Badge
              variant="outline"
              className="mb-4 border-indigo-500/30 text-indigo-400 bg-indigo-500/5 px-3 py-1"
            >
              <Sparkles className="w-3 h-3 mr-1" /> Smart Auto-Detection — Just Paste &amp; Go
            </Badge>
            <h2 className="text-5xl md:text-8xl font-extrabold tracking-tight mb-6 leading-[1.1]">
              The Internet&apos;s <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-white to-emerald-400">
                Intelligence Layer.
              </span>
            </h2>
            <p className="text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Paste anything — a GitHub handle, company URL, email, or idea.
              DevScout AI detects what it is and deploys the right agents instantly.
            </p>
          </motion.div>

          {/* Smart Search Bar */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="max-w-2xl mx-auto w-full"
          >
            <div className="p-2 bg-neutral-900/50 border border-neutral-800 rounded-2xl backdrop-blur-xl shadow-2xl">
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="flex-1 flex items-center px-4 gap-3 min-w-0">
                  <Search className="w-5 h-5 text-neutral-500 shrink-0" />
                  <input
                    type="text"
                    placeholder={placeholder}
                    className="w-full min-w-0 bg-transparent border-none outline-none text-white placeholder:text-neutral-600 py-3 transition-all"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setManualType("auto");
                    }}
                    onKeyDown={(e) => e.key === "Enter" && startResearch()}
                  />
                </div>
                <Button
                  onClick={startResearch}
                  disabled={!query.trim()}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-8 py-6 rounded-xl transition-all disabled:opacity-40 shrink-0"
                >
                  Scout Now <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>

            {/* Live detection pill */}
            <AnimatePresence>
              {detection && (
                <motion.div
                  key="detection"
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="mt-3 flex items-center justify-center gap-2"
                >
                  <Badge
                    variant="outline"
                    className={`gap-1.5 px-3 py-1 text-xs font-medium ${detection.color}`}
                  >
                    {detection.icon}
                    {detection.confidence} → Running <strong>{detection.label}</strong>
                  </Badge>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Example hints */}
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {["github.com/torvalds", "stripe.com", "user@example.com", "AI writing tool idea"].map(
                (ex) => (
                  <button
                    key={ex}
                    onClick={() => {
                      setQuery(ex);
                      setManualType("auto");
                    }}
                    className="text-xs text-neutral-600 hover:text-neutral-300 border border-neutral-800 hover:border-neutral-600 px-3 py-1 rounded-full transition-all"
                  >
                    {ex}
                  </button>
                )
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-y border-neutral-900 bg-neutral-950/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <p className="text-xs uppercase tracking-widest text-neutral-500 mb-3">
              What DevScout detects
            </p>
            <h2 className="text-3xl font-bold">One input. Every angle covered.</h2>
          </div>
          {/* Scrollable on very small screens, grid on larger */}
          <div className="overflow-x-auto sm:overflow-visible">
            <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-4 min-w-[640px] sm:min-w-0">
              {features.map((f, i) => (
                <motion.div
                  key={i}
                  whileHover={{ y: -5 }}
                  onClick={() => {
                    setQuery(f.example);
                    setManualType("auto");
                    document
                      .getElementById("dashboard")
                      ?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="p-5 bg-neutral-900/40 border border-neutral-800 rounded-2xl cursor-pointer hover:border-neutral-700 transition-all"
                >
                  <div className="w-9 h-9 bg-neutral-950 rounded-lg flex items-center justify-center mb-3 border border-neutral-800">
                    {f.icon}
                  </div>
                  <h3 className="text-sm font-bold mb-1">{f.title}</h3>
                  <p className="text-xs text-neutral-500 leading-relaxed mb-2">{f.desc}</p>
                  <code className="text-[10px] text-neutral-600 bg-neutral-900 px-2 py-1 rounded">
                    {f.example}
                  </code>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Console / Dashboard */}
      <section id="dashboard" className="py-24 relative">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold flex items-center justify-center gap-3">
              <LayoutDashboard className="w-8 h-8 text-indigo-500" />
              Intelligence Console
            </h2>
            <p className="text-neutral-500 mt-2">
              Auto-routes your input to the right agent pipeline.
            </p>
          </div>

          {/* 12-col grid — stacks to single col on mobile */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
            {/* Control Panel */}
            <div className="lg:col-span-4 space-y-4">
              <Card className="bg-black border-neutral-800 shadow-xl">
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-widest text-neutral-500">
                    Mission Control
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  {/* Smart input */}
                  <div className="space-y-2">
                    <Label className="text-neutral-400">Target Input</Label>
                    <div className="relative">
                      <Input
                        className="bg-neutral-900 border-neutral-800 pr-10"
                        placeholder="URL, email, handle, or idea..."
                        value={query}
                        onChange={(e) => {
                          setQuery(e.target.value);
                          setManualType("auto");
                        }}
                        onKeyDown={(e) => e.key === "Enter" && startResearch()}
                      />
                      {detection && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500">
                          {detection.icon}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Auto-detected type badge */}
                  {detection && manualType === "auto" && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center gap-2"
                    >
                      <Sparkles className="w-3 h-3 text-indigo-400" />
                      <span className="text-xs text-neutral-500">Auto-detected:</span>
                      <Badge variant="outline" className={`text-xs gap-1 ${detection.color}`}>
                        {detection.icon} {detection.label}
                      </Badge>
                    </motion.div>
                  )}

                  {/* Advanced override toggle */}
                  <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-1.5 text-xs text-neutral-600 hover:text-neutral-400 transition-colors w-full"
                  >
                    <ChevronDown
                      className={`w-3 h-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
                    />
                    Override detection
                  </button>

                  <AnimatePresence>
                    {showAdvanced && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-2 pt-1">
                          <Label className="text-neutral-400 text-xs">Force Module</Label>
                          <Select
                            value={manualType}
                            onValueChange={(v) =>
                              setManualType(v as ResearchType | "auto")
                            }
                          >
                            <SelectTrigger className="bg-neutral-900 border-neutral-800 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-neutral-900 border-neutral-800 text-white">
                              <SelectItem value="auto">⚡ Auto-Detect</SelectItem>
                              <SelectItem value="developer">Developer Intel</SelectItem>
                              <SelectItem value="startup">Startup Research</SelectItem>
                              <SelectItem value="email">Email OSINT</SelectItem>
                              <SelectItem value="youtube">YouTube Analysis</SelectItem>
                              <SelectItem value="reddit">Reddit Insights</SelectItem>
                              <SelectItem value="idea">Idea Validator</SelectItem>
                              <SelectItem value="social">Social Tracker</SelectItem>
                              <SelectItem value="linkedin">LinkedIn Intel</SelectItem>
                              <SelectItem value="npm">npm Analyzer</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <Button
                    className="w-full bg-white text-black hover:bg-neutral-200 font-bold py-6"
                    onClick={startResearch}
                    disabled={status === "loading" || !query.trim()}
                  >
                    {status === "loading" ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="animate-spin w-4 h-4" /> Deploying Agents...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Zap className="w-4 h-4" /> Execute Command
                      </span>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Status Indicator */}
              <Card className="bg-black border-neutral-800">
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-neutral-500">Agent Network</span>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <span className="text-[10px] font-mono text-emerald-500">HEALTHY</span>
                    </div>
                  </div>
                  {detection && (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-neutral-500">Active Module</span>
                      <span className="text-[10px] font-mono text-indigo-400 uppercase">
                        {activeType}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Output Display */}
            <div className="lg:col-span-8">
              <AnimatePresence mode="wait">
                {status === "loading" && (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <Card className="bg-neutral-900/20 border-neutral-800 border-dashed min-h-[400px] flex items-center justify-center">
                      <CardContent className="flex flex-col items-center gap-6">
                        <div className="relative">
                          <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full" />
                          <div className="absolute top-0 w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-medium text-neutral-300">
                            Agents are in the field
                          </p>
                          <p className="text-sm text-neutral-500 mt-1">
                            Running{" "}
                            <span className="text-indigo-400 font-semibold">{activeType}</span>{" "}
                            pipeline...
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "success" && report && (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    {/* Score Ring */}
                    {score !== null && (
                      <div className="mb-6 bg-neutral-900/40 border border-neutral-800 rounded-2xl overflow-hidden">
                        <ScoreRing
                          score={score}
                          label={activeType === "developer" ? "Dev Score" : "Viability"}
                        />
                      </div>
                    )}

                    {/* SWOT Grid for startup reports */}
                    {activeType === "startup" && report.report && (
                      <SwotGrid markdown={report.report} />
                    )}

                    <Card className="bg-black border-neutral-800 min-h-[400px] overflow-hidden">
                      {/* Toolbar */}
                      <div className="p-4 border-b border-neutral-800 bg-neutral-900/50 flex items-center justify-between">
                        <div className="flex gap-2">
                          <div className="w-3 h-3 rounded-full bg-red-500/50" />
                          <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                          <div className="w-3 h-3 rounded-full bg-green-500/50" />
                        </div>
                        <span className="text-[10px] font-mono text-neutral-600">
                          RESEARCH_REPORT.MD
                        </span>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className="text-[10px] border-indigo-500/30 text-indigo-400"
                          >
                            {activeType.toUpperCase()}
                          </Badge>
                          <button
                            onClick={() => downloadMarkdown(report.report, activeType)}
                            className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-white border border-neutral-700 hover:border-neutral-500 rounded px-2 py-1 transition-all"
                            title="Download report as Markdown"
                          >
                            <Download className="w-3 h-3" />
                            .md
                          </button>
                        </div>
                      </div>
                      <CardContent className="p-6 sm:p-8">
                        <MarkdownReport content={report.report} />
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "idle" && (
                  <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <Card className="bg-neutral-900/10 border-neutral-800 border-dashed min-h-[400px] flex items-center justify-center">
                      <CardContent className="text-center max-w-xs">
                        <Cpu className="w-12 h-12 text-neutral-800 mx-auto mb-4" />
                        <p className="text-neutral-600 text-sm font-medium mb-2">
                          Awaiting target input
                        </p>
                        <p className="text-neutral-700 text-xs">
                          Paste a URL, email, GitHub handle, or describe your idea — DevScout
                          figures out the rest.
                        </p>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "error" && (
                  <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <Alert
                      variant="destructive"
                      className="bg-red-950/30 border-red-900 text-red-400 py-10 flex flex-col items-center gap-4"
                    >
                      <AlertCircle className="w-12 h-12" />
                      <div className="text-center">
                        <AlertTitle className="text-lg font-bold">
                          Extraction Interrupted
                        </AlertTitle>
                        <AlertDescription className="mt-2">
                          {errorMessage ||
                            "The agents were blocked or the source timed out. Please try a different target."}
                        </AlertDescription>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-red-700 text-red-400 hover:bg-red-950"
                        onClick={() => setStatus("idle")}
                      >
                        Dismiss
                      </Button>
                    </Alert>
                  </motion.div>
                )}

                {status === "rate_limited" && (
                  <motion.div key="rate_limited" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <RateLimitAlert onRetry={startResearch} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-20 bg-black border-t border-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-8">
            <Zap className="w-6 h-6 text-indigo-500 fill-current" />
            <span className="text-2xl font-bold tracking-tighter">DevScout AI</span>
          </div>
          <div className="flex justify-center gap-8 mb-12">
            <Link href="#" className="text-neutral-500 hover:text-white">
              <GitBranch className="w-5 h-5" />
            </Link>
            <Link href="#" className="text-neutral-500 hover:text-white">
              <X className="w-5 h-5" />
            </Link>
            <Link href="#" className="text-neutral-500 hover:text-white">
              <PlayCircle className="w-5 h-5" />
            </Link>
          </div>
          <p className="text-neutral-600 text-sm">
            &copy; 2026 DevScout AI. Built for the next generation of researchers.
          </p>
        </div>
      </footer>
    </div>
  );
}
