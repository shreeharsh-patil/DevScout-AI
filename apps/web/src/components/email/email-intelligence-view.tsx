"use client";

import React, { useState, useMemo } from "react";
import {
  ShieldCheck,
  Mail,
  Globe,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Lock,
  User,
  Layers,
  Code2,
  FileCode,
  Tag,
  Info,
  Network,
  GitBranch,
  ChevronDown,
  ChevronUp,
  PlusCircle,
  MinusCircle,
  HelpCircle,
  History,
  Activity,
  UserPlus,
  AlertTriangle,
  Zap,
  Download,
  Share2,
  EyeOff,
  Filter,
  ArrowUpDown,
  Sparkles,
  Terminal,
  Printer,
  Copy,
  Check,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ResearchReport, ResearchSource } from "@/types/research";
import { safeExternalUrl } from "@/lib/utils";
import { EvidenceGraphView, type EvidenceGraphData } from "@/components/reports/evidence-graph-view";
import { SourcesPanel } from "@/components/reports/sources-panel";

interface Evidence { snippet?: string; title?: string; source_quality?: string; strength?: string }
interface Account {
  account_identifier?: string; avatar_url?: string; bio?: string; evidence?: Evidence[];
  method?: string; platform?: string; profile_url?: string; status?: string;
  public_email_match?: boolean; username_match?: boolean; website_match?: boolean;
  ecosystem_category?: string; confidence_score?: number; retrieved_at?: string;
}
interface Repository { description?: string; language?: string; name?: string; stars?: number; forks?: number; url?: string }
interface NpmPackage { description?: string; name?: string; version?: string }
interface CommitRecord { commit_date?: string; commit_message?: string; commit_url?: string; repo_name?: string; sha?: string }
interface DeveloperFootprint {
  contributions_summary?: string; npm_packages?: NpmPackage[]; repositories?: Repository[];
  top_languages?: string[]; total_stars?: number; total_forks?: number; github_commits?: CommitRecord[];
  location?: string; website_url?: string; organizations?: string[];
}
interface WebMention { canonical_url?: string; domain?: string; is_exact_match?: boolean; mention_category?: string; snippet?: string; title?: string; url?: string }
interface Breach {
  added_date?: string; breach_date?: string; breach_name?: string; data_classes?: string[];
  domain?: string; is_retired?: boolean; is_spam_list?: boolean; is_verified?: boolean; severity?: string;
}
interface UsernameCandidate { generation_rule?: string; username?: string }
interface IdentityCluster {
  accounts?: Account[]; ambiguity_warning?: string; cluster_id?: string; cluster_name?: string;
  confidence_score?: number; shared_signals?: string[]; status?: string;
}
interface IdentitySignals {
  ambiguity_note?: string; locations?: string[]; organizations?: string[]; possible_name?: string; websites?: string[];
}
interface ReputationSignal { signal_name: string; severity: string; description: string; }
interface EmailReputation { category?: string; signals?: ReputationSignal[]; impersonation_risk?: string; summary?: string; }
interface SnapshotDelta { change_type: string; field_name: string; old_value?: any; new_value?: any; description: string; timestamp?: string; }
interface HistoricalComparison { has_previous_scan?: boolean; previous_scan_date?: string; previous_job_id?: string; changes?: SnapshotDelta[]; summary?: string; }
interface InvestigationScope { depth?: string; estimated_coverage?: string; enabled_providers?: string[]; depth_rationale?: string; }
interface AIExplanation { summary?: string; key_highlights?: string[]; developer_archetype?: string; uncertainty_notes?: string[]; }
interface ProviderMetric { provider: string; duration_ms: number; status: string; cache_hit: boolean; records_count: number; }

interface EmailAnalysis {
  account_discovery?: Account[]; accounts?: Account[]; breach_status?: string; breaches?: Breach[];
  confidence?: {
    contradicting_signals?: string[]; evidence_count?: number; independent_source_count?: number;
    level?: string; reasons?: string[]; score?: number; supporting_signals?: string[];
  };
  developer_footprint?: DeveloperFootprint; footprint?: DeveloperFootprint;
  evidence_graph?: EvidenceGraphData; identity_clusters?: IdentityCluster[];
  identity_signals?: IdentitySignals; reputation?: EmailReputation;
  historical_comparison?: HistoricalComparison; scope?: InvestigationScope;
  ai_explanation?: AIExplanation; provider_metrics?: ProviderMetric[];
  sources?: ResearchSource[]; username_candidates?: UsernameCandidate[];
  validation?: {
    disposable?: boolean; domain_classification?: string; email?: string;
    is_role_account?: boolean; mx_status?: string; provider_type?: string; role_type?: string;
  };
  web_mentions?: WebMention[];
}
interface EmailRaw extends EmailAnalysis { analysis?: EmailAnalysis }

