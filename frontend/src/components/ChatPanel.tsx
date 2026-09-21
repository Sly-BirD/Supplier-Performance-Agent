"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Sparkles, Upload, Send, X, ArrowRight, Layers, FileText, CheckCircle2 } from "lucide-react";
import { sendChat, uploadFile, seedSampleData, type Supplier, type AlertData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import ExpandingDotsLoader from "@/components/ui/ExpandingDotsLoader";

interface ActionChip {
  label: string;
  type: "inspect_supplier" | "compare_suppliers" | "filter_alerts" | "send_message";
  payload?: any;
}

interface IntelligenceLogItem {
  id: string;
  role: "user" | "agent";
  queryText?: string;
  content: string;
  timestamp: string;
  actions?: ActionChip[];
}

interface ChatPanelProps {
  suppliers?: Supplier[];
  alerts?: AlertData[];
  onClose?: () => void;
  onRefresh?: () => void;
  onSelectSupplier?: (id: string) => void;
  onCompareSuppliers?: (ids: string[]) => void;
  className?: string;
}

export default function ChatPanel({
  suppliers = [],
  alerts = [],
  onClose,
  onRefresh,
  onSelectSupplier,
  onCompareSuppliers,
  className = "",
}: ChatPanelProps) {
  const [logs, setLogs] = useState<IntelligenceLogItem[]>(() => {
    const count = suppliers.length;
    return [
      {
        id: "init-1",
        role: "agent",
        content:
          count > 0
            ? `Signal intelligence engine active with Gemini 2.5 Flash.\nMonitoring ${count} active supplier nodes across Quality, Delivery, Pricing, Communication, and Reliability dimensions.`
            : "Signal intelligence engine initialized with Gemini 2.5 Flash.\nCurrently 0 supplier datasets are loaded. Drop a CSV or Excel file into this console to compute scores, evaluate risk trajectories, and trigger anomaly alerts.",
        timestamp: "SYSTEM READY",
        actions:
          count > 0
            ? [
                { label: "Check at-risk suppliers", type: "send_message", payload: "Which suppliers should I worry about?" },
                { label: "Compare top suppliers", type: "compare_suppliers", payload: suppliers.slice(0, 3).map((s) => s.id) },
              ]
            : [
                { label: "⚡ Load Benchmark Dataset", type: "send_message", payload: "Load benchmark supplier dataset" },
              ],
      },
    ];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [logs, loading, scrollToBottom]);

  // Parse contextual actions out of text responses
  const extractActions = (replyText: string): ActionChip[] => {
    const chips: ActionChip[] = [];

    // Check if reply mentions any specific supplier
    for (const sup of suppliers) {
      if (replyText.toLowerCase().includes(sup.name.toLowerCase())) {
        chips.push({
          label: `Scorecard: ${sup.name}`,
          type: "inspect_supplier",
          payload: sup.id,
        });
        if (chips.length >= 2) break;
      }
    }

    // If comparison or benchmark suggested
    if (replyText.toLowerCase().includes("compare") || replyText.toLowerCase().includes("benchmark")) {
      if (suppliers.length >= 2) {
        chips.push({
          label: "Open Benchmark Comparison",
          type: "compare_suppliers",
          payload: suppliers.slice(0, 3).map((s) => s.id),
        });
      }
    }

    return chips;
  };

  const handleActionClick = (action: ActionChip) => {
    if (action.type === "inspect_supplier" && action.payload) {
      onSelectSupplier?.(action.payload);
    } else if (action.type === "compare_suppliers" && action.payload) {
      onCompareSuppliers?.(action.payload);
    } else if (action.type === "send_message" && action.payload) {
      if (action.payload === "Load benchmark supplier dataset") {
        handleLoadSample();
      } else {
        handleSend(action.payload);
      }
    }
  };

  const handleSend = async (queryToSend?: string) => {
    const text = (queryToSend || input).trim();
    if (!text || loading) return;

    const userLog: IntelligenceLogItem = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setLogs((prev) => [...prev, userLog]);
    setInput("");
    setLoading(true);

    try {
      const historyPayload = logs.slice(-6).map((l) => ({
        role: l.role,
        content: l.content,
      }));
      const res = await sendChat(text, undefined, historyPayload);
      const actions = extractActions(res.reply);

      const agentLog: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        queryText: text,
        content: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        actions: actions.length > 0 ? actions : undefined,
      };
      setLogs((prev) => [...prev, agentLog]);
      if (res.reply.toLowerCase().includes("approved") || res.reply.toLowerCase().includes("active")) {
        onRefresh?.();
      }
    } catch (err) {
      const errMsg: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        queryText: text,
        content: `Connection alert: ${
          err instanceof Error ? err.message : "Service timeout"
        }.\nPlease verify the backend server is operational on port 8000.`,
        timestamp: "EXCEPTION",
      };
      setLogs((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const processFile = async (file: File) => {
    setLoading(true);
    const userLog: IntelligenceLogItem = {
      id: Date.now().toString(),
      role: "user",
      content: `Uploaded supplier dataset: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setLogs((prev) => [...prev, userLog]);

    try {
      const res = await uploadFile(file);
      const agentLog: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: `✓ Dataset ingested successfully.\n• Status: ${res.message}\n• Processed rows: ${
          res.row_count || 0
        }\nAll dimensional scores and trajectories have been recomputed.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        actions: [
          { label: "View network scorecard directory", type: "send_message", payload: "Show network summary" },
        ],
      };
      setLogs((prev) => [...prev, agentLog]);
      onRefresh?.();
    } catch (err) {
      const agentLog: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: `⚠️ Ingestion exception: ${
          err instanceof Error ? err.message : "Failed to parse file format."
        }`,
        timestamp: "ERROR",
      };
      setLogs((prev) => [...prev, agentLog]);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleLoadSample = async () => {
    setLoading(true);
    const userLog: IntelligenceLogItem = {
      id: Date.now().toString(),
      role: "user",
      content: "Load benchmark supplier dataset",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setLogs((prev) => [...prev, userLog]);

    try {
      const res = await seedSampleData();
      const agentLog: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: `✓ ${res.message}\n• Ingested 5 benchmark suppliers.\n• Computed 5-dimensional scorecards across Quality, Delivery, Pricing, and Communication.\n• Populated real-time anomaly alerts and trajectories.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        actions: [
          { label: "Compare benchmark suppliers", type: "compare_suppliers", payload: ["sup-001", "sup-002", "sup-003"] },
        ],
      };
      setLogs((prev) => [...prev, agentLog]);
      onRefresh?.();
    } catch (err) {
      const agentLog: IntelligenceLogItem = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: `⚠️ Failed to load sample dataset: ${err instanceof Error ? err.message : "Error"}`,
        timestamp: "ERROR",
      };
      setLogs((prev) => [...prev, agentLog]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`bg-zinc-950/90 border ${
        dragOver ? "border-orange-500 bg-orange-950/10" : "border-zinc-800/80"
      } rounded-sm p-5 h-full flex flex-col justify-between transition-colors ${className}`}
    >
      {/* Console Header */}
      <div>
        <div className="flex items-center justify-between pb-3.5 border-b border-zinc-900">
          <div className="space-y-0.5">
            <span className="technical-label">SIGNAL INTELLIGENCE INTERFACE</span>
            <h2 className="text-sm font-bold tracking-tight text-zinc-100 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-orange-500" />
              Ask Signal Copilot
            </h2>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-1.5 text-[10px] font-mono-data text-zinc-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              LIVE COPILOT
            </div>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                title="Collapse sidebar (⌘K)"
                className="p-1 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Quick Query Prompts */}
        <div className="py-2.5 flex flex-wrap gap-1.5 border-b border-zinc-900/60">
          {suppliers.length === 0 && (
            <button
              type="button"
              onClick={handleLoadSample}
              disabled={loading}
              className="text-[11px] font-mono-data px-2.5 py-1 rounded bg-orange-950/80 hover:bg-orange-900 text-orange-300 hover:text-orange-200 border border-orange-700/80 transition-colors flex items-center gap-1 font-semibold"
            >
              <span>⚡ Seed Benchmark Data</span>
            </button>
          )}
          {[
            "Which suppliers should I worry about?",
            "What are the active threshold alerts?",
            "How does Signal score suppliers?",
          ].map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handleSend(prompt)}
              className="text-[11px] font-mono-data px-2.5 py-1 rounded bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 border border-zinc-800/80 transition-colors"
            >
              &ldquo;{prompt}&rdquo;
            </button>
          ))}
        </div>
      </div>

      {/* Logs / Interaction Stream */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
        {logs.map((item) => (
          <div key={item.id} className="space-y-1.5">
            <div className="flex items-center gap-2 text-[10px] font-mono-data uppercase text-zinc-400">
              <span
                className={
                  item.role === "user" ? "text-orange-400 font-bold" : "text-zinc-400 font-bold"
                }
              >
                {item.role === "user" ? "OPERATOR" : "SIGNAL AGENT"}
              </span>
              <span>·</span>
              <span>{item.timestamp}</span>
            </div>

            <div
              className={`text-xs leading-relaxed p-3.5 rounded ${
                item.role === "user"
                  ? "bg-zinc-900 text-zinc-100 border border-zinc-800 max-w-2xl"
                  : "bg-zinc-950/90 text-zinc-200 border border-zinc-900/90"
              }`}
            >
              <p className="whitespace-pre-line font-normal leading-relaxed">{item.content}</p>

              {/* Contextual Action Chips */}
              {item.actions && item.actions.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-zinc-900/80 flex flex-wrap gap-2">
                  {item.actions.map((act, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleActionClick(act)}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-orange-950/60 hover:bg-orange-900/80 border border-orange-600/60 text-[11px] font-mono-data text-orange-200 font-medium transition-colors"
                    >
                      {act.type === "compare_suppliers" && <Layers className="w-3 h-3 text-orange-400" />}
                      {act.type === "inspect_supplier" && <ArrowRight className="w-3 h-3 text-orange-400" />}
                      <span>{act.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Expanding Dots Loader */}
        {loading && (
          <ExpandingDotsLoader
            label="Signal is analyzing your query..."
            sublabel="Evaluating dimensional metrics & reasoning graph"
          />
        )}

        <div ref={logsEndRef} />
      </div>

      {/* Input & Ingestion Bar */}
      <div className="pt-3 border-t border-zinc-900">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.tsv"
          onChange={handleFileUpload}
          className="hidden"
        />

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Ingest CSV / Excel"
            className="p-2.5 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-800 transition-colors"
          >
            <Upload className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            disabled={loading}
            placeholder="Ask about scorecards, risk trajectories, or supplier comparisons..."
            className="flex-1 py-2.5 px-3.5 text-xs bg-zinc-900/80 border border-zinc-800 rounded text-zinc-100 placeholder:text-zinc-500 outline-none focus:border-orange-500/60"
          />

          <Button
            size="sm"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="h-9 px-4 text-xs font-semibold bg-orange-600 hover:bg-orange-500 text-white"
          >
            <Send className="w-3.5 h-3.5 mr-1" />
            Query
          </Button>
        </div>

        <div className="flex items-center justify-between text-[10px] font-mono-data text-zinc-500 pt-2">
          <span>DROP CSV OR EXCEL FILES DIRECTLY TO INGEST</span>
          <span>SUPPORTED: CSV · XLSX · TSV</span>
        </div>
      </div>
    </div>
  );
}
