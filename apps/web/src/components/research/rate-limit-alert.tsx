"use client";

import { useState, useEffect } from "react";
import { Clock } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface RateLimitAlertProps {
  onRetry: () => void;
}

export default function RateLimitAlert({ onRetry }: RateLimitAlertProps) {
  const [seconds, setSeconds] = useState(60);

  useEffect(() => {
    if (seconds <= 0) return;
    const id = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(id);
  }, [seconds]);

  return (
    <Alert className="bg-amber-950/30 border-amber-700 text-amber-400 py-6 flex flex-col items-center gap-3">
      <Clock className="w-10 h-10" />
      <div className="text-center">
        <AlertTitle className="text-base font-bold">⏳ Free Tier Rate Limit Hit</AlertTitle>
        <AlertDescription className="mt-2 text-amber-300/80">
          Wait about 60 seconds and try again.
          {seconds > 0 ? (
            <span className="block mt-2 font-mono text-2xl font-bold text-amber-400">
              {seconds}s
            </span>
          ) : (
            <Button
              onClick={onRetry}
              size="sm"
              className="mt-3 bg-amber-600 hover:bg-amber-700 text-black font-bold"
            >
              Try Again
            </Button>
          )}
        </AlertDescription>
      </div>
    </Alert>
  );
}
