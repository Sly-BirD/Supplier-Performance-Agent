"use client";

import React, { useState, useMemo } from "react";

export interface DataPoint {
  date: string;
  score: number;
}

interface NetworkTrajectoryProps {
  currentScore?: number;
  changeLabel?: string;
}

export default function NetworkTrajectory({
  currentScore = 0,
  changeLabel = "Stable",
}: NetworkTrajectoryProps) {
  const [timeRange, setTimeRange] = useState<"7D" | "14D" | "30D" | "90D">("30D");
  const [activePoint, setActivePoint] = useState<DataPoint | null>(null);

  // Generate dynamic data points based on currentScore & timeRange
  const data: DataPoint[] = useMemo(() => {
    if (!currentScore || currentScore <= 0) {
      return [
        { date: "DAY 1", score: 0 },
        { date: "DAY 5", score: 0 },
        { date: "DAY 10", score: 0 },
        { date: "DAY 15", score: 0 },
        { date: "DAY 20", score: 0 },
        { date: "DAY 30", score: 0 },
      ];
    }

    const count = timeRange === "7D" ? 7 : timeRange === "14D" ? 6 : timeRange === "30D" ? 6 : 8;
    const points: DataPoint[] = [];
    const baseline = Math.max(20, currentScore - 6);

    for (let i = 0; i < count; i++) {
      const progress = i / (count - 1);
      // Smooth trajectory curve converging to currentScore
      const jitter = Math.sin(i * 1.5) * 2.2;
      const score = Math.round(baseline + progress * (currentScore - baseline) + jitter);
      const dayOffset = Math.round((1 - progress) * (timeRange === "7D" ? 7 : timeRange === "14D" ? 14 : timeRange === "30D" ? 30 : 90));
      const dateLabel = dayOffset === 0 ? "TODAY" : `-${dayOffset}D`;
      points.push({ date: dateLabel, score: Math.min(100, Math.max(10, i === count - 1 ? currentScore : score)) });
    }

    return points;
  }, [currentScore, timeRange]);

  // SVG dimensions
  const width = 500;
  const height = 120;
  const paddingX = 24;
  const paddingY = 20;

  const minScore = Math.max(0, Math.min(...data.map((d) => d.score)) - 3);
  const maxScore = Math.min(100, Math.max(...data.map((d) => d.score)) + 3);
  const range = maxScore - minScore || 1;

  const points = data.map((d, i) => {
    const x = paddingX + (i / (data.length - 1)) * (width - paddingX * 2);
    const y = height - paddingY - ((d.score - minScore) / range) * (height - paddingY * 2);
    return { x, y, ...d };
  });

  const pathD = points.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`;
  }, "");

  const areaD = `${pathD} L ${points[points.length - 1].x},${height - paddingY} L ${points[0].x},${height - paddingY} Z`;

  return (
    <div className="bg-zinc-950/40 border border-zinc-800/60 rounded-sm p-5">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-zinc-900 gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="technical-label">NETWORK TRAJECTORY</span>
            <span className="text-[10px] font-mono-data text-orange-400 bg-orange-950/50 border border-orange-800/40 px-1.5 rounded">
              INTERACTIVE
            </span>
          </div>
          <p className="text-xs text-zinc-400">
            Composite health trajectory & historical momentum
          </p>
        </div>

        {/* Time range selector & display value */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-zinc-900/80 border border-zinc-800 rounded p-0.5 text-[10px] font-mono-data">
            {(["7D", "14D", "30D", "90D"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setTimeRange(r)}
                className={`px-2 py-0.5 rounded transition-colors ${
                  timeRange === r
                    ? "bg-orange-600 text-white font-bold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <div className="text-right">
            <div className="text-xs font-mono-data font-semibold text-emerald-400">
              {changeLabel}
            </div>
            <div className="text-[11px] font-mono-data text-zinc-400">
              SCORE: <strong className="text-zinc-100">{activePoint ? activePoint.score : currentScore || "—"}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* SVG Chart */}
      <div className="relative pt-4 overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-28 overflow-visible cursor-crosshair"
          preserveAspectRatio="none"
          onMouseLeave={() => setActivePoint(null)}
        >
          {/* Subtle Grid reference line */}
          <line
            x1={paddingX}
            y1={height / 2}
            x2={width - paddingX}
            y2={height / 2}
            stroke="#27272a"
            strokeDasharray="3 3"
            strokeWidth={1}
          />

          {/* Area fill */}
          <path d={areaD} fill="rgba(249, 115, 22, 0.08)" />

          {/* Trajectory hairline */}
          <path
            d={pathD}
            fill="none"
            stroke="#f97316"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Active hover crosshair */}
          {activePoint && (
            <line
              x1={points.find((p) => p.date === activePoint.date)?.x || 0}
              y1={paddingY}
              x2={points.find((p) => p.date === activePoint.date)?.x || 0}
              y2={height - paddingY}
              stroke="#f97316"
              strokeDasharray="2 2"
              strokeWidth={1}
            />
          )}

          {/* Data nodes */}
          {points.map((pt, i) => {
            const isHovered = activePoint?.date === pt.date;
            return (
              <g key={pt.date}>
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? 5 : i === points.length - 1 ? 3.5 : 2.5}
                  className={`transition-all duration-150 cursor-pointer ${
                    isHovered
                      ? "fill-orange-400 stroke-white stroke-2"
                      : "fill-zinc-950 stroke-orange-500 stroke-[1.5]"
                  }`}
                  onMouseEnter={() => setActivePoint(pt)}
                />
              </g>
            );
          })}
        </svg>

        {/* X-Axis Labels */}
        <div className="flex justify-between px-2 pt-2 border-t border-zinc-900/60 text-[10px] font-mono-data text-zinc-400">
          {data.map((d) => (
            <span
              key={d.date}
              className={activePoint?.date === d.date ? "text-orange-400 font-bold" : ""}
            >
              {d.date}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
