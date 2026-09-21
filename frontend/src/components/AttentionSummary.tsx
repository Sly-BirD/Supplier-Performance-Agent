"use client";

import React from "react";
import { ArrowRight, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AttentionSummaryProps {
  activeAlertsCount?: number;
  criticalCount?: number;
  deterioratingCount?: number;
  onReviewExceptions?: () => void;
}

export default function AttentionSummary({
  activeAlertsCount = 0,
  criticalCount = 0,
  deterioratingCount = 0,
  onReviewExceptions,
}: AttentionSummaryProps) {
  const isAttentionNeeded = activeAlertsCount > 0;

  return (
    <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-5 flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
          <span className="technical-label">EXCEPTIONS & ANOMALIES</span>
          <span
            className={`inline-flex items-center gap-1.5 text-[10px] font-mono-data font-semibold tracking-wider uppercase px-2 py-0.5 rounded ${
              isAttentionNeeded
                ? "bg-rose-950/50 text-rose-400 border border-rose-800/40"
                : "bg-emerald-950/50 text-emerald-400 border border-emerald-800/40"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isAttentionNeeded ? "bg-rose-500 animate-ping" : "bg-emerald-500"
              }`}
            />
            {isAttentionNeeded ? "ATTENTION REQUIRED" : "STATUS CLEAR"}
          </span>
        </div>

        <div className="mt-4">
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-extrabold font-mono-data text-zinc-100">
              {activeAlertsCount}
            </span>
            <span className="text-sm font-semibold tracking-wide text-zinc-200 uppercase font-mono-data">
              {activeAlertsCount === 1 ? "SUPPLIER AT RISK" : "SUPPLIERS AT RISK"}
            </span>
          </div>

          <div className="mt-3 space-y-1.5">
            {activeAlertsCount > 0 ? (
              <>
                <div className="flex items-center gap-2 text-xs text-zinc-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                  <span className="font-mono-data font-medium text-rose-400">
                    {criticalCount} critical
                  </span>
                  <span className="text-zinc-500">·</span>
                  <span className="text-zinc-400">SLA breach or severe defect</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-zinc-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  <span className="font-mono-data font-medium text-amber-400">
                    {deterioratingCount} deteriorating
                  </span>
                  <span className="text-zinc-500">·</span>
                  <span className="text-zinc-400">Downward metric trajectory</span>
                </div>
              </>
            ) : (
              <div className="text-xs text-zinc-400 py-1">
                All supplier thresholds within normal tolerance boundaries.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="pt-4 mt-4 border-t border-zinc-900/80">
        <Button
          variant="outline"
          size="sm"
          onClick={onReviewExceptions}
          className="w-full text-xs font-mono-data tracking-wide bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border-zinc-800 hover:border-zinc-700 flex items-center justify-between"
        >
          <span>{activeAlertsCount > 0 ? "REVIEW EXCEPTIONS" : "VIEW ALERT LOG"}</span>
          <ArrowRight className="w-3.5 h-3.5 text-orange-500" />
        </Button>
      </div>
    </div>
  );
}
