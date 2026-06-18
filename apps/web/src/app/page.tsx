import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-black text-white">
      {/* Navigation */}
      <header className="px-6 py-4 flex justify-between items-center border-b border-neutral-800">
        <h1 className="text-2xl font-bold tracking-tighter text-indigo-400">DevScout AI</h1>
        <nav className="flex gap-4">
          <Link href="/dashboard" className="text-sm font-medium hover:text-indigo-300 transition-colors">
            Dashboard
          </Link>
          <Button variant="outline" className="bg-transparent border-indigo-500 text-indigo-400 hover:bg-indigo-950">
            Sign In
          </Button>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20">
        <h2 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6">
          Stop Searching. <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">Start Understanding.</span>
        </h2>
        <p className="text-xl md:text-2xl text-neutral-400 max-w-3xl mb-10">
          The unified AI intelligence platform that transforms raw data from GitHub, Reddit, and the Web into actionable, boardroom-ready insights.
        </p>
        
        <div className="flex gap-4 max-w-lg w-full">
          <Link href="/dashboard" className="w-full">
            <Button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-lg py-6 rounded-xl shadow-lg shadow-indigo-900/20">
              Start Scouting for Free
            </Button>
          </Link>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 max-w-6xl w-full">
          <Card className="bg-neutral-900 border-neutral-800 text-left">
            <CardHeader>
              <CardTitle className="text-emerald-400">Developer Intelligence</CardTitle>
              <CardDescription className="text-neutral-400">Deep dive into GitHub profiles.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-neutral-300">
              Analyze tech stacks, code quality, and open-source impact to generate comprehensive developer scores.
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 text-left">
            <CardHeader>
              <CardTitle className="text-indigo-400">Startup Research</CardTitle>
              <CardDescription className="text-neutral-400">Automated competitor analysis.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-neutral-300">
              Generate SWOT analysis, track funding, and validate market positioning with a single URL.
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 text-left">
            <CardHeader>
              <CardTitle className="text-blue-400">Multi-Agent Synthesis</CardTitle>
              <CardDescription className="text-neutral-400">Beyond simple scraping.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-neutral-300">
              Our agents gather, analyze, and synthesize data across Reddit, YouTube, and the Web into citable reports.
            </CardContent>
          </Card>
        </div>
      </main>

      <footer className="py-6 text-center text-neutral-500 border-t border-neutral-800">
        &copy; 2026 DevScout AI. All rights reserved.
      </footer>
    </div>
  );
}
