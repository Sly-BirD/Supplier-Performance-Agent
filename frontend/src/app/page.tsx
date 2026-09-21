"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import Sidebar, { type NavPage } from "@/components/Sidebar";
import NetworkHealth from "@/components/NetworkHealth";
import AttentionSummary from "@/components/AttentionSummary";
import NetworkTrajectory from "@/components/NetworkTrajectory";
import WhatChanged from "@/components/WhatChanged";
import ScorecardPanel from "@/components/ScorecardPanel";
import SuppliersView from "@/components/SuppliersView";
import SupplierCompareView from "@/components/SupplierCompareView";
import AlertsView from "@/components/AlertsView";
import ChatPanel from "@/components/ChatPanel";
import DataHealthModal from "@/components/DataHealthModal";
import SettingsView from "@/components/SettingsView";
import ResizeHandle from "@/components/ui/ResizeHandle";
import { UserNav } from "@/components/UserNav";
import { generateExecutiveReport } from "@/lib/reportGenerator";
import { onAuthChange } from "@/lib/authFetch";
import {
  listSuppliers,
  listAlerts,
  checkHealth,
  getAllScorecards,
  getConfig,
  computeNetworkHealth,
  deriveWhatChanged,
  type Supplier,
  type AlertData,
  type ScorecardMap,
  type ConfigData,
} from "@/lib/api";
import { Sparkles, FileSpreadsheet, Activity, ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  const [activePage, setActivePage] = useState<NavPage>("dashboard");
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [scorecardMap, setScorecardMap] = useState<ScorecardMap>({});
  const [configData, setConfigData] = useState<ConfigData | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState<string | null>(null);
  const [compareSupplierIds, setCompareSupplierIds] = useState<string[]>([]);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isHealthModalOpen, setIsHealthModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [leftWidth, setLeftWidth] = useState(256);
  const [rightWidth, setRightWidth] = useState(420);
  const [lastFetchTime, setLastFetchTime] = useState<string>("just now");

  // Global keyboard shortcut: ⌘K or Ctrl+K toggles the right chatbot sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsChatOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Memoize supplier ID→name lookup
  const supplierNameMap = useMemo(
    () => new Map(suppliers.map((s) => [s.id, s.name])),
    [suppliers]
  );

  // Fetch all dashboard data concurrently (no waterfall)
  const fetchStats = useCallback(async () => {
    try {
      const [suppliersData, alertsData, scorecardsData, config] = await Promise.all([
        listSuppliers().catch(() => [] as Supplier[]),
        listAlerts().catch(() => [] as AlertData[]),
        getAllScorecards().catch(() => ({} as ScorecardMap)),
        getConfig("scoring_weights").catch(() => null),
      ]);
      setSuppliers(suppliersData);
      setAlerts(alertsData);
      setScorecardMap(scorecardsData);
      setConfigData(config);
      setDataLoaded(true);
      setLastFetchTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    } catch {
      setDataLoaded(true);
    }
  }, []);

  useEffect(() => {
    checkHealth()
      .then(() => {
        setBackendOnline(true);
        fetchStats();
      })
      .catch(() => {
        setBackendOnline(false);
        setDataLoaded(true);
      });
  }, [fetchStats]);

  // Re-fetch data whenever user signs in, signs out, or token changes
  useEffect(() => {
    const unsubscribe = onAuthChange(() => {
      fetchStats();
    });
    return unsubscribe;
  }, [fetchStats]);

  // Derive metrics dynamically
  const networkHealth = useMemo(
    () => computeNetworkHealth(scorecardMap),
    [scorecardMap]
  );

  const { activeAlerts, activeAlertsCount, criticalCount, deterioratingCount } = useMemo(() => {
    const active = alerts.filter((a) => !a.acknowledged);
    let crit = 0;
    let det = 0;
    for (const a of active) {
      if (a.severity === "critical") crit++;
      else if (a.severity === "high" || a.severity === "medium") det++;
    }
    return {
      activeAlerts: active,
      activeAlertsCount: active.length,
      criticalCount: crit,
      deterioratingCount: det,
    };
  }, [alerts]);

  const totalSuppliersCount = suppliers.length;

  const whatChangedItems = useMemo(
    () => deriveWhatChanged(alerts, suppliers),
    [alerts, suppliers]
  );

  const effectiveSupplierId = useMemo(
    () => selectedSupplierId || (suppliers.length > 0 ? suppliers[0].id : null),
    [selectedSupplierId, suppliers]
  );

  // Handlers
  const handleSelectSupplierById = (id: string) => {
    setSelectedSupplierId(id);
  };

  const handleSelectSupplierByName = (name: string) => {
    const supplier = suppliers.find((s) => s.name === name);
    if (supplier) {
      setSelectedSupplierId(supplier.id);
    }
  };

  const handleLaunchCompare = (ids: string[]) => {
    setCompareSupplierIds(ids);
    setActivePage("compare");
  };

  const handleToggleSidebar = () => {
    setIsSidebarCollapsed((prev) => !prev);
  };

  // Render the active main view
  const renderContent = () => {
    switch (activePage) {
      case "chat":
        return (
          <ChatPanel
            suppliers={suppliers}
            alerts={alerts}
            onRefresh={fetchStats}
            onSelectSupplier={(id) => {
              setSelectedSupplierId(id);
              setActivePage("suppliers");
            }}
            onCompareSuppliers={handleLaunchCompare}
          />
        );

      case "compare":
        return (
          <SupplierCompareView
            suppliers={suppliers}
            scorecardMap={scorecardMap}
            initialSelectedIds={compareSupplierIds}
            onClose={() => setActivePage("dashboard")}
            onSelectSupplier={(id) => {
              setSelectedSupplierId(id);
              setActivePage("suppliers");
            }}
          />
        );

      case "suppliers":
        return (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
            <div className="lg:col-span-2 h-full">
              <SuppliersView
                suppliers={suppliers}
                scorecardMap={scorecardMap}
                onSelectSupplier={handleSelectSupplierById}
                onOpenUpload={() => setIsChatOpen(true)}
                onRefresh={fetchStats}
                onCompareSuppliers={handleLaunchCompare}
              />
            </div>
            <div className="h-full">
              <ScorecardPanel supplierId={effectiveSupplierId} />
            </div>
          </div>
        );

      case "alerts":
        return (
          <AlertsView
            suppliers={suppliers}
            onInvestigateSupplier={(supplierId) => {
              setSelectedSupplierId(supplierId);
              setActivePage("suppliers");
            }}
            onRefresh={fetchStats}
          />
        );

      case "settings":
        return (
          <SettingsView
            configData={configData}
            suppliersCount={suppliers.length}
            alertsCount={alerts.length}
            scorecardsCount={Object.keys(scorecardMap).length}
            backendOnline={Boolean(backendOnline)}
            onRefresh={fetchStats}
          />
        );

      default:
        // Main Dashboard: Asymmetric Editorial Composition
        return (
          <div className="space-y-6">
            {/* Top Editorial Row: Asymmetric 60/40 */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left 62%: Network Health Hero + Trajectory Sparkline */}
              <div className="lg:col-span-7 bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-6 flex flex-col space-y-6">
                <NetworkHealth
                  score={
                    networkHealth.score > 0 ? networkHealth.score : undefined
                  }
                  trendPct={networkHealth.trendPct}
                  supplierCount={totalSuppliersCount}
                  eventCount={alerts.length}
                  lastUpdated={lastFetchTime}
                  statusText={networkHealth.statusText}
                  dimensionAverages={networkHealth.dimensionAverages}
                  telemetry={networkHealth.telemetry}
                  onOpenDiagnostics={() => setIsHealthModalOpen(true)}
                />
                <NetworkTrajectory
                  currentScore={networkHealth.score > 0 ? networkHealth.score : undefined}
                  changeLabel={
                    networkHealth.trendPct !== 0
                      ? `${networkHealth.trendPct > 0 ? "+" : ""}${networkHealth.trendPct}% vs prior cycle`
                      : undefined
                  }
                />
              </div>

              {/* Right 38%: Exceptions Summary + Spotlight Scorecard */}
              <div className="lg:col-span-5 space-y-6 flex flex-col">
                <AttentionSummary
                  activeAlertsCount={activeAlertsCount}
                  criticalCount={criticalCount}
                  deterioratingCount={deterioratingCount}
                  onReviewExceptions={() => setActivePage("alerts")}
                />
                <ScorecardPanel supplierId={effectiveSupplierId} />
              </div>
            </div>

            {/* Middle Section: What Changed Operational Shifts */}
            <div>
              <WhatChanged
                items={whatChangedItems}
                onSelectSupplier={handleSelectSupplierByName}
              />
            </div>

            {/* Bottom Section: Inline Supplier Directory */}
            <div>
              <SuppliersView
                suppliers={suppliers}
                scorecardMap={scorecardMap}
                onSelectSupplier={handleSelectSupplierById}
                onOpenUpload={() => setIsChatOpen(true)}
                onRefresh={fetchStats}
                onCompareSuppliers={handleLaunchCompare}
              />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="flex h-screen w-screen bg-background overflow-hidden select-none">
      {/* Resizable Left Sidebar */}
      <div className="relative flex shrink-0 h-full">
        <Sidebar
          width={isSidebarCollapsed ? 68 : leftWidth}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
          activePage={activePage}
          onNavigate={setActivePage}
          supplierCount={totalSuppliersCount}
          alertCount={activeAlertsCount}
          isChatOpen={isChatOpen}
          onToggleChat={() => setIsChatOpen((prev) => !prev)}
          lastUpdatedText={lastFetchTime}
          totalEventsCount={alerts.length}
        />
        {!isSidebarCollapsed && (
          <ResizeHandle
            side="right"
            onResize={(clientX) => setLeftWidth(Math.min(380, Math.max(200, clientX)))}
            onReset={() => setLeftWidth(256)}
          />
        )}
      </div>

      {/* Main Control Room Container */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0 bg-background select-text">
        {/* Editorial Hairline Header */}
        <header className="h-14 min-h-[3.5rem] px-6 border-b border-zinc-900 flex items-center justify-between bg-zinc-950/80 shrink-0">
          <div className="flex items-center gap-3">
            {isSidebarCollapsed && (
              <button
                type="button"
                onClick={handleToggleSidebar}
                title="Expand sidebar"
                className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
            <span className="text-xs font-mono-data uppercase tracking-wider font-semibold text-zinc-300">
              {activePage === "dashboard" && "CONTROL OVERVIEW"}
              {activePage === "chat" && "INTELLIGENCE CONSOLE"}
              {activePage === "suppliers" && "SUPPLIER NETWORK"}
              {activePage === "compare" && "SUPPLIER BENCHMARK & COMPARISON"}
              {activePage === "alerts" && "EXCEPTIONS & ANOMALIES"}
              {activePage === "settings" && "SYSTEM CONFIGURATION"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Executive Report Print/PDF Generator */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => generateExecutiveReport(networkHealth, suppliers, scorecardMap, alerts)}
              className="h-8 px-2.5 text-xs font-mono-data bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 border-zinc-800 hover:text-white"
              title="Generate 1-page executive printable report"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 mr-1 text-orange-400" />
              <span>Report Brief</span>
            </Button>

            {/* ⌘K Toggle Button for Chatbot Sidebar */}
            <button
              type="button"
              onClick={() => setIsChatOpen((prev) => !prev)}
              className={`flex items-center gap-2 h-8 px-3 rounded text-xs font-mono-data border transition-colors ${
                isChatOpen
                  ? "bg-orange-950/60 text-orange-300 border-orange-500/50 shadow-[0_0_10px_rgba(249,115,22,0.15)]"
                  : "bg-zinc-900/80 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border-zinc-800"
              }`}
              title="Toggle Signal AI Copilot sidebar (⌘K)"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isChatOpen ? "text-orange-400" : "text-zinc-400"}`} />
              <span>Signal Copilot</span>
              <kbd className="px-1 py-0.2 text-[9px] bg-zinc-950 text-zinc-400 border border-zinc-800 rounded">
                ⌘K
              </kbd>
            </button>

            {/* Rich Data Health Diagnostic Indicator */}
            <button
              type="button"
              onClick={() => setIsHealthModalOpen(true)}
              className="flex items-center gap-1.5 text-[11px] font-mono-data px-2.5 py-1 rounded bg-zinc-900/50 hover:bg-zinc-900 border border-zinc-800/80 text-zinc-300 hover:text-white transition-colors"
              title="Open full Data Health Diagnostics"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendOnline === null
                    ? "bg-zinc-500"
                    : backendOnline
                    ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)]"
                    : "bg-rose-500 animate-pulse"
                }`}
              />
              <Activity className="w-3 h-3 text-zinc-400" />
              <span>
                {backendOnline === null
                  ? "HEALTH: SYNCING"
                  : backendOnline
                  ? "DATA HEALTH: NOMINAL"
                  : "DATA HEALTH: DEGRADED"}
              </span>
            </button>

            {/* User Profile / Auth Navigation */}
            <UserNav />
          </div>
        </header>

        {/* Scrollable Body Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderContent()}
        </div>
      </main>

      {/* Resizable Right Sidebar: Signal AI Chatbot */}
      {isChatOpen && (
        <aside
          style={{ width: `${rightWidth}px` }}
          className="relative shrink-0 border-l border-zinc-800/80 bg-zinc-950 flex flex-col h-full z-20 transition-[width] duration-75 select-text"
        >
          <ResizeHandle
            side="left"
            onResize={(clientX) => {
              const newWidth = window.innerWidth - clientX;
              setRightWidth(Math.min(750, Math.max(320, newWidth)));
            }}
            onReset={() => setRightWidth(420)}
          />
          <ChatPanel
            suppliers={suppliers}
            alerts={alerts}
            onClose={() => setIsChatOpen(false)}
            onRefresh={fetchStats}
            onSelectSupplier={(id) => {
              setSelectedSupplierId(id);
              setActivePage("suppliers");
            }}
            onCompareSuppliers={handleLaunchCompare}
            className="border-none rounded-none h-full"
          />
        </aside>
      )}

      {/* Interactive Data Health Diagnostic Modal */}
      <DataHealthModal
        isOpen={isHealthModalOpen}
        onClose={() => setIsHealthModalOpen(false)}
        supplierCount={totalSuppliersCount}
        alertCount={activeAlertsCount}
        backendOnline={backendOnline}
      />
    </div>
  );
}
