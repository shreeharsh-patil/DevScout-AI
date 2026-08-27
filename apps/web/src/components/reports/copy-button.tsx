"use client";

import { useState } from "react";
import { Copy, ClipboardCheck } from "lucide-react";

interface CopyButtonProps {
  text: string;
}

export default function CopyButton({ text }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be unavailable
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-white border border-neutral-700 hover:border-neutral-500 rounded px-2 py-1 transition-all"
      title="Copy report to clipboard"
    >
      {copied ? (
        <>
          <ClipboardCheck className="w-3 h-3 text-emerald-400" />copied
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />copy
        </>
      )}
    </button>
  );
}
