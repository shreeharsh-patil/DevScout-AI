"use client";

import {
  ShieldCheck,
  AlertCircle,
  Globe,
  User,
  Building2,
  Link as LinkIcon,
  ExternalLink,
  Hash,
  ShieldAlert,
  Newspaper,
  Key,
  ClipboardList,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
    </svg>
  );
}

interface GravatarData {
  has_profile: boolean;
  display_name?: string;
  avatar_url?: string;
  profile_url?: string;
  urls?: string[];
}

interface WhoIsData {
  has_data: boolean;
  registrant_name?: string;
  registrant_org?: string;
  registrant_email?: string;
  created_date?: string;
}

interface BreachData {
  name: string;
  domain?: string;
  breach_date?: string;
  data_classes?: string[];
}

interface SocialProfile {
  platform: string;
  url?: string;
  title?: string;
  confidence_category?: string;
  is_confirmed?: boolean;
  evidence?: string;
}

interface GitHubAccount {
  login: string;
  avatar_url?: string;
  confidence?: string;
  strategy?: string;
  profile_url?: string;
  confidence_category?: string;
  is_confirmed?: boolean;
  evidence?: string;
}


interface WebMention {
  title?: string;
  url?: string;
  snippet?: string;
}

interface Props {
  analysis?: Record<string, unknown> | undefined;
  researcher?: Record<string, unknown> | undefined;
}


function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 60 ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" :
    score >= 30 ? "text-amber-400 border-amber-500/30 bg-amber-500/10" :
    "text-red-400 border-red-500/30 bg-red-500/10";

  return (
    <Badge variant="outline" className={`text-sm px-3 py-1 ${color}`}>
      {score}/100
    </Badge>
  );
}

