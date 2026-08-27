/**
 * Parse a numeric score (0-100) from a markdown report.
 * Looks for patterns like "## Developer Score: 85 / 100" or "Score: 85/100".
 */
export function parseScore(markdown: string): number | null {
  const match = markdown.match(
    /##\s+(?:Developer|Idea Viability)\s+Score:\s*(\d+)\s*\/\s*100/i
  );
  if (match) return parseInt(match[1], 10);
  const loose = markdown.match(/Score:\s*(\d+)\s*\/\s*100/i);
  if (loose) return parseInt(loose[1], 10);
  return null;
}

/**
 * Trigger a browser download of a markdown string as a .md file.
 */
export function downloadMarkdown(content: string, type: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `devscout-report-${type}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Format an ISO date string to a human-readable format.
 */
export function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Format an ISO date string as a relative time ("3m ago", "1h ago", etc.).
 */
export function formatRelative(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    const hrs = Math.floor(mins / 60);
    const days = Math.floor(hrs / 24);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    if (hrs < 24) return `${hrs}h ago`;
    return `${days}d ago`;
  } catch {
    return iso;
  }
}
