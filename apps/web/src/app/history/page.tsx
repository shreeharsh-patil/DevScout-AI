"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  History,
  ArrowLeft,
  X,
  Loader2,
  AlertCircle,
  RefreshCw,
  FileText,
  Download,
  GitBranch,
  Globe,
  Mail,
  PlayCircle,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Package,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
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
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// ─── Types ────────────────────────────────────────────────────────────────────
interface HistoryItem {
  job_id: string;
  query: string;
  type: string;
  status: "completed" | "failed" | "pending" | "running" | string;
  created_at: string;
  completed_at?: string;
}

interface FullReport {
  job_id: string;
  query: string;
  type: string;
  status: string;
  report?: string;
  error?: string;
  created_at: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const TYPE_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  developer: {
    label: "Developer Intel",
    icon: <GitBranch className="w-3 h-3" />,
    color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
  },
  startup: {
    label: "Startup Research",
    icon: <Globe className="w-3 h-3" />,
    color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
  },
  email: {
    label: "Email OSINT",
    icon: <Mail className="w-3 h-3" />,
    color: "text-orange-400 border-orange-500/30 bg-orange-500/5",
  },
  youtube: {
    label: "YouTube Analysis",
    icon: <PlayCircle className="w-3 h-3" />,
    color: "text-red-400 border-red-500/30 bg-red-500/5",
  },
  reddit: {
    label: "Reddit Insights",
    icon: <MessageSquare className="w-3 h-3" />,
    color: "text-orange-500 border-orange-500/30 bg-orange-500/5",
  },
  idea: {
    label: "Idea Validator",
    icon: <ShieldCheck className="w-3 h-3" />,
    color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
  },
  social: {
    label: "Social Tracker",
    icon: <TrendingUp className="w-3 h-3" />,
    color: "text-blue-400 border-blue-500/30 bg-blue-500/5",
  },
  linkedin: {
    label: "LinkedIn Intel",
    icon: <LinkedinIcon className="w-3 h-3" />,
    color: "text-sky-400 border-sky-500/30 bg-sky-500/5",
  },
  npm: {
    label: "npm Analyzer",
    icon: <Package className="w-3 h-3" />,
    color: "text-rose-400 border-rose-500/30 bg-rose-500/5",
  },
};

