"use client";

import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onDismiss: () => void;
}

export default function ErrorState({ message, onDismiss }: ErrorStateProps) {
  return (
    <Alert
      variant="destructive"
      className="bg-red-950/30 border-red-900 text-red-400 py-10 flex flex-col items-center gap-4"
    >
      <AlertCircle className="w-12 h-12" />
      <div className="text-center">
        <AlertTitle className="text-lg font-bold">Extraction Interrupted</AlertTitle>
        <AlertDescription className="mt-2">
          {message || "The agents were blocked or the source timed out. Please try a different target."}
        </AlertDescription>
      </div>
      <Button
        size="sm"
        variant="outline"
        className="border-red-700 text-red-400 hover:bg-red-950"
        onClick={onDismiss}
      >
        Dismiss
      </Button>
    </Alert>
  );
}
