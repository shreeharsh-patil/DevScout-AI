"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Zap,
  History,
  Bookmark,
  LayoutDashboard,
  Building2,
  Plus,
  Check,
  ChevronDown,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { Button } from "@/components/ui/button";

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [showWsMenu, setShowWsMenu] = useState(false);
  const [isCreatingWs, setIsCreatingWs] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const pathname = usePathname();

  const {
    user,
    workspace,
    workspaces,
    switchWorkspace,
    createNewWorkspace,
  } = useAuth();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleCreateWs = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    await createNewWorkspace(newWsName.trim());
    setNewWsName("");
    setIsCreatingWs(false);
    setShowWsMenu(false);
  };

  const remainingCredits = workspace
    ? Math.max(0, workspace.monthly_credit_limit - workspace.credits_used)
    : 50;

  return (
    <header
      className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        scrolled || pathname !== "/"
          ? "bg-black/90 backdrop-blur-md border-b border-neutral-800 py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex justify-between items-center gap-4">
        {/* Brand & Workspace Switcher */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-emerald-500 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Zap className="w-5 h-5 text-white fill-current" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white hidden sm:inline">
              DevScout <span className="text-indigo-400">AI</span>
            </span>
          </Link>

          {/* Workspace Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowWsMenu(!showWsMenu)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-800 hover:border-neutral-700 text-xs font-medium text-neutral-300 transition-colors"
            >
              <Building2 className="w-3.5 h-3.5 text-indigo-400" />
              <span className="max-w-[120px] truncate">
                {workspace?.name || "Personal Workspace"}
              </span>
              <ChevronDown className="w-3 h-3 text-neutral-500" />
            </button>

            {showWsMenu && (
              <div
                className="absolute left-0 mt-2 w-56 rounded-lg bg-neutral-900 border border-neutral-800 shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100"
                onMouseLeave={() => setShowWsMenu(false)}
              >
                <div className="px-3 py-1.5 border-b border-neutral-800 text-[10px] uppercase font-mono text-neutral-500 tracking-wider">
                  Workspaces
                </div>
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      switchWorkspace(ws.id);
                      setShowWsMenu(false);
                    }}
                    className="w-full text-left px-3 py-2 text-xs flex items-center justify-between text-neutral-300 hover:bg-neutral-800/60 transition-colors"
                  >
                    <span className="truncate">{ws.name}</span>
                    {workspace?.id === ws.id && (
                      <Check className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                    )}
                  </button>
                ))}

                <div className="border-t border-neutral-800 p-2">
                  {isCreatingWs ? (
                    <form onSubmit={handleCreateWs} className="space-y-1.5">
                      <input
                        type="text"
                        placeholder="Workspace name..."
                        value={newWsName}
                        onChange={(e) => setNewWsName(e.target.value)}
                        className="w-full bg-black border border-neutral-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                        autoFocus
                      />
                      <div className="flex gap-1">
                        <Button type="submit" size="sm" className="h-6 text-[10px] flex-1 bg-indigo-600 hover:bg-indigo-500">
                          Create
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-6 text-[10px] text-neutral-400"
                          onClick={() => setIsCreatingWs(false)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </form>
                  ) : (
                    <button
                      onClick={() => setIsCreatingWs(true)}
                      className="w-full flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium py-1 px-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      New Workspace
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-2 sm:gap-6">
          <Link
            href="/"
            className={`text-xs sm:text-sm font-medium transition-colors ${
              pathname === "/" ? "text-white font-semibold" : "text-neutral-400 hover:text-white"
            }`}
          >
            Research
          </Link>
          <Link
            href="/dashboard"
            className={`text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
              pathname === "/dashboard" ? "text-white font-semibold" : "text-neutral-400 hover:text-white"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            Dashboard
          </Link>
          <Link
            href="/saved"
            className={`text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
              pathname === "/saved" ? "text-white font-semibold" : "text-neutral-400 hover:text-white"
            }`}
          >
            <Bookmark className="w-3.5 h-3.5 text-emerald-400" />
            Saved
          </Link>
          <Link
            href="/history"
            className={`text-xs sm:text-sm font-medium transition-colors flex items-center gap-1.5 ${
              pathname === "/history" ? "text-white font-semibold" : "text-neutral-400 hover:text-white"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            History
          </Link>

          {/* Credits pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-950/40 border border-indigo-500/30 text-[11px] font-mono text-indigo-300">
            <Zap className="w-3 h-3 text-indigo-400 fill-indigo-400" />
            <span>{remainingCredits} / {workspace?.monthly_credit_limit || 50}</span>
            <span className="text-[9px] uppercase tracking-wider text-indigo-400 font-bold ml-0.5">
              {workspace?.plan_tier || "FREE"}
            </span>
          </div>

          {/* User profile avatar pill */}
          <div className="flex items-center gap-2 pl-2 border-l border-neutral-800">
            <div className="w-7 h-7 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center text-xs font-semibold text-neutral-300" title={user?.email || "Demo User"}>
              {user?.name ? user.name[0].toUpperCase() : <UserIcon className="w-3.5 h-3.5" />}
            </div>
          </div>
        </nav>
      </div>
    </header>
  );
}
