"use client";

import React from "react";
import { ArrowDown, ArrowUp, AlertCircle, Inbox } from "lucide-react";

export interface SignalChangeItem {
  id: string;
  supplier: string;
  direction: "down" | "up" | "alert";
  metric: string;
  explanation: string;
  timestamp: string;
  supplierId?: string;
}

interface WhatChangedProps {
  items?: SignalChangeItem[];
  onSelectSupplier?: (name: string) => void;
}

export default function WhatChanged({
  items,
  onSelectSupplier,
}: WhatChangedProps) {
  const hasData = items && items.length > 0;

  return (
    <div className="bg-zinc-950/40 border border-zinc-800/60 rounded-sm p-5">
      <div className="flex items-center justify-between pb-3 border-b border-zinc-900">
        <div className="space-y-0.5">
          <span className="technical-label">WHAT CHANGED</span>
          <p className="text-xs text-zinc-300">
            {hasData
              ? "Real-time operational shifts across monitored supplier nodes"
              : "Continuous telemetry monitor waiting for operational shifts"}
          </p>
        </div>
        <span className="text-[11px] font-mono-data text-zinc-400">
          {hasData ? `${items.length} RECENT SHIFTS` : "NOMINAL / NO DRIFT"}
        </span>
      </div>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Inbox className="w-5 h-5 text-zinc-700 mb-2" />
          <p className="text-xs text-zinc-400">
            No operational shifts or alerts detected. Network telemetry is stable.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-zinc-900/80 mt-2">
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => onSelectSupplier?.(item.supplier)}
              className="py-3 group flex items-start justify-between gap-4 cursor-pointer hover:bg-zinc-900/40 px-2 -mx-2 rounded transition-colors"
            >
              <div className="flex items-start gap-3">
                {/* Directional Signal Indicator */}
                <div
                  className={`mt-0.5 w-5 h-5 rounded flex items-center justify-center shrink-0 text-xs font-mono-data font-bold ${
                    item.direction === "down"
                      ? "bg-rose-950/70 text-rose-400 border border-rose-900/50"
                      : item.direction === "up"
                      ? "bg-emerald-950/70 text-emerald-400 border border-emerald-900/50"
                      : "bg-amber-950/70 text-amber-400 border border-amber-900/50"
                  }`}
                >
                  {item.direction === "down" && <ArrowDown className="w-3 h-3 stroke-[2.5]" />}
                  {item.direction === "up" && <ArrowUp className="w-3 h-3 stroke-[2.5]" />}
                  {item.direction === "alert" && <AlertCircle className="w-3 h-3 stroke-[2.5]" />}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-zinc-200 group-hover:text-orange-400 transition-colors">
                      {item.supplier}
                    </span>
                    <span className="text-zinc-600 font-mono-data">·</span>
                    <span
                      className={`text-xs font-mono-data font-medium ${
                        item.direction === "down"
                          ? "text-rose-400"
                          : item.direction === "up"
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {item.metric}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">
                    {item.explanation}
                  </p>
                </div>
              </div>

              <span className="text-[10px] font-mono-data text-zinc-500 shrink-0 pt-0.5">
                {item.timestamp}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
