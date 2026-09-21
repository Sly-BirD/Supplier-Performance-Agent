"use client";

import React from "react";
import { Sparkles } from "lucide-react";

interface ExpandingDotsLoaderProps {
  label?: string;
  sublabel?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export default function ExpandingDotsLoader({
  label = "Signal intelligence model reasoning...",
  sublabel = "Evaluating network telemetry & knowledge graph",
  size = "md",
  className = "",
}: ExpandingDotsLoaderProps) {
  const dotSize = size === "sm" ? "w-1.5 h-1.5" : size === "lg" ? "w-2.5 h-2.5" : "w-2 h-2";

  return (
    <div
      className={`flex items-center gap-3 p-3.5 bg-zinc-950/80 border border-zinc-800/90 rounded-sm ${className}`}
    >
      <div className="relative flex items-center justify-center">
        <Sparkles className="w-4 h-4 text-orange-400 animate-pulse" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-zinc-200 tracking-tight">{label}</span>
          {/* Expanding Dots Wave */}
          <div className="inline-flex items-center gap-1.5 px-1 py-0.5" aria-label="Loading response">
            <span
              className={`${dotSize} rounded-full bg-orange-500 animate-expand-dot-1 inline-block`}
            />
            <span
              className={`${dotSize} rounded-full bg-orange-500 animate-expand-dot-2 inline-block`}
            />
            <span
              className={`${dotSize} rounded-full bg-orange-500 animate-expand-dot-3 inline-block`}
            />
          </div>
        </div>
        {sublabel && (
          <p className="text-[10px] font-mono-data text-zinc-500 mt-0.5 tracking-wide uppercase">
            {sublabel}
          </p>
        )}
      </div>
    </div>
  );
}