function SignalBadge({ signal }: { signal: string }) {
  const config: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    "gravatar_profile": { label: "Gravatar", color: "text-purple-400 border-purple-500/30 bg-purple-500/10", icon: <User className="w-3 h-3" /> },
    "github_presence": { label: "GitHub", color: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10", icon: <GithubIcon className="w-3 h-3" /> },
    "social_media_presence": { label: "Social Media", color: "text-sky-400 border-sky-500/30 bg-sky-500/10", icon: <Globe className="w-3 h-3" /> },
    "web_mentions": { label: "Web Mentions", color: "text-indigo-400 border-indigo-500/30 bg-indigo-500/10", icon: <LinkIcon className="w-3 h-3" /> },
    "breach_records": { label: "Breach Records", color: "text-red-400 border-red-500/30 bg-red-500/10", icon: <ShieldAlert className="w-3 h-3" /> },
    "news_mentions": { label: "News Mentions", color: "text-amber-400 border-amber-500/30 bg-amber-500/10", icon: <Newspaper className="w-3 h-3" /> },
    "domain_registration": { label: "Domain Reg.", color: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10", icon: <Building2 className="w-3 h-3" /> },
    "pgp_key": { label: "PGP Key", color: "text-rose-400 border-rose-500/30 bg-rose-500/10", icon: <Key className="w-3 h-3" /> },
    "pastebin_mentions": { label: "Pastebin", color: "text-orange-400 border-orange-500/30 bg-orange-500/10", icon: <ClipboardList className="w-3 h-3" /> },
  };

  const c = config[signal] || { label: signal, color: "text-neutral-400 border-neutral-700 bg-neutral-800/30", icon: <Hash className="w-3 h-3" /> };

  return (
    <Badge variant="outline" className={`gap-1 px-2 py-0.5 text-[10px] ${c.color}`}>
      {c.icon} {c.label}
    </Badge>
  );
}

export default function IdentityProfile({ analysis, researcher }: Props) {
  if (!analysis && !researcher) return null;

  const a = analysis as Record<string, unknown> | undefined;
  const r = researcher as Record<string, unknown> | undefined;
  const email = String(a?.email || r?.email || "");
  const possibleName = (a?.possible_name || (r?.data_enrichment as Record<string, unknown>)?.possible_name) as string | undefined;
  const confidenceScore = Number(a?.confidence_score ?? (r?.profile_completeness as Record<string, unknown>)?.score ?? 0);
  const categorization = String(a?.categorization || (r?.profile_completeness as Record<string, unknown>)?.categorization || "low");
  const signals = (a?.signals_found || []) as string[];
  const gravatar = (a?.gravatar || r?.gravatar || {}) as GravatarData;
  const whois = (a?.whois || r?.whois || {}) as WhoIsData;
  const breaches = (a?.breaches || r?.breaches || []) as BreachData[];
  const socialProfiles = (a?.social_profiles || r?.social_profiles || []) as SocialProfile[];
  const githubAccounts = (a?.github_accounts || (r?.github as Record<string, unknown>)?.accounts || []) as GitHubAccount[];
  const webMentions = (a?.web_mentions || []) as WebMention[];
  const summary = String(a?.summary || "");


  return (
    <div className="space-y-6">
      {/* Identity Card */}
      <Card className="bg-black border-neutral-800 overflow-hidden">
        <div className="bg-gradient-to-r from-indigo-900/30 via-purple-900/20 to-transparent p-6">
          <div className="flex items-start gap-5">
            {gravatar.avatar_url ? (
              <img
                src={gravatar.avatar_url}
                alt="Avatar"
                className="w-20 h-20 rounded-full border-2 border-indigo-500/30 object-cover shrink-0"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-neutral-900 border-2 border-neutral-700 flex items-center justify-center shrink-0">
                <User className="w-8 h-8 text-neutral-600" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-2xl font-bold text-white truncate">
                  {possibleName || "Unknown Identity"}
                </h2>
                <ScoreBadge score={confidenceScore} />
              </div>
              <p className="text-neutral-400 font-mono text-sm mt-1">{email}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className={`text-[10px] uppercase tracking-widest ${
                  categorization === "high" ? "text-emerald-400" :
                  categorization === "medium" ? "text-amber-400" :
                  "text-neutral-500"
                }`}>
                  {categorization} confidence
                </span>
                <span className="text-neutral-700">|</span>
                <span className="text-[10px] text-neutral-500">{signals.length} signal(s) detected</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Signals */}
      {signals.length > 0 && (
        <Card className="bg-black border-neutral-800">
          <CardContent className="p-4">
            <p className="text-[10px] uppercase tracking-widest text-neutral-600 mb-3">Public Signals</p>
            <div className="flex flex-wrap gap-2">
              {signals.map((signal: string) => (
                <SignalBadge key={signal} signal={signal} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      {summary && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              Intelligence Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-neutral-400 leading-relaxed">{summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Gravatar Profile */}
      {gravatar.has_profile && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <User className="w-4 h-4 text-purple-400" />
              Gravatar Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {gravatar.display_name && (
              <p className="text-sm text-neutral-400">
                <span className="text-neutral-500">Name:</span> {gravatar.display_name}
              </p>
            )}
            {gravatar.urls && gravatar.urls.length > 0 && (
              <div>
                <p className="text-xs text-neutral-500 mb-1">Associated URLs:</p>
                {gravatar.urls.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 mb-0.5">
                    <ExternalLink className="w-3 h-3 shrink-0" /> {url}
                  </a>
                ))}
              </div>
            )}
            {gravatar.profile_url && (
              <a href={gravatar.profile_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 mt-2">
                View Full Profile <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </CardContent>
        </Card>
      )}

      {/* Social Media Profiles */}
      {socialProfiles.length > 0 && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <Globe className="w-4 h-4 text-sky-400" />
              Social Media Profiles
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {socialProfiles.map((sp, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs font-medium text-neutral-400 w-28 shrink-0">{sp.platform}:</span>
                {sp.url ? (
                  <a href={sp.url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-indigo-400 hover:text-indigo-300 truncate flex items-center gap-1">
                    {sp.title || sp.url} <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                  </a>
                ) : (
                  <span className="text-xs text-neutral-500 truncate">{sp.title || "Mention found"}</span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* GitHub Accounts */}
      {githubAccounts.length > 0 && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <GithubIcon className="w-4 h-4 text-emerald-400" />
              GitHub Accounts ({githubAccounts.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {githubAccounts.map((acc, i) => {
              const isVerified = acc.confidence_category === "verified" || acc.is_confirmed === true;
              const isProbable = acc.confidence_category === "probable";
              const isCandidate = acc.confidence_category === "candidate" || (!isVerified && !isProbable);

              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-neutral-900/50 border border-neutral-800">
                  {acc.avatar_url ? (
                    <img src={acc.avatar_url} alt="" className="w-8 h-8 rounded-full mt-0.5" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center mt-0.5">
                      <GithubIcon className="w-4 h-4 text-neutral-500" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <a href={acc.profile_url || `https://github.com/${acc.login}`}
                        target="_blank" rel="noopener noreferrer"
                        className="text-sm font-medium text-indigo-400 hover:text-indigo-300 truncate">
                        {acc.login}
                      </a>
                      {isVerified && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                          Verified Match
                        </Badge>
                      )}
                      {isProbable && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-sky-400 border-sky-500/30 bg-sky-500/10">
                          Probable Match
                        </Badge>
                      )}
                      {isCandidate && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-amber-400 border-amber-500/30 bg-amber-500/10">
                          Candidate Lead (Unverified)
                        </Badge>
                      )}
                    </div>
                    {acc.evidence ? (
                      <p className="text-[11px] text-neutral-400 mt-1">{acc.evidence}</p>
                    ) : acc.confidence ? (
                      <p className="text-[10px] text-neutral-500 mt-0.5">{acc.confidence}</p>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* WHOIS / Domain Registration */}
      {whois.has_data && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-cyan-400" />
              Domain Registration
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {whois.registrant_name && (
              <p className="text-sm text-neutral-400">
                <span className="text-neutral-500">Registrant:</span> {whois.registrant_name}
              </p>
            )}
            {whois.registrant_org && (
              <p className="text-sm text-neutral-400">
                <span className="text-neutral-500">Organization:</span> {whois.registrant_org}
              </p>
            )}
            {whois.registrant_email && (
              <p className="text-sm text-neutral-400">
                <span className="text-neutral-500">Registrant Email:</span> {whois.registrant_email}
              </p>
            )}
            {whois.created_date && (
              <p className="text-sm text-neutral-400">
                <span className="text-neutral-500">Domain Created:</span> {whois.created_date}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Data Breaches */}
      {breaches.length > 0 && (
        <Card className="bg-black border-red-900/50">
          <CardHeader>
            <CardTitle className="text-sm text-red-400 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4" />
              Data Breaches Found ({breaches.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {breaches.map((b, i) => (
              <Alert key={i} className="bg-red-950/20 border-red-900/30 py-3">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <AlertTitle className="text-sm text-red-300">{b.name}</AlertTitle>
                <AlertDescription className="text-xs text-red-400/70">
                  {b.breach_date && <span>Date: {b.breach_date} | </span>}
                  {b.data_classes && b.data_classes.length > 0 && (
                    <span>Exposed: {b.data_classes.join(", ")}</span>
                  )}
                </AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Web Mentions */}
      {webMentions.length > 0 && (
        <Card className="bg-black border-neutral-800">
          <CardHeader>
            <CardTitle className="text-sm text-neutral-300 flex items-center gap-2">
              <LinkIcon className="w-4 h-4 text-indigo-400" />
              Web Mentions ({webMentions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {webMentions.map((wm, i) => (
              <div key={i} className="text-sm">
                {wm.url ? (
                  <a href={wm.url} target="_blank" rel="noopener noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
                    {wm.title || wm.url} <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                ) : (
                  <span className="text-neutral-400">{wm.title || "Web mention"}</span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Footer */}
      <p className="text-[10px] text-neutral-700 text-center pt-2">
        Identity intelligence from publicly available sources. Results may not be complete.
      </p>
    </div>
  );
}
