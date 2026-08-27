"use client";

import { useState, useEffect } from "react";

interface ScoreRingProps {
  score: number;
  label: string;
}

export default function ScoreRing({ score, label }: ScoreRingProps) {
  const [animated, setAnimated] = useState(0);
  const r = 54;
  const circ = 2 * Math.PI * r;

  useEffect(() => {
    let start: number | null = null;
    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / 1200, 1);
      setAnimated(Math.round(progress * score));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [score]);

  const color = score <= 40 ? "#ef4444" : score <= 70 ? "#f59e0b" : "#10b981";
  const dashOffset = circ - (animated / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-3 py-6">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#1f2937" strokeWidth="12" />
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circ}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.05s linear" }}
        />
      </svg>
      <div className="flex flex-col items-center -mt-[120px] mb-[80px] pointer-events-none select-none">
        <span className="text-4xl font-extrabold text-white">{animated}</span>
        <span className="text-xs text-neutral-500 font-mono">/100</span>
        <span className="text-[10px] uppercase tracking-widest text-neutral-600 mt-1">{label}</span>
      </div>
    </div>
  );
}