interface EmailIntelligenceViewProps {
  report: ResearchReport;
}

export default function EmailIntelligenceView({ report }: EmailIntelligenceViewProps) {
  const [activeTab, setActiveTab] = useState<
    "accounts" | "developer" | "graph" | "timeline" | "web" | "breaches" | "identity" | "candidates" | "sources" | "raw"
  >("accounts");
  const [showWhyConfidence, setShowWhyConfidence] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"confidence" | "platform" | "strongest">("confidence");
  const [isRedacted, setIsRedacted] = useState<boolean>(false);
  const [copiedShare, setCopiedShare] = useState<boolean>(false);

  const raw = report.raw_data as EmailRaw | undefined;
  const analysis = raw?.analysis || raw || {};
  const validation = analysis.validation || {};
  const confidence = analysis.confidence || {};
  const accounts: Account[] = analysis.accounts || analysis.account_discovery || [];
  const footprint = analysis.footprint || analysis.developer_footprint || {};
  const webMentions: WebMention[] = analysis.web_mentions || [];
  const breaches: Breach[] = analysis.breaches || [];
  const breachStatus = analysis.breach_status || "unavailable";
  const usernameCandidates: UsernameCandidate[] = analysis.username_candidates || [];
  const identityClusters: IdentityCluster[] = analysis.identity_clusters || [];
  const evidenceGraphData: EvidenceGraphData | undefined = analysis.evidence_graph || (footprint as any).evidence_graph;
  const reputation: EmailReputation = analysis.reputation || {};
  const history: HistoricalComparison = analysis.historical_comparison || {};
  const scope: InvestigationScope = analysis.scope || { depth: "standard" };
  const aiExplanation: AIExplanation | undefined = analysis.ai_explanation;
  const metrics: ProviderMetric[] = analysis.provider_metrics || [];
  const sources: ResearchSource[] = report.sources || analysis.sources || [];

  const rawEmail = validation.email || report.query || "target@example.com";
  const displayEmail = isRedacted
    ? rawEmail.replace(/^([^@]{2})[^@]+(@.*)$/, "$1***$2")
    : rawEmail;


  const score = confidence.score ?? 0;
  const confidenceLevel = confidence.level || "NO_EVIDENCE";
  const supportingSignals = confidence.supporting_signals || [];
  const contradictingSignals = confidence.contradicting_signals || [];
  const independentSources = confidence.independent_source_count ?? 0;
  const totalEvidence = confidence.evidence_count ?? 0;

  // Counts for Overview
  const verifiedCount = accounts.filter((a) => a.status === "VERIFIED" || a.public_email_match).length;
  const candidateCount = accounts.filter((a) => a.status === "CANDIDATE" && !a.public_email_match).length;
  const webCount = webMentions.length;
  const breachCount = breaches.length;

  // Filtered and Sorted Accounts
  const filteredAccounts = useMemo(() => {
    let list = [...accounts];
    if (statusFilter === "verified") {
      list = list.filter((a) => a.status === "VERIFIED" || a.public_email_match);
    } else if (statusFilter === "candidate") {
      list = list.filter((a) => a.status === "CANDIDATE");
    } else if (statusFilter === "probable") {
      list = list.filter((a) => a.status === "PROBABLE" || a.status === "HIGH_CONFIDENCE");
    }

    if (sortBy === "confidence") {
      list.sort((a, b) => (b.confidence_score ?? 0) - (a.confidence_score ?? 0));
    } else if (sortBy === "platform") {
      list.sort((a, b) => (a.platform || "").localeCompare(b.platform || ""));
    } else if (sortBy === "strongest") {
      list.sort((a, b) => (b.evidence?.length ?? 0) - (a.evidence?.length ?? 0));
    }

    return list;
  }, [accounts, statusFilter, sortBy]);

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(analysis, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `intelligence_${report.job_id || "report"}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleExportMarkdown = () => {
    const dataStr = "data:text/markdown;charset=utf-8," + encodeURIComponent(report.report_markdown || "# Email Intelligence Report");
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `report_${report.job_id || "intelligence"}.md`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setCopiedShare(true);
      setTimeout(() => setCopiedShare(false), 2000);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case "VERIFIED":
        return <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-xs gap-1"><CheckCircle2 className="w-3 h-3" /> VERIFIED</Badge>;
      case "HIGH_CONFIDENCE":
        return <Badge className="bg-sky-500/10 text-sky-400 border-sky-500/30 text-xs gap-1"><ShieldCheck className="w-3 h-3" /> HIGH CONFIDENCE</Badge>;
      case "PROBABLE":
        return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-xs gap-1"><AlertCircle className="w-3 h-3" /> PROBABLE</Badge>;
      case "CANDIDATE":
        return <Badge className="bg-neutral-800 text-neutral-400 border-neutral-700 text-xs">CANDIDATE</Badge>;
      default:
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/30 text-xs">NO EVIDENCE</Badge>;
    }
  };

  const getReputationBadge = (cat?: string) => {
    switch (cat?.toLowerCase()) {
      case "high_public_exposure":
        return <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/40 text-[10px] font-mono">HIGH PUBLIC EXPOSURE</Badge>;
      case "elevated_exposure":
        return <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/40 text-[10px] font-mono">ELEVATED EXPOSURE</Badge>;
      case "limited_public_footprint":
        return <Badge className="bg-neutral-800 text-neutral-400 border-neutral-700 text-[10px] font-mono">LIMITED PUBLIC FOOTPRINT</Badge>;
      case "uncertain":
        return <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/40 text-[10px] font-mono">UNCERTAIN</Badge>;
      default:
        return <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-[10px] font-mono">NORMAL REPUTATION</Badge>;
    }
  };

  const getSeverityBadge = (severity?: string) => {
    switch (severity?.toUpperCase()) {
      case "CRITICAL":
        return <Badge className="bg-rose-500/20 text-rose-400 border-rose-500/40 text-[10px]">CRITICAL</Badge>;
      case "HIGH":
        return <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/40 text-[10px]">HIGH</Badge>;
      case "MEDIUM":
        return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/40 text-[10px]">MEDIUM</Badge>;
      default:
        return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/40 text-[10px]">LOW</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Top Header Hero Card ── */}
      <Card className="bg-neutral-900/70 border-neutral-800 overflow-hidden shadow-2xl">
        <div className="p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 bg-gradient-to-br from-neutral-900 via-neutral-900/90 to-indigo-950/20">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-indigo-500/40 bg-indigo-950/40 text-indigo-300 font-mono text-[11px]">
                <Mail className="w-3 h-3 mr-1 inline" />
                EMAIL INTELLIGENCE
              </Badge>
              {scope.depth && (
                <Badge variant="outline" className="border-indigo-500/30 bg-indigo-950/20 text-indigo-400 font-mono text-[10px] uppercase">
                  <Zap className="w-2.5 h-2.5 mr-1 inline" />
                  DEPTH: {scope.depth}
                </Badge>
              )}
              {getReputationBadge(reputation.category)}
              {validation.disposable && (
                <Badge className="bg-red-500/20 text-red-400 border-red-500/40 text-[11px]">
                  DISPOSABLE DOMAIN
                </Badge>
              )}
              {validation.is_role_account && (
                <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/40 text-[11px]">
                  ROLE MAILBOX ({validation.role_type || "GENERIC"})
                </Badge>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white font-mono break-all">
              {displayEmail}
            </h2>

            <p className="text-xs sm:text-sm text-neutral-400">
              {reputation.summary || "Deterministic, evidence-backed public account signals, developer footprint, and security audit."}
            </p>

            {/* Action Bar (Export, Share, Redaction) */}
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsRedacted(!isRedacted)}
                className={`text-[11px] h-7 border-neutral-700 ${isRedacted ? "bg-indigo-950 text-indigo-300 border-indigo-500/50" : "text-neutral-300"}`}
              >
                <EyeOff className="w-3 h-3 mr-1" />
                {isRedacted ? "Redacted" : "Redact PII"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportJSON}
                className="text-[11px] h-7 border-neutral-700 text-neutral-300 hover:text-white"
              >
                <Download className="w-3 h-3 mr-1" /> JSON
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportMarkdown}
                className="text-[11px] h-7 border-neutral-700 text-neutral-300 hover:text-white"
              >
                <Download className="w-3 h-3 mr-1" /> Markdown
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => typeof window !== "undefined" && window.print()}
                className="text-[11px] h-7 border-neutral-700 text-neutral-300 hover:text-white"
              >
                <Printer className="w-3 h-3 mr-1" /> Print / PDF
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
                className="text-[11px] h-7 border-neutral-700 text-neutral-300 hover:text-white"
              >
                {copiedShare ? <Check className="w-3 h-3 mr-1 text-emerald-400" /> : <Share2 className="w-3 h-3 mr-1" />}
                {copiedShare ? "Link Copied!" : "Share"}
              </Button>
            </div>
          </div>

          {/* Footprint Score Ring + Expandable Trigger */}
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-4 bg-black/60 border border-neutral-800 p-4 rounded-xl">
              <div className="relative flex items-center justify-center w-16 h-16 rounded-full border-2 border-indigo-500/40 bg-indigo-950/30">
                <span className="text-xl font-bold text-white font-mono">{score}</span>
                <span className="text-[9px] text-neutral-400 absolute -bottom-1">/100</span>
              </div>
              <div className="space-y-0.5">
                <div className="text-[10px] text-neutral-500 uppercase font-mono tracking-wider">Footprint Tier</div>
                <div className="text-sm font-semibold text-neutral-200 capitalize">
                  {confidenceLevel.replace(/_/g, " ").toLowerCase()}
                </div>
              </div>
            </div>

            {/* Explainable Confidence Toggle */}
            <button
              onClick={() => setShowWhyConfidence(!showWhyConfidence)}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 bg-indigo-950/40 px-2.5 py-1 rounded-md border border-indigo-500/30 transition-colors"
            >
              <HelpCircle className="w-3 h-3" />
              Why {score}% confidence? {showWhyConfidence ? <ChevronUp className="w-3 h-3 ml-0.5" /> : <ChevronDown className="w-3 h-3 ml-0.5" />}
            </button>
          </div>
        </div>

        {/* ── Expandable "Why X% Confidence?" Breakdown ── */}
        {showWhyConfidence && (
          <div className="px-6 py-4 bg-black/80 border-t border-neutral-800 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800/80 pb-2">
              <div className="text-xs font-bold text-neutral-200 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
                Transparent Deterministic Scoring Breakdown
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-neutral-400">
                <Badge variant="outline" className="border-neutral-700 text-neutral-300">
                  {independentSources} Independent Source(s)
                </Badge>
                <Badge variant="outline" className="border-neutral-700 text-neutral-300">
                  {totalEvidence} Evidence Record(s)
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div className="space-y-1.5">
                <div className="text-[10px] uppercase font-mono tracking-wider text-emerald-400 flex items-center gap-1 font-semibold">
                  <PlusCircle className="w-3 h-3" /> Supporting Evidence ({supportingSignals.length})
                </div>
                {supportingSignals.length === 0 ? (
                  <div className="text-xs text-neutral-500 italic">No positive signals verified.</div>
                ) : (
                  supportingSignals.map((sig, idx) => (
                    <div key={idx} className="text-xs bg-emerald-950/20 border border-emerald-500/20 text-emerald-300 p-2 rounded flex items-start gap-1.5 font-mono">
                      <span className="text-emerald-400 font-bold">{sig}</span>
                    </div>
                  ))
                )}
              </div>

              <div className="space-y-1.5">
                <div className="text-[10px] uppercase font-mono tracking-wider text-amber-400 flex items-center gap-1 font-semibold">
                  <MinusCircle className="w-3 h-3" /> Dampening / Restraining Factors ({contradictingSignals.length})
                </div>
                {contradictingSignals.length === 0 ? (
                  <div className="text-xs text-neutral-500 italic">No dampening factors identified.</div>
                ) : (
                  contradictingSignals.map((sig, idx) => (
                    <div key={idx} className="text-xs bg-amber-950/20 border border-amber-500/20 text-amber-300 p-2 rounded flex items-start gap-1.5 font-mono">
                      <span className="text-amber-400 font-bold">{sig}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* ── Overview Metric Bar ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="bg-black/60 border-neutral-800 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-neutral-400 uppercase font-mono">Verified Accounts</div>
            <div className="text-xl font-bold text-emerald-400">{verifiedCount}</div>
          </div>
          <CheckCircle2 className="w-6 h-6 text-emerald-500/60" />
        </Card>
        <Card className="bg-black/60 border-neutral-800 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-neutral-400 uppercase font-mono">Candidates</div>
            <div className="text-xl font-bold text-neutral-300">{candidateCount}</div>
          </div>
          <User className="w-6 h-6 text-neutral-500" />
        </Card>
        <Card className="bg-black/60 border-neutral-800 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-neutral-400 uppercase font-mono">Web Mentions</div>
            <div className="text-xl font-bold text-sky-400">{webCount}</div>
          </div>
          <Globe className="w-6 h-6 text-sky-500/60" />
        </Card>
        <Card className="bg-black/60 border-neutral-800 p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-neutral-400 uppercase font-mono">Breach Exposures</div>
            <div className="text-xl font-bold text-rose-400">{breachCount}</div>
          </div>
          <Lock className="w-6 h-6 text-rose-500/60" />
        </Card>
      </div>

      {/* ── Explainable AI Narrative Card (Phase 18) ── */}
      {aiExplanation && (
        <Card className="bg-gradient-to-r from-indigo-950/30 via-neutral-900 to-purple-950/20 border-indigo-500/30 p-5 space-y-3 shadow-lg">
          <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2.5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-neutral-100">Grounded Intelligence Briefing</h3>
            </div>
            <Badge variant="outline" className="border-indigo-500/40 text-indigo-300 text-[10px] font-mono">
              {aiExplanation.developer_archetype || "General Developer"}
            </Badge>
          </div>

          <p className="text-xs text-neutral-300 leading-relaxed">{aiExplanation.summary}</p>

          {aiExplanation.key_highlights && aiExplanation.key_highlights.length > 0 && (
            <div className="space-y-1 pt-1">
              <span className="text-[10px] uppercase font-mono tracking-wider text-neutral-400 font-semibold">Key Highlights:</span>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-xs text-neutral-300">
                {aiExplanation.key_highlights.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-indigo-400 font-bold">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* ── Sub Navigation Tabs ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-800 pb-2">
        <div className="flex flex-wrap gap-1.5">
          <Button
            variant={activeTab === "accounts" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("accounts")}
            className={`text-xs gap-1.5 ${activeTab === "accounts" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Globe className="w-3.5 h-3.5" />
            Accounts ({accounts.length})
          </Button>
          <Button
            variant={activeTab === "developer" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("developer")}
            className={`text-xs gap-1.5 ${activeTab === "developer" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Code2 className="w-3.5 h-3.5" />
            Developer Footprint
          </Button>
          <Button
            variant={activeTab === "graph" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("graph")}
            className={`text-xs gap-1.5 ${activeTab === "graph" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Network className="w-3.5 h-3.5" />
            Evidence Graph
          </Button>
          <Button
            variant={activeTab === "timeline" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("timeline")}
            className={`text-xs gap-1.5 ${activeTab === "timeline" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <History className="w-3.5 h-3.5" />
            Timeline & Diff ({history.changes?.length || 0})
          </Button>
          <Button
            variant={activeTab === "web" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("web")}
            className={`text-xs gap-1.5 ${activeTab === "web" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <FileCode className="w-3.5 h-3.5" />
            Web Footprint ({webMentions.length})
          </Button>
          <Button
            variant={activeTab === "breaches" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("breaches")}
            className={`text-xs gap-1.5 ${activeTab === "breaches" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Lock className="w-3.5 h-3.5" />
            Breach Audit ({breaches.length})
          </Button>
          <Button
            variant={activeTab === "identity" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("identity")}
            className={`text-xs gap-1.5 ${activeTab === "identity" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <User className="w-3.5 h-3.5" />
            Clusters ({identityClusters.length || 1})
          </Button>
          <Button
            variant={activeTab === "candidates" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("candidates")}
            className={`text-xs gap-1.5 ${activeTab === "candidates" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Tag className="w-3.5 h-3.5" />
            Usernames ({usernameCandidates.length})
          </Button>
          <Button
            variant={activeTab === "sources" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("sources")}
            className={`text-xs gap-1.5 ${activeTab === "sources" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Layers className="w-3.5 h-3.5" />
            Sources ({sources.length})
          </Button>
          <Button
            variant={activeTab === "raw" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("raw")}
            className={`text-xs gap-1.5 ${activeTab === "raw" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
          >
            <Terminal className="w-3.5 h-3.5" />
            Telemetry
          </Button>
        </div>

        {/* Filter and Sort Controls for Accounts tab */}
        {activeTab === "accounts" && (
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-neutral-900 border border-neutral-700 text-[11px] text-neutral-300 rounded px-2 py-1 outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="verified">Verified Only</option>
              <option value="probable">Probable</option>
              <option value="candidate">Candidates</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-neutral-900 border border-neutral-700 text-[11px] text-neutral-300 rounded px-2 py-1 outline-none"
            >
              <option value="confidence">Sort by Confidence</option>
              <option value="platform">Sort by Platform</option>
              <option value="strongest">Sort by Strongest Evidence</option>
            </select>
          </div>
        )}
      </div>

      {/* ── Tab Content ── */}

      {/* Tab 1: Ecosystem Accounts */}
      {activeTab === "accounts" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredAccounts.length === 0 ? (
            <Card className="col-span-full bg-black border-neutral-800 p-8 text-center text-neutral-500 text-xs">
              No accounts matching selected filter.
            </Card>
          ) : (
            filteredAccounts.map((acc, idx) => (
              <Card key={idx} className="bg-black border-neutral-800 hover:border-neutral-700 transition-all p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      {acc.avatar_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={safeExternalUrl(acc.avatar_url)} alt="" className="w-10 h-10 rounded-full border border-neutral-700 object-cover" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center font-bold text-sm text-neutral-300">
                          {(acc.platform || "?")[0]?.toUpperCase() ?? "?"}
                        </div>
                      )}
                      <div>
                        <div className="font-bold text-white text-sm uppercase flex items-center gap-2">
                          {acc.platform || "Platform"}
                          {acc.ecosystem_category && (
                            <span className="text-[10px] text-neutral-500 font-mono font-normal">
                              ({acc.ecosystem_category.replace(/_/g, " ")})
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-neutral-400 font-mono">
                          {isRedacted ? `${(acc.account_identifier || "—").slice(0, 2)}***` : (acc.account_identifier || "—")}
                        </div>
                      </div>
                    </div>

                    <div>{getStatusBadge(acc.status || "")}</div>
                  </div>

                  {acc.bio && (
                    <p className="text-xs text-neutral-300 italic bg-neutral-900/60 p-2.5 rounded border border-neutral-800 mb-3">
                      &ldquo;{acc.bio}&rdquo;
                    </p>
                  )}

                  {acc.evidence && acc.evidence.length > 0 && (
                    <div className="space-y-1.5 mb-3">
                      <div className="text-[10px] uppercase font-mono tracking-wider text-neutral-500">Concrete Evidence:</div>
                      {acc.evidence.map((ev, eIdx) => (
                        <div key={eIdx} className="text-xs text-neutral-300 bg-neutral-950 p-2 rounded border border-neutral-800/80">
                          <div className="flex items-center justify-between">
                            <span className="font-medium text-indigo-300">{ev.title}</span>
                            {ev.source_quality && (
                              <Badge variant="outline" className="text-[9px] border-neutral-700 font-mono text-neutral-400">
                                {ev.source_quality}
                              </Badge>
                            )}
                          </div>
                          {ev.snippet && <div className="text-[11px] text-neutral-400 mt-0.5">{ev.snippet}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {acc.profile_url && safeExternalUrl(acc.profile_url) && (
                  <div className="pt-3 border-t border-neutral-800/80 flex items-center justify-between">
                    <a
                      href={safeExternalUrl(acc.profile_url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                    >
                      View Public Profile <ExternalLink className="w-3 h-3" />
                    </a>
                    <span className="text-[10px] text-neutral-500 font-mono capitalize">
                      {acc.method?.replace(/_/g, " ")}
                    </span>
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Developer Footprint */}
      {activeTab === "developer" && (
        <div className="space-y-6">
          {footprint.contributions_summary && (
            <Card className="bg-black border-neutral-800 p-5">
              <h3 className="text-sm font-semibold text-neutral-200 mb-2 flex items-center gap-2">
                <Code2 className="w-4 h-4 text-indigo-400" /> Summary
              </h3>
              <p className="text-xs text-neutral-300 leading-relaxed">{footprint.contributions_summary}</p>
            </Card>
          )}

          {footprint.top_languages && footprint.top_languages.length > 0 && (
            <Card className="bg-black border-neutral-800 p-5">
              <h3 className="text-sm font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4 text-indigo-400" /> Primary Languages
              </h3>
              <div className="flex flex-wrap gap-2">
                {footprint.top_languages.map((lang, idx) => (
                  <Badge key={idx} variant="outline" className="bg-neutral-900 border-neutral-700 text-neutral-200 px-3 py-1 font-mono">
                    {lang}
                  </Badge>
                ))}
              </div>
            </Card>
          )}

          {footprint.repositories && footprint.repositories.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-indigo-400" /> Public Repositories ({footprint.repositories.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {footprint.repositories.map((repo, idx) => (
                  <Card key={idx} className="bg-black border-neutral-800 p-4 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <a
                        href={safeExternalUrl(repo.url || "")}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        {repo.name} <ExternalLink className="w-3 h-3" />
                      </a>
                      {repo.language && (
                        <Badge variant="outline" className="text-[10px] border-neutral-700 text-neutral-300 font-mono">
                          {repo.language}
                        </Badge>
                      )}
                    </div>
                    {repo.description && <p className="text-xs text-neutral-400 line-clamp-2">{repo.description}</p>}
                    <div className="flex items-center gap-3 text-[11px] text-neutral-500 font-mono">
                      <span>⭐ {repo.stars ?? 0} stars</span>
                      {repo.forks !== undefined && <span>🍴 {repo.forks} forks</span>}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Interactive Evidence Graph */}
      {activeTab === "graph" && (
        <EvidenceGraphView graphData={evidenceGraphData} queryEmail={displayEmail} />
      )}

      {/* Tab 4: Historical Timeline & Diff */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          <Card className="bg-black border-neutral-800 p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-neutral-200">Historical Intelligence Snapshot Timeline</h3>
              </div>
              <Badge variant="outline" className="text-neutral-400 border-neutral-700 text-[10px] font-mono">
                {history.has_previous_scan ? "Multi-Snapshot Tracking" : "Baseline Snapshot"}
              </Badge>
            </div>

            <p className="text-xs text-neutral-300">{history.summary}</p>

            {history.changes && history.changes.length > 0 ? (
              <div className="space-y-2 pt-2">
                {history.changes.map((delta, idx) => (
                  <div key={idx} className="bg-neutral-950 border border-neutral-800 p-3 rounded-lg flex items-start gap-3">
                    <div className="p-1.5 rounded bg-indigo-950/40 border border-indigo-500/30 text-indigo-400">
                      {delta.change_type === "new_account" && <UserPlus className="w-3.5 h-3.5" />}
                      {delta.change_type === "github_activity" && <GitBranch className="w-3.5 h-3.5" />}
                      {delta.change_type === "new_breach" && <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />}
                      {delta.change_type === "new_web_mention" && <Globe className="w-3.5 h-3.5" />}
                      {!["new_account", "github_activity", "new_breach", "new_web_mention"].includes(delta.change_type) && <Activity className="w-3.5 h-3.5" />}
                    </div>
                    <div className="space-y-0.5 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-neutral-200 capitalize">{delta.change_type.replace(/_/g, " ")}</span>
                        <span className="text-[10px] font-mono text-neutral-500">{delta.timestamp?.slice(0, 10) || "Recent"}</span>
                      </div>
                      <p className="text-xs text-neutral-400">{delta.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center border border-dashed border-neutral-800 rounded-lg text-xs text-neutral-500">
                This is your baseline scan for this target. Future investigations in this workspace will automatically highlight newly discovered accounts, repository updates, and breach disclosures here.
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab 5: Web Footprint */}
      {activeTab === "web" && (
        <div className="space-y-3">
          {webMentions.length === 0 ? (
            <Card className="bg-black border-neutral-800 p-8 text-center text-neutral-500 text-xs">
              No public web occurrences found.
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {webMentions.map((mention, idx) => (
                <Card key={idx} className="bg-black border-neutral-800 p-4 space-y-2 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-mono uppercase text-indigo-400">{mention.domain || "Web"}</span>
                      {mention.is_exact_match ? (
                        <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/40 text-[9px]">
                          EXACT EMAIL MATCH
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[9px] text-neutral-400 border-neutral-700">
                          {mention.mention_category?.replace(/_/g, " ") || "MENTION"}
                        </Badge>
                      )}
                    </div>
                    <h4 className="text-xs font-semibold text-neutral-200 line-clamp-1">{mention.title || "Web Citation"}</h4>
                    {mention.snippet && (
                      <p className="text-xs text-neutral-400 line-clamp-3 bg-neutral-900/50 p-2 rounded border border-neutral-800/60 leading-relaxed">
                        &ldquo;{mention.snippet}&rdquo;
                      </p>
                    )}
                  </div>
                  {mention.url && safeExternalUrl(mention.url) && (
                    <div className="pt-2 border-t border-neutral-800/80">
                      <a
                        href={safeExternalUrl(mention.url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 truncate"
                      >
                        <span className="truncate">{mention.canonical_url || mention.url}</span>
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      </a>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Breach Exposures */}
      {activeTab === "breaches" && (
        <div className="space-y-4">
          {breachStatus === "unavailable" ? (
            <Card className="bg-black border-neutral-800 p-6 text-center text-xs text-neutral-400 space-y-2">
              <Lock className="w-6 h-6 text-neutral-600 mx-auto" />
              <p>HaveIBeenPwned API key is unconfigured. Breach exposure auditing was skipped.</p>
            </Card>
          ) : breaches.length === 0 ? (
            <Card className="bg-emerald-950/20 border-emerald-500/30 p-6 text-center text-xs text-emerald-300 flex items-center justify-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              No public breach exposures discovered in audited security disclosures.
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="text-xs text-neutral-400">
                Found <strong>{breaches.length}</strong> public security breach disclosure(s) involving this email address.
              </div>

              <div className="bg-neutral-900/80 border border-neutral-800 p-3.5 rounded-lg text-xs text-neutral-400 space-y-1">
                <div className="font-semibold text-neutral-200 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" /> Privacy & Security Guarantee
                </div>
                <p>
                  Breach exposure auditing tracks public metadata disclosures only. Zero passwords, password hashes, auth tokens, session cookies, or raw credentials are ever queried, fetched, stored, or displayed.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {breaches.map((b, idx) => (
                  <Card key={idx} className="bg-black border-neutral-800 p-4 space-y-2 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-xs font-bold text-white block">{b.breach_name}</span>
                          <span className="text-[10px] text-neutral-500 font-mono">{b.domain || "Domain"}</span>
                        </div>
                        <div>{getSeverityBadge(b.severity)}</div>
                      </div>

                      {b.data_classes && b.data_classes.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase font-mono tracking-wider text-neutral-500">Exposed Categories:</span>
                          <div className="flex flex-wrap gap-1">
                            {b.data_classes.map((cls, cIdx) => (
                              <Badge key={cIdx} variant="outline" className="text-[9px] bg-red-950/20 border-red-500/30 text-red-400 font-mono">
                                {cls}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-neutral-800 flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                      <span>Breach: {b.breach_date || "Unknown"}</span>
                      {b.is_verified && <span className="text-emerald-400">Verified Incident</span>}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Identity Clusters */}
      {activeTab === "identity" && (
        <div className="space-y-4">
          {identityClusters.length === 0 ? (
            <Card className="bg-black border-neutral-800 p-6">
              <h3 className="text-sm font-semibold text-neutral-200">Unified Public Identity</h3>
            </Card>
          ) : (
            identityClusters.map((cluster, idx) => (
              <Card key={idx} className="bg-black border-neutral-800 p-5 space-y-3">
                <div className="flex items-center justify-between gap-2 border-b border-neutral-800 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{cluster.status === "VERIFIED" ? "✅" : "⚪"}</span>
                    <h3 className="text-sm font-bold text-neutral-100">{cluster.cluster_name}</h3>
                  </div>
                  <Badge
                    className={
                      cluster.status === "VERIFIED"
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40 text-xs"
                        : "bg-neutral-800 text-neutral-400 border-neutral-700 text-xs"
                    }
                  >
                    {cluster.status || "CANDIDATE"}
                  </Badge>
                </div>

                {cluster.shared_signals && cluster.shared_signals.length > 0 && (
                  <div className="text-xs text-neutral-300 space-y-1">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-neutral-500">Shared Signals:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {cluster.shared_signals.map((sig, sIdx) => (
                        <span key={sIdx} className="bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800 font-mono text-[11px] text-indigo-300">
                          {sig}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {cluster.ambiguity_warning && (
                  <div className="text-xs bg-amber-950/20 border border-amber-500/30 p-2.5 rounded text-amber-300 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>{cluster.ambiguity_warning}</span>
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab 8: Candidate Permutations */}
      {activeTab === "candidates" && (
        <Card className="bg-black border-neutral-800 p-5 space-y-3">
          <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
            <Tag className="w-4 h-4 text-neutral-400" /> Syntactically Derived Candidate Handles
          </h3>
          <p className="text-xs text-neutral-400">
            Syntactically derived permutations from email local part. These must never be treated as confirmed identities without cryptographic proof.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            {usernameCandidates.map((cand, idx) => (
              <Badge key={idx} variant="outline" className="bg-neutral-900 border-neutral-700 text-neutral-300 font-mono px-3 py-1 text-xs">
                @{cand.username}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Tab 9: Searchable Sources Panel */}
      {activeTab === "sources" && (
        <SourcesPanel sources={sources} />
      )}

      {/* Tab 10: Technical Telemetry & Raw JSON */}
      {activeTab === "raw" && (
        <div className="space-y-4">
          {metrics.length > 0 && (
            <Card className="bg-black border-neutral-800 p-5 space-y-3">
              <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" /> Provider Execution Telemetry
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
                {metrics.map((m, idx) => (
                  <div key={idx} className="bg-neutral-950 border border-neutral-800 p-3 rounded text-xs space-y-1">
                    <div className="flex items-center justify-between font-mono font-bold text-neutral-200">
                      <span>{m.provider}</span>
                      <span className="text-indigo-400">{m.duration_ms}ms</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                      <span>Status: {m.status}</span>
                      <span>{m.cache_hit ? "⚡ Cache HIT" : "Network"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card className="bg-black border-neutral-800 p-5 space-y-2">
            <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-neutral-400" /> Raw Structured Intelligence Payload
            </h3>
            <pre className="text-[11px] font-mono bg-neutral-950 p-4 rounded-lg overflow-x-auto text-neutral-300 border border-neutral-800/80 max-h-96">
              {JSON.stringify(analysis, null, 2)}
            </pre>
          </Card>
        </div>
      )}
    </div>
  );
}
