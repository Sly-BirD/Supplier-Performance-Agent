"use client";

import React, { useState, useMemo } from "react";
import { ArrowDown, ArrowUp, Minus, RefreshCw, Upload, Search, Download, Filter, Layers, Check, Cable } from "lucide-react";
import { type Supplier, type ScorecardMap } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { exportSuppliersCSV } from "@/lib/reportGenerator";
import LiveConnectorsModal from "@/components/LiveConnectorsModal";

interface SupplierIntelligenceItem {
  id: string;
  name: string;
  score: number | null;
  trend: "up" | "down" | "flat";
  trendLabel: string;
  tier: string;
  category: string;
  region: string;
  contact?: string;
}

interface SuppliersViewProps {
  suppliers: Supplier[];
  scorecardMap: ScorecardMap;
  onSelectSupplier?: (supplierId: string) => void;
  onOpenUpload?: () => void;
  onRefresh?: () => void;
  onCompareSuppliers?: (selectedIds: string[]) => void;
}

export default function SuppliersView({
  suppliers,
  scorecardMap,
  onSelectSupplier,
  onOpenUpload,
  onRefresh,
  onCompareSuppliers,
}: SuppliersViewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [regionFilter, setRegionFilter] = useState<string>("all");
  const [trendFilter, setTrendFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "score-desc" | "score-asc">("score-desc");
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [isConnectorsOpen, setIsConnectorsOpen] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    await onRefresh?.();
    setRefreshing(false);
  };

  // Map suppliers to display items
  const displayItems: SupplierIntelligenceItem[] = useMemo(() => {
    return suppliers.map((s) => {
      const sc = scorecardMap[s.id];
      const score = sc?.composite_score ?? null;
      const rawTrend = sc?.trend;
      const tier = sc?.tier || "Unranked";

      let trend: "up" | "down" | "flat" = "flat";
      let trendLabel = "—";
      if (rawTrend === "improving") {
        trend = "up";
        trendLabel = "Improving";
      } else if (rawTrend === "declining") {
        trend = "down";
        trendLabel = "Declining";
      } else if (rawTrend === "stable") {
        trend = "flat";
        trendLabel = "Stable";
      }

      return {
        id: s.id,
        name: s.name,
        score,
        trend,
        trendLabel,
        tier,
        category: s.category || "General Supply",
        region: s.region || "Global",
        contact: s.contact_email || undefined,
      };
    });
  }, [suppliers, scorecardMap]);

  // Extract distinct regions for filter dropdown
  const uniqueRegions = useMemo(() => {
    const set = new Set<string>();
    suppliers.forEach((s) => {
      if (s.region) set.add(s.region);
    });
    return Array.from(set);
  }, [suppliers]);

  // Multi-dimensional filtering and sorting
  const filteredAndSortedItems = useMemo(() => {
    return displayItems
      .filter((item) => {
        // Search filter
        const matchesSearch =
          item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.region.toLowerCase().includes(searchTerm.toLowerCase());

        // Tier filter
        const matchesTier =
          tierFilter === "all" || item.tier.toLowerCase() === tierFilter.toLowerCase();

        // Region filter
        const matchesRegion =
          regionFilter === "all" || item.region.toLowerCase() === regionFilter.toLowerCase();

        // Trend filter
        const matchesTrend =
          trendFilter === "all" || item.trend === trendFilter;

        return matchesSearch && matchesTier && matchesRegion && matchesTrend;
      })
      .sort((a, b) => {
        if (sortBy === "name") return a.name.localeCompare(b.name);
        if (sortBy === "score-desc") return (b.score ?? -1) - (a.score ?? -1);
        if (sortBy === "score-asc") return (a.score ?? 101) - (b.score ?? 101);
        return 0;
      });
  }, [displayItems, searchTerm, tierFilter, regionFilter, trendFilter, sortBy]);

  const toggleCompare = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedForCompare.includes(id)) {
      setSelectedForCompare(selectedForCompare.filter((item) => item !== id));
    } else {
      if (selectedForCompare.length >= 4) {
        alert("Maximum 4 suppliers can be compared simultaneously.");
        return;
      }
      setSelectedForCompare([...selectedForCompare, id]);
    }
  };

  const getTierStyle = (tier: string) => {
    switch (tier.toLowerCase()) {
      case "preferred":
        return "text-emerald-400 font-medium";
      case "approved":
        return "text-blue-400 font-medium";
      case "watch":
        return "text-amber-400 font-medium";
      case "at-risk":
      case "at risk":
        return "text-rose-400 font-medium";
      default:
        return "text-zinc-500 font-medium";
    }
  };

  if (suppliers.length === 0) {
    return (
      <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-6 h-full flex flex-col items-center justify-center text-center">
        <span className="technical-label">SUPPLIER NETWORK DIRECTORY</span>
        <p className="text-xs text-zinc-500 mt-2">
          No suppliers found in database. Ingest a dataset (CSV / Excel) or load benchmark samples to populate.
        </p>
        <div className="flex items-center gap-2 mt-4">
          {onOpenUpload && (
            <Button
              size="sm"
              onClick={onOpenUpload}
              className="h-8 px-3 text-xs bg-orange-600 hover:bg-orange-500 text-white font-medium"
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" />
              Upload Dataset
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsConnectorsOpen(true)}
            className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white flex items-center gap-1.5"
          >
            <Cable className="w-3.5 h-3.5 text-orange-400" />
            <span>Live ERP Connectors</span>
            <span className="text-[9px] font-mono-data uppercase bg-orange-500/20 text-orange-400 border border-orange-500/30 px-1 py-0.2 rounded font-semibold">
              SOON
            </span>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-6 h-full flex flex-col justify-between">
      <div>
        {/* Top Header & Export Buttons */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-900">
          <div className="space-y-0.5">
            <span className="technical-label">SUPPLIER NETWORK DIRECTORY</span>
            <h2 className="text-base font-bold tracking-tight text-zinc-100">
              Active Network Intelligence ({filteredAndSortedItems.length} of {suppliers.length})
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportSuppliersCSV(suppliers, scorecardMap)}
              className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
              title="Download CSV Report"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Export CSV
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="h-8 px-2.5 text-xs bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200"
              title="Refresh directory"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConnectorsOpen(true)}
              className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white hover:border-zinc-700 flex items-center gap-1.5"
              title="Inspect Live ERP and Cloud Sheet connector roadmap"
            >
              <Cable className="w-3.5 h-3.5 text-orange-400" />
              <span>Live ERP / Sheets</span>
              <span className="text-[9px] font-mono-data uppercase bg-orange-500/20 text-orange-400 border border-orange-500/30 px-1 py-0.2 rounded font-semibold">
                SOON
              </span>
            </Button>

            {onOpenUpload && (
              <Button
                size="sm"
                onClick={onOpenUpload}
                className="h-8 px-3 text-xs bg-orange-600 hover:bg-orange-500 text-white font-medium"
              >
                <Upload className="w-3.5 h-3.5 mr-1.5" />
                Upload Data
              </Button>
            )}
          </div>
        </div>

        {/* Multi-Dimensional Filter Toolbar */}
        <div className="py-3 border-b border-zinc-900 flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative flex-1 min-w-[180px]">
            <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-zinc-500" />
            <Input
              placeholder="Filter by name or category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 h-8 text-xs bg-zinc-900/80 border-zinc-800 text-zinc-200 placeholder:text-zinc-500 focus-visible:ring-orange-500/40"
            />
          </div>

          {/* Tier Filter */}
          <div className="flex items-center gap-1.5 text-xs font-mono-data">
            <span className="text-zinc-500 text-[10px] uppercase">Tier:</span>
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="h-8 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs outline-none"
            >
              <option value="all">All Tiers</option>
              <option value="preferred">Preferred</option>
              <option value="approved">Approved</option>
              <option value="watch">Watch</option>
              <option value="at-risk">At-Risk</option>
            </select>
          </div>

          {/* Region Filter */}
          {uniqueRegions.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs font-mono-data">
              <span className="text-zinc-500 text-[10px] uppercase">Region:</span>
              <select
                value={regionFilter}
                onChange={(e) => setRegionFilter(e.target.value)}
                className="h-8 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs outline-none"
              >
                <option value="all">All Regions</option>
                {uniqueRegions.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Trend Filter */}
          <div className="flex items-center gap-1.5 text-xs font-mono-data">
            <span className="text-zinc-500 text-[10px] uppercase">Trend:</span>
            <select
              value={trendFilter}
              onChange={(e) => setTrendFilter(e.target.value)}
              className="h-8 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs outline-none"
            >
              <option value="all">All Trends</option>
              <option value="up">Improving (↑)</option>
              <option value="flat">Stable (—)</option>
              <option value="down">Declining (↓)</option>
            </select>
          </div>

          {/* Sort Control */}
          <div className="flex items-center gap-1.5 text-xs font-mono-data">
            <span className="text-zinc-500 text-[10px] uppercase">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="h-8 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs outline-none"
            >
              <option value="score-desc">Score (High to Low)</option>
              <option value="score-asc">Score (Low to High)</option>
              <option value="name">Supplier Name (A-Z)</option>
            </select>
          </div>
        </div>

        {/* Floating Compare Action Bar if suppliers selected */}
        {selectedForCompare.length > 0 && (
          <div className="my-2 p-2.5 rounded bg-orange-950/60 border border-orange-600/50 flex items-center justify-between animate-in fade-in duration-200">
            <div className="flex items-center gap-2 text-xs text-orange-200">
              <Layers className="w-4 h-4 text-orange-400" />
              <span>
                <strong>{selectedForCompare.length}</strong> supplier{selectedForCompare.length > 1 ? "s" : ""} selected for benchmark comparison
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => onCompareSuppliers?.(selectedForCompare)}
                className="h-7 px-3 text-xs bg-orange-600 hover:bg-orange-500 text-white font-semibold"
              >
                Compare Selected Now &rarr;
              </Button>
              <button
                onClick={() => setSelectedForCompare([])}
                className="text-[11px] font-mono-data text-zinc-400 hover:text-zinc-200 px-1"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Intelligence Table */}
        <div className="overflow-x-auto mt-2">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-900 text-[11px] font-mono-data uppercase tracking-wider text-zinc-400">
                <th className="py-2.5 px-3 w-10 text-center">COMPARE</th>
                <th className="py-2.5 px-3">SUPPLIER</th>
                <th className="py-2.5 px-3">SCORE</th>
                <th className="py-2.5 px-3">TREND</th>
                <th className="py-2.5 px-3">TIER</th>
                <th className="py-2.5 px-3">CATEGORY</th>
                <th className="py-2.5 px-3">REGION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-900/60 text-xs">
              {filteredAndSortedItems.map((item) => {
                const isChecked = selectedForCompare.includes(item.id);

                return (
                  <tr
                    key={item.id}
                    onClick={() => onSelectSupplier?.(item.id)}
                    className="hover:bg-zinc-900/40 cursor-pointer group transition-colors"
                  >
                    <td
                      className="py-2.5 px-3 text-center"
                      onClick={(e) => toggleCompare(item.id, e)}
                    >
                      <div
                        className={`w-3.5 h-3.5 mx-auto rounded-xs border flex items-center justify-center transition-colors ${
                          isChecked
                            ? "bg-orange-500 border-orange-400"
                            : "border-zinc-700 hover:border-zinc-500"
                        }`}
                      >
                        {isChecked && <Check className="w-2.5 h-2.5 text-black stroke-[3]" />}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-zinc-200 group-hover:text-orange-400 transition-colors">
                      {item.name}
                    </td>
                    <td className="py-2.5 px-3 font-mono-data font-bold text-zinc-100 text-sm">
                      {item.score !== null ? Math.round(item.score) : "—"}
                    </td>
                    <td className="py-2.5 px-3 font-mono-data">
                      <span
                        className={`inline-flex items-center gap-1 font-semibold ${
                          item.trend === "up"
                            ? "text-emerald-400"
                            : item.trend === "down"
                            ? "text-rose-400"
                            : "text-zinc-500"
                        }`}
                      >
                        {item.trend === "up" && <ArrowUp className="w-3 h-3 stroke-[2.5]" />}
                        {item.trend === "down" && <ArrowDown className="w-3 h-3 stroke-[2.5]" />}
                        {item.trend === "flat" && <Minus className="w-3 h-3 stroke-[2.5]" />}
                        {item.trendLabel}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={getTierStyle(item.tier)}>{item.tier}</span>
                    </td>
                    <td className="py-2.5 px-3 text-zinc-400">{item.category}</td>
                    <td className="py-2.5 px-3 text-zinc-400 font-mono-data text-[11px]">
                      {item.region}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Table Footer */}
      <div className="pt-4 mt-4 border-t border-zinc-900 flex items-center justify-between text-[11px] font-mono-data text-zinc-400">
        <span>SHOWING {filteredAndSortedItems.length} SUPPLIER NODES</span>
        <span>SELECT CHECKBOXES TO BENCHMARK SIDE-BY-SIDE · CLICK ANY ROW TO DRILL DOWN</span>
      </div>

      <LiveConnectorsModal
        open={isConnectorsOpen}
        onOpenChange={setIsConnectorsOpen}
        onOpenUpload={onOpenUpload}
      />
    </div>
  );
}
