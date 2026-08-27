"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  Zap,
  Bookmark,
  History,
  TrendingUp,
  Search,
  ExternalLink,
  Edit2,
  Trash2,
  Check,
  X,
  Clock,
  Building2,
  ShieldCheck,
  Cpu,
} from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { getHistory, updateReport, deleteJob, HistoryItem } from "@/lib/api";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import IconForType from "@/components/research/icon-for-type";

export default function DashboardPage() {
  const { user, workspace, stats, refreshAuth } = useAuth();
  const [jobs, setJobs] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  const loadDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      const historyData = await getHistory();
      setJobs(historyData);
      await refreshAuth();
    } catch (err) {
      console.error("Failed to load dashboard history:", err);
    } finally {
      setIsLoading(false);
    }
  }, [refreshAuth]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleToggleSave = async (job: HistoryItem) => {
    try {
      const nextSaved = !job.is_saved;
      await updateReport(job.job_id, { is_saved: nextSaved });
      setJobs((prev) =>
        prev.map((j) => (j.job_id === job.job_id ? { ...j, is_saved: nextSaved } : j))
      );
      refreshAuth();
    } catch (err) {
      console.error("Failed to toggle save status:", err);
    }
  };

  const handleStartRename = (job: HistoryItem) => {
    setEditingJobId(job.job_id);
    setEditTitle(job.custom_title || job.query);
  };

  const handleSaveRename = async (jobId: string) => {
    try {
      await updateReport(jobId, { custom_title: editTitle.trim() });
      setJobs((prev) =>
        prev.map((j) => (j.job_id === jobId ? { ...j, custom_title: editTitle.trim() } : j))
      );
      setEditingJobId(null);
    } catch (err) {
      console.error("Failed to rename report:", err);
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm("Are you sure you want to delete this research job?")) return;
    try {
      await deleteJob(jobId);
      setJobs((prev) => prev.filter((j) => j.job_id !== jobId));
      refreshAuth();
    } catch (err) {
      console.error("Failed to delete job:", err);
    }
  };

  const filteredJobs = jobs.filter(
    (j) =>
      (j.custom_title || j.query).toLowerCase().includes(searchFilter.toLowerCase()) ||
      j.research_type.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const creditsUsed = workspace?.credits_used || 0;
  const creditLimit = workspace?.monthly_credit_limit || 50;
  const creditsRemaining = Math.max(0, creditLimit - creditsUsed);
  const creditPercent = Math.min(100, Math.round((creditsUsed / creditLimit) * 100));

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0a] text-white">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 pt-28 pb-16">
        {/* Workspace Title & Intro */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="w-5 h-5 text-indigo-400" />
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                {workspace?.name || "Workspace Dashboard"}
              </h1>
              <Badge variant="outline" className="text-xs uppercase border-indigo-500/30 text-indigo-400">
                {workspace?.plan_tier || "Free"} Tier
              </Badge>
            </div>
            <p className="text-sm text-neutral-400">
              Welcome back, <span className="text-neutral-200 font-medium">{user?.name || "Developer"}</span>. Monitor research execution, saved reports, and API quota.
            </p>
          </div>

          <Link href="/">
            <Button className="bg-indigo-600 hover:bg-indigo-500 text-white gap-2 text-xs font-semibold shadow-lg shadow-indigo-600/20">
              <Zap className="w-4 h-4 fill-white" />
              New Research Query
            </Button>
          </Link>
        </div>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {/* Card 1: Total Jobs */}
          <Card className="bg-neutral-900/60 border-neutral-800">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center justify-between">
                Total Research Jobs
                <Cpu className="w-4 h-4 text-indigo-400" />
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold text-white">{jobs.length}</div>
              <p className="text-[11px] text-neutral-500 mt-1">Autonomous runs executed</p>
            </CardContent>
          </Card>

          {/* Card 2: Saved Reports */}
          <Card className="bg-neutral-900/60 border-neutral-800">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center justify-between">
                Saved & Starred
                <Bookmark className="w-4 h-4 text-emerald-400" />
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold text-emerald-400">
                {jobs.filter((j) => j.is_saved).length}
              </div>
              <p className="text-[11px] text-neutral-500 mt-1">
                <Link href="/saved" className="text-emerald-500 hover:underline">
                  View bookmarked reports &rarr;
                </Link>
              </p>
            </CardContent>
          </Card>

          {/* Card 3: Monthly Credits */}
          <Card className="bg-neutral-900/60 border-neutral-800">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center justify-between">
                Credits Remaining
                <Zap className="w-4 h-4 text-amber-400" />
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold text-white">
                {creditsRemaining}{" "}
                <span className="text-xs text-neutral-500 font-normal">/ {creditLimit}</span>
              </div>
              <div className="w-full bg-neutral-800 rounded-full h-1.5 mt-2 overflow-hidden">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${creditPercent}%` }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Multi-Tenant Plan */}
          <Card className="bg-neutral-900/60 border-neutral-800">
            <CardHeader className="p-4 pb-2">
              <CardTitle className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center justify-between">
                Current Plan
                <ShieldCheck className="w-4 h-4 text-sky-400" />
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="text-2xl font-bold text-sky-400 capitalize">
                {workspace?.plan_tier || "Free"}
              </div>
              <p className="text-[11px] text-neutral-500 mt-1">
                Ready for Stripe/billing upgrade
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Research Jobs Table & Management */}
        <Card className="bg-black border-neutral-800 overflow-hidden">
          <CardHeader className="p-4 sm:p-6 border-b border-neutral-800 bg-neutral-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-base font-semibold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                Workspace Research Jobs ({filteredJobs.length})
              </CardTitle>
              <p className="text-xs text-neutral-400 mt-0.5">
                Manage, rename, bookmark, and export intelligence reports.
              </p>
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-neutral-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search queries or titles..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full bg-neutral-900 border border-neutral-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-700"
              />
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-12 text-center text-xs text-neutral-500 font-mono">
                Loading workspace data...
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="p-12 text-center">
                <Cpu className="w-10 h-10 text-neutral-800 mx-auto mb-3" />
                <p className="text-sm font-medium text-neutral-400">No research jobs found</p>
                <p className="text-xs text-neutral-600 mt-1">
                  {searchFilter ? "Try a different search query." : "Run your first research query above."}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-neutral-800/80">
                {filteredJobs.map((job) => {
                  const isEditing = editingJobId === job.job_id;
                  const displayTitle = job.custom_title || job.query;

                  return (
                    <div
                      key={job.job_id}
                      className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-neutral-900/30 transition-colors"
                    >
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="w-8 h-8 rounded-md bg-neutral-900 border border-neutral-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <IconForType type={job.research_type} />
                        </div>

                        <div className="min-w-0 flex-1">
                          {isEditing ? (
                            <div className="flex items-center gap-1.5 max-w-md">
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                className="bg-black border border-indigo-500 rounded px-2 py-0.5 text-xs text-white focus:outline-none flex-1"
                                autoFocus
                              />
                              <Button
                                size="sm"
                                className="h-6 px-2 text-[10px] bg-indigo-600 hover:bg-indigo-500"
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
                            <div className="flex items-center gap-2">
                              <span className="text-xs sm:text-sm font-medium text-white truncate" title={displayTitle}>
                                {displayTitle}
                              </span>
                              {job.custom_title && (
                                <span className="text-[10px] text-neutral-500 font-mono truncate hidden md:inline">
                                  ({job.query})
                                </span>
                              )}
                            </div>
                          )}

                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant="outline" className="text-[10px] uppercase font-mono px-1.5 py-0 border-neutral-800 text-neutral-400">
                              {job.research_type}
                            </Badge>
                            <span className="text-[11px] text-neutral-500 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {new Date(job.created_at).toLocaleDateString([], {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                            <span
                              className={`text-[10px] font-mono capitalize px-1.5 py-0.5 rounded ${
                                job.status === "completed"
                                  ? "text-emerald-400 bg-emerald-950/40 border border-emerald-500/20"
                                  : "text-amber-400 bg-amber-950/40 border border-amber-500/20"
                              }`}
                            >
                              {job.status}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5 sm:self-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          className={`h-7 px-2 text-xs gap-1 ${
                            job.is_saved
                              ? "text-emerald-400 hover:text-emerald-300"
                              : "text-neutral-500 hover:text-white"
                          }`}
                          onClick={() => handleToggleSave(job)}
                          title={job.is_saved ? "Unsave Report" : "Save Report"}
                        >
                          <Bookmark className={`w-3.5 h-3.5 ${job.is_saved ? "fill-emerald-400" : ""}`} />
                          <span className="hidden sm:inline">{job.is_saved ? "Saved" : "Save"}</span>
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-neutral-500 hover:text-white"
                          onClick={() => handleStartRename(job)}
                          title="Rename Report"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-neutral-500 hover:text-red-400"
                          onClick={() => handleDelete(job.job_id)}
                          title="Delete Job"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      <Footer />
    </div>
  );
}
