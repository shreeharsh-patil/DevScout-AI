"use client";

import { Card, CardContent } from "@/components/ui/card";

interface ResearchProgressProps {
  label: string;
}

export default function ResearchProgress({ label }: ResearchProgressProps) {
  return (
    <Card className="bg-neutral-900/20 border-neutral-800 border-dashed min-h-[400px] flex items-center justify-center">
      <CardContent className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full" />
          <div className="absolute top-0 w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <div className="text-center">
          <p className="text-lg font-medium text-neutral-300">Agents are in the field</p>
          <p className="text-sm text-neutral-500 mt-1">
            Running <span className="text-indigo-400 font-semibold">{label}</span> pipeline...
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
