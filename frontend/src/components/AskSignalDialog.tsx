"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Sparkles, Upload, AlertCircle, FileText, ArrowRight, Search, X } from "lucide-react";
import { sendChat, uploadFile } from "@/lib/api";
import ExpandingDotsLoader from "@/components/ui/ExpandingDotsLoader";

interface AskSignalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectSupplier?: (name: string) => void;
  onNavigateExceptions?: () => void;
}

export default function AskSignalDialog({
  open,
  onOpenChange,
  onSelectSupplier,
  onNavigateExceptions,
}: AskSignalDialogProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<{
    reply: string;
    queryText?: string;
  } | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut listener for ⌘K / Ctrl+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  // Focus input on open
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  const handleSubmitQuery = async (promptText: string) => {
    const text = promptText.trim();
    if (!text || loading) return;
    setLoading(true);
    setResponse(null);
    setUploadStatus(null);
    try {
      const res = await sendChat(text);
      setResponse({
        reply: res.reply,
        queryText: text,
      });
    } catch (err) {
      setResponse({
        reply: `Could not complete query: ${
          err instanceof Error ? err.message : "Service timeout or connection error"
        }.\nPlease verify that the backend server is operational on port 8000.`,
        queryText: text,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setUploadStatus(`Ingesting ${file.name}...`);
    try {
      const result = await uploadFile(file);
      setUploadStatus(
        result.message || `✓ Ingested dataset: ${result.row_count || 0} rows processed.`
      );
      setResponse({
        reply:
          result.message ||
          `Successfully ingested ${file.name}. Processed ${result.row_count || 0} rows and recomputed network scorecards.`,
        queryText: `Upload ${file.name}`,
      });
    } catch (err) {
      setUploadStatus(`Upload failed: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".csv,.xlsx,.xls,.tsv"
        className="hidden"
      />

      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="bg-zinc-950 border border-zinc-800 text-zinc-100 max-w-2xl sm:max-w-2xl p-0 gap-0 overflow-hidden shadow-2xl rounded-lg">
          <DialogHeader className="p-4 pb-2 border-b border-zinc-900">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-orange-500" />
                <DialogTitle className="text-sm font-semibold tracking-tight text-zinc-100">
                  Ask Signal Intelligence
                </DialogTitle>
              </div>
              <span className="text-[10px] font-mono-data text-zinc-500 uppercase tracking-wider">
                LIVE AGENT REASONING
              </span>
            </div>
            <DialogDescription className="text-xs text-zinc-400 mt-1">
              Natural language queries on supplier quality, delivery SLA, risk evidence, or file ingestion
            </DialogDescription>
          </DialogHeader>

          {/* Search Input Bar */}
          <div className="p-3 border-b border-zinc-900 flex items-center gap-2 bg-zinc-900/40">
            <Search className="w-4 h-4 text-zinc-400 shrink-0 ml-1" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && query.trim()) {
                  e.preventDefault();
                  handleSubmitQuery(query);
                }
              }}
              disabled={loading}
              placeholder="Ask anything about your supplier network... (e.g. Which suppliers should I worry about?)"
              className="flex-1 bg-transparent text-xs text-zinc-100 placeholder:text-zinc-500 outline-none"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="text-zinc-500 hover:text-zinc-300 p-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              type="button"
              onClick={() => handleSubmitQuery(query)}
              disabled={!query.trim() || loading}
              className="px-3 py-1 text-xs font-medium rounded bg-orange-600 hover:bg-orange-500 disabled:opacity-40 disabled:hover:bg-orange-600 text-white transition-colors"
            >
              Ask
            </button>
          </div>

          {/* Content Body: Loading / Result / Suggested Queries */}
          <div className="max-h-[26rem] overflow-y-auto p-4 space-y-4">
            {/* Loading State with Expanding Dots Animation */}
            {loading && (
              <ExpandingDotsLoader
                label="Signal intelligence model reasoning..."
                sublabel="Querying dimensional engine & synthesizing response"
              />
            )}

            {/* Response Card */}
            {!loading && response && (
              <div className="space-y-4">
                {response.queryText && (
                  <div className="flex items-center justify-between pb-2 border-b border-zinc-900">
                    <span className="text-[10px] font-mono-data text-zinc-500 uppercase">
                      QUERY
                    </span>
                    <span className="text-xs font-mono-data text-orange-400 font-medium">
                      &ldquo;{response.queryText}&rdquo;
                    </span>
                  </div>
                )}

                <div className="bg-zinc-900/60 border border-zinc-800/80 rounded p-4 text-xs leading-relaxed text-zinc-200">
                  <div className="technical-label text-orange-400 mb-2">SIGNAL INTELLIGENCE SYNTHESIS</div>
                  <p className="whitespace-pre-line font-normal text-zinc-200 leading-relaxed">
                    {response.reply}
                  </p>
                </div>

                {uploadStatus && (
                  <div className="text-xs font-mono-data text-emerald-400 bg-emerald-950/40 border border-emerald-900/50 rounded px-3 py-2">
                    {uploadStatus}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-zinc-900">
                  <button
                    type="button"
                    onClick={() => {
                      setResponse(null);
                      setQuery("");
                      inputRef.current?.focus();
                    }}
                    className="text-[11px] font-mono-data text-zinc-400 hover:text-zinc-200 underline"
                  >
                    Clear & ask new question
                  </button>
                  <span className="text-[10px] font-mono-data text-zinc-500">
                    GROUNDED IN LIVE DATABASE METRICS
                  </span>
                </div>
              </div>
            )}

            {/* Default State: Recommended Queries */}
            {!loading && !response && (
              <div className="space-y-4">
                <div>
                  <span className="technical-label block mb-2">RECOMMENDED INTELLIGENCE QUERIES</span>
                  <div className="space-y-1.5">
                    {[
                      {
                        prompt: "Which suppliers should I worry about?",
                        icon: AlertCircle,
                        color: "text-rose-400",
                      },
                      {
                        prompt: "What are the current threshold violation alerts?",
                        icon: AlertCircle,
                        color: "text-amber-400",
                      },
                      {
                        prompt: "Show me the performance scorecard overview",
                        icon: FileText,
                        color: "text-orange-400",
                      },
                    ].map((item) => {
                      const Icon = item.icon;
                      return (
                        <button
                          key={item.prompt}
                          type="button"
                          onClick={() => {
                            setQuery(item.prompt);
                            handleSubmitQuery(item.prompt);
                          }}
                          className="w-full text-left flex items-center justify-between p-2.5 rounded hover:bg-zinc-900/80 border border-transparent hover:border-zinc-800 transition-colors group"
                        >
                          <div className="flex items-center gap-2.5 text-xs text-zinc-300 group-hover:text-white">
                            <Icon className={`w-3.5 h-3.5 ${item.color} shrink-0`} />
                            <span>&ldquo;{item.prompt}&rdquo;</span>
                          </div>
                          <ArrowRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-300 transition-colors" />
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="pt-3 border-t border-zinc-900">
                  <span className="technical-label block mb-2">ACTIONS & INGESTION</span>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full text-left flex items-center justify-between p-2.5 rounded hover:bg-zinc-900/80 border border-transparent hover:border-zinc-800 transition-colors group"
                  >
                    <div className="flex items-center gap-2.5 text-xs text-zinc-300 group-hover:text-white">
                      <Upload className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>Upload supplier CSV / Excel dataset</span>
                    </div>
                    <span className="text-[10px] font-mono-data text-zinc-500">CSV · XLSX</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer Bar */}
          <div className="px-4 py-2 border-t border-zinc-900 flex items-center justify-between text-[10px] font-mono-data text-zinc-500 bg-zinc-950">
            <span>SIGNAL AI MODEL: GEMINI 2.5 FLASH · ZERO HALLUCINATION POLICY</span>
            <span>ESC TO CLOSE · ⌘K SHORTCUT</span>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
