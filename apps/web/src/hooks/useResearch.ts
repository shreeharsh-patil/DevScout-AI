"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startResearch as apiStartResearch, getJobStatus } from "@/lib/api";
import type { ResearchType, ResearchStatus, ResearchReport } from "@/types/research";
import { ApiError, ApiNetworkError, ApiTimeoutError } from "@/lib/api";

const MAX_POLLS = 30; // 30 × 2s = 60s timeout
const POLL_INTERVAL_MS = 2000;

interface UseResearchReturn {
  status: ResearchStatus;
  report: ResearchReport | null;
  errorMessage: string;
  startResearch: (query: string, type: ResearchType) => void;
  reset: () => void;
}

export function useResearch(): UseResearchReturn {
  const [status, setStatus] = useState<ResearchStatus>("idle");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearPoll();
    setStatus("idle");
    setReport(null);
    setErrorMessage("");
  }, [clearPoll]);

  const startResearch = useCallback(
    async (query: string, type: ResearchType) => {
      if (!query.trim()) return;

      clearPoll();

      // Scroll to dashboard
      document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" });

      setStatus("loading");
      setReport(null);
      setErrorMessage("");

      try {
        const { job_id } = await apiStartResearch({
          query: query.trim(),
          type,
          depth: "standard",
        });

        let pollCount = 0;

        pollRef.current = setInterval(async () => {
          pollCount++;

          if (pollCount >= MAX_POLLS) {
            clearPoll();
            setStatus("error");
            setErrorMessage("Request timed out after 60 seconds. Please try again.");
            return;
          }

          try {
            const statusData = await getJobStatus(job_id);

            if (statusData.status === "rate_limited") {
              clearPoll();
              setStatus("rate_limited");
              return;
            }

            if (statusData.status === "completed" || statusData.status === "failed") {
              clearPoll();
              if (statusData.status === "completed") {
                setStatus("success");
                setReport(statusData);
              } else {
                setStatus("error");
                setErrorMessage(
                  statusData.error || statusData.message || "The agents encountered an error."
                );
                setReport(statusData);
              }
            }
          } catch (pollErr) {
            // Network errors during polling — keep trying unless it's a 429
            if (pollErr instanceof ApiError && pollErr.status === 429) {
              clearPoll();
              setStatus("rate_limited");
            }
            console.error("Poll error:", pollErr);
          }
        }, POLL_INTERVAL_MS);
      } catch (e) {
        console.error(e);
        if (e instanceof ApiTimeoutError) {
          setStatus("error");
          setErrorMessage("Request timed out. The server took too long to respond.");
        } else if (e instanceof ApiNetworkError) {
          setStatus("error");
          setErrorMessage("Network error — could not reach the backend.");
        } else if (e instanceof ApiError) {
          setStatus("error");
          setErrorMessage(e.message || "An API error occurred.");
        } else {
          setStatus("error");
          setErrorMessage("An unexpected error occurred. Please try again.");
        }
      }
    },
    [clearPoll]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => clearPoll();
  }, [clearPoll]);

  return { status, report, errorMessage, startResearch, reset };
}
