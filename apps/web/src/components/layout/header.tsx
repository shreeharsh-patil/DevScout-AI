"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Zap, History } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Header() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        scrolled
          ? "bg-black/80 backdrop-blur-md border-b border-neutral-800 py-3"
          : "bg-transparent py-6"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-emerald-500 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white fill-current" />
          </div>
          <h1 className="text-xl font-bold tracking-tighter">DevScout AI</h1>
        </div>
        <nav className="hidden md:flex items-center gap-8">
          <a
            href="#features"
            className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
          >
            Features
          </a>
          <a
            href="#dashboard"
            className="text-sm font-medium text-neutral-400 hover:text-white transition-colors"
          >
            Console
          </a>
          <Link
            href="/history"
            className="text-sm font-medium text-neutral-400 hover:text-white transition-colors flex items-center gap-1.5"
          >
            <History className="w-4 h-4" />
            History
          </Link>
          <Button
            variant="outline"
            className="border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-white"
            onClick={() =>
              document.getElementById("dashboard")?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Launch Console
          </Button>
        </nav>
      </div>
    </header>
  );
}
