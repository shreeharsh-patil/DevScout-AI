"use client";

import React, { useState, useCallback } from "react";

import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Cpu,
  Globe,
  GitBranch,
  Mail,
  ShieldAlert,
  Building2,
  User,
  Zap,
  ArrowRight,
  TrendingUp,
  LayoutDashboard,
  Loader2,
  Sparkles,
  ChevronDown,
  Download,
  Bookmark,
  Edit2,
  Trash2,
  Check,
  X,
} from "lucide-react";



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
import { Badge } from "@/components/ui/badge";
import EmailIntelligenceView from "@/components/email/email-intelligence-view";


// Extracted components
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import MarkdownReport from "@/components/reports/markdown-report";
import ScoreRing from "@/components/reports/score-ring";
import SwotGrid from "@/components/reports/swot-grid";
import CopyButton from "@/components/reports/copy-button";
import { SourcesPanel } from "@/components/reports/sources-panel";
import ResearchProgress from "@/components/research/research-progress";

import ErrorState from "@/components/research/error-state";
import RateLimitAlert from "@/components/research/rate-limit-alert";
import HistoryPreview from "@/components/research/history-preview";
import IconForType from "@/components/research/icon-for-type";

// Extracted logic
import { detectQueryType } from "@/lib/query-detector";
import { parseScore, downloadMarkdown } from "@/lib/report-utils";
import { useResearch } from "@/hooks/useResearch";
import { useAuth } from "@/context/auth-context";
import { updateReport, deleteJob } from "@/lib/api";

import { useCyclingPlaceholder } from "@/hooks/use-cycling-placeholder";
import { ALL_RESEARCH_TYPES } from "@/lib/type-meta";
import type { ResearchSource, ResearchType } from "@/types/research";

function reportSources(report: { sources?: ResearchSource[]; raw_data?: unknown }): ResearchSource[] | undefined {
  if (report.sources) return report.sources;
  const raw = report.raw_data as {
    sources?: ResearchSource[];
    researcher?: { sources?: ResearchSource[] };
    analysis?: { sources?: ResearchSource[] };
  } | undefined;
  return raw?.sources ?? raw?.researcher?.sources ?? raw?.analysis?.sources;
}

// LinkedIn icon used only in features grid (not in type-meta)
function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

// ─── Feature card data ───────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: <GitBranch className="w-5 h-5 text-violet-400" />,
    title: "Repository Intelligence",
    desc: "Paste a GitHub repo URL. Get health score, tech stack, contributors & risks.",
    example: "vercel/next.js",
  },
  {
    icon: <Mail className="w-5 h-5 text-orange-400" />,
    title: "Email Identity Intel",
    desc: "Enter any email. Get Gravatar, social profiles, GitHub accounts & more.",
    example: "someone@gmail.com",
  },
  {
    icon: <ShieldAlert className="w-5 h-5 text-red-400" />,
    title: "Breach Detection",
    desc: "Check if an email appears in known data breaches & pastes.",
    example: "user@example.com",
  },
  {
    icon: <Building2 className="w-5 h-5 text-cyan-400" />,
    title: "Domain Intelligence",
    desc: "WHOIS lookups, domain registration data & company affiliation.",
    example: "contact@company.com",
  },
  {
    icon: <Globe className="w-5 h-5 text-sky-400" />,
    title: "Social Footprint",
    desc: "Find LinkedIn, Twitter, Facebook & other social profiles.",
    example: "john.doe@gmail.com",
  },
  {
    icon: <GitBranch className="w-5 h-5 text-emerald-400" />,
    title: "GitHub OSINT",
    desc: "Commit history, profile searches & username inference.",
    example: "dev@github-user.com",
  },
  {
    icon: <User className="w-5 h-5 text-purple-400" />,
    title: "Gravatar Identity",
    desc: "Check Gravatar for profile photos, display names & linked URLs.",
    example: "sarah@startup.io",
  },
  {
    icon: <LinkedinIcon className="w-5 h-5 text-sky-400" />,
    title: "LinkedIn Intel",
    desc: "Paste a LinkedIn profile URL. Get professional background & insights.",
    example: "linkedin.com/in/satyanadella",
  },
  {
    icon: <GitBranch className="w-5 h-5 text-violet-400" />,
    title: "GitHub Profile",
    desc: "Paste a GitHub handle. Get tech stack, impact score & AI insights.",
    example: "github.com/torvalds",
  },
  {
    icon: <Globe className="w-5 h-5 text-indigo-400" />,
    title: "Startup Research",
    desc: "Paste any company URL. Get automated SWOT + competitor analysis.",
    example: "stripe.com",
  },
  {
    icon: <TrendingUp className="w-5 h-5 text-amber-400" />,
    title: "Social Tracker",
    desc: "Type a keyword or topic. Get cross-platform sentiment comparison.",
    example: "react vs vue",
  },
];

const EXAMPLE_HINTS = [
  "vercel/next.js",
  "someone@gmail.com",
  "john.doe@company.com",
  "contact@startup.io",
];

