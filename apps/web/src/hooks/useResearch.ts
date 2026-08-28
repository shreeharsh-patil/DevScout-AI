"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startResearch as apiStartResearch, getJobStatus } from "@/lib/api";
import type { ResearchType, ResearchStatus, ResearchReport, ResearchDepth } from "@/types/research";
import { ApiError, ApiNetworkError, ApiTimeoutError } from "@/lib/api";

const MAX_POLLS = 90; // 90 × 2s = 180s total timeout
const POLL_INTERVAL_MS = 2000;

interface UseResearchReturn {
  status: ResearchStatus;
  report: ResearchReport | null;
  stage: string;
  progress: number;
  errorMessage: string;
  startResearch: (query: string, type: ResearchType, depth?: ResearchDepth) => void;
  reset: () => void;
}

export function useResearch(): UseResearchReturn {
  const [status, setStatus] = useState<ResearchStatus>("idle");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [stage, setStage] = useState<string>("queued");
  const [progress, setProgress] = useState<number>(0);
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
    setStage("queued");
    setProgress(0);
    setErrorMessage("");
  }, [clearPoll]);

  const startResearch = useCallback(
    async (query: string, type: ResearchType, depth: ResearchDepth = "standard") => {
      if (!query.trim()) return;

      clearPoll();
      const runId = ++runIdRef.current;
      const controller = new AbortController();
      abortRef.current = controller;

      // Scroll to dashboard
      document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" });

      setStatus("loading");
      setReport(null);
      setStage("queued");
      setProgress(5);
      setErrorMessage("");

      try {
        const { job_id } = await apiStartResearch({
          query: query.trim(),
          type,
          depth,
        }, controller.signal);

        let pollCount = 0;

        const poll = async () => {
          if (runId !== runIdRef.current || controller.signal.aborted) return;
          pollCount++;

          if (pollCount >= MAX_POLLS) {
            clearPoll();
            setStatus("error");
            setErrorMessage("Research is taking longer than expected. You can revisit this report from History at any time.");
            return;
          }

          try {
            const statusData = await getJobStatus(job_id, controller.signal);
            if (runId !== runIdRef.current) return;

            if (statusData.stage) {
              setStage(statusData.stage);
            }
            if (typeof statusData.progress === "number") {
              setProgress(statusData.progress);
            }

            // Keep live intermediate report state
            setReport(statusData);

            if (statusData.status === "rate_limited") {
              clearPoll();
              setStatus("rate_limited");
              return;
            }

            if (statusData.status === "completed" || statusData.status === "failed") {
              clearPoll();
              if (statusData.status === "completed") {
                setStatus("success");
                setProgress(100);
                setReport(statusData);
              } else {
                setStatus("error");
                setErrorMessage(
                  statusData.error || statusData.message || "The agents encountered an error."
                );
                setReport(statusData);
              }
              return;
            }
          } catch (pollErr) {
            // Network errors during polling — keep trying unless it's a 429
            if (pollErr instanceof ApiError && pollErr.status === 429) {
              clearPoll();
              setStatus("rate_limited");
              return;
            }
            if (!(pollErr instanceof DOMException && pollErr.name === "AbortError")) {
              console.error("Poll error:", pollErr);
            }
          }
          if (runId === runIdRef.current && !controller.signal.aborted) {
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

  return { status, report, stage, progress, errorMessage, startResearch, reset };
}
