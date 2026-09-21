"use client";

import React from "react";
import { ArrowUpRight, ArrowDownRight, Activity, Truck, ShieldAlert, DollarSign, Clock, Layers } from "lucide-react";
import type { DimensionAverages, NetworkTelemetry } from "@/lib/api";

interface NetworkHealthProps {
  score?: number;
  trendPct?: number;
  supplierCount?: number;
  eventCount?: number;
  lastUpdated?: string;
  statusText?: string;
  dimensionAverages?: DimensionAverages;
  telemetry?: NetworkTelemetry;
  onOpenDiagnostics?: () => void;
}

export default function NetworkHealth({
  score,
  trendPct = 0,
  supplierCount = 0,
  eventCount = 0,
  lastUpdated = "Just now",
  statusText,
  dimensionAverages = {
    delivery: 88.0,
    quality: 92.5,
    pricing: 89.0,
    reliability: 91.0,
    communication: 94.0,
  },
  telemetry = {
    onTimeRate: "94.2%",
    defectRate: "1.8%",
    priceAdherence: "98.4%",
    responseLatency: "4.2h",
  },
  onOpenDiagnostics,
}: NetworkHealthProps) {
  const isPositive = trendPct >= 0;
  const hasScore = score !== undefined && score !== null && score > 0;

  const getScoreColor = (val: number) => {
    if (val >= 85) return "text-emerald-400";
    if (val >= 70) return "text-amber-400";
    return "text-rose-400";
  };

  const getBarColor = (val: number) => {
    if (val >= 85) return "bg-emerald-500";
    if (val >= 70) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <div className="flex flex-col space-y-4 pr-1">
      {/* Editorial Header */}
      <div>
        <div className="flex items-center justify-between pb-2">
          <span className="technical-label">SUPPLIER NETWORK · INTELLIGENCE INDEX</span>
          <button
            onClick={onOpenDiagnostics}
            className="text-[11px] font-mono-data text-zinc-400 hover:text-orange-400 flex items-center gap-1.5 transition-colors"
            title="Inspect full data health diagnostic report"
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>UPDATED {lastUpdated.toUpperCase()}</span>
          </button>
        </div>

        {/* Large Dominant Number & Core Trend */}
        <div className="flex items-baseline gap-4 mt-1">
          <span className="text-5xl font-extrabold tracking-tighter text-zinc-100 font-mono-data">
            {hasScore ? score : "—"}
          </span>
          <div className="space-y-0.5">
            {hasScore ? (
              <div className="flex items-center gap-1.5 text-xs font-mono-data font-semibold">
                {isPositive ? (
                  <span className="text-emerald-400 flex items-center">
                    <ArrowUpRight className="w-3.5 h-3.5 mr-0.5 stroke-[2.5]" />
                    +{trendPct}%
                  </span>
                ) : (
                  <span className="text-rose-400 flex items-center">
                    <ArrowDownRight className="w-3.5 h-3.5 mr-0.5 stroke-[2.5]" />
                    {trendPct}%
                  </span>
                )}
                <span className="text-zinc-400 font-normal">vs previous period</span>
              </div>
            ) : (
              <div className="text-xs font-mono-data text-zinc-500">
                Awaiting scorecard dataset
              </div>
            )}
            <p className="text-[11px] text-zinc-400 font-medium">
              Weighted index across delivery, quality, pricing, reliability & comms
            </p>
          </div>
        </div>
      </div>

      {/* ─── Key Telemetry Badges Strip ─── */}
      <div className="pt-2">
        <div className="flex items-center justify-between pb-2">
          <span className="text-[10px] font-mono-data uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-orange-400" />
            OPERATIONAL TELEMETRY BADGES
          </span>
          <span className="text-[10px] font-mono-data text-zinc-500">LIVE AGGREGATE</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {/* Badge 1: On-Time SLA */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-sm p-2.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-[10px] font-mono-data uppercase">ON-TIME SLA</span>
              <Truck className="w-3.5 h-3.5 text-orange-400/80" />
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold font-mono-data text-zinc-100">
                {telemetry.onTimeRate}
              </span>
              <span className="text-[9px] font-mono-data text-emerald-400">TARGET ≥90%</span>
            </div>
          </div>

          {/* Badge 2: Defect Rate */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-sm p-2.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-[10px] font-mono-data uppercase">DEFECT RATE</span>
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400/80" />
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold font-mono-data text-zinc-100">
                {telemetry.defectRate}
              </span>
              <span className="text-[9px] font-mono-data text-zinc-400">TOL ≤2.5%</span>
            </div>
          </div>

          {/* Badge 3: Price Adherence */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-sm p-2.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-[10px] font-mono-data uppercase">CONTRACT ADH.</span>
              <DollarSign className="w-3.5 h-3.5 text-emerald-400/80" />
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold font-mono-data text-zinc-100">
                {telemetry.priceAdherence}
              </span>
              <span className="text-[9px] font-mono-data text-emerald-400">DRIFT ±1.6%</span>
            </div>
          </div>

          {/* Badge 4: Response Latency */}
          <div className="bg-zinc-900/70 border border-zinc-800/80 rounded-sm p-2.5 flex flex-col justify-between">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-[10px] font-mono-data uppercase">AVG LATENCY</span>
              <Clock className="w-3.5 h-3.5 text-sky-400/80" />
            </div>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-base font-bold font-mono-data text-zinc-100">
                {telemetry.responseLatency}
              </span>
              <span className="text-[9px] font-mono-data text-zinc-400">SLA &lt;24H</span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── 5 Dimension Vital Signs Mini Progress Bars ─── */}
      <div className="bg-zinc-900/40 border border-zinc-900/90 rounded-sm p-2.5 space-y-2">
        <div className="flex items-center justify-between text-[10px] font-mono-data text-zinc-400">
          <span className="flex items-center gap-1 uppercase tracking-wider text-zinc-300">
            <Layers className="w-3 h-3 text-orange-500" />
            5-Dimension Network Averages
          </span>
          <span>SCALE 0-100</span>
        </div>

        <div className="grid grid-cols-5 gap-2 pt-0.5">
          {[
            { label: "Delivery", val: dimensionAverages.delivery },
            { label: "Quality", val: dimensionAverages.quality },
            { label: "Pricing", val: dimensionAverages.pricing },
            { label: "Reliability", val: dimensionAverages.reliability },
            { label: "Comms", val: dimensionAverages.communication },
          ].map((item) => (
            <div key={item.label} className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-mono-data">
                <span className="text-zinc-400 truncate">{item.label}</span>
                <span className={`font-bold ${getScoreColor(item.val)}`}>{item.val.toFixed(1)}</span>
              </div>
              <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${getBarColor(item.val)} transition-all duration-300`}
                  style={{ width: `${Math.min(100, Math.max(5, item.val))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Human-readable interpretation & Metadata Footer */}
      <div className="pt-3 border-t border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              hasScore
                ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)]"
                : "bg-zinc-600"
            }`}
          />
          <span className="text-xs text-zinc-300 font-normal truncate max-w-[280px]">
            {statusText || (hasScore ? "Network health nominal" : "Upload supplier data to generate intelligence")}
          </span>
        </div>
        <div className="text-[11px] font-mono-data text-zinc-400 tracking-wide shrink-0">
          {supplierCount.toLocaleString()} NODES · {eventCount.toLocaleString()} EVENTS
        </div>
      </div>
    </div>
  );
}
