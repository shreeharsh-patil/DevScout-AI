"use client";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function DashboardPage() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("developer");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [report, setReport] = useState<any>(null);

  const startResearch = async () => {
    setStatus("loading");
    setReport(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, type, depth: "standard" }),
      });
      const data = await res.json();
      
      // Poll for status
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

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="bg-neutral-900 border-neutral-800">
          <CardHeader>
            <CardTitle>New Research</CardTitle>
            <CardDescription>Deploy an agent to gather intelligence.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="type">Module</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger id="type" className="bg-neutral-950 border-neutral-800">
                  <SelectValue placeholder="Select module" />
                </SelectTrigger>
                <SelectContent className="bg-neutral-900 border-neutral-800 text-white">
                  <SelectItem value="developer">Developer Intel (GitHub)</SelectItem>
                  <SelectItem value="startup">Startup Research (Web)</SelectItem>
                  <SelectItem value="email">Email OSINT (Footprint Check)</SelectItem>
                  <SelectItem value="youtube">YouTube Analysis (Video)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="query">Target</Label>
              <Input 
                id="query" 
                placeholder={type === "developer" ? "GitHub Handle (e.g., torvalds)" : type === "startup" ? "Company URL (e.g., stripe.com)" : type === "email" ? "Email Address (e.g., user@gmail.com)" : "YouTube Video URL"} 
                className="bg-neutral-950 border-neutral-800"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            
            <Button 
              className="w-full bg-indigo-600 hover:bg-indigo-700" 
              onClick={startResearch}
              disabled={!query || status === "loading"}
            >
              {status === "loading" ? "Agents Deploying..." : "Start Scouting"}
            </Button>
          </CardContent>
        </Card>

        {/* Results Area */}
        <div className="space-y-6">
          {status === "loading" && (
            <Card className="bg-neutral-900 border-neutral-800 h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="flex flex-col items-center gap-4">
                <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-neutral-400">Agents are gathering data...</p>
              </CardContent>
            </Card>
          )}

          {status === "error" && (
            <Alert variant="destructive" className="bg-red-950 border-red-900 text-red-200">
              <AlertTitle>Research Failed</AlertTitle>
              <AlertDescription>
                The agents encountered an error while gathering intelligence.
              </AlertDescription>
            </Alert>
          )}

          {status === "success" && report && (
            <Card className="bg-neutral-900 border-neutral-800">
              <CardHeader>
                <CardTitle className="text-emerald-400">Intelligence Report</CardTitle>
                <CardDescription>Generated by DevScout AI</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="prose prose-invert max-w-none prose-p:text-sm prose-h3:text-lg prose-h2:text-xl">
                  {report.report.split('\n').map((line: string, i: number) => {
                    if (line.startsWith('# ')) return <h1 key={i} className="text-2xl font-bold mb-4">{line.substring(2)}</h1>;
                    if (line.startsWith('## ')) return <h2 key={i} className="text-xl font-bold mt-6 mb-3">{line.substring(3)}</h2>;
                    if (line.startsWith('### ')) return <h3 key={i} className="text-lg font-bold mt-4 mb-2">{line.substring(4)}</h3>;
                    if (line.startsWith('- ')) return <li key={i} className="ml-4">{line.substring(2)}</li>;
                    if (line.trim() === '') return <br key={i} />;
                    return <p key={i} className="mb-2 text-neutral-300">{line}</p>;
                  })}
                </div>
              </CardContent>
            </Card>
          )}
          
          {status === "idle" && (
            <Card className="bg-neutral-900/50 border-neutral-800 border-dashed h-full flex items-center justify-center min-h-[300px]">
              <CardContent>
                <p className="text-neutral-500 text-center">Results will appear here.</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
