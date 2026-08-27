"use client";

import { useState, useEffect } from "react";

const PLACEHOLDERS = [
  "vercel/next.js",
  "someone@gmail.com",
  "john.doe@company.com",
  "sarah@startup.io",
  "github.com/torvalds",
  "stripe.com",
  "youtu.be/dQw4w9WgXcQ",
  "AI meeting notes app",
  "linkedin.com/in/satyanadella",
  "contact@organization.org",
  "dev@example.com",
];

/**
 * Cycles through placeholder strings at 3-second intervals.
 * Only cycles when `active` is true (typically when the input is empty).
 */
export function useCyclingPlaceholder(active: boolean): string {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setIdx((i) => (i + 1) % PLACEHOLDERS.length), 3000);
    return () => clearInterval(id);
  }, [active]);

  return PLACEHOLDERS[idx];
}
