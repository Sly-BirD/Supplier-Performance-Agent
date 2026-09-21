"use client";

import React, { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MorphIcon } from "morphicons/react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export type NavPage = "dashboard" | "chat" | "suppliers" | "compare" | "alerts" | "settings";

interface SidebarProps {
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
  supplierCount?: number;
  alertCount?: number;
  isChatOpen?: boolean;
  onToggleChat?: () => void;
  width?: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  lastUpdatedText?: string;
  totalEventsCount?: number;
}

const NAV_ICONS: Record<string, string> = {
  dashboard: "M22 12h-4l-3 9L9 3l-3 9H2",
  suppliers: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
  compare: "M16 3h5v5 M4 20L21 3 M21 16v5h-5 M15 15l6 6 M4 4l5 5",
  performance: "M22 7L13.5 15.5L8.5 10.5L2 17 M16 7h6v6",
  alerts: "M12 9v4 M12 17h.01 M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
  chat: "M4 17l6-6-6-6 M12 19h8",
  settings: "M4 21v-7 M4 10V3 M12 21v-9 M12 8V3 M20 21v-5 M20 12V3 M1 14h6 M9 8h6 M17 16h6",
};

export default function Sidebar({
  activePage,
  onNavigate,
  supplierCount = 0,
  alertCount = 0,
  isChatOpen = false,
  onToggleChat,
  width,
  isCollapsed = false,
  onToggleCollapse,
  lastUpdatedText = "Just now",
  totalEventsCount = 0,
}: SidebarProps) {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const mainNavItems = [
    {
      id: "dashboard" as NavPage,
      label: "Overview",
      sublabel: "Network Health",
      path: NAV_ICONS.dashboard,
    },
    {
      id: "suppliers" as NavPage,
      label: "Network",
      sublabel: `${supplierCount} suppliers`,
      path: NAV_ICONS.suppliers,
      counter: supplierCount > 0 ? `${supplierCount}` : undefined,
    },
    {
      id: "compare" as NavPage,
      label: "Compare",
      sublabel: "Side-by-side Matrix",
      path: NAV_ICONS.compare,
    },
    {
      id: "alerts" as NavPage,
      label: "Exceptions",
      sublabel: alertCount > 0 ? `${alertCount} active` : "Clear",
      path: NAV_ICONS.alerts,
      badge: alertCount > 0 ? `${alertCount}` : undefined,
    },
  ];

  return (
    <aside
      style={{ width: `${width}px` }}
      className="bg-zinc-950 border-r border-zinc-800/80 flex flex-col justify-between select-none z-20 shrink-0 relative transition-[width] duration-150 overflow-hidden"
    >
      {/* Brand & Collapse Header */}
      <div>
        <div className={`px-4 pt-5 pb-4 border-b border-zinc-900 flex items-center ${isCollapsed ? "justify-center" : "justify-between"}`}>
          {!isCollapsed ? (
            <div>
              <div className="flex items-center gap-2.5">
                <div className="w-2 h-2 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.8)] animate-pulse" />
                <h1 className="text-base font-bold tracking-[0.18em] text-zinc-100 uppercase font-mono-data">
                  SIGNAL
                </h1>
                <span className="text-[10px] font-mono-data tracking-wider uppercase text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-1.5 py-0.5 rounded ml-1">
                  v1.0
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 tracking-wide mt-1 font-normal">
                Supplier Intelligence & Control
              </p>
            </div>
          ) : (
            <Tooltip>
              <TooltipTrigger render={<div />}>
                <div className="w-8 h-8 rounded bg-orange-500/10 border border-orange-500/30 flex items-center justify-center text-orange-400 font-bold font-mono-data">
                  S
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">Signal Intelligence Platform</TooltipContent>
            </Tooltip>
          )}

          {onToggleCollapse && !isCollapsed && (
            <button
              type="button"
              onClick={onToggleCollapse}
              title="Collapse sidebar"
              className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Primary Navigation */}
        <div className="px-2 py-3 space-y-1">
          {!isCollapsed && (
            <div className="px-3 pb-2">
              <span className="technical-label">INTELLIGENCE</span>
            </div>
          )}

          {mainNavItems.map((item) => {
            const isActive = activePage === item.id;
            const isHovered = hoveredItem === item.label;

            const buttonContent = (
              <button
                type="button"
                onClick={() => onNavigate(item.id)}
                onMouseEnter={() => setHoveredItem(item.label)}
                onMouseLeave={() => setHoveredItem(null)}
                className={`w-full group flex items-center ${
                  isCollapsed ? "justify-center px-2 py-2.5" : "justify-between px-3 py-2"
                } rounded text-left transition-all duration-150 ${
                  isActive
                    ? "bg-zinc-900 text-zinc-100 border border-zinc-800/90 shadow-xs"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`transition-colors duration-150 ${
                      isActive
                        ? "text-orange-500"
                        : isHovered
                        ? "text-zinc-200"
                        : "text-zinc-500"
                    }`}
                  >
                    <MorphIcon
                      icon={item.path}
                      size={18}
                      strokeWidth={isActive ? 2.2 : 1.8}
                      spring="snappy"
                    />
                  </div>
                  {!isCollapsed && (
                    <div>
                      <span className="text-xs font-medium tracking-wide">
                        {item.label}
                      </span>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <>
                    {item.badge ? (
                      <Badge
                        variant="destructive"
                        className="text-[10px] font-mono-data px-1.5 py-0 h-4 bg-rose-950/80 border-rose-800/60 text-rose-300"
                      >
                        {item.badge}
                      </Badge>
                    ) : item.counter ? (
                      <span className="text-[11px] font-mono-data text-zinc-400 group-hover:text-zinc-300">
                        {item.counter}
                      </span>
                    ) : null}
                  </>
                )}

                {isCollapsed && item.badge && (
                  <span className="absolute top-1.5 right-2 w-2 h-2 rounded-full bg-rose-500" />
                )}
              </button>
            );

            if (isCollapsed) {
              return (
                <Tooltip key={item.label}>
                  <TooltipTrigger render={<div className="w-full relative" />}>
                    {buttonContent}
                  </TooltipTrigger>
                  <TooltipContent side="right" className="text-xs bg-zinc-900 border-zinc-800 text-zinc-200">
                    <span className="font-semibold">{item.label}</span> &mdash; {item.sublabel}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.label}>{buttonContent}</div>;
          })}
        </div>

        {/* Action Layer: Copilot Toggle & Settings */}
        <div className="px-2 py-2">
          <Separator className="bg-zinc-900 my-2" />

          {!isCollapsed && (
            <div className="px-3 pt-1 pb-1.5 flex items-center justify-between">
              <span className="technical-label">COPILOT & CONTROL</span>
              <span
                className={`text-[9px] font-mono-data font-semibold px-1.5 py-0.5 rounded transition-colors ${
                  isChatOpen
                    ? "bg-orange-950/80 text-orange-400 border border-orange-500/40"
                    : "bg-zinc-900 text-zinc-500 border border-zinc-800"
                }`}
              >
                {isChatOpen ? "ACTIVE" : "COLLAPSED"}
              </span>
            </div>
          )}

          {/* Signal Chatbot Toggle */}
          <Tooltip>
            <TooltipTrigger render={<div className="w-full" />}>
              <button
                type="button"
                onClick={onToggleChat}
                className={`w-full group flex items-center ${
                  isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
                } rounded text-left transition-all duration-150 ${
                  isChatOpen
                    ? "bg-zinc-900 text-orange-400 border border-orange-500/40 shadow-sm"
                    : "text-zinc-300 hover:text-white bg-zinc-900/40 hover:bg-zinc-900/80 border border-zinc-800/60"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div className={isChatOpen ? "text-orange-500" : "text-zinc-400 group-hover:text-zinc-200"}>
                    <MorphIcon
                      icon={NAV_ICONS.chat}
                      size={18}
                      strokeWidth={isChatOpen ? 2.2 : 1.8}
                      spring="snappy"
                    />
                  </div>
                  {!isCollapsed && (
                    <div>
                      <span className="text-xs font-semibold tracking-wide text-zinc-200 block">
                        Signal Chatbot
                      </span>
                      <span className="text-[10px] font-mono-data text-zinc-500 block">
                        {isChatOpen ? "Docked right panel" : "Toggle copilot sidebar"}
                      </span>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <div className="flex items-center gap-1.5">
                    <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[9px] font-mono-data font-medium bg-zinc-950 text-zinc-400 border border-zinc-800 rounded">
                      ⌘K
                    </kbd>
                    <div
                      className={`w-7 h-4 rounded-full p-0.5 transition-colors flex items-center ${
                        isChatOpen ? "bg-orange-600 justify-end" : "bg-zinc-800 justify-start"
                      }`}
                    >
                      <div className="w-3 h-3 rounded-full bg-white shadow-xs" />
                    </div>
                  </div>
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="text-xs bg-zinc-900 border-zinc-800 text-zinc-300">
              Toggle Signal AI Copilot sidebar (⌘K)
            </TooltipContent>
          </Tooltip>

          {/* Settings Nav Item */}
          <Tooltip>
            <TooltipTrigger render={<div className="w-full" />}>
              <button
                type="button"
                onClick={() => onNavigate("settings")}
                className={`w-full mt-1.5 flex items-center ${
                  isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2"
                } rounded text-left transition-all duration-150 ${
                  activePage === "settings"
                    ? "bg-zinc-900 text-zinc-100 border border-zinc-800/90"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="text-zinc-500">
                    <MorphIcon
                      icon={NAV_ICONS.settings}
                      size={18}
                      strokeWidth={1.8}
                      spring="snappy"
                    />
                  </div>
                  {!isCollapsed && (
                    <span className="text-xs font-medium tracking-wide">Settings</span>
                  )}
                </div>
                {!isCollapsed && (
                  <span className="text-[10px] font-mono-data text-zinc-500">Rules</span>
                )}
              </button>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right" className="text-xs bg-zinc-900 border-zinc-800 text-zinc-300">
                Settings & Scoring Weights
              </TooltipContent>
            )}
          </Tooltip>
        </div>
      </div>

      {/* Footer Status & Metadata */}
      <div className="p-3 border-t border-zinc-900/90 bg-zinc-950/80">
        {!isCollapsed ? (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono-data text-zinc-400">
              <span>NETWORK STATUS</span>
              <span className="text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                ONLINE
              </span>
            </div>
            <div className="text-[10px] text-zinc-400 font-mono-data truncate uppercase">
              UPDATED {lastUpdatedText} · {totalEventsCount.toLocaleString()} EVENTS
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <button
              onClick={onToggleCollapse}
              title="Expand sidebar"
              className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <span className="w-2 h-2 rounded-full bg-emerald-500" title="Online" />
          </div>
        )}
      </div>
    </aside>
  );
}
