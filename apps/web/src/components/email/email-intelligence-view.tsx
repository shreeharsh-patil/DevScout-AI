"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  Mail,
  Globe,
  Package,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Lock,
  User,
  Layers,
  Code2,
  FileCode,
  Tag,
  Star,
  Info,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ResearchReport, ResearchSource } from "@/types/research";
import { safeExternalUrl } from "@/lib/utils";

interface Evidence { snippet?: string; title?: string }
interface Account {
  account_identifier?: string; avatar_url?: string; bio?: string; evidence?: Evidence[];
  method?: string; platform?: string; profile_url?: string; status?: string;
}
interface Repository { description?: string; language?: string; name?: string; stars?: number; url?: string }
interface NpmPackage { description?: string; name?: string; version?: string }
interface DeveloperFootprint {
  contributions_summary?: string; npm_packages?: NpmPackage[]; repositories?: Repository[]; top_languages?: string[];
}
interface WebMention { domain?: string; snippet?: string; title?: string; url?: string }
interface Breach { breach_date?: string; breach_name?: string; data_classes?: string[] }
interface UsernameCandidate { generation_rule?: string; username?: string }
interface IdentitySignals {
  ambiguity_note?: string; locations?: string[]; organizations?: string[]; possible_name?: string; websites?: string[];
}
interface EmailAnalysis {
  account_discovery?: Account[]; accounts?: Account[]; breach_status?: string; breaches?: Breach[];
  confidence?: { level?: string; reasons?: string[]; score?: number };
  developer_footprint?: DeveloperFootprint; footprint?: DeveloperFootprint;
  identity_signals?: IdentitySignals; sources?: ResearchSource[]; username_candidates?: UsernameCandidate[];
  validation?: { disposable?: boolean; email?: string; provider_type?: string }; web_mentions?: WebMention[];
}
interface EmailRaw extends EmailAnalysis { analysis?: EmailAnalysis }

interface EmailIntelligenceViewProps {
  report: ResearchReport;
}

