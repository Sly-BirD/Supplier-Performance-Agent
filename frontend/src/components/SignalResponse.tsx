"use client";

import React from "react";
import { ArrowRight, AlertTriangle, CheckCircle2, TrendingDown, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface StructuredRiskRow {
  supplier: string;
  risk: "HIGH" | "MEDIUM" | "LOW";
  details?: string;
}

interface SignalResponseProps {
  query?: string;
  summaryText: string;
  riskRows?: StructuredRiskRow[];
  whyPoints?: string[];
  evidencePoints?: string[];
  onInvestigateSupplier?: (name: string) => void;
}

export default function SignalResponse({
  query,
  summaryText,
  riskRows = [
    { supplier: "Acme Components Ltd", risk: "HIGH", details: "Delivery -11%, 12 late orders" },
    { supplier: "Delta Microelectronics", risk: "HIGH", details: "Response time 19h → 31h" },
    { supplier: "Nova Plastics Corp", risk: "MEDIUM", details: "2 quality rejects in Q3" },
    { supplier: "Bharat Logistics Express", risk: "LOW", details: "Performance +8%, recovering" },
  ],
  whyPoints = [
    "Delivery reliability fell 11% across 3 consecutive reporting periods",
    "Quality defect anomalies concentrated in plastic injection batches",
    "Inquiry response latency prolonged from 19h average to 31h",
  ],
  evidencePoints = [
    "12 late delivery occurrences logged in the last 21 days",
    "3 batch rejections exceeding 3.2% tolerance window",
    "High probability (74%) of SLA contract miss this calendar cycle",
  ],
  onInvestigateSupplier,
}: SignalResponseProps) {
  return (
    <div className="bg-zinc-950 border border-zinc-800/90 rounded-sm p-5 space-y-5 text-zinc-200">
      {/* Query Banner if provided */}
      {query && (
        <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
          <span className="text-[10px] font-mono-data uppercase tracking-wider text-zinc-500">
            INTELLIGENCE QUERY
          </span>
          <span className="text-xs font-mono-data text-orange-400 font-medium">
            &ldquo;{query}&rdquo;
          </span>
        </div>
      )}

      {/* Primary Intelligence Summary */}
      <div className="space-y-1">
        <span className="technical-label text-orange-400">ANALYSIS SYNTHESIS</span>
        <p className="text-xs text-zinc-200 leading-relaxed font-normal">
          {summaryText}
        </p>
      </div>

      {/* Structured Risk Table */}
      {riskRows && riskRows.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-zinc-900">
          <div className="flex items-center justify-between">
            <span className="technical-label">SUPPLIER RISK MATRIX</span>
            <span className="text-[10px] font-mono-data text-zinc-500">
              PRIORITIZED BY SEVERITY
            </span>
          </div>

          <div className="border border-zinc-900 rounded overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/60 border-b border-zinc-900 text-[10px] font-mono-data text-zinc-400 uppercase">
                <tr>
                  <th className="py-2 px-3">Supplier</th>
                  <th className="py-2 px-3">Risk Level</th>
                  <th className="py-2 px-3">Signal Anomaly</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900 text-xs">
                {riskRows.map((row) => (
                  <tr key={row.supplier} className="hover:bg-zinc-900/40 transition-colors">
                    <td className="py-2 px-3 font-semibold text-zinc-200">
                      {row.supplier}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`text-[10px] font-mono-data font-bold px-1.5 py-0.5 rounded ${
                          row.risk === "HIGH"
                            ? "bg-rose-950/80 text-rose-300 border border-rose-800"
                            : row.risk === "MEDIUM"
                            ? "bg-amber-950/80 text-amber-300 border border-amber-800"
                            : "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                        }`}
                      >
                        {row.risk}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-zinc-400 font-mono-data text-[11px]">
                      {row.details || "Observed metrics shift"}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => onInvestigateSupplier?.(row.supplier)}
                        className="text-[11px] font-mono-data text-orange-400 hover:text-orange-300 inline-flex items-center gap-1 hover:underline"
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Why Section */}
      {whyPoints && whyPoints.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-zinc-900">
          <span className="technical-label">CAUSAL EXPLANATION (WHY)</span>
          <ul className="space-y-1 text-xs text-zinc-300">
            {whyPoints.map((point, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-orange-500 font-mono-data">·</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Observable Evidence */}
      {evidencePoints && evidencePoints.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-zinc-900">
          <span className="technical-label">OBSERVABLE EVIDENCE & SIGNALS</span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
            {evidencePoints.map((ev, i) => (
              <div
                key={i}
                className="bg-zinc-900/60 border border-zinc-800/80 rounded p-2 text-[11px] text-zinc-300 font-mono-data leading-relaxed"
              >
                {ev}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
