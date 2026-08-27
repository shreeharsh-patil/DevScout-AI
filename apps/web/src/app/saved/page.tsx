"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Bookmark,
  Search,
  ExternalLink,
  Edit2,
  Trash2,
  Check,
  X,
  Clock,
  Download,
  Building2,
  FileText,
} from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { getSavedReports, updateReport, deleteJob, getReport, HistoryItem } from "@/lib/api";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import IconForType from "@/components/research/icon-for-type";

export default function SavedReportsPage() {
  const { workspace, refreshAuth } = useAuth();
  const [savedJobs, setSavedJobs] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  const loadSavedReports = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getSavedReports();
      setSavedJobs(data);
    } catch (err) {
      console.error("Failed to load saved reports:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSavedReports();
  }, [loadSavedReports]);

  const handleUnsave = async (jobId: string) => {
    try {
      await updateReport(jobId, { is_saved: false });
      setSavedJobs((prev) => prev.filter((j) => j.job_id !== jobId));
      refreshAuth();
    } catch (err) {
      console.error("Failed to unsave report:", err);
    }
  };

  const handleStartRename = (job: HistoryItem) => {
    setEditingJobId(job.job_id);
    setEditTitle(job.custom_title || job.query);
  };

  const handleSaveRename = async (jobId: string) => {
    try {
      await updateReport(jobId, { custom_title: editTitle.trim() });
      setSavedJobs((prev) =>
        prev.map((j) => (j.job_id === jobId ? { ...j, custom_title: editTitle.trim() } : j))
      );
      setEditingJobId(null);
    } catch (err) {
      console.error("Failed to rename report:", err);
    }
  };

  const handleDownload = async (jobId: string, title: string, type: string) => {
    try {
      const rep = await getReport(jobId);
      const md = rep.report_markdown || `# ${title}\n`;
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `devscout-${type}-${title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download report:", err);
    }
  };

  const filtered = savedJobs.filter(
    (j) =>
      (j.custom_title || j.query).toLowerCase().includes(searchFilter.toLowerCase()) ||
      j.research_type.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0a] text-white">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-28 pb-16">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Bookmark className="w-5 h-5 text-emerald-400 fill-emerald-400" />
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                Saved Reports
              </h1>
              <Badge variant="outline" className="text-xs border-emerald-500/30 text-emerald-400">
                {savedJobs.length} Bookmarked
              </Badge>
            </div>
            <p className="text-sm text-neutral-400">
              Curated and bookmarked research reports in{" "}
              <span className="text-neutral-200 font-medium">{workspace?.name || "Workspace"}</span>.
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter saved reports..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-neutral-900 border border-neutral-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-700"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-16 text-center text-xs text-neutral-500 font-mono">
            Loading saved reports...
          </div>
        ) : filtered.length === 0 ? (
          <Card className="bg-neutral-900/30 border-neutral-800 border-dashed p-12 text-center">
            <Bookmark className="w-10 h-10 text-neutral-800 mx-auto mb-3" />
            <p className="text-sm font-medium text-neutral-400">No saved reports yet</p>
            <p className="text-xs text-neutral-600 mt-1">
              Star or bookmark reports from the main research console or dashboard.
            </p>
            <Link href="/" className="inline-block mt-4">
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-500 text-xs">
                Start New Research
              </Button>
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((job) => {
              const isEditing = editingJobId === job.job_id;
              const displayTitle = job.custom_title || job.query;

              return (
                <Card
                  key={job.job_id}
                  className="bg-neutral-900/40 border-neutral-800 hover:border-neutral-700 transition-colors flex flex-col justify-between"
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded bg-neutral-800 border border-neutral-700 flex items-center justify-center">
                          <IconForType type={job.research_type} />
                        </div>
                        <Badge variant="outline" className="text-[10px] uppercase font-mono border-neutral-800 text-neutral-400">
                          {job.research_type}
                        </Badge>
                      </div>

                      <button
                        onClick={() => handleUnsave(job.job_id)}
                        className="text-emerald-400 hover:text-neutral-500 transition-colors p-1"
                        title="Remove from saved"
                      >
                        <Bookmark className="w-4 h-4 fill-emerald-400" />
                      </button>
                    </div>

                    {isEditing ? (
                      <div className="flex items-center gap-1 mt-1">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="bg-black border border-indigo-500 rounded px-2 py-1 text-xs text-white focus:outline-none flex-1"
                          autoFocus
                        />
                        <Button
                          size="sm"
                          className="h-6 px-2 text-[10px] bg-indigo-600"
                          onClick={() => handleSaveRename(job.job_id)}
                        >
                          <Check className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-[10px] text-neutral-400"
                          onClick={() => setEditingJobId(null)}
                        >
                          <X className="w-3 h-3" />
                        </Button>
                      </div>
                    ) : (
                      <div>
                        <CardTitle className="text-sm font-semibold text-white line-clamp-1" title={displayTitle}>
                          {displayTitle}
                        </CardTitle>
                        {job.custom_title && (
                          <p className="text-[11px] text-neutral-500 font-mono truncate mt-0.5">
                            {job.query}
                          </p>
                        )}
                      </div>
                    )}
                  </CardHeader>

                  <CardContent className="p-4 pt-2">
                    <div className="flex items-center justify-between text-[11px] text-neutral-500 pt-3 border-t border-neutral-800/60 mt-2">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3" />
                        {new Date(job.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}
                      </span>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleStartRename(job)}
                          className="p-1 text-neutral-500 hover:text-white transition-colors"
                          title="Rename"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDownload(job.job_id, displayTitle, job.research_type)}
                          className="p-1 text-neutral-500 hover:text-white transition-colors"
                          title="Download Markdown"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
