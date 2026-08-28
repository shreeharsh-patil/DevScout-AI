"use client";

import React from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ResearchProgressProps {
  label?: string;
  stage?: string;
  progress?: number;
  researchType?: string;
}

const EMAIL_STAGES = [
  { key: "validating_email", label: "Email syntax & MX routing validated" },
  { key: "checking_developer_sources", label: "Public developer registries & accounts queried" },
  { key: "searching_public_web", label: "Public web citations & mentions searched" },
  { key: "processing_account_findings", label: "Account findings & false positives calibrated" },
  { key: "correlating_identities", label: "Cross-platform identity clusters correlated" },
  { key: "scoring_evidence", label: "Deterministic confidence & evidence graph computed" },
  { key: "building_report", label: "Evidence-backed intelligence report generated" },
];

export default function ResearchProgress({
  label = "Research",
  stage = "researching",
  progress = 0,
  researchType,
}: ResearchProgressProps) {
  const isEmailIntel =
    researchType === "email_intelligence" ||
    researchType === "email" ||
    label.toLowerCase().includes("email");

  // Determine stage progress for email
  const currentStageIndex = EMAIL_STAGES.findIndex((s) => s.key === stage);
  const activeIdx = currentStageIndex >= 0 ? currentStageIndex : 0;

  return (
    <Card className="bg-neutral-900/30 border-neutral-800 border-dashed min-h-[380px] flex items-center justify-center p-6">
      <CardContent className="flex flex-col items-center gap-6 max-w-md w-full">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full" />
          <div className="absolute top-0 w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>

        <div className="text-center space-y-1">
          <p className="text-base font-semibold text-neutral-200">
            Agents executing autonomous research
          </p>
          <p className="text-xs text-neutral-500">
            Pipeline: <span className="text-indigo-400 font-medium capitalize">{label}</span>
          </p>
        </div>

        {/* Visual Progress Bar */}
        {progress > 0 && (
          <div className="w-full space-y-1.5 pt-1">
            <div className="flex justify-between text-xs text-neutral-400">
              <span>Overall Progress</span>
              <span className="font-mono text-indigo-400 font-semibold">{progress}%</span>
            </div>
            <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              />
            </div>
          </div>
        )}

        {/* Real Stage Tracker for Email Intelligence */}
        {isEmailIntel && (
          <div className="w-full space-y-2 pt-2 border-t border-neutral-800/80">
            {EMAIL_STAGES.map((s, idx) => {
              const isPassed = idx < activeIdx;
              const isCurrent = idx === activeIdx;

              return (
                <div
                  key={s.key}
                  className={`flex items-center gap-2.5 text-xs transition-all ${
                    isPassed
                      ? "text-emerald-400 font-medium"
                      : isCurrent
                      ? "text-indigo-300 font-semibold"
                      : "text-neutral-600"
                  }`}
                >
                  {isPassed ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin flex-shrink-0" />
                  ) : (
                    <Circle className="w-3.5 h-3.5 text-neutral-700 flex-shrink-0" />
                  )}
                  <span>{s.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
