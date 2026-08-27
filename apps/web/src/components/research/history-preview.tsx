"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  GitBranch,
  Globe,
  Mail,
  PlayCircle,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Package,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { getHistory } from "@/lib/api";

interface RecentJob {
  job_id: string;
  query: string;
  research_type: string;
  status: string;
}

const TYPE_ICON_MAP: Record<string, React.ReactNode> = {
  developer: <GitBranch className="w-3 h-3" />,
  startup: <Globe className="w-3 h-3" />,
  email: <Mail className="w-3 h-3" />,
  youtube: <PlayCircle className="w-3 h-3" />,
  reddit: <MessageSquare className="w-3 h-3" />,
  idea: <ShieldCheck className="w-3 h-3" />,
  social: <TrendingUp className="w-3 h-3" />,
  npm: <Package className="w-3 h-3" />,
};

interface HistoryPreviewProps {
  onSelect: (query: string) => void;
}

export default function HistoryPreview({ onSelect }: HistoryPreviewProps) {
  const [jobs, setJobs] = useState<RecentJob[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getHistory()
      .then((data) => {
        const arr = Array.isArray(data) ? data : [];
        setJobs(arr.slice(0, 5));
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, []);

  if (!loaded || jobs.length === 0) return null;

  return (
    <Card className="bg-black border-neutral-800">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] uppercase tracking-widest text-neutral-600">
            Recent Scans
          </span>
          <Link
            href="/history"
            className="text-[10px] text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"
          >
            View all
          </Link>
        </div>
        <div className="space-y-2">
          {jobs.map((job) => (
            <button
              key={job.job_id}
              onClick={() => onSelect(job.query)}
              className="w-full flex items-center gap-2 text-left hover:bg-neutral-900/60 rounded-lg px-2 py-1.5 transition-all group"
            >
              <span className="text-neutral-600 group-hover:text-neutral-400 transition-colors shrink-0">
                {TYPE_ICON_MAP[job.research_type] ?? <FileText className="w-3 h-3" />}
              </span>
              <span className="text-xs text-neutral-400 group-hover:text-white transition-colors truncate flex-1">
                {job.query}
              </span>
              {job.status === "completed" && (
                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-500 shrink-0" />
              )}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
