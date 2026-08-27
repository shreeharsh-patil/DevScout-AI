import React from "react";
import {
  GitBranch,
  Globe,
  Mail,
  PlayCircle,
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Package,
} from "lucide-react";const ICONS: Record<string, React.ReactNode> = {
  developer: <GitBranch className="w-4 h-4" />,
  startup: <Globe className="w-4 h-4" />,
  email: <Mail className="w-4 h-4" />,
  youtube: <PlayCircle className="w-4 h-4" />,
  reddit: <MessageSquare className="w-4 h-4" />,
  idea: <ShieldCheck className="w-4 h-4" />,
  social: <TrendingUp className="w-4 h-4" />,
  linkedin: (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  ),
  npm: <Package className="w-4 h-4" />,
  hackernews: <TrendingUp className="w-4 h-4" />,
  "github-repo": <GitBranch className="w-4 h-4" />,
};

interface IconForTypeProps {
  type: string;
  className?: string;
}

export default function IconForType({ type, className }: IconForTypeProps) {
  const icon = ICONS[type];
  if (!icon) return null;
  if (className && React.isValidElement(icon)) {
    return React.cloneElement(icon as React.ReactElement<{ className?: string }>, { className });
  }
  return <>{icon}</>;
}
