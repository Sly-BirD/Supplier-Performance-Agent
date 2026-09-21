"use client";

import React, { useState, useEffect, useRef } from "react";

interface ResizeHandleProps {
  side: "left" | "right";
  onResize: (clientX: number) => void;
  onReset?: () => void;
  className?: string;
  title?: string;
}

export default function ResizeHandle({
  side,
  onResize,
  onReset,
  className = "",
  title = "Drag to resize · Double-click to reset",
}: ResizeHandleProps) {
  const [isDragging, setIsDragging] = useState(false);
  const handleRef = useRef<HTMLDivElement>(null);
  const rafId = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
      }
    };
  }, []);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
    handleRef.current?.setPointerCapture(e.pointerId);
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const clientX = e.clientX;
    if (rafId.current !== null) {
      cancelAnimationFrame(rafId.current);
    }
    rafId.current = requestAnimationFrame(() => {
      onResize(clientX);
      rafId.current = null;
    });
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (isDragging) {
      setIsDragging(false);
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current);
        rafId.current = null;
      }
      try {
        handleRef.current?.releasePointerCapture(e.pointerId);
      } catch {
        // Ignored
      }
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    }
  };

  return (
    <div
      ref={handleRef}
      role="separator"
      aria-orientation="vertical"
      title={title}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onDoubleClick={(e) => {
        e.preventDefault();
        onReset?.();
      }}
      className={`absolute top-0 bottom-0 z-30 cursor-col-resize select-none flex items-center justify-center transition-colors group ${
        side === "right" ? "-right-1.5 w-3" : "-left-1.5 w-3"
      } ${className}`}
    >
      {/* Hairline Divider & Accent Pill */}
      <div
        className={`w-[2px] h-full transition-all duration-150 ${
          isDragging
            ? "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.8)] w-[3px]"
            : "bg-zinc-800 group-hover:bg-orange-500/70 group-hover:w-[2.5px]"
        }`}
      />

      {/* Grip Indicator Pill on Hover */}
      <div
        className={`absolute top-1/2 -translate-y-1/2 w-1.5 h-7 rounded-full bg-zinc-700 transition-all ${
          isDragging
            ? "bg-orange-400 scale-110 opacity-100"
            : "opacity-0 group-hover:opacity-80 group-hover:bg-orange-500/80"
        }`}
      />
    </div>
  );
}
