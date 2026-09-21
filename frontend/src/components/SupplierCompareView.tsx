"use client";

import React, { useState } from "react";
import { ArrowUp, ArrowDown, Minus, Check, Download, Layers, ShieldAlert, Sparkles, X } from "lucide-react";
import { type Supplier, type ScorecardMap } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { exportComparisonCSV } from "@/lib/reportGenerator";

interface SupplierCompareViewProps {
  suppliers: Supplier[];
  scorecardMap: ScorecardMap;
  initialSelectedIds?: string[];
  onClose?: () => void;
  onSelectSupplier?: (id: string) => void;
}

export default function SupplierCompareView({
  suppliers,
  scorecardMap,
  initialSelectedIds = [],
  onClose,
  onSelectSupplier,
}: SupplierCompareViewProps) {
  // Pre-select first 2 or 3 suppliers if none provided
  const [selectedIds, setSelectedIds] = useState<string[]>(() => {
    if (initialSelectedIds.length >= 2) return initialSelectedIds.slice(0, 4);
    return suppliers.slice(0, 3).map((s) => s.id);
  });

  const selectedSuppliers = suppliers.filter((s) => selectedIds.includes(s.id));

  const toggleSupplier = (id: string) => {
    if (selectedIds.includes(id)) {
      if (selectedIds.length <= 1) return; // Keep at least one
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length >= 4) return; // Limit to 4 for side-by-side readability
      setSelectedIds([...selectedIds, id]);
    }
  };

  const dimensions = [
    { key: "quality", label: "Quality & Inspection", desc: "Batch pass rate & defect frequency" },
    { key: "delivery", label: "Delivery & Fulfillment", desc: "On-time arrival against SLA" },
    { key: "pricing", label: "Cost & Pricing Stability", desc: "Unit variance against contract" },
    { key: "communication", label: "Response & Communications", desc: "Inquiry turnaround time" },
    { key: "reliability", label: "Operational Reliability", desc: "Consistency & order fulfillment" },
  ];

  // Helper to find the best scoring supplier for a given metric
  const getBestSupplierId = (metricGetter: (s: Supplier) => number | null | undefined) => {
    let bestId: string | null = null;
    let highest = -Infinity;
    selectedSuppliers.forEach((s) => {
      const val = metricGetter(s);
      if (val !== null && val !== undefined && val > highest) {
        highest = val;
        bestId = s.id;
      }
    });
    return bestId;
  };

  const bestCompositeId = getBestSupplierId((s) => scorecardMap[s.id]?.composite_score);

  return (
    <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 h-full flex flex-col justify-between">
      <div>
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-zinc-900 gap-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="technical-label">SIDE-BY-SIDE INTELLIGENCE</span>
              <span className="text-[10px] font-mono-data px-1.5 py-0.5 rounded bg-orange-950/70 text-orange-400 border border-orange-800/50">
                {selectedSuppliers.length} COMPARED (MAX 4)
              </span>
            </div>
            <h2 className="text-base font-bold tracking-tight text-zinc-100 flex items-center gap-2">
              <Layers className="w-4 h-4 text-orange-500" />
              Supplier Benchmark & Comparison Matrix
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportComparisonCSV(selectedSuppliers, scorecardMap)}
              className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Export CSV
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0 text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Supplier Selector Chips */}
        <div className="py-4 border-b border-zinc-900/80">
          <div className="text-[11px] font-mono-data text-zinc-400 mb-2 uppercase tracking-wider">
            Select suppliers to compare (Click to toggle):
          </div>
          <div className="flex flex-wrap gap-2">
            {suppliers.map((s) => {
              const isSelected = selectedIds.includes(s.id);
              const sc = scorecardMap[s.id];
              return (
                <button
                  key={s.id}
                  onClick={() => toggleSupplier(s.id)}
                  className={`flex items-center gap-2 px-2.5 py-1 rounded text-xs transition-colors border ${
                    isSelected
                      ? "bg-orange-950/60 border-orange-500/50 text-orange-200 font-semibold"
                      : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                  }`}
                >
                  <div className={`w-3 h-3 rounded-xs border flex items-center justify-center ${
                    isSelected ? "bg-orange-500 border-orange-400" : "border-zinc-700"
                  }`}>
                    {isSelected && <Check className="w-2.5 h-2.5 text-black stroke-[3]" />}
                  </div>
                  <span>{s.name}</span>
                  {sc?.composite_score && (
                    <span className="font-mono-data text-[10px] text-zinc-500">
                      [{Math.round(sc.composite_score)}]
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Matrix View */}
        {selectedSuppliers.length === 0 ? (
          <div className="py-16 text-center text-zinc-500 text-xs">
            Select at least one supplier from above to view performance breakdown.
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <div className="grid grid-cols-12 gap-4 pb-3 border-b border-zinc-900 text-xs font-mono-data text-zinc-400 uppercase tracking-wider">
              <div className="col-span-4">Metric & Dimensional Factor</div>
              {selectedSuppliers.map((s) => (
                <div key={s.id} className="col-span-2 text-right">
                  <div className="font-bold text-zinc-200 truncate">{s.name}</div>
                  <div className="text-[10px] text-zinc-500">{s.category || "General"}</div>
                </div>
              ))}
            </div>

            {/* Composite Score Row */}
            <div className="grid grid-cols-12 gap-4 py-3.5 border-b border-zinc-900/80 items-center bg-zinc-900/20 px-2 -mx-2 rounded">
              <div className="col-span-4">
                <span className="font-bold text-zinc-100 text-xs">COMPOSITE INDEX SCORE</span>
                <p className="text-[11px] text-zinc-400">Holistic performance index</p>
              </div>
              {selectedSuppliers.map((s) => {
                const sc = scorecardMap[s.id];
                const score = sc?.composite_score ? Math.round(sc.composite_score) : null;
                const isBest = s.id === bestCompositeId && selectedSuppliers.length > 1;

                return (
                  <div key={s.id} className="col-span-2 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {isBest && (
                        <span className="text-[9px] font-mono-data px-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                          LEADER
                        </span>
                      )}
                      <span className={`font-mono-data text-xl font-extrabold ${
                        isBest ? "text-emerald-400" : "text-zinc-100"
                      }`}>
                        {score !== null ? score : "—"}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono-data uppercase text-zinc-400">
                      Tier: {sc?.tier || "N/A"}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Dimensions Rows */}
            {dimensions.map((dim) => {
              const bestDimId = getBestSupplierId(
                (s) => scorecardMap[s.id]?.dimensions?.[dim.key]?.score
              );

              return (
                <div
                  key={dim.key}
                  className="grid grid-cols-12 gap-4 py-3 border-b border-zinc-900/60 items-center hover:bg-zinc-900/30 px-2 -mx-2 rounded transition-colors"
                >
                  <div className="col-span-4">
                    <div className="text-xs font-semibold text-zinc-200">{dim.label}</div>
                    <div className="text-[11px] text-zinc-500">{dim.desc}</div>
                  </div>

                  {selectedSuppliers.map((s) => {
                    const dimData = scorecardMap[s.id]?.dimensions?.[dim.key];
                    const val = dimData?.score !== undefined ? Math.round(dimData.score) : null;
                    const isWinner = s.id === bestDimId && selectedSuppliers.length > 1;

                    return (
                      <div key={s.id} className="col-span-2 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {isWinner && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block mr-1" />
                          )}
                          <span className={`font-mono-data text-sm font-bold ${
                            val === null
                              ? "text-zinc-600"
                              : val >= 80
                              ? "text-emerald-400"
                              : val >= 70
                              ? "text-amber-400"
                              : "text-rose-400"
                          }`}>
                            {val !== null ? `${val}%` : "—"}
                          </span>
                        </div>
                        {/* Tiny progress bar */}
                        {val !== null && (
                          <div className="w-full h-1 bg-zinc-900 rounded-full mt-1 overflow-hidden">
                            <div
                              className={`h-full ${
                                val >= 80 ? "bg-emerald-500" : val >= 70 ? "bg-amber-500" : "bg-rose-500"
                              }`}
                              style={{ width: `${val}%` }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}

            {/* Trajectory & Risk Row */}
            <div className="grid grid-cols-12 gap-4 py-3 items-center px-2 -mx-2">
              <div className="col-span-4">
                <div className="text-xs font-semibold text-zinc-200">Trajectory & Trend</div>
                <div className="text-[11px] text-zinc-500">Historical velocity</div>
              </div>

              {selectedSuppliers.map((s) => {
                const sc = scorecardMap[s.id];
                const trend = sc?.trend;

                return (
                  <div key={s.id} className="col-span-2 text-right">
                    <span className={`inline-flex items-center gap-1 text-xs font-mono-data uppercase font-semibold ${
                      trend === "improving"
                        ? "text-emerald-400"
                        : trend === "declining"
                        ? "text-rose-400"
                        : "text-zinc-400"
                    }`}>
                      {trend === "improving" && <ArrowUp className="w-3 h-3 stroke-[2.5]" />}
                      {trend === "declining" && <ArrowDown className="w-3 h-3 stroke-[2.5]" />}
                      {trend === "stable" && <Minus className="w-3 h-3 stroke-[2.5]" />}
                      {trend || "Stable"}
                    </span>
                    <div className="mt-1">
                      <button
                        onClick={() => onSelectSupplier?.(s.id)}
                        className="text-[10px] font-mono-data text-orange-400 hover:text-orange-300 underline underline-offset-2"
                      >
                        Inspect Full Scorecard &rarr;
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Footer Summary */}
      <div className="pt-4 border-t border-zinc-900 flex items-center justify-between text-[11px] font-mono-data text-zinc-400">
        <span>RADAR BENCHMARK: 5 STANDARD LOGISTICAL DIMENSIONS</span>
        <span>BENCHMARKED AGAINST CURRENT NETWORK THRESHOLDS</span>
      </div>
    </div>
  );
}
