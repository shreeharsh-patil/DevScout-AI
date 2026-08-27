"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
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
  ChevronRight,
  Search,
  BarChart3,
  Filter,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// Shared components
import MarkdownReport from "@/components/reports/markdown-report";
import IconForType from "@/components/research/icon-for-type";

// Shared logic
import { getHistory, getReport, ApiError } from "@/lib/api";
import { formatDate, formatRelative, downloadMarkdown } from "@/lib/report-utils";
import { TYPE_META, STATUS_META, getTypeMetaFallback, getStatusMetaFallback } from "@/lib/type-meta";
import type { HistoryItem, FullReport } from "@/types/research";

// ─── Stats Banner ─────────────────────────────────────────────────────────────
function StatsBanner({ history }: { history: HistoryItem[] }) {
  const total = history.length;
  const completed = history.filter((h) => h.status === "completed").length;
  const failed = history.filter((h) => h.status === "failed").length;
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0;

  const typeCounts: Record<string, number> = {};
  history.forEach((h) => {
    typeCounts[h.research_type] = (typeCounts[h.research_type] || 0) + 1;
  });
  const topType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]?.[0];
  const topTypeMeta = topType ? TYPE_META[topType] : null;

  const stats = [
    { label: "Total Scans", value: total, icon: <BarChart3 className="w-4 h-4 text-indigo-400" /> },
    { label: "Completed", value: completed, icon: <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg> },
    { label: "Failed", value: failed, icon: <svg className="w-4 h-4 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg> },
    { label: "Success Rate", value: `${successRate}%`, icon: <svg className="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></svg> },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8"
    >
      {stats.map((s) => (
        <div
          key={s.label}
          className="bg-neutral-900/40 border border-neutral-800 rounded-xl p-4 flex items-center gap-3"
        >
          <div className="w-8 h-8 rounded-lg bg-neutral-800 flex items-center justify-center shrink-0">
            {s.icon}
          </div>
          <div>
            <p className="text-xl font-bold text-white">{s.value}</p>
            <p className="text-[10px] uppercase tracking-wider text-neutral-600">{s.label}</p>
          </div>
        </div>
      ))}
      {topTypeMeta && (
        <div className="col-span-2 md:col-span-4 bg-neutral-900/20 border border-neutral-800 rounded-xl px-4 py-3 flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-wider text-neutral-600">Most used module:</span>
          <Badge variant="outline" className={`text-xs gap-1.5 ${topTypeMeta.color}`}>
            {topTypeMeta.icon}
            {topTypeMeta.label}
          </Badge>
          <span className="text-xs text-neutral-600">
            — {typeCounts[topType!]} scan{typeCounts[topType!] !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </motion.div>
  );
}

// ─── Report Modal / Slide-over ────────────────────────────────────────────────
function ReportModal({ item, onClose }: { item: HistoryItem; onClose: () => void }) {
  const [fullReport, setFullReport] = useState<FullReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getReport(item.job_id)
      .then((data) => {
        if (!cancelled) {
          setFullReport(data as FullReport);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          const msg = e instanceof ApiError ? e.message : "Failed to load report.";
          setError(msg);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [item.job_id]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const typeMeta = TYPE_META[item.research_type] ?? getTypeMetaFallback(item.research_type);
  const reportContent = fullReport?.report_markdown || fullReport?.report;

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
            {reportContent && (
              <button
                onClick={() => downloadMarkdown(reportContent, item.research_type)}
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
            <Alert variant="destructive" className="bg-red-950/30 border-red-900 text-red-400">
              <AlertCircle className="w-4 h-4" />
              <AlertTitle>Failed to load</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {!loading && fullReport && (
            <>
              {reportContent ? (
                <MarkdownReport content={reportContent} />
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
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTypeFilter, setActiveTypeFilter] = useState<string>("all");
  const [activeStatusFilter, setActiveStatusFilter] = useState<string>("all");

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getHistory();
      setHistory(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : "Failed to fetch history.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await getHistory();
        if (!cancelled) setHistory(Array.isArray(data) ? data : []);
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof ApiError ? e.message : "Failed to fetch history.";
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const uniqueTypes = useMemo(() => {
    const types = Array.from(new Set(history.map((h) => h.research_type)));
    return types.sort();
  }, [history]);

  const filtered = useMemo(() => {
    return history.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.research_type.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType = activeTypeFilter === "all" || item.research_type === activeTypeFilter;
      const matchesStatus = activeStatusFilter === "all" || item.status === activeStatusFilter;
      return matchesSearch && matchesType && matchesStatus;
    });
  }, [history, searchQuery, activeTypeFilter, activeStatusFilter]);

  const hasFilters = searchQuery || activeTypeFilter !== "all" || activeStatusFilter !== "all";

  return (
    <div className="flex flex-col min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30">
      {/* History-specific header */}
      <header className="fixed top-0 w-full z-40 bg-transparent py-6">
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
            className="mb-8"
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
                  All past research jobs — click <strong className="text-neutral-400">View</strong> to
                  open the full report.
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

          {/* Stats Banner */}
          {!loading && !error && history.length > 0 && <StatsBanner history={history} />}

          {/* Search + Filters */}
          {!loading && !error && history.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="mb-6 space-y-3"
            >
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" />
                <input
                  type="text"
                  placeholder="Search queries or module types..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-neutral-900/60 border border-neutral-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder:text-neutral-600 outline-none focus:border-neutral-600 transition-colors"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-600 hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-[10px] uppercase tracking-wider text-neutral-600 flex items-center gap-1">
                  <Filter className="w-3 h-3" /> Filter:
                </span>

                <button
                  onClick={() => setActiveTypeFilter("all")}
                  className={`text-xs px-3 py-1 rounded-full border transition-all ${
                    activeTypeFilter === "all"
                      ? "border-indigo-500/50 bg-indigo-500/10 text-indigo-300"
                      : "border-neutral-800 text-neutral-500 hover:border-neutral-600 hover:text-neutral-300"
                  }`}
                >
                  All types
                </button>
                {uniqueTypes.map((t) => {
                  const meta = TYPE_META[t];
                  return (
                    <button
                      key={t}
                      onClick={() => setActiveTypeFilter(activeTypeFilter === t ? "all" : t)}
                      className={`text-xs px-3 py-1 rounded-full border transition-all flex items-center gap-1 ${
                        activeTypeFilter === t
                          ? meta?.color || "border-neutral-600 bg-neutral-800 text-white"
                          : "border-neutral-800 text-neutral-500 hover:border-neutral-600 hover:text-neutral-300"
                      }`}
                    >
                      <IconForType type={t} />
                      {meta?.label || t}
                    </button>
                  );
                })}

                <span className="w-px h-4 bg-neutral-800 mx-1" />

                {(["all", "completed", "failed"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setActiveStatusFilter(s)}
                    className={`text-xs px-3 py-1 rounded-full border transition-all ${
                      activeStatusFilter === s
                        ? s === "all"
                          ? "border-neutral-600 bg-neutral-800 text-white"
                          : STATUS_META[s]?.color || "border-neutral-600 bg-neutral-800 text-white"
                        : "border-neutral-800 text-neutral-500 hover:border-neutral-600 hover:text-neutral-300"
                    }`}
                  >
                    {s === "all" ? "Any status" : s.charAt(0).toUpperCase() + s.slice(1)}
                  </button>
                ))}
              </div>

              <p className="text-[11px] text-neutral-600">
                Showing <span className="text-neutral-400 font-medium">{filtered.length}</span> of{" "}
                <span className="text-neutral-400 font-medium">{history.length}</span> results
                {hasFilters && (
                  <button
                    onClick={() => {
                      setSearchQuery("");
                      setActiveTypeFilter("all");
                      setActiveStatusFilter("all");
                    }}
                    className="ml-2 text-indigo-400 hover:text-indigo-300 underline"
                  >
                    Clear filters
                  </button>
                )}
              </p>
            </motion.div>
          )}

          {/* Error state */}
          {error && (
            <Alert variant="destructive" className="mb-8 bg-red-950/30 border-red-900 text-red-400">
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

          {/* No filter results */}
          {!loading && !error && history.length > 0 && filtered.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-24 gap-3"
            >
              <Search className="w-12 h-12 text-neutral-800" />
              <p className="text-neutral-500 font-medium">No results match your filters</p>
              <button
                onClick={() => {
                  setSearchQuery("");
                  setActiveTypeFilter("all");
                  setActiveStatusFilter("all");
                }}
                className="text-sm text-indigo-400 hover:text-indigo-300"
              >
                Clear all filters
              </button>
            </motion.div>
          )}

          {/* History list */}
          {!loading && filtered.length > 0 && (
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

              {filtered.map((item, i) => {
                const typeMeta = TYPE_META[item.research_type] ?? getTypeMetaFallback(item.research_type);
                const statusMeta = STATUS_META[item.status] ?? getStatusMetaFallback(item.status);

                return (
                  <motion.div
                    key={item.job_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="group bg-neutral-900/30 hover:bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 rounded-xl p-4 transition-all cursor-pointer"
                    onClick={() => setSelectedItem(item)}
                  >
                    {/* Mobile layout */}
                    <div className="md:hidden flex flex-col gap-2">
                      <p className="font-medium text-sm text-white truncate">{item.query}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline" className={`text-[10px] gap-1 ${typeMeta.color}`}>
                          <IconForType type={item.research_type} /> {typeMeta.label}
                        </Badge>
                        <Badge variant="outline" className={`text-[10px] gap-1 ${statusMeta.color}`}>
                          {statusMeta.icon} {statusMeta.label}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-neutral-600 font-mono">
                          {formatRelative(item.created_at)}
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
                          <IconForType type={item.research_type} />
                        </div>
                        <p className="font-medium text-sm text-white truncate">{item.query}</p>
                      </div>
                      <div className="col-span-2">
                        <Badge variant="outline" className={`text-[10px] gap-1 ${typeMeta.color}`}>
                          <IconForType type={item.research_type} /> {typeMeta.label}
                        </Badge>
                      </div>
                      <div className="col-span-2">
                        <Badge variant="outline" className={`text-[10px] gap-1 ${statusMeta.color}`}>
                          {statusMeta.icon} {statusMeta.label}
                        </Badge>
                      </div>
                      <div className="col-span-3">
                        <span
                          className="text-[11px] text-neutral-500 font-mono"
                          title={formatDate(item.created_at)}
                        >
                          {formatRelative(item.created_at)}
                          <span className="ml-1 text-neutral-700">· {formatDate(item.created_at)}</span>
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
      {selectedItem && <ReportModal item={selectedItem} onClose={() => setSelectedItem(null)} />}
    </div>
  );
}
