import React, { useMemo, useState } from "react";
import {
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Network,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  status: string; // verified, probable, candidate, info
  confidence: number;
  value?: string;
  sources?: string[];
  metadata?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  strength: string; // deterministic, strong, moderate, weak
  weight: number;
  description: string;
}

export interface EvidenceGraphData {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  summary?: string;
  verification_tier?: string;
  confidence_score?: number;
  total_nodes?: number;
  total_edges?: number;
}

interface EvidenceGraphViewProps {
  graphData?: EvidenceGraphData;
  queryEmail?: string;
}

export function EvidenceGraphView({ graphData }: EvidenceGraphViewProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);

  const nodes = useMemo(() => graphData?.nodes || [], [graphData]);
  const edges = useMemo(() => graphData?.edges || [], [graphData]);

  // Compute 2D node coordinates deterministically around center
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    const width = 800;
    const height = 500;
    const centerX = width / 2;
    const centerY = height / 2;

    if (nodes.length === 0) return positions;

    // Root email node in center
    const emailNode = nodes.find((n) => n.node_type === "email") || nodes[0];
    positions[emailNode.id] = { x: centerX, y: centerY };

    const otherNodes = nodes.filter((n) => n.id !== emailNode.id);
    const verifiedNodes = otherNodes.filter((n) => n.status === "verified");
    const otherRankNodes = otherNodes.filter((n) => n.status !== "verified");

    // Inner circle for verified nodes
    const innerRadius = 160;
    verifiedNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(1, verifiedNodes.length)) * 2 * Math.PI - Math.PI / 2;
      positions[node.id] = {
        x: centerX + Math.cos(angle) * innerRadius,
        y: centerY + Math.sin(angle) * innerRadius,
      };
    });

    // Outer circle for candidate / repo / breach nodes
    const outerRadius = 240;
    otherRankNodes.forEach((node, idx) => {
      const angle = (idx / Math.max(1, otherRankNodes.length)) * 2 * Math.PI - Math.PI / 4;
      positions[node.id] = {
        x: centerX + Math.cos(angle) * outerRadius,
        y: centerY + Math.sin(angle) * outerRadius,
      };
    });

    return positions;
  }, [nodes]);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, nodes]);

  const selectedNodeEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return edges.filter((e) => e.source === selectedNodeId || e.target === selectedNodeId);
  }, [selectedNodeId, edges]);

  const getNodeColor = (node: GraphNode) => {
    if (node.node_type === "email") return { fill: "#4f46e5", stroke: "#818cf8", text: "#e0e7ff" };
    if (node.status === "verified") return { fill: "#065f46", stroke: "#34d399", text: "#ecfdf5" };
    if (node.node_type === "organization") return { fill: "#581c87", stroke: "#c084fc", text: "#faf5ff" };
    if (node.node_type === "repository") return { fill: "#713f12", stroke: "#facc15", text: "#fefce8" };
    if (node.node_type === "package") return { fill: "#7c2d12", stroke: "#fb923c", text: "#fff7ed" };
    if (node.node_type === "breach") return { fill: "#881337", stroke: "#f43f5e", text: "#fff1f2" };
    return { fill: "#262626", stroke: "#737373", text: "#d4d4d4" };
  };

  if (nodes.length === 0) {
    return (
      <Card className="bg-neutral-900/60 border-neutral-800 p-8 text-center">
        <Network className="w-8 h-8 text-neutral-600 mx-auto mb-2" />
        <p className="text-sm text-neutral-400">Evidence Graph will populate upon investigation completion.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="bg-black border-neutral-800 overflow-hidden">
        <CardHeader className="p-4 sm:p-5 border-b border-neutral-800 bg-neutral-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
              <Network className="w-4 h-4 text-indigo-400" />
              Interactive Evidence Graph ({nodes.length} Nodes, {edges.length} Edges)
            </CardTitle>
            <p className="text-xs text-neutral-400 mt-0.5">
              Click any node to inspect provenance citations, deterministic relationships, and correlation weights.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center bg-neutral-900 border border-neutral-800 rounded-lg p-0.5">
              <button
                onClick={() => setZoom((z) => Math.min(1.6, z + 0.15))}
                className="p-1 text-neutral-400 hover:text-neutral-200"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
                className="p-1 text-neutral-400 hover:text-neutral-200"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setZoom(1);
                  setSelectedNodeId(null);
                }}
                className="p-1 text-neutral-400 hover:text-neutral-200"
                title="Reset Graph"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 relative bg-neutral-950/90 overflow-hidden min-h-[460px]">
          {/* ── Legend ── */}
          <div className="absolute top-3 left-3 z-10 flex flex-wrap gap-2 pointer-events-none">
            <div className="flex items-center gap-1.5 bg-black/80 backdrop-blur-md px-2.5 py-1 rounded-full border border-emerald-500/30 text-[10px] text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
              Verified Evidence (Solid)
            </div>
            <div className="flex items-center gap-1.5 bg-black/80 backdrop-blur-md px-2.5 py-1 rounded-full border border-neutral-700 text-[10px] text-neutral-400">
              <span className="w-2 h-2 rounded-full border border-dashed border-neutral-400 inline-block"></span>
              Candidate Lead (Dashed)
            </div>
          </div>

          {/* ── SVG Canvas ── */}
          <div className="w-full h-[460px] overflow-auto flex items-center justify-center p-4">
            <svg
              viewBox="0 0 800 500"
              className="w-full h-full max-w-[800px] transition-transform duration-200"
              style={{ transform: `scale(${zoom})` }}
            >
              <defs>
                <marker
                  id="arrow-verified"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
                </marker>
                <marker
                  id="arrow-candidate"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#737373" />
                </marker>
              </defs>

              {/* ── Edges ── */}
              {edges.map((edge, idx) => {
                const posA = nodePositions[edge.source];
                const posB = nodePositions[edge.target];
                if (!posA || !posB) return null;

                const isDeterministic = edge.strength === "deterministic" || edge.strength === "strong";
                const isSelected = selectedNodeId && (edge.source === selectedNodeId || edge.target === selectedNodeId);

                return (
                  <g key={`${edge.source}-${edge.target}-${idx}`}>
                    <line
                      x1={posA.x}
                      y1={posA.y}
                      x2={posB.x}
                      y2={posB.y}
                      stroke={isSelected ? "#818cf8" : isDeterministic ? "#059669" : "#525252"}
                      strokeWidth={isSelected ? 2.5 : isDeterministic ? 1.8 : 1.2}
                      strokeDasharray={isDeterministic ? "none" : "4 3"}
                      strokeOpacity={isSelected ? 1.0 : isDeterministic ? 0.85 : 0.5}
                      markerEnd={isDeterministic ? "url(#arrow-verified)" : "url(#arrow-candidate)"}
                    />
                    {/* Edge Label on Midpoint */}
                    <text
                      x={(posA.x + posB.x) / 2}
                      y={(posA.y + posB.y) / 2 - 4}
                      fill="#737373"
                      fontSize="8.5"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="select-none pointer-events-none"
                    >
                      {edge.relationship.replace(/_/g, " ")}
                    </text>
                  </g>
                );
              })}

              {/* ── Nodes ── */}
              {nodes.map((node) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;

                const color = getNodeColor(node);
                const isSelected = selectedNodeId === node.id;
                const isEmail = node.node_type === "email";
                const radius = isEmail ? 24 : 18;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => setSelectedNodeId(node.id)}
                    className="cursor-pointer group"
                  >
                    {/* Pulsing ring for selected or root email */}
                    {isSelected && (
                      <circle
                        r={radius + 8}
                        fill="none"
                        stroke="#818cf8"
                        strokeWidth="2"
                        strokeDasharray="3 3"
                        className="animate-spin"
                        style={{ transformOrigin: "0 0" }}
                      />
                    )}

                    <circle
                      r={radius}
                      fill={color.fill}
                      stroke={color.stroke}
                      strokeWidth={isSelected ? 3 : node.status === "verified" ? 2 : 1.2}
                      strokeDasharray={node.status === "candidate" ? "3 2" : "none"}
                      className="transition-all duration-150 group-hover:brightness-125 shadow-lg"
                    />

                    {/* Node Icon / Symbol */}
                    <text
                      textAnchor="middle"
                      dy="4"
                      fill={color.text}
                      fontSize={isEmail ? "11" : "9"}
                      fontWeight="bold"
                      fontFamily="monospace"
                      className="select-none pointer-events-none"
                    >
                      {node.node_type === "email"
                        ? "@"
                        : node.node_type === "repository"
                        ? "repo"
                        : node.node_type === "package"
                        ? "pkg"
                        : node.node_type === "organization"
                        ? "org"
                        : node.node_type === "breach"
                        ? "!"
                        : node.label.slice(0, 3)}
                    </text>

                    {/* Node Label Below */}
                    <text
                      y={radius + 13}
                      textAnchor="middle"
                      fill={isSelected ? "#e0e7ff" : "#a3a3a3"}
                      fontSize="9"
                      fontWeight={isSelected ? "bold" : "normal"}
                      className="select-none pointer-events-none"
                    >
                      {node.label.length > 20 ? `${node.label.slice(0, 18)}...` : node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* ── Node Inspector Card ── */}
          {selectedNode && (
            <div className="absolute bottom-3 right-3 left-3 sm:left-auto sm:w-80 bg-neutral-900/95 backdrop-blur-md border border-neutral-700 rounded-xl p-4 shadow-2xl space-y-2 z-20">
              <div className="flex items-start justify-between gap-2 border-b border-neutral-800 pb-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-neutral-400">
                      {selectedNode.node_type}
                    </span>
                    <Badge
                      className={`text-[9px] px-1.5 py-0 ${
                        selectedNode.status === "verified"
                          ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
                          : "bg-neutral-800 text-neutral-400 border-neutral-700"
                      }`}
                    >
                      {selectedNode.status.toUpperCase()}
                    </Badge>
                  </div>
                  <h4 className="text-xs font-bold text-neutral-100 mt-0.5 truncate">{selectedNode.label}</h4>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="text-neutral-400 hover:text-neutral-200 text-xs font-mono"
                >
                  ✕
                </button>
              </div>

              {selectedNode.value && (
                <p className="text-[11px] text-neutral-300 font-mono break-all">{selectedNode.value}</p>
              )}

              {/* Connected Relationships */}
              {selectedNodeEdges.length > 0 && (
                <div className="space-y-1 pt-1">
                  <span className="text-[10px] uppercase tracking-wider text-neutral-500 font-mono">
                    Connected Relations ({selectedNodeEdges.length})
                  </span>
                  <div className="space-y-1 max-h-24 overflow-y-auto pr-1">
                    {selectedNodeEdges.map((edge, i) => (
                      <div
                        key={i}
                        className="text-[10px] bg-neutral-950 p-1.5 rounded border border-neutral-800 flex items-center justify-between"
                      >
                        <span className="text-indigo-400 font-mono truncate">{edge.relationship.replace(/_/g, " ")}</span>
                        <span className="text-[9px] text-neutral-500 font-mono capitalize">{edge.strength}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Provenance */}
              {selectedNode.sources && selectedNode.sources.length > 0 && (
                <div className="pt-1 border-t border-neutral-800 flex items-center justify-between">
                  <span className="text-[10px] text-neutral-500 font-mono">
                    {selectedNode.sources.length} Provenance Link(s)
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" /> Grounded
                  </span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
