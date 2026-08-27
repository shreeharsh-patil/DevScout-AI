"use client";

import React, { useState } from "react";
import {
  Mail,
  ArrowRight,
  Download,
  RefreshCw,
} from "lucide-react";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useResearch } from "@/hooks/useResearch";
import EmailIntelligenceView from "@/components/email/email-intelligence-view";
import ResearchProgress from "@/components/research/research-progress";
import MarkdownReport from "@/components/reports/markdown-report";
import { downloadMarkdown } from "@/lib/report-utils";

const EXAMPLES = [
  "torvalds@linux-foundation.org",
  "dan.abramov@gmail.com",
  "contact@stripe.com",
  "founder@ycombinator.com",
];

export default function EmailIntelligencePage() {
  const [emailInput, setEmailInput] = useState("");
  const [viewMode, setViewMode] = useState<"interactive" | "markdown">("interactive");
  const { status, report, errorMessage, startResearch } = useResearch();

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!emailInput.trim()) return;
    startResearch(emailInput.trim(), "email_intelligence");
  };

  const handleSelectExample = (ex: string) => {
    setEmailInput(ex);
    startResearch(ex, "email_intelligence");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#050505] text-white">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-28 pb-16">
        {/* Header Hero */}
        <div className="text-center max-w-3xl mx-auto mb-10 space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs font-mono text-amber-400">
            <Mail className="w-3.5 h-3.5" />
            <span>Autonomous Identity & Developer OSINT</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white">
            Email Intelligence Engine
          </h1>

          <p className="text-sm sm:text-base text-neutral-400 max-w-2xl mx-auto">
            Discovers public GitHub commit metadata, Gravatar profiles, package registries, web citations, and high-level breach exposures with deterministic confidence scoring.
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-2xl mx-auto mb-8">
          <form onSubmit={handleSearch} className="relative flex items-center">
            <div className="absolute left-4 text-neutral-500">
              <Mail className="w-5 h-5" />
            </div>

            <input
              type="email"
              aria-label="Email address to investigate"
              autoComplete="email"
              placeholder="Enter email address (e.g. developer@company.com)..."
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              className="w-full bg-neutral-900/80 border border-neutral-800 rounded-xl pl-12 pr-32 py-4 text-sm text-white placeholder-neutral-500 focus:outline-none focus:border-indigo-500 shadow-xl transition-all"
            />

            <div className="absolute right-2 flex items-center gap-2">
              <Button
                type="submit"
                disabled={status === "loading" || !emailInput.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 h-auto rounded-lg shadow-lg shadow-indigo-600/30 gap-1.5"
              >
                {status === "loading" ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Investigating...
                  </>
                ) : (
                  <>
                    Investigate
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </Button>
            </div>
          </form>

          {/* Example query chips */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-4 text-xs text-neutral-500">
            <span>Try example:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => handleSelectExample(ex)}
                className="font-mono text-[11px] text-neutral-400 hover:text-white bg-neutral-900 border border-neutral-800 hover:border-neutral-700 px-2 py-0.5 rounded transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Execution & Progress Section */}
        {status === "loading" && (
          <div className="max-w-xl mx-auto my-12">
            <ResearchProgress
              stage={report?.stage || "researching"}
              researchType="email_intelligence"
            />
          </div>
        )}

        {/* Error Alert */}
        {status === "error" && (
          <Card className="max-w-2xl mx-auto bg-red-950/20 border-red-500/30 p-6 text-center text-xs text-red-300">
            <p className="font-semibold text-sm mb-1">Investigation Error</p>
            <p>{errorMessage || "Failed to complete email intelligence investigation."}</p>
          </Card>
        )}

        {/* Successful Report View */}
        {status === "success" && report && (
          <div className="space-y-4">
            {/* View Mode Switcher Toolbar */}
            <div className="flex items-center justify-between bg-neutral-900/60 border border-neutral-800 rounded-lg p-2 px-4">
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === "interactive" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("interactive")}
                  className={`text-xs h-7 px-3 ${viewMode === "interactive" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
                >
                  Interactive Visualizer
                </Button>
                <Button
                  variant={viewMode === "markdown" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("markdown")}
                  className={`text-xs h-7 px-3 ${viewMode === "markdown" ? "bg-indigo-600 text-white" : "text-neutral-400"}`}
                >
                  Markdown View
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs border-neutral-700 bg-neutral-900 text-neutral-300 hover:text-white gap-1"
                  onClick={() => downloadMarkdown(report.report || "", "email_intelligence")}
                >
                  <Download className="w-3.5 h-3.5" />
                  Download .md
                </Button>
              </div>
            </div>

            {/* Display Interactive vs Markdown */}
            {viewMode === "interactive" ? (
              <EmailIntelligenceView report={report} />
            ) : (
              <Card className="bg-black border-neutral-800 p-6 sm:p-8">
                <MarkdownReport content={report.report || ""} />
              </Card>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