export default function EmailIntelligenceView({ report }: EmailIntelligenceViewProps) {
  const [activeTab, setActiveTab] = useState<"accounts" | "developer" | "web" | "breaches" | "identity" | "sources">("accounts");

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
  const identitySignals = analysis.identity_signals || {};
  const sources: ResearchSource[] = report.sources || analysis.sources || [];

  const score = confidence.score ?? 0;
  const confidenceLevel = confidence.level || "NO_EVIDENCE";

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

  return (
    <div className="space-y-6">
      {/* ── Top Hero Card ── */}
      <Card className="bg-neutral-900/70 border-neutral-800 overflow-hidden shadow-2xl">
        <div className="p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 bg-gradient-to-br from-neutral-900 via-neutral-900/90 to-indigo-950/20">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-indigo-500/40 bg-indigo-950/40 text-indigo-300 font-mono text-[11px]">
                <Mail className="w-3 h-3 mr-1 inline" />
                EMAIL INTELLIGENCE
              </Badge>
              {validation.disposable && (
                <Badge className="bg-red-500/20 text-red-400 border-red-500/40 text-[11px]">
                  TEMPORARY / DISPOSABLE DOMAIN
                </Badge>
              )}
              {validation.provider_type && (
                <Badge variant="outline" className="border-neutral-700 text-neutral-400 capitalize text-[11px]">
                  {validation.provider_type} Domain
                </Badge>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white font-mono break-all">
              {validation.email || report.query}
            </h2>

            <p className="text-xs sm:text-sm text-neutral-400">
              Deterministic, evidence-backed public account signals, developer footprint, and security audit.
            </p>
          </div>

          {/* Footprint Score Meter */}
          <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-black/60 border border-neutral-800/80 min-w-[170px]">
            <span className="text-[11px] font-mono text-neutral-500 uppercase tracking-wider mb-1">
              Footprint Score
            </span>
            <div className="flex items-baseline gap-1">
              <span className={`text-4xl font-black font-mono tracking-tight ${
                score >= 70 ? "text-emerald-400" : score >= 40 ? "text-amber-400" : "text-neutral-400"
              }`}>
                {score}
              </span>
              <span className="text-xs font-mono text-neutral-600">/ 100</span>
            </div>
            <div className="mt-2">
              {getStatusBadge(confidenceLevel)}
            </div>
          </div>
        </div>

        {/* Confidence Rationale */}
        {confidence.reasons && confidence.reasons.length > 0 && (
          <div className="px-6 py-3 bg-black/40 border-t border-neutral-800/60 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-neutral-400">
            <span className="font-semibold text-neutral-300 flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-indigo-400" /> Evidence Rationale:
            </span>
            {confidence.reasons.map((reason: string, idx: number) => (
              <span key={idx} className="flex items-center gap-1.5 text-neutral-300">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                {reason}
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* ── Sub Navigation Tabs ── */}
      <div className="flex flex-wrap gap-2 border-b border-neutral-800 pb-2">
        <Button
          variant={activeTab === "accounts" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("accounts")}
          className={`text-xs gap-1.5 ${activeTab === "accounts" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
        >
          <Globe className="w-3.5 h-3.5" />
          Public Accounts ({accounts.length})
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
          variant={activeTab === "web" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("web")}
          className={`text-xs gap-1.5 ${activeTab === "web" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
        >
          <FileCode className="w-3.5 h-3.5" />
          Web Mentions ({webMentions.length})
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
          Identity Signals
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
      </div>

      {/* ── Tab Content ── */}

      {/* Tab 1: Public Accounts */}
      {activeTab === "accounts" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {accounts.length === 0 ? (
            <Card className="col-span-full bg-black border-neutral-800 p-8 text-center text-neutral-500 text-xs">
              No public accounts retrieved.
            </Card>
          ) : (
            accounts.map((acc, idx) => (
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
                        <div className="font-bold text-white text-sm capitalize">{acc.platform || "Platform"}</div>
                        <div className="text-xs text-neutral-400 font-mono">{acc.account_identifier || "—"}</div>
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
                    <div className="space-y-1 mb-3">
                      <span className="text-[10px] uppercase font-mono text-neutral-500 font-bold">Evidence:</span>
                      {acc.evidence.map((ev: Evidence, evIdx: number) => (
                        <p key={evIdx} className="text-xs text-neutral-400 bg-neutral-950 p-2 rounded border border-neutral-800/80">
                          {ev.snippet || ev.title}
                        </p>
                      ))}
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-neutral-800/60 flex items-center justify-between text-xs text-neutral-500">
                  <span className="font-mono text-[11px] text-neutral-400 capitalize">
                    Method: {acc.method?.replace(/_/g, " ")}
                  </span>

                  {acc.profile_url && (
                    <a
                      href={safeExternalUrl(acc.profile_url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium text-xs"
                    >
                      Open Profile <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Developer Footprint */}
      {activeTab === "developer" && (
        <div className="space-y-4">
          <Card className="bg-black border-neutral-800 p-6 space-y-6">
            <div>
              <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                <Code2 className="w-4 h-4 text-emerald-400" />
                Technical Profiles & Language Footprint
              </h3>
              {footprint.contributions_summary ? (
                <p className="text-xs text-neutral-300 bg-neutral-900/60 p-3 rounded border border-neutral-800">
                  {footprint.contributions_summary}
                </p>
              ) : (
                <p className="text-xs text-neutral-500">No developer profile summary available.</p>
              )}
            </div>

            {footprint.top_languages && footprint.top_languages.length > 0 && (
              <div>
                <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider block mb-2 font-bold">
                  Top Languages:
                </span>
                <div className="flex flex-wrap gap-2">
                  {footprint.top_languages.map((lang: string, i: number) => (
                    <Badge key={i} variant="outline" className="bg-neutral-900 border-neutral-700 text-white font-mono text-xs px-2.5 py-1">
                      {lang}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Repositories Table */}
            {footprint.repositories && footprint.repositories.length > 0 && (
              <div>
                <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider block mb-2 font-bold">
                  Public Repositories ({footprint.repositories.length}):
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {footprint.repositories.map((repo: Repository, i: number) => (
                    <a
                      key={i}
                      href={safeExternalUrl(repo.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-3 rounded-lg bg-neutral-900/40 border border-neutral-800 hover:border-neutral-700 transition-all block"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-white text-xs truncate">{repo.name}</span>
                        <div className="flex items-center gap-2 text-[11px] text-neutral-400">
                          {repo.language && <span className="text-indigo-400 font-mono">{repo.language}</span>}
                          {(repo.stars ?? 0) > 0 && <span className="flex items-center gap-0.5"><Star className="w-3 h-3 text-amber-400 fill-amber-400" /> {repo.stars}</span>}
                        </div>
                      </div>
                      {repo.description && (
                        <p className="text-[11px] text-neutral-400 line-clamp-2 mt-1">{repo.description}</p>
                      )}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* npm Packages */}
            {footprint.npm_packages && footprint.npm_packages.length > 0 && (
              <div>
                <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider block mb-2 font-bold">
                  npm Packages:
                </span>
                <div className="space-y-2">
                  {footprint.npm_packages.map((pkg: NpmPackage, i: number) => (
                    <div key={i} className="p-2.5 rounded bg-neutral-900 border border-neutral-800 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-white font-mono">{pkg.name}</span>
                        <span className="text-neutral-500 ml-2">v{pkg.version || "latest"}</span>
                        {pkg.description && <p className="text-neutral-400 text-[11px] mt-0.5">{pkg.description}</p>}
                      </div>
                      <Package className="w-4 h-4 text-rose-400 flex-shrink-0" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab 3: Web Mentions */}
      {activeTab === "web" && (
        <Card className="bg-black border-neutral-800 p-6 space-y-4">
          <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
            <Globe className="w-4 h-4 text-indigo-400" />
            Public Web Mentions ({webMentions.length})
          </h3>
          {webMentions.length === 0 ? (
            <p className="text-xs text-neutral-500 p-6 text-center">No exact web occurrences discovered.</p>
          ) : (
            <div className="space-y-3">
              {webMentions.map((m: WebMention, idx: number) => (
                <div key={idx} className="p-3.5 rounded-lg bg-neutral-900/50 border border-neutral-800 hover:border-neutral-700 transition-all">
                  <div className="flex items-center justify-between gap-2">
                    <a
                      href={safeExternalUrl(m.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold text-xs text-indigo-400 hover:underline flex items-center gap-1.5"
                    >
                      {m.title} <ExternalLink className="w-3 h-3" />
                    </a>
                    <Badge variant="outline" className="text-[10px] font-mono border-neutral-800 text-neutral-400">
                      {m.domain}
                    </Badge>
                  </div>
                  {m.snippet && (
                    <p className="text-xs text-neutral-300 mt-1.5 line-clamp-2">
                      &ldquo;{m.snippet}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Tab 4: Breach Exposure */}
      {activeTab === "breaches" && (
        <Card className="bg-black border-neutral-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-400" />
              Security & Breach Disclosures
            </h3>
            <span className="text-[11px] font-mono text-neutral-500">
              Strict Zero-Credential Policy
            </span>
          </div>

          {breachStatus === "unavailable" ? (
            <div className="p-6 rounded-lg bg-neutral-900/40 border border-neutral-800 text-xs text-neutral-400">
              ℹ️ Breach disclosure API key (<code className="text-indigo-400">HIBP_API_KEY</code>) is not configured. This module is marked <span className="font-mono text-neutral-200">UNAVAILABLE</span>.
            </div>
          ) : breaches.length === 0 ? (
            <div className="p-6 rounded-lg bg-emerald-950/20 border border-emerald-500/20 text-xs text-emerald-300">
              ✅ No known public breach disclosures found for this email target.
            </div>
          ) : (
            <div className="space-y-3">
              {breaches.map((b: Breach, idx: number) => (
                <div key={idx} className="p-4 rounded-lg bg-neutral-900/60 border border-neutral-800">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">{b.breach_name}</span>
                    <span className="text-xs font-mono text-neutral-500">{b.breach_date || "Unknown Date"}</span>
                  </div>
                  {b.data_classes && b.data_classes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {b.data_classes.map((cls: string, cIdx: number) => (
                        <Badge key={cIdx} variant="outline" className="text-[10px] border-neutral-700 text-neutral-400">
                          {cls}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Tab 5: Identity Signals & Candidates */}
      {activeTab === "identity" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-black border-neutral-800 p-5 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <User className="w-4 h-4 text-indigo-400" />
              Correlated Identity Metadata
            </h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-neutral-800/80">
                <span className="text-neutral-500">Possible Name:</span>
                <span className="text-white font-medium">{identitySignals.possible_name || "—"}</span>
              </div>
              {identitySignals.organizations && identitySignals.organizations.length > 0 && (
                <div className="flex justify-between py-1 border-b border-neutral-800/80">
                  <span className="text-neutral-500">Organizations:</span>
                  <span className="text-white font-medium">{identitySignals.organizations.join(", ")}</span>
                </div>
              )}
              {identitySignals.locations && identitySignals.locations.length > 0 && (
                <div className="flex justify-between py-1 border-b border-neutral-800/80">
                  <span className="text-neutral-500">Locations:</span>
                  <span className="text-white font-medium">{identitySignals.locations.join(", ")}</span>
                </div>
              )}
              {identitySignals.websites && identitySignals.websites.length > 0 && (
                <div className="flex justify-between py-1 border-b border-neutral-800/80">
                  <span className="text-neutral-500">Websites:</span>
                  <span className="text-indigo-400 font-medium truncate max-w-[200px]">{identitySignals.websites.join(", ")}</span>
                </div>
              )}
            </div>

            {identitySignals.ambiguity_note && (
              <p className="text-xs text-amber-300 bg-amber-950/30 p-2.5 rounded border border-amber-500/20">
                ⚠️ {identitySignals.ambiguity_note}
              </p>
            )}
          </Card>

          <Card className="bg-black border-neutral-800 p-5 space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Tag className="w-4 h-4 text-neutral-400" />
              Candidate Usernames (Syntax Derived)
            </h3>
            <p className="text-[11px] text-neutral-500">
              Candidate hypotheses derived from email local-parts. Unconfirmed unless backed by independent proof.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              {usernameCandidates.map((cand: UsernameCandidate, idx: number) => (
                <Badge key={idx} variant="outline" className="bg-neutral-900 border-neutral-800 text-neutral-300 font-mono text-xs px-2.5 py-1">
                  {cand.username} <span className="text-[9px] text-neutral-500 ml-1">({cand.generation_rule?.replace(/_/g, " ")})</span>
                </Badge>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Tab 6: Normalized Sources */}
      {activeTab === "sources" && (
        <Card className="bg-black border-neutral-800 p-6 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            Verified Citations & Sources ({sources.length})
          </h3>
          {sources.length === 0 ? (
            <p className="text-xs text-neutral-500 p-6 text-center">No external sources cited.</p>
          ) : (
            <div className="divide-y divide-neutral-800/80">
              {sources.map((src: ResearchSource, idx: number) => (
                <div key={idx} className="py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded bg-indigo-950/60 border border-indigo-500/30 flex items-center justify-center font-mono text-xs font-bold text-indigo-300">
                      [{src.source_id}]
                    </span>
                    <div>
                      <div className="font-semibold text-xs text-white">{src.title}</div>
                      <div className="text-[11px] text-neutral-500 font-mono">{src.platform} &bull; {src.source_type}</div>
                    </div>
                  </div>

                  <a
                    href={safeExternalUrl(src.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono flex-shrink-0"
                  >
                    Visit <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </Card