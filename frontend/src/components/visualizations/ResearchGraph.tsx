"use client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ResearchTree } from "@/lib/types";
import * as d3 from "d3";
import React, { useEffect, useRef, useState } from "react";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  size: number;
  depth: number;
  url?: string;
  width?: number;
  height?: number;
  sources?: Record<string, string>;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
}

interface ResearchGraphProps {
  researchTree: ResearchTree | undefined;
}

const ResearchGraph: React.FC<ResearchGraphProps> = ({ researchTree }) => {
  const selectedNodeRef = useRef<GraphNode | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedNodeContent, setSelectedNodeContent] = useState<{ title: string; sources: Record<string, string> }>({
    title: "",
    sources: {},
  });
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});
  const [nodesState, setNodesState] = useState<GraphNode[]>([]); // Store nodes for both D3 and rendering
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

  // Resize observer to update graph size
  useEffect(() => {
    if (!containerRef.current) return;
    const handleResize = () => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        setDimensions({ width: rect.width, height: rect.height });
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (!researchTree) return;

    // Prepare data
    const nodes: GraphNode[] = [];
    const links: GraphLink[] = [];

    const processTree = (tree: ResearchTree, parentId?: string) => {
      const nodeId = `${tree.query}_${tree.depth}`;
      const textLength = tree.query.length;
      const nodeWidth = Math.max(120, Math.min(300, textLength * 6));
      const nodeHeight = 60;

      nodes.push({
        id: nodeId,
        name: tree.query,
        size: Object.keys(tree.sources).length + 10,
        depth: tree.depth,
        width: nodeWidth,
        height: nodeHeight,
        sources: tree.sources,
      });

      if (parentId) {
        links.push({
          source: parentId,
          target: nodeId,
        });
      }

      tree.children.forEach((child) => {
        processTree(child, nodeId);
      });
    };

    processTree(researchTree);
    setNodesState([...nodes]); // Save nodes for rendering

    const { width, height } = dimensions;
    const simulation = d3
      .forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>()
          .id((d: GraphNode) => d.id)
          .links(links)
          .distance(80)
      )
      .force("charge", d3.forceManyBody().strength(-800))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3.forceCollide().radius((d: d3.SimulationNodeDatum) => {
          const node = d as GraphNode;
          return Math.max(node.width || 0, node.height || 0) / 2 + 40;
        })
      )
      .on("tick", () => {
        setNodePositions((prev) => {
          const updated: Record<string, { x: number; y: number }> = {};
          nodes.forEach((n) => {
            // Clamp positions to container
            updated[n.id] = {
              x: Math.max((n.width || 120) / 2, Math.min(n.x || 0, width - (n.width || 120) / 2)),
              y: Math.max((n.height || 60) / 2, Math.min(n.y || 0, height - (n.height || 60) / 2)),
            };
          });
          return updated;
        });
      });

    return () => {
      simulation.stop();
    };
  }, [researchTree, dimensions]);

  const formatSourceContent = () => {
    return Object.entries(selectedNodeContent.sources).map(([url, content]) => (
      <div key={url} className="mb-6 border-b pb-4">
        <h3 className="text-base font-semibold mb-2">
          <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline break-words">
            {url}
          </a>
        </h3>
        <div className="prose prose-sm dark:prose-invert max-w-none break-words">{content}</div>
      </div>
    ));
  };

  const renderNodeCard = (node: GraphNode) => {
    const pos = nodePositions[node.id] || { x: 0, y: 0 };
    return (
      <div
        key={node.id}
        style={{
          position: "absolute",
          left: pos.x - (node.width || 120) / 2,
          top: pos.y - (node.height || 60) / 2,
          width: node.width || 120,
          zIndex: 2,
          cursor: node.url ? "pointer" : "default",
          userSelect: "none",
          pointerEvents: "auto",
        }}
        tabIndex={0}
        className="select-none focus:outline-none"
        onClick={(e) => {
          e.stopPropagation();
          selectedNodeRef.current = node;
          if (node.url) {
            window.open(node.url, "_blank");
          } else if (node.sources && Object.keys(node.sources).length > 0) {
            setSelectedNodeContent({ title: node.name, sources: node.sources });
            setDialogOpen(true);
          }
        }}
        onMouseDown={(e) => e.stopPropagation()}>
        <Card className={"bg-muted text-white cursor-pointer" + (node.name === "_" ? " w-32 h-[5rem]" : "")}>
          <CardTitle className={`p-2 pb-0 text-sm ${node.name === "_" ? "text-lg grid place-items-center h-4/5 w-full" : ""}`} title={node.name}>
            {node.name === "_" ? "Master Node" : node.name}
          </CardTitle>
          {node.name !== "_" && (
            <CardContent className="p-2 flex flex-wrap gap-1 w-full">
              <Badge variant="secondary" className="w-full bg-white/20 text-white border-white/20 grid place-items-center" title={node.name}>
                Source
              </Badge>
            </CardContent>
          )}
        </Card>
      </div>
    );
  };

  return (
    <div ref={containerRef} className="flex flex-col h-full flex-1 relative" style={{ minHeight: 600 }} onClick={() => setDialogOpen(false)}>
      <Card className="p-4 mb-4" id="graph-info-panel">
        <h3 className="text-lg font-medium">Research Visualization</h3>
        <p className="text-sm text-muted-foreground">Click on a node to see details. Source nodes are shown in purple. Click a node to open its source or view sources.</p>
      </Card>
      <div className="flex-1 border rounded-lg bg-card flex relative overflow-hidden" style={{ minHeight: 600 }}>
        {!researchTree ? (
          <div className="h-full w-full flex items-center justify-center text-muted-foreground">
            <p>No research data available yet. Start a conversation to begin research.</p>
          </div>
        ) : (
          <div style={{ width: "100%", height: "100%", position: "relative" }}>
            {/* Background for interaction */}
            <div style={{ position: "absolute", inset: 0, zIndex: 0, pointerEvents: "auto" }} onClick={() => setDialogOpen(false)} />
            {/* SVG for links only */}
            <svg width={dimensions.width} height={dimensions.height} style={{ position: "absolute", top: 0, left: 0, zIndex: 1, pointerEvents: "none" }}>
              {(() => {
                if (!researchTree) return null;
                const nodes: GraphNode[] = [];
                const links: GraphLink[] = [];
                const processTree = (tree: ResearchTree, parentId?: string) => {
                  const nodeId = `${tree.query}_${tree.depth}`;
                  nodes.push({ id: nodeId, name: tree.query, size: 10, depth: tree.depth });
                  if (parentId) {
                    links.push({ source: parentId, target: nodeId });
                  }
                  tree.children.forEach((child) => processTree(child, nodeId));
                };
                processTree(researchTree);
                return links.map((l, i) => {
                  const src = nodePositions[(typeof l.source === "string" ? l.source : l.source.id) as string];
                  const tgt = nodePositions[(typeof l.target === "string" ? l.target : l.target.id) as string];
                  if (!src || !tgt) return null;
                  return <line key={i} x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y} stroke="#bbb" strokeWidth={2} strokeOpacity={0.7} />;
                });
              })()}
            </svg>
            {/* Render node cards using nodesState */}
            {nodesState.map(renderNodeCard)}
          </div>
        )}
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold">Sources for: {selectedNodeContent.title}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto py-4">{formatSourceContent()}</div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ResearchGraph;