const STATUS_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  completed: {
    label: "Completed",
    icon: <CheckCircle2 className="w-3 h-3" />,
    color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
  },
  failed: {
    label: "Failed",
    icon: <XCircle className="w-3 h-3" />,
    color: "text-red-400 border-red-500/30 bg-red-500/5",
  },
  pending: {
    label: "Pending",
    icon: <Clock className="w-3 h-3" />,
    color: "text-amber-400 border-amber-500/30 bg-amber-500/5",
  },
  running: {
    label: "Running",
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
    color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/5",
  },
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function downloadMarkdown(content: string, type: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `devscout-report-${type}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Markdown renderer (same as main page) ────────────────────────────────────
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
        ul: ({ children }) => <ul className="mb-4 space-y-1 ml-2">{children}</ul>,
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
        em: ({ children }) => <em className="text-neutral-400 italic">{children}</em>,
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
        tbody: ({ children }) => (
          <tbody className="divide-y divide-neutral-800">{children}</tbody>
        ),
        tr: ({ children }) => <tr className="hover:bg-neutral-900/50">{children}</tr>,
        th: ({ children }) => (
          <th className="px-4 py-2 text-left font-medium text-neutral-400">{children}</th>
        ),
        td: ({ children }) => <td className="px-4 py-3 text-neutral-300">{children}</td>,
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

// ─── Report Modal / Slide-over ────────────────────────────────────────────────
function ReportModal({
  item,
  onClose,
}: {
  item: HistoryItem;
  onClose: () => void;
}) {
  const [fullReport, setFullReport] = useState<FullReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(
          `http://localhost:8000/api/v1/research/status/${item.job_id}`
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setFullReport(data);
      } catch (e: any) {
        setError(e.message || "Failed to load report.");
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [item.job_id]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const typeMeta = TYPE_META[item.type] ?? {
    label: item.type,
    icon: <FileText className="w-3 h-3" />,
    color: "text-neutral-400 border-neutral-700 bg-neutral-800/30",
  };

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "spring", damping: 28, stiffness: 280 }}
        className="fixed right-0 top-0 h-full w-full max-w-2xl bg-[#090909] border-l border-neutral-800 z-50 flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-neutral-800 bg-neutral-900/50">
          <div className="flex flex-col gap-1 min-w-0 flex-1 mr-4">
            <p className="text-xs text-neutral-500 uppercase tracking-widest">Report</p>
            <p className="text-sm font-semibold text-white truncate">{item.query}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="outline" className={`text-[10px] gap-1 ${typeMeta.color}`}>
              {typeMeta.icon}
              {typeMeta.label}
            </Badge>
            {fullReport?.report && (
              <button
                onClick={() => downloadMarkdown(fullReport.report!, item.type)}
                className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-white border border-neutral-700 hover:border-neutral-500 rounded px-2 py-1 transition-all"
                title="Download"
              >
                <Download className="w-3 h-3" />
                .md
              </button>
            )}
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-500 hover:text-white hover:bg-neutral-800 transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center h-48 gap-4">
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-neutral-500 text-sm">Loading report…</p>
            </div>
          )}
          {!loading && error && (
            <Alert
              variant="destructive"
              className="bg-red-950/30 border-red-900 text-red-400"
            >
              <AlertCircle className="w-4 h-4" />
              <AlertTitle>Failed to load</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {!loading && fullReport && (
            <>
              {fullReport.report ? (
                <MarkdownReport content={fullReport.report} />
              ) : (
                <div className="text-center py-16">
                  <FileText className="w-12 h-12 text-neutral-700 mx-auto mb-4" />
                  <p className="text-neutral-500 text-sm">
                    {fullReport.error || "No report content available."}
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-800 bg-neutral-900/30">
          <p className="text-[10px] text-neutral-600 font-mono">
            JOB: {item.job_id} · {formatDate(item.created_at)}
          </p>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

// ─── History Page ─────────────────────────────────────────────────────────────
export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/api/v1/history");
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      // Accept array or { items: [] } shape
      setHistory(Array.isArray(data) ? data : data.items ?? []);
    } catch (e: any) {
      setError(e.message || "Failed to fetch history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <div className="flex flex-col min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30">

      {/* Header */}
      <header
        className={`fixed top-0 w-full z-40 transition-all duration-300 ${
          scrolled
            ? "bg-black/80 backdrop-blur-md border-b border-neutral-800 py-3"
            : "bg-transparent py-6"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-emerald-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white fill-current" />
            </div>
            <span className="text-xl font-bold tracking-tighter">DevScout AI</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <Link
              href="/"
              className="text-sm font-medium text-neutral-400 hover:text-white transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Console
            </Link>
            <Link
              href="/history"
              className="text-sm font-medium text-white flex items-center gap-1.5"
            >
              <History className="w-4 h-4 text-indigo-400" />
              History
            </Link>
          </nav>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 pt-32 pb-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          {/* Page title */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-10"
          >
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-neutral-900 border border-neutral-800 rounded-xl flex items-center justify-center">
                    <History className="w-5 h-5 text-indigo-400" />
                  </div>
                  <h1 className="text-3xl font-extrabold tracking-tight">Research History</h1>
                </div>
                <p className="text-neutral-500 text-sm ml-[52px]">
                  All past research jobs — click <strong className="text-neutral-400">View</strong> to open the full report.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchHistory}
                disabled={loading}
                className="border-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-900"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </motion.div>

          {/* Error state */}
          {error && (
            <Alert
              variant="destructive"
              className="mb-8 bg-red-950/30 border-red-900 text-red-400"
            >
              <AlertCircle className="w-4 h-4" />
              <AlertTitle>Failed to load history</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-32 gap-4">
              <Loader2 className="w-10 h-10 text-indigo-400 animate-spin" />
              <p className="text-neutral-500 text-sm">Loading history…</p>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && history.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-32 gap-4"
            >
              <FileText className="w-16 h-16 text-neutral-800" />
              <p className="text-neutral-500 font-medium">No research history yet</p>
              <p className="text-neutral-700 text-sm">Run your first query from the console.</p>
              <Link href="/">
                <Button
                  variant="outline"
                  className="mt-2 border-neutral-800 text-neutral-400 hover:text-white"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Go to Console
                </Button>
              </Link>
            </motion.div>
          )}

          {/* History list */}
          {!loading && history.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="space-y-3"
            >
              {/* Table header — desktop */}
              <div className="hidden md:grid grid-cols-12 gap-4 px-4 py-2 text-[10px] uppercase tracking-widest text-neutral-600">
                <span className="col-span-4">Query</span>
                <span className="col-span-2">Type</span>
                <span className="col-span-2">Status</span>
                <span className="col-span-3">Date</span>
                <span className="col-span-1 text-right">Action</span>
              </div>

              {history.map((item, i) => {
                const typeMeta = TYPE_META[item.type] ?? {
                  label: item.type,
                  icon: <FileText className="w-3 h-3" />,
                  color: "text-neutral-400 border-neutral-700 bg-neutral-800/30",
                };
                const statusMeta = STATUS_META[item.status] ?? {
                  label: item.status,
                  icon: <Clock className="w-3 h-3" />,
                  color: "text-neutral-400 border-neutral-700 bg-neutral-800/30",
                };

                return (
                  <motion.div
                    key={item.job_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="group bg-neutral-900/30 hover:bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 rounded-xl p-4 transition-all cursor-pointer"
                    onClick={() => setSelectedItem(item)}
                  >
                    {/* Mobile layout */}
                    <div className="md:hidden flex flex-col gap-2">
                      <p className="font-medium text-sm text-white truncate">{item.query}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className={`text-[10px] gap-1 ${typeMeta.color}`}>
                          {typeMeta.icon} {typeMeta.label}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={`text-[10px] gap-1 ${statusMeta.color}`}
                        >
                          {statusMeta.icon} {statusMeta.label}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-neutral-600 font-mono">
                          {formatDate(item.created_at)}
                        </span>
                        <Button size="sm" variant="ghost" className="text-xs text-indigo-400 h-7 px-2">
                          View <ChevronRight className="w-3 h-3 ml-1" />
                        </Button>
                      </div>
                    </div>

                    {/* Desktop layout */}
                    <div className="hidden md:grid grid-cols-12 gap-4 items-center">
                      <div className="col-span-4 flex items-center gap-3 min-w-0">
                        <div className="w-7 h-7 rounded-md bg-neutral-800 flex items-center justify-center shrink-0 text-neutral-500">
                          {typeMeta.icon}
                        </div>
                        <p className="font-medium text-sm text-white truncate">{item.query}</p>
                      </div>
                      <div className="col-span-2">
                        <Badge variant="outline" className={`text-[10px] gap-1 ${typeMeta.color}`}>
                          {typeMeta.icon} {typeMeta.label}
                        </Badge>
                      </div>
                      <div className="col-span-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] gap-1 ${statusMeta.color}`}
                        >
                          {statusMeta.icon} {statusMeta.label}
                        </Badge>
                      </div>
                      <div className="col-span-3">
                        <span className="text-[11px] text-neutral-500 font-mono">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                      <div className="col-span-1 flex justify-end">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-xs text-indigo-400 hover:text-indigo-300 hover:bg-indigo-950/30 h-7 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedItem(item);
                          }}
                        >
                          View <ChevronRight className="w-3 h-3 ml-1" />
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-10 bg-black border-t border-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <p className="text-neutral-700 text-xs">
            &copy; 2026 DevScout AI · All past reports are stored locally.
          </p>
        </div>
      </footer>

      {/* Report Modal */}
      {selectedItem && (
        <ReportModal item={selectedItem} onClose={() => setSelectedItem(null)} />
      )}
    </div>
  );
}
