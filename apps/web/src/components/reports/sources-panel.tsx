"use client";

import React from "react";
import { ExternalLink, ShieldCheck, Database, Globe, GitBranch, Package, PlayCircle, MessageSquare, TrendingUp } from "lucide-react";
import type { ResearchSource } from "@/types/research";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface SourcesPanelProps {
  sources?: ResearchSource[];
}

function getPlatformIcon(platform: string) {
  const p = platform.toLowerCase();
  if (p === "github") return <GitBranch className="w-3.5 h-3.5 text-neutral-300" />;
  if (p === "npm") return <Package className="w-3.5 h-3.5 text-red-400" />;
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
  if (p === "npm") return "border-red-500/30 bg-red-500/10 text-red-400";
  if (p === "youtube") return "border-rose-500/30 bg-rose-500/10 text-rose-400";
  if (p === "reddit") return "border-orange-500/30 bg-orange-500/10 text-orange-400";
  if (p === "hackernews") return "border-amber-500/30 bg-amber-500/10 text-amber-400";
  if (p === "whois" || p === "gravatar" || p === "hibp" || p === "openpgp") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
  }
  return "border-sky-500/30 bg-sky-500/10 text-sky-400";
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <Card className="bg-black border-neutral-800 mt-6 overflow-hidden">
      <CardHeader className="p-4 sm:p-5 border-b border-neutral-800/80 bg-neutral-900/40">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-400" />
            Verified Research Sources ({sources.length})
          </CardTitle>
          <Badge variant="outline" className="text-[10px] text-neutral-400 border-neutral-700">
            Deduplicated Provenance
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4 sm:p-5 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sources.map((src, index) => {
            const sid = src.source_id || String(index + 1);
            return (
              <div
                key={sid}
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

                {src.url && (
                  <div className="mt-2 pt-2 border-t border-neutral-800/50 flex items-center justify-between">
                    <a
                      href={src.url}
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
      </CardContent>
    </Card>
  );
}
