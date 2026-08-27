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
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const runIdRef = useRef(0);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
    abortRef.current?.abort();
    abortRef.current = null;
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
      const runId = ++runIdRef.current;
      const controller = new AbortController();
      abortRef.current = controller;

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
        }, controller.signal);

        let pollCount = 0;

        const poll = async () => {
          if (runId !== runIdRef.current || controller.signal.aborted) return;
          pollCount++;

          if (pollCount >= MAX_POLLS) {
            clearPoll();
            setStatus("error");
            setErrorMessage("Request timed out after 60 seconds. Please try again.");
            return;
          }

          try {
            const statusData = await getJobStatus(job_id, controller.signal);
            if (runId !== runIdRef.current) return;

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
            if (!(pollErr instanceof DOMException && pollErr.name === "AbortError")) {
              console.error("Poll error:", pollErr);
            }
          }
          if (runId === runIdRef.current && !controller.signal.aborted && pollRef.current !== null) {
            pollRef.current = setTimeout(poll, POLL_INTERVAL_MS);
          }
        };
        pollRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (e) {
        if (runId !== runIdRef.current || (e instanceof DOMException && e.name === "AbortError")) return;
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
    return () => {
      clearPoll();
    };
  }, [clearPoll]);

  return { status, report, errorMessage, startResearch, reset };
}
