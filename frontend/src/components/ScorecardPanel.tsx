"use client";

import React, { useState, useEffect } from "react";
import { ArrowDown, ArrowUp, Minus, Sparkles, Loader2 } from "lucide-react";
import { getScorecard, type Scorecard } from "@/lib/api";

interface ScorecardPanelProps {
  supplierId?: string | null;
}

export default function ScorecardPanel({ supplierId }: ScorecardPanelProps) {
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supplierId) {
      setScorecard(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getScorecard(supplierId)
      .then((data) => {
        if (!cancelled) setScorecard(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load scorecard");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [supplierId]);

  const getTierColor = (t: string) => {
    switch (t.toLowerCase()) {
      case "preferred":
        return "text-emerald-400 bg-emerald-950/60 border-emerald-800/40";
      case "approved":
        return "text-blue-400 bg-blue-950/60 border-blue-800/40";
      case "watch":
        return "text-amber-400 bg-amber-950/60 border-amber-800/40";
      case "at-risk":
      case "at risk":
        return "text-rose-400 bg-rose-950/60 border-rose-800/40";
      default:
        return "text-zinc-400 bg-zinc-900 border-zinc-800";
    }
  };

  const getTrendIcon = (trend: string | null) => {
    if (trend === "improving") return { icon: <ArrowUp className="w-3.5 h-3.5 stroke-[2.5]" />, color: "text-emerald-400", label: "Improving" };
    if (trend === "declining") return { icon: <ArrowDown className="w-3.5 h-3.5 stroke-[2.5]" />, color: "text-rose-400", label: "Deteriorating" };
    return { icon: <Minus className="w-3.5 h-3.5 stroke-[2.5]" />, color: "text-zinc-400", label: "Stable" };
  };

  // ─── Empty state: no supplier selected ───
  if (!supplierId) {
    return (
      <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 flex flex-col items-center justify-center h-full text-center">
        <span className="technical-label">INTELLIGENCE SCORECARD</span>
        <p className="text-xs text-zinc-500 mt-2">
          Select a supplier to view their performance scorecard
        </p>
      </div>
    );
  }

  // ─── Loading state ───
  if (loading) {
    return (
      <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 flex flex-col items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-orange-500 mb-2" />
        <span className="text-[11px] font-mono-data text-zinc-400">LOADING SCORECARD...</span>
      </div>
    );
  }

  // ─── Error state ───
  if (error) {
    return (
      <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 flex flex-col items-center justify-center h-full text-center">
        <span className="technical-label">INTELLIGENCE SCORECARD</span>
        <p className="text-xs text-zinc-500 mt-2">
          {error.includes("404")
            ? "No scorecard data yet — upload performance data to generate"
            : `Connection error: ${error}`}
        </p>
      </div>
    );
  }

  // ─── No data for this supplier ───
  if (!scorecard || scorecard.composite_score === null) {
    return (
      <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 flex flex-col items-center justify-center h-full text-center">
        <span className="technical-label">INTELLIGENCE SCORECARD</span>
        <h2 className="text-base font-bold tracking-tight text-zinc-100 uppercase mt-1">
          {scorecard?.supplier_name || supplierId}
        </h2>
        <p className="text-xs text-zinc-500 mt-2">
          No performance data available yet. Upload CSV/Excel data to generate scorecard.
        </p>
      </div>
    );
  }

  // ─── Full scorecard display ───
  const { supplier_name, composite_score, tier, trend, dimensions, computed_at } = scorecard;
  const displayScore = composite_score ?? 0;
  const trendInfo = getTrendIcon(trend);

  return (
    <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-sm p-6 flex flex-col justify-between h-full">
      {/* Supplier Name & Score Section */}
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
          <div className="space-y-0.5">
            <span className="technical-label">INTELLIGENCE SCORECARD</span>
            <h2 className="text-base font-bold tracking-tight text-zinc-100 uppercase">
              {supplier_name}
            </h2>
          </div>
          {tier && (
            <span
              className={`text-[10px] font-mono-data font-semibold tracking-wider uppercase px-2 py-0.5 rounded border ${getTierColor(tier)}`}
            >
              {tier}
            </span>
          )}
        </div>

        {/* Large Score + Trend */}
        <div className="py-4 flex items-baseline gap-4">
          <span className="text-5xl font-extrabold font-mono-data text-zinc-100">
            {displayScore}
          </span>
          <div className="space-y-0.5">
            <span className="text-xs font-semibold text-zinc-300 uppercase font-mono-data tracking-wider">
              INDEX SCORE
            </span>
            <div className={`flex items-center gap-1 text-xs font-mono-data ${trendInfo.color}`}>
              {trendInfo.icon}
              <span>{trendInfo.label}</span>
            </div>
          </div>
        </div>

        {/* Dimension Breakdown with Trends */}
        {dimensions && Object.keys(dimensions).length > 0 && (
          <div className="pt-2 pb-4 space-y-2.5 border-t border-zinc-900/80">
            <span className="technical-label">PERFORMANCE DIMENSIONS</span>

            {Object.entries(dimensions).map(([dim, data]) => {
              const val = data.score;
              return (
                <div key={dim} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="capitalize text-zinc-300">{dim}</span>
                    <div className="flex items-center gap-2 font-mono-data">
                      <span className="text-zinc-200 font-medium">{Math.round(val)}</span>
                    </div>
                  </div>
                  {/* Hairline track */}
                  <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        val >= 80
                          ? "bg-emerald-500"
                          : val >= 70
                          ? "bg-amber-500"
                          : "bg-rose-500"
                      }`}
                      style={{ width: `${Math.min(val, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Computed At */}
        {computed_at && (
          <div className="pt-4 border-t border-zinc-900/80 space-y-1.5">
            <div className="flex items-center gap-1.5 text-orange-400">
              <Sparkles className="w-3.5 h-3.5" />
              <span className="technical-label text-orange-400">ANALYSIS DETAILS</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed font-normal">
              Scorecard computed at {new Date(computed_at).toLocaleString()}. Performance index is
              derived from weighted dimensional analysis across delivery, quality, pricing,
              communication, and reliability metrics.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
