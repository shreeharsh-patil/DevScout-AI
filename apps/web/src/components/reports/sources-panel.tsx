"use client";

import React, { useMemo, useState } from "react";
import {
  ExternalLink,
  ShieldCheck,
  Database,
  Globe,
  GitBranch,
  Package,
  PlayCircle,
  MessageSquare,
  TrendingUp,
  Search,
  Filter,
  X,
} from "lucide-react";
import type { ResearchSource } from "@/types/research";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { safeExternalUrl } from "@/lib/utils";

interface SourcesPanelProps {
  sources?: ResearchSource[];
}

function getPlatformIcon(platform: string) {
  const p = platform.toLowerCase();
  if (p === "github" || p === "gitlab") return <GitBranch className="w-3.5 h-3.5 text-neutral-300" />;
  if (p === "npm" || p === "pypi" || p === "crates") return <Package className="w-3.5 h-3.5 text-red-400" />;
  if (p === "youtube") return <PlayCircle className="w-3.5 h-3.5 text-rose-400" />;
  if (p === "reddit") return <MessageSquare className="w-3.5 h-3.5 text-orange-400" />;
  if (p === "hackernews") return <TrendingUp className="w-3.5 h-3.5 text-amber-400" />;
  if (p === "whois" || p === "gravatar" || p === "hibp" || p === "openpgp") {
    return <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
  }
  return <Globe className="w-3.5 h-3.5 text-sky-400" />;
}

function getPlatformColor(platform: string) {
  const p = platform.toLowerCase();
  if (p === "github") return "border-neutral-700 bg-neutral-800 text-neutral-200";
  if (p === "gitlab") return "border-amber-500/30 bg-amber-500/10 text-amber-400";
  if (p === "npm") return "border-red-500/30 bg-red-500/10 text-red-400";
  if (p === "pypi") return "border-blue-500/30 bg-blue-500/10 text-blue-400";
  if (p === "crates") return "border-orange-500/30 bg-orange-500/10 text-orange-400";
  if (p === "youtube") return "border-rose-500/30 bg-rose-500/10 text-rose-400";
  if (p === "reddit") return "border-orange-500/30 bg-orange-500/10 text-orange-400";
  if (p === "hackernews") return "border-amber-500/30 bg-amber-500/10 text-amber-400";
  if (p === "whois" || p === "gravatar" || p === "hibp" || p === "openpgp") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
  }
  return "border-sky-500/30 bg-sky-500/10 text-sky-400";
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("ALL");

  const platformOptions = useMemo(() => {
    if (!sources || sources.length === 0) return [];
    const set = new Set(sources.map((s) => s.platform.toLowerCase()));
    return ["ALL", ...Array.from(set)];
  }, [sources]);

  const filteredSources = useMemo(() => {
    if (!sources) return [];
    const q = searchQuery.toLowerCase().trim();

    return sources.filter((src) => {
      const matchPlatform =
        selectedPlatform === "ALL" || src.platform.toLowerCase() === selectedPlatform.toLowerCase();
      if (!matchPlatform) return false;

      if (!q) return true;

      const titleMatch = (src.title || "").toLowerCase().includes(q);
      const urlMatch = (src.url || "").toLowerCase().includes(q);
      const snippetMatch = (src.snippet || "").toLowerCase().includes(q);
      const idMatch = (src.source_id || "").toLowerCase().includes(q);
      const typeMatch = (src.source_type || "").toLowerCase().includes(q);

      return titleMatch || urlMatch || snippetMatch || idMatch || typeMatch;
    });
  }, [sources, searchQuery, selectedPlatform]);

  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Card className="bg-black border-neutral-800 mt-6 overflow-hidden">
      <CardHeader className="p-4 sm:p-5 border-b border-neutral-800/80 bg-neutral-900/40">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-400" />
              Searchable Research Sources ({sources.length})
            </CardTitle>
            <p className="text-xs text-neutral-400 mt-0.5">
              Verified citations, registry records, and public web occurrences.
            </p>
          </div>
          <Badge variant="outline" className="text-[10px] text-neutral-400 border-neutral-700 self-start sm:self-auto">
            Deduplicated Provenance
          </Badge>
        </div>

        {/* ── Search & Filter Controls ── */}
        <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
            <Input
              type="text"
              placeholder="Search sources by title, URL, snippet, or platform..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-8 py-1 text-xs bg-neutral-950 border-neutral-800 h-8 focus-visible:ring-indigo-500/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
            {platformOptions.map((plat) => (
              <button
                key={plat}
                onClick={() => setSelectedPlatform(plat)}
                className={`px-2.5 py-1 text-[11px] rounded-full uppercase tracking-wider font-mono transition-colors whitespace-nowrap ${
                  selectedPlatform === plat
                    ? "bg-indigo-600 text-white font-semibold"
                    : "bg-neutral-900 hover:bg-neutral-800 text-neutral-400 border border-neutral-800"
                }`}
              >
                {plat}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-3">
        {filteredSources.length === 0 ? (
          <div className="p-8 text-center bg-neutral-950/40 rounded-lg border border-neutral-800/60">
            <Filter className="w-6 h-6 text-neutral-600 mx-auto mb-2" />
            <p className="text-xs text-neutral-400 font-medium">No sources matched your query.</p>
            <button
              onClick={() => {
                setSearchQuery("");
                setSelectedPlatform("ALL");
              }}
              className="text-xs text-indigo-400 hover:text-indigo-300 mt-2 inline-block font-mono"
            >
              Reset search & filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredSources.map((src, index) => {
              const sid = src.source_id || String(index + 1);
              const safeUrl = safeExternalUrl(src.url);
              return (
                <div
                  key={`${sid}-${index}`}
                  className="flex flex-col justify-between p-3 rounded-lg bg-neutral-900/50 border border-neutral-800 hover:border-neutral-700 transition-colors"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-xs font-bold text-indigo-400">
                          [{sid}]
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 gap-1 capitalize ${getPlatformColor(src.platform)}`}
                        >
                          {getPlatformIcon(src.platform)}
                          {src.platform}
                        </Badge>
                      </div>
                      {src.source_type && (
                        <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-mono">
                          {src.source_type.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>

                    <h4 className="text-xs font-medium text-neutral-200 line-clamp-1" title={src.title}>
                      {src.title}
                    </h4>

                    {src.snippet && (
                      <p className="text-[11px] text-neutral-400 line-clamp-2 leading-relaxed bg-black/40 p-1.5 rounded border border-neutral-800/50">
                        {src.snippet}
                      </p>
                    )}
                  </div>

                  {safeUrl && (
                    <div className="mt-2 pt-2 border-t border-neutral-800/50 flex items-center justify-between">
                      <a
                        href={safeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 truncate max-w-[280px]"
                      >
                        <span className="truncate">{src.url.replace(/^https?:\/\//, "")}</span>
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      </a>
                      {src.retrieved_at && (
                        <span className="text-[9px] text-neutral-600 font-mono">
                          {new Date(src.retrieved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
