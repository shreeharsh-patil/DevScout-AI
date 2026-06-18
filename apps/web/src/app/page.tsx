"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, 
  Cpu, 
  Globe, 
  Github, 
  Twitter, 
  Youtube, 
  MessageSquare, 
  Mail, 
  ShieldCheck, 
  Zap, 
  ArrowRight,
  TrendingUp,
  LayoutDashboard,
  CheckCircle2,
  AlertCircle,
  Loader2
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

export default function OnePageApp() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("developer");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [report, setReport] = useState<any>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const startResearch = async () => {
    if (!query) return;
    
    // Smooth scroll to dashboard if not already there
    const dashboard = document.getElementById("dashboard");
    dashboard?.scrollIntoView({ behavior: "smooth" });

    setStatus("loading");
    setReport(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, type, depth: "standard" }),
      });
      const data = await res.json();
      
      const poll = setInterval(async () => {
        const statusRes = await fetch(`http://localhost:8000/api/v1/research/status/${data.job_id}`);
        const statusData = await statusRes.json();
        
        if (statusData.status === "completed" || statusData.status === "failed") {
          clearInterval(poll);
          setStatus(statusData.status === "completed" ? "success" : "error");
          setReport(statusData);
        }
      }, 2000);
      
    } catch (e) {
      console.error(e);
      setStatus("error");
    }
  };

  const features = [
    { icon: <Github className="w-5 h-5 text-emerald-400" />, title: "Developer Intel", desc: "Scan GitHub profiles for real tech stacks and impact scores." },
    { icon: <Globe className="w-5 h-5 text-indigo-400" />, title: "Startup Research", desc: "Automated SWOT and competitor analysis from any URL." },
    { icon: <TrendingUp className="w-5 h-5 text-blue-400" />, title: "Social Tracker", desc: "Compare global sentiment across Bilibili, X, and Reddit." },
    { icon: <Mail className="w-5 h-5 text-orange-400" />, title: "Email OSINT", desc: "Find public digital footprints associated with any email." },
    { icon: <Youtube className="w-5 h-5 text-red-400" />, title: "YouTube Analysis", desc: "Extract deep metadata and target audiences from videos." },
    { icon: <ShieldCheck className="w-5 h-5 text-cyan-400" />, title: "Idea Validator", desc: "Validate SaaS concepts against live market data." },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30">
      
      {/* Dynamic Header */}
      <header className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? "bg-black/80 backdrop-blur-md border-b border-neutral-800 py-3" : "bg-transparent py-6"}`}>
        <div className="max-w-7xl mx-auto px-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-emerald-500 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white fill-current" />
            </div>
            <h1 className="text-xl font-bold tracking-tighter">DevScout AI</h1>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-neutral-400 hover:text-white transition-colors">Features</a>
            <a href="#dashboard" className="text-sm font-medium text-neutral-400 hover:text-white transition-colors">Console</a>
            <a href="#pricing" className="text-sm font-medium text-neutral-400 hover:text-white transition-colors">Pricing</a>
            <Button variant="outline" className="border-neutral-800 bg-neutral-900/50 hover:bg-neutral-800 text-white">
              Launch Console
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />
        
        <div className="max-w-7xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-4 border-indigo-500/30 text-indigo-400 bg-indigo-500/5 px-3 py-1">
              Powered by Agent Reach v1.5
            </Badge>
            <h2 className="text-6xl md:text-8xl font-extrabold tracking-tight mb-6 leading-[1.1]">
              The Internet's <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-white to-emerald-400">
                Intelligence Layer.
              </span>
            </h2>
            <p className="text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              Stop manual digging. DevScout AI deploys autonomous agents to gather, 
              analyze, and synthesize real-time data into boardroom-ready reports.
            </p>
          </motion.div>

          {/* Quick Start Input */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="max-w-2xl mx-auto p-2 bg-neutral-900/50 border border-neutral-800 rounded-2xl backdrop-blur-xl shadow-2xl"
          >
            <div className="flex flex-col md:flex-row gap-2">
              <div className="flex-1 flex items-center px-4 gap-3">
                <Search className="w-5 h-5 text-neutral-500" />
                <input 
                  type="text" 
                  placeholder="Paste GitHub URL, Company URL, or Email..." 
                  className="w-full bg-transparent border-none outline-none text-white placeholder:text-neutral-600 py-3"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && startResearch()}
                />
              </div>
              <Button 
                onClick={startResearch}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-8 py-6 rounded-xl transition-all"
              >
                Scout Now
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 border-y border-neutral-900 bg-neutral-950/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((f, i) => (
              <motion.div 
                key={i}
                whileHover={{ y: -5 }}
                className="p-6 bg-neutral-900/40 border border-neutral-800 rounded-2xl"
              >
                <div className="w-10 h-10 bg-neutral-950 rounded-lg flex items-center justify-center mb-4 border border-neutral-800">
                  {f.icon}
                </div>
                <h3 className="text-lg font-bold mb-2">{f.title}</h3>
                <p className="text-sm text-neutral-500 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Integrated Console (Dashboard) */}
      <section id="dashboard" className="py-24 relative">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold flex items-center justify-center gap-3">
              <LayoutDashboard className="w-8 h-8 text-indigo-500" />
              Intelligence Console
            </h2>
            <p className="text-neutral-500 mt-2">Interact with your agents in real-time.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Control Panel */}
            <div className="lg:col-span-4 space-y-6">
              <Card className="bg-black border-neutral-800 shadow-xl">
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-widest text-neutral-500">Parameters</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label className="text-neutral-400">Intelligence Module</Label>
                    <Select value={type} onValueChange={setType}>
                      <SelectTrigger className="bg-neutral-900 border-neutral-800">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-neutral-900 border-neutral-800 text-white">
                        <SelectItem value="developer">Developer Intel</SelectItem>
                        <SelectItem value="startup">Startup Research</SelectItem>
                        <SelectItem value="email">Email OSINT</SelectItem>
                        <SelectItem value="youtube">YouTube Analysis</SelectItem>
                        <SelectItem value="reddit">Reddit Insights</SelectItem>
                        <SelectItem value="idea">Idea Validator</SelectItem>
                        <SelectItem value="social">Social Tracker</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-neutral-400">Active Query</Label>
                    <Input 
                      className="bg-neutral-900 border-neutral-800"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  
                  <Button 
                    className="w-full bg-white text-black hover:bg-neutral-200 font-bold py-6"
                    onClick={startResearch}
                    disabled={status === "loading" || !query}
                  >
                    {status === "loading" ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="animate-spin w-4 h-4" /> Deploying Agents...
                      </span>
                    ) : "Execute Command"}
                  </Button>
                </CardContent>
              </Card>

              {/* Status Indicator */}
              <Card className="bg-black border-neutral-800">
                <CardContent className="p-4 flex items-center justify-between">
                  <span className="text-xs text-neutral-500">Agent Network</span>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-mono text-emerald-500">HEALTHY</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Output Display */}
            <div className="lg:col-span-8">
              <AnimatePresence mode="wait">
                {status === "loading" && (
                  <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <Card className="bg-neutral-900/20 border-neutral-800 border-dashed min-h-[400px] flex items-center justify-center">
                      <CardContent className="flex flex-col items-center gap-6">
                        <div className="relative">
                           <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full" />
                           <div className="absolute top-0 w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                        <div className="text-center">
                          <p className="text-lg font-medium text-neutral-300">Agents are in the field</p>
                          <p className="text-sm text-neutral-500 mt-1">Gleaning data from {type} sources...</p>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "success" && report && (
                  <motion.div
                    key="success"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <Card className="bg-black border-neutral-800 min-h-[400px] overflow-hidden">
                      <div className="p-4 border-b border-neutral-800 bg-neutral-900/50 flex items-center justify-between">
                        <div className="flex gap-2">
                          <div className="w-3 h-3 rounded-full bg-red-500/50" />
                          <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                          <div className="w-3 h-3 rounded-full bg-green-500/50" />
                        </div>
                        <span className="text-[10px] font-mono text-neutral-600">RESEARCH_REPORT.MD</span>
                        <div className="w-4" />
                      </div>
                      <CardContent className="p-8 prose prose-invert max-w-none">
                        <div className="font-mono text-sm leading-relaxed">
                          {report.report.split('\n').map((line: string, i: number) => {
                            if (line.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold text-white mb-6 border-b border-neutral-800 pb-2">{line.substring(2)}</h1>;
                            if (line.startsWith('## ')) return <h2 key={i} className="text-xl font-semibold text-indigo-400 mt-8 mb-4">{line.substring(3)}</h2>;
                            if (line.startsWith('### ')) return <h3 key={i} className="text-lg font-medium text-emerald-400 mt-6 mb-2">{line.substring(4)}</h3>;
                            if (line.startsWith('- ')) return <div key={i} className="flex gap-2 ml-2 my-1 text-neutral-400"><span>•</span><span>{line.substring(2)}</span></div>;
                            if (line.trim() === '') return <div key={i} className="h-4" />;
                            return <p key={i} className="text-neutral-300 mb-2">{line}</p>;
                          })}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "idle" && (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <Card className="bg-neutral-900/10 border-neutral-800 border-dashed min-h-[400px] flex items-center justify-center">
                      <CardContent className="text-center max-w-xs">
                        <Cpu className="w-12 h-12 text-neutral-800 mx-auto mb-4" />
                        <p className="text-neutral-600 text-sm font-medium italic">Command line interface waiting for entry...</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                )}

                {status === "error" && (
                  <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <Alert variant="destructive" className="bg-red-950/30 border-red-900 text-red-400 py-10 flex flex-col items-center gap-4">
                      <AlertCircle className="w-12 h-12" />
                      <div className="text-center">
                        <AlertTitle className="text-lg font-bold">Extraction Interrupted</AlertTitle>
                        <AlertDescription className="mt-2">
                          The agents were blocked or the source timed out. Please try a different target.
                        </AlertDescription>
                      </div>
                    </Alert>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-20 bg-black border-t border-neutral-900">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-8">
            <Zap className="w-6 h-6 text-indigo-500 fill-current" />
            <span className="text-2xl font-bold tracking-tighter">DevScout AI</span>
          </div>
          <div className="flex justify-center gap-8 mb-12">
            <Link href="#" className="text-neutral-500 hover:text-white"><Github className="w-5 h-5" /></Link>
            <Link href="#" className="text-neutral-500 hover:text-white"><Twitter className="w-5 h-5" /></Link>
            <Link href="#" className="text-neutral-500 hover:text-white"><Youtube className="w-5 h-5" /></Link>
          </div>
          <p className="text-neutral-600 text-sm">
            &copy; 2026 DevScout AI. Built for the next generation of researchers.
          </p>
        </div>
      </footer>
    </div>
  );
}
