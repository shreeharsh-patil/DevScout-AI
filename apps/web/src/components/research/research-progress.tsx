"use client";

import React from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ResearchProgressProps {
  label?: string;
  stage?: string;
  researchType?: string;
}

const EMAIL_STAGES = [
  { key: "validating_email", label: "Email syntax & domain validated" },
  { key: "discovering_accounts", label: "Public accounts & Gravatar checked" },
  { key: "searching_developer_sources", label: "GitHub & package registries queried" },
  { key: "searching_web", label: "Public web mentions retrieved" },
  { key: "checking_breaches", label: "Security & breach exposure audited" },
  { key: "correlating_identity", label: "Identity & candidate handles correlated" },
  { key: "generating_report", label: "Evidence-backed report generated" },
];

export default function ResearchProgress({ label = "Research", stage = "researching", researchType }: ResearchProgressProps) {
  const isEmailIntel = researchType === "email_intelligence" || researchType === "email" || label.toLowerCase().includes("email");

  // Determine stage progress for email
  const currentStageIndex = EMAIL_STAGES.findIndex((s) => s.key === stage);
  const activeIdx = currentStageIndex >= 0 ? currentStageIndex : 1;

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
