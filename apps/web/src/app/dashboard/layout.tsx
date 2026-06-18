import Link from "next/link";
import { ReactNode } from "react";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-black text-white">
      {/* Sidebar */}
      <aside className="w-64 border-r border-neutral-800 flex flex-col">
        <div className="p-6 border-b border-neutral-800">
          <Link href="/">
            <h1 className="text-xl font-bold tracking-tight text-indigo-400">DevScout AI</h1>
          </Link>
        </div>
        <nav className="flex-1 p-4 flex flex-col gap-2">
          <Link href="/dashboard" className="px-4 py-2 bg-neutral-900 text-white rounded-md font-medium">
            Overview
          </Link>
          <div className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mt-4 mb-2 px-4">Modules</div>
          <Link href="/dashboard/developer" className="px-4 py-2 text-neutral-400 hover:text-white hover:bg-neutral-900 rounded-md">
            Developer Intel
          </Link>
          <Link href="/dashboard/startup" className="px-4 py-2 text-neutral-400 hover:text-white hover:bg-neutral-900 rounded-md">
            Startup Research
          </Link>
          <Link href="/dashboard/reddit" className="px-4 py-2 text-neutral-400 hover:text-white hover:bg-neutral-900 rounded-md">
            Reddit Insights
          </Link>
        </nav>
        <div className="p-4 border-t border-neutral-800">
          <div className="text-sm font-medium">Free Plan</div>
          <div className="text-xs text-neutral-500">10 / 10 Credits remaining</div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <header className="h-16 border-b border-neutral-800 flex items-center justify-between px-6">
          <h2 className="text-lg font-semibold">Dashboard</h2>
          <div className="flex items-center gap-4">
            <span className="text-sm text-neutral-400">Welcome, Founder</span>
          </div>
        </header>
        <div className="flex-1 p-6 overflow-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
