import Link from "next/link";
import { Zap, GitBranch, X, PlayCircle } from "lucide-react";

export default function Footer() {
  return (
    <footer className="py-20 bg-black border-t border-neutral-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Zap className="w-6 h-6 text-indigo-500 fill-current" />
          <span className="text-2xl font-bold tracking-tighter">DevScout AI</span>
        </div>
        <div className="flex justify-center gap-8 mb-12">
          <Link href="#" className="text-neutral-500 hover:text-white">
            <GitBranch className="w-5 h-5" />
          </Link>
          <Link href="#" className="text-neutral-500 hover:text-white">
            <X className="w-5 h-5" />
          </Link>
          <Link href="#" className="text-neutral-500 hover:text-white">
            <PlayCircle className="w-5 h-5" />
          </Link>
        </div>
        <p className="text-neutral-600 text-sm">
          &copy; 2026 DevScout AI. Identity intelligence from publicly available sources.
        </p>
      </div>
    </footer>
  );
}
