"use client";

import React, { useState, useEffect, useCallback } from "react";
import { CheckCircle2, RefreshCw, Inbox, Download, Mail } from "lucide-react";
import { listAlerts, acknowledgeAlert, type AlertData, type Supplier } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { exportAlertsCSV } from "@/lib/reportGenerator";

interface AlertsViewProps {
  suppliers?: Supplier[];
  onInvestigateSupplier?: (supplierId: string) => void;
  onRefresh?: () => void;
}

export default function AlertsView({
  suppliers = [],
  onInvestigateSupplier,
  onRefresh,
}: AlertsViewProps) {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<"active" | "all" | "acknowledged">("active");

  const supplierNameMap = new Map(suppliers.map((s) => [s.id, s.name]));

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listAlerts();
      setAlerts(data);
    } catch {
      // keep empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
      );
      onRefresh?.();
    } catch {
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
      );
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (statusFilter === "active" && a.acknowledged) return false;
    if (statusFilter === "acknowledged" && !a.acknowledged) return false;
    if (severityFilter !== "all" && a.severity.toLowerCase() !== severityFilter.toLowerCase()) return false;
    return true;
  });

  const activeCount = alerts.filter((a) => !a.acknowledged).length;

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return (
          <span className="text-[10px] font-mono-data uppercase font-bold px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300">
            CRITICAL
          </span>
        );
      case "high":
        return (
          <span className="text-[10px] font-mono-data uppercase font-bold px-2 py-0.5 rounded bg-orange-950/80 border border-orange-800 text-orange-300">
            HIGH
          </span>
        );
      case "medium":
        return (
          <span className="text-[10px] font-mono-data uppercase font-bold px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300">
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono-data uppercase font-bold px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
            LOW
          </span>
        );
    }
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
      return `${Math.floor(diffMins / 1440)}d ago`;
    } catch {
      return "RECENT";
    }
  };

  return (
    <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-6 h-full flex flex-col justify-between">
      <div>
        {/* Header & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-900 gap-3">
          <div className="space-y-0.5">
            <span className="technical-label">ANOMALY LOG & EXCEPTIONS</span>
            <h2 className="text-base font-bold tracking-tight text-zinc-100">
              Active Network Alerts ({activeCount})
            </h2>
            <p className="text-xs text-zinc-400">
              {activeCount > 0
                ? `${activeCount} threshold violations detected across the supplier network`
                : "No active alerts — all supplier dimensions within acceptable thresholds"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportAlertsCSV(alerts, suppliers)}
              className="h-8 px-3 text-xs bg-zinc-900 border-zinc-800 text-zinc-300 hover:text-white"
            >
              <Download className="w-3.5 h-3.5 mr-1.5" />
              Export CSV
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => { fetchAlerts(); onRefresh?.(); }}
              className="h-8 px-2.5 text-xs bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              Sync
            </Button>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="py-3 border-b border-zinc-900 flex items-center gap-3 text-xs font-mono-data">
          <div className="flex items-center gap-1 bg-zinc-900/80 border border-zinc-800 rounded p-0.5">
            <button
              onClick={() => setStatusFilter("active")}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                statusFilter === "active" ? "bg-orange-600 text-white font-semibold" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Active ({activeCount})
            </button>
            <button
              onClick={() => setStatusFilter("all")}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                statusFilter === "all" ? "bg-orange-600 text-white font-semibold" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              All History ({alerts.length})
            </button>
            <button
              onClick={() => setStatusFilter("acknowledged")}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                statusFilter === "acknowledged" ? "bg-orange-600 text-white font-semibold" : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Resolved ({alerts.length - activeCount})
            </button>
          </div>

          <div className="flex items-center gap-1.5 ml-auto">
            <span className="text-zinc-500 text-[10px] uppercase">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="h-7 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs outline-none"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        {/* Empty State */}
        {filteredAlerts.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Inbox className="w-8 h-8 text-zinc-700 mb-3" />
            <p className="text-sm font-semibold text-zinc-400">No alerts matching filter criteria</p>
            <p className="text-xs text-zinc-500 mt-1">
              Anomaly engine monitors continuous delivery variance, quality drops, and contract drift.
            </p>
          </div>
        )}

        {/* Alerts List */}
        <div className="divide-y divide-zinc-900/90 mt-2 space-y-0 max-h-[520px] overflow-y-auto pr-1">
          {filteredAlerts.map((alert) => {
            const supplierName = supplierNameMap.get(alert.supplier_id) || alert.supplier_id;

            return (
              <div
                key={alert.id}
                className={`py-4 transition-all duration-150 ${
                  alert.acknowledged ? "opacity-40" : "opacity-100"
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2.5">
                      {getSeverityBadge(alert.severity)}
                      <span className="text-xs font-bold text-zinc-100">
                        {alert.title}
                      </span>
                      <span className="text-zinc-600 font-mono-data">·</span>
                      <button
                        type="button"
                        onClick={() => onInvestigateSupplier?.(alert.supplier_id)}
                        className="text-[11px] font-mono-data text-orange-400 hover:text-orange-300 uppercase underline decoration-zinc-700 underline-offset-2 transition-colors"
                      >
                        {supplierName}
                      </button>
                    </div>

                    <p className="text-xs text-zinc-300 leading-relaxed font-normal">
                      {alert.description}
                    </p>

                    {alert.suggested_action && (
                      <div className="mt-2 text-xs bg-zinc-900/60 border border-zinc-800/80 rounded px-3 py-1.5 text-zinc-300 flex items-start gap-2">
                        <span className="text-orange-400 font-mono-data font-semibold uppercase text-[10px]">
                          ACTION:
                        </span>
                        <span>{alert.suggested_action}</span>
                      </div>
                    )}

                    <div className="flex items-center gap-4 text-[11px] font-mono-data text-zinc-400 pt-1">
                      <span>
                        METRIC:{" "}
                        <strong className="text-rose-400">
                          {alert.metric_value.toFixed(1)}
                        </strong>{" "}
                        (THRESHOLD {alert.threshold_value.toFixed(1)})
                      </span>
                      <span>{formatTimestamp(alert.fired_at)}</span>
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    {!alert.acknowledged ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleAcknowledge(alert.id)}
                        className="text-xs font-mono-data h-7 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-zinc-800"
                      >
                        Acknowledge
                      </Button>
                    ) : (
                      <span className="text-[11px] font-mono-data text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Acknowledged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="pt-4 border-t border-zinc-900 text-[11px] font-mono-data text-zinc-400 flex justify-between">
        <span>ALERT RULES MONITORED: DELIVERY SLA, DEFECTS, LATENCY, PRICING DRIFT</span>
        <span>NOTIFICATION CHANNELS: IN-APP · EMAIL DISPATCH (RESEND)</span>
      </div>
    </div>
  );
}