// ─── Main Component ───────────────────────────────────────────────────────────
export default function OnePageApp() {
  const [query, setQuery] = useState("");
  const [manualType, setManualType] = useState<ResearchType | "auto">("auto");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { status, report, errorMessage, startResearch, reset } = useResearch();
  const placeholder = useCyclingPlaceholder(query.trim() === "");

  const { refreshAuth } = useAuth();
  const [savedOverride, setSavedOverride] = useState<{ jobId: string; value: boolean } | null>(null);
  const [titleOverride, setTitleOverride] = useState<{ jobId: string; value: string } | null>(null);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const isSaved = report
    ? savedOverride?.jobId === report.job_id ? savedOverride.value : Boolean(report.is_saved)
    : false;
  const customTitle = report
    ? titleOverride?.jobId === report.job_id ? titleOverride.value : report.custom_title || ""
    : "";

  const handleToggleSaveCurrentReport = async () => {
    if (!report?.job_id) return;
    try {
      const next = !isSaved;
      await updateReport(report.job_id, { is_saved: next });
      setSavedOverride({ jobId: report.job_id, value: next });
      refreshAuth();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRenameCurrentReport = async () => {
    if (!report?.job_id) return;
    try {
      await updateReport(report.job_id, { custom_title: customTitle.trim() });
      setTitleOverride({ jobId: report.job_id, value: customTitle.trim() });
      setIsEditingTitle(false);
      refreshAuth();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteCurrentReport = async () => {
    if (!report?.job_id) return;
    if (!confirm("Are you sure you want to delete this research job?")) return;
    try {
      await deleteJob(report.job_id);
      reset();
      refreshAuth();
    } catch (e) {
      console.error(e);
    }
  };

  // Live detection as user types
  const detection = query.trim() ? detectQueryType(query) : null;
  const activeType: ResearchType =
    (manualType !== "auto" ? manualType : detection?.type) ?? "idea";

  const handleStartResearch = useCallback(() => {
    startResearch(query, activeType);
    refreshAuth();
  }, [startResearch, query, activeType, refreshAuth]);

  const handleSelectQuery = useCallback((q: string) => {
    setQuery(q);
    setManualType("auto");
  }, []);

  // Score for developer / idea / github-repo / repository reports
  const score =
    report?.report &&
    (activeType === "developer" || activeType === "idea" || activeType === "github-repo" || activeType === "repository")
      ? parseScore(report.report)
      : null;


  return (
    <div className="flex flex-col min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30">
      <Header />

      {/* Hero */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge
              variant="outline"
              className="mb-4 border-indigo-500/30 text-indigo-400 bg-indigo-500/5 px-3 py-1"
            >
              <Sparkles className="w-3 h-3 mr-1" /> Developer &amp; Repository Intelligence
            </Badge>
            <h2 className="text-5xl md:text-8xl font-extrabold tracking-tight mb-6 leading-[1.1]">
              Understand Any <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-white to-emerald-400">
                Open Source Project.
              </span>
            </h2>
            <p className="text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Paste a GitHub repository URL or owner/repo slug. Get a transparent health score,
              tech stack analysis, contributor insights, and risk assessment.
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
                    onKeyDown={(e) => e.key === "Enter" && handleStartResearch()}
                  />
                </div>
                <Button
                  onClick={handleStartResearch}
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
                    <IconForType type={detection.type} />
                    {detection.confidence} → Running <strong>{detection.label}</strong>
                  </Badge>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Example hints */}
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {EXAMPLE_HINTS.map((ex) => (
                <button
                  key={ex}
                  onClick={() => handleSelectQuery(ex)}
                  className="text-xs text-neutral-600 hover:text-neutral-300 border border-neutral-800 hover:border-neutral-600 px-3 py-1 rounded-full transition-all"
                >
                  {ex}
                </button>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-y border-neutral-900 bg-neutral-950/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <p className="text-xs uppercase tracking-widest text-neutral-500 mb-3">
              Intelligence Modules
            </p>
            <h2 className="text-3xl font-bold">From email to identity. Every signal covered.</h2>
          </div>
          <div className="overflow-x-auto sm:overflow-visible">
            <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-4 min-w-[640px] sm:min-w-0">
              {FEATURES.map((f, i) => (
                <motion.div
                  key={i}
                  whileHover={{ y: -5 }}
                  onClick={() => {
                    handleSelectQuery(f.example);
                    document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" });
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
              Paste an email to generate a full identity intelligence profile.
            </p>
          </div>

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
                        placeholder="someone@gmail.com"
                        value={query}
                        onChange={(e) => {
                          setQuery(e.target.value);
                          setManualType("auto");
                        }}
                        onKeyDown={(e) => e.key === "Enter" && handleStartResearch()}
                      />
                      {detection && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500">
                          <IconForType type={detection.type} />
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
                        <IconForType type={detection.type} /> {detection.label}
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
                            onValueChange={(v) => setManualType(v as ResearchType | "auto")}
                          >
                            <SelectTrigger className="bg-neutral-900 border-neutral-800 text-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-neutral-900 border-neutral-800 text-white">
                              {ALL_RESEARCH_TYPES.map((rt) => (
                                <SelectItem key={rt.value} value={rt.value}>
                                  {rt.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <Button
                    className="w-full bg-white text-black hover:bg-neutral-200 font-bold py-6"
                    onClick={handleStartResearch}
                    disabled={status === "loading" || !query.trim()}
                  >
                    {status === "loading" ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="animate-spin w-4 h-4" /> Deploying Agents...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Zap className="w-4 h-4" />
                        {activeType === "email" ? "Search Identity" : "Execute Command"}
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

              {/* Recent Scans */}
              <HistoryPreview onSelect={handleSelectQuery} />
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
                    <ResearchProgress
                      label={detection?.label || activeType}
                    />
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
                          label={activeType === "developer" ? "Dev Score" : activeType === "repository" ? "Repository Score" : "Viability"}
                        />
                      </div>
                    )}

                    {/* SWOT Grid for startup reports */}
                    {activeType === "startup" && report.report && (
                      <SwotGrid markdown={report.report} />
                    )}

                    {(activeType === "email" || activeType === "email_intelligence") && report?.raw_data ? (
                      <EmailIntelligenceView report={report} />
                    ) : (

                      <Card className="bg-black border-neutral-800 min-h-[400px] overflow-hidden">
                        {/* Toolbar */}
                        <div className="p-4 border-b border-neutral-800 bg-neutral-900/50 flex items-center justify-between">
                          <div className="flex gap-2">
                            <div className="w-3 h-3 rounded-full bg-red-500/50" />
                            <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                            <div className="w-3 h-3 rounded-full bg-green-500/50" />
                          </div>
                          <div className="flex items-center gap-2">
                            {isEditingTitle ? (
                              <div className="flex items-center gap-1">
                                <input
                                  type="text"
                                  placeholder="Custom report title..."
                                  value={customTitle}
                                  onChange={(e) => report && setTitleOverride({ jobId: report.job_id, value: e.target.value })}
                                  className="bg-black border border-indigo-500 rounded px-2 py-0.5 text-xs text-white focus:outline-none"
                                  autoFocus
                                />
                                <button
                                  onClick={handleRenameCurrentReport}
                                  className="p-1 text-indigo-400 hover:text-indigo-300"
                                >
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => setIsEditingTitle(false)}
                                  className="p-1 text-neutral-500 hover:text-white"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => setIsEditingTitle(true)}
                                className="text-xs text-neutral-400 hover:text-white flex items-center gap-1 font-medium truncate max-w-[200px]"
                                title="Click to rename report"
                              >
                                <span>{customTitle || "RESEARCH_REPORT.MD"}</span>
                                <Edit2 className="w-3 h-3 text-neutral-500" />
                              </button>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 sm:gap-2">
                            <Badge
                              variant="outline"
                              className="text-[10px] border-indigo-500/30 text-indigo-400"
                            >
                              {activeType.toUpperCase()}
                            </Badge>

                            {/* Bookmark / Save Report */}
                            <button
                              onClick={handleToggleSaveCurrentReport}
                              className={`flex items-center gap-1 text-[10px] border rounded px-2 py-1 transition-all ${
                                isSaved
                                  ? "border-emerald-500/40 bg-emerald-950/40 text-emerald-400"
                                  : "border-neutral-700 hover:border-neutral-500 text-neutral-400 hover:text-white"
                              }`}
                              title={isSaved ? "Saved in workspace" : "Save / Bookmark Report"}
                            >
                              <Bookmark className={`w-3 h-3 ${isSaved ? "fill-emerald-400" : ""}`} />
                              <span className="hidden sm:inline">{isSaved ? "Saved" : "Save"}</span>
                            </button>

                            <CopyButton text={report.report || ""} />

                            <button
                              onClick={() => downloadMarkdown(report.report || "", activeType)}
                              className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-white border border-neutral-700 hover:border-neutral-500 rounded px-2 py-1 transition-all"
                              title="Download report as Markdown"
                            >
                              <Download className="w-3 h-3" />
                              .md
                            </button>

                            <button
                              onClick={handleDeleteCurrentReport}
                              className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-red-400 border border-neutral-800 hover:border-red-900/50 rounded px-1.5 py-1 transition-all"
                              title="Delete Report"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>

                        <CardContent className="p-6 sm:p-8">
                          <MarkdownReport content={report.report || ""} />
                        </CardContent>
                      </Card>
                    )}

                    {/* Normalized Sources Explorer */}
                    <SourcesPanel
                      sources={reportSources(report)}
                    />
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
                          Paste an email, URL, GitHub handle, or anything else — DevScout figures
                          out the rest.
                        </p>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "error" && (
                  <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <ErrorState message={errorMessage} onDismiss={reset} />
                  </motion.div>
                )}

                {status === "rate_limited" && (
                  <motion.div key="rate_limited" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <RateLimitAlert onRetry={handleStartResearch} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
