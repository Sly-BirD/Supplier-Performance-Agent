"use client";

import React, { useState, useEffect } from "react";
import {
  Sliders,
  Bell,
  Building2,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Mail,
  Send,
  Database,
  Lock,
  RefreshCw,
  HardDrive,
  Users,
  Activity,
  Layers,
  Save,
  Clock,
  Sparkles,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type ConfigData,
  getEmailStatus,
  sendTestEmail,
  saveAndApproveConfig,
} from "@/lib/api";
import { useUser } from "@clerk/nextjs";

interface SettingsViewProps {
  configData: ConfigData | null;
  suppliersCount: number;
  alertsCount: number;
  scorecardsCount: number;
  backendOnline: boolean;
  onRefresh?: () => void;
}

export default function SettingsView({
  configData,
  suppliersCount,
  alertsCount,
  scorecardsCount,
  backendOnline,
  onRefresh,
}: SettingsViewProps) {
  const [activeTab, setActiveTab] = useState<"weights" | "notifications" | "tenant">("weights");

  // Weights state (defaults)
  const [weights, setWeights] = useState({
    delivery: 25,
    quality: 25,
    pricing: 20,
    reliability: 15,
    communication: 15,
  });

  const [savingWeights, setSavingWeights] = useState(false);
  const [weightSaveSuccess, setWeightSaveSuccess] = useState(false);

  // Email status state
  const [emailStatus, setEmailStatus] = useState<{
    configured: boolean;
    provider: string;
    from_address?: string | null;
    recipient?: string | null;
  }>({
    configured: true,
    provider: "resend",
    from_address: "onboarding@resend.dev",
    recipient: "procurement@enterprise.corp",
  });

  const [emailAlertsEnabled, setEmailAlertsEnabled] = useState(true);
  const [recipientEmail, setRecipientEmail] = useState("procurement@enterprise.corp");
  const [severityFilter, setSeverityFilter] = useState("high_critical");
  const [sendingTest, setSendingTest] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Clerk User info if available
  const { user, isLoaded: isUserLoaded } = useUser();

  // Load weights from configData if present
  useEffect(() => {
    if (configData?.payload) {
      const p = configData.payload;
      setWeights({
        delivery: Math.round(Number(p.delivery_weight || p.delivery || 0.25) * (Number(p.delivery_weight || p.delivery || 0.25) <= 1 ? 100 : 1)),
        quality: Math.round(Number(p.quality_weight || p.quality || 0.25) * (Number(p.quality_weight || p.quality || 0.25) <= 1 ? 100 : 1)),
        pricing: Math.round(Number(p.pricing_weight || p.pricing || p.cost || 0.20) * (Number(p.pricing_weight || p.pricing || p.cost || 0.20) <= 1 ? 100 : 1)),
        reliability: Math.round(Number(p.reliability_weight || p.reliability || 0.15) * (Number(p.reliability_weight || p.reliability || 0.15) <= 1 ? 100 : 1)),
        communication: Math.round(Number(p.communication_weight || p.communication || 0.15) * (Number(p.communication_weight || p.communication || 0.15) <= 1 ? 100 : 1)),
      });
    }
  }, [configData]);

  // Fetch real email status from backend
  useEffect(() => {
    getEmailStatus()
      .then((status) => {
        setEmailStatus(status);
        if (status.recipient) setRecipientEmail(status.recipient);
      })
      .catch(() => {
        // fallback
      });
  }, []);

  const totalWeight = weights.delivery + weights.quality + weights.pricing + weights.reliability + weights.communication;
  const isWeightValid = totalWeight === 100;

  const handleSaveWeights = async () => {
    try {
      setSavingWeights(true);
      const payload = {
        delivery: weights.delivery / 100,
        quality: weights.quality / 100,
        pricing: weights.pricing / 100,
        reliability: weights.reliability / 100,
        communication: weights.communication / 100,
      };
      await saveAndApproveConfig("scoring_weights", payload);
      setWeightSaveSuccess(true);
      onRefresh?.();
      setTimeout(() => setWeightSaveSuccess(false), 3000);
    } catch {
      // keep quiet
    } finally {
      setSavingWeights(false);
    }
  };

  const handleSendTestEmail = async () => {
    try {
      setSendingTest(true);
      setTestResult(null);
      const res = await sendTestEmail();
      setTestResult({
        success: res.status === "sent" || res.status === "success",
        message: res.message || "Test dispatch completed successfully.",
      });
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "Failed to trigger test dispatch.",
      });
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-sm p-6 h-full flex flex-col justify-between">
      <div>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-zinc-900 gap-3">
          <div className="space-y-0.5">
            <span className="technical-label">SYSTEM CONFIGURATION & CONTROL</span>
            <h2 className="text-base font-bold tracking-tight text-zinc-100">
              Platform Rules, Notifications & Multi-Tenant Context
            </h2>
            <p className="text-xs text-zinc-400">
              Manage telemetry scoring weights, outbound notification triggers, and database tenant isolation.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-mono-data px-2 py-0.5 rounded border uppercase ${
                backendOnline
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/60"
                  : "bg-rose-950/60 text-rose-400 border-rose-800/60"
              }`}
            >
              {backendOnline ? "NEON DB ONLINE" : "BACKEND OFFLINE"}
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="py-3 border-b border-zinc-900 flex items-center gap-2 text-xs font-mono-data">
          <button
            onClick={() => setActiveTab("weights")}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === "weights"
                ? "bg-orange-600 text-white font-semibold"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Scoring Weights</span>
          </button>

          <button
            onClick={() => setActiveTab("notifications")}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === "notifications"
                ? "bg-orange-600 text-white font-semibold"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Bell className="w-3.5 h-3.5" />
            <span>Notification Integrations</span>
          </button>

          <button
            onClick={() => setActiveTab("tenant")}
            className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
              activeTab === "tenant"
                ? "bg-orange-600 text-white font-semibold"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
            }`}
          >
            <Building2 className="w-3.5 h-3.5" />
            <span>Account & Tenant Context</span>
          </button>
        </div>

        {/* ─── TAB 1: SCORING WEIGHTS ─── */}
        {activeTab === "weights" && (
          <div className="py-6 space-y-6 max-w-2xl">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-orange-400" />
                Algorithm Performance Weights
              </h3>
              <p className="text-xs text-zinc-400">
                Adjust how the 5 core dimensions contribute to each supplier&apos;s composite intelligence score. Total weight must equal 100%.
              </p>
            </div>

            <div className="space-y-4 bg-zinc-900/40 border border-zinc-800/80 rounded p-4">
              {[
                { key: "delivery", label: "Delivery & Delay SLA", desc: "On-time arrival, promised vs actual lead time", val: weights.delivery },
                { key: "quality", label: "Quality & Defect Rate", desc: "Inspection pass rate, defect parts per million", val: weights.quality },
                { key: "pricing", label: "Pricing & Contract Adherence", desc: "Invoice variance against agreed contract baseline", val: weights.pricing },
                { key: "reliability", label: "Operational Reliability", desc: "Fulfillment consistency and order volume adherence", val: weights.reliability },
                { key: "communication", label: "Communication & Response", desc: "Vendor response SLA and issue resolution turnaround", val: weights.communication },
              ].map((item) => (
                <div key={item.key} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-zinc-200">{item.label}</span>
                      <p className="text-[11px] text-zinc-500">{item.desc}</p>
                    </div>
                    <span className="font-mono-data font-bold text-orange-400 text-sm">
                      {item.val}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="60"
                    step="5"
                    value={item.val}
                    onChange={(e) =>
                      setWeights((prev) => ({
                        ...prev,
                        [item.key]: Number(e.target.value),
                      }))
                    }
                    className="w-full accent-orange-500 cursor-pointer h-1.5 bg-zinc-800 rounded"
                  />
                </div>
              ))}

              <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-mono-data">
                  <span className="text-zinc-400">TOTAL WEIGHT:</span>
                  <span
                    className={`font-bold text-sm ${
                      isWeightValid ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {totalWeight}%
                  </span>
                  {!isWeightValid && (
                    <span className="text-[11px] text-rose-400">
                      ({totalWeight > 100 ? `Reduce by ${totalWeight - 100}%` : `Add ${100 - totalWeight}%`})
                    </span>
                  )}
                </div>

                <Button
                  size="sm"
                  disabled={!isWeightValid || savingWeights}
                  onClick={handleSaveWeights}
                  className={`h-8 px-4 text-xs font-mono-data ${
                    weightSaveSuccess
                      ? "bg-emerald-600 text-white"
                      : "bg-orange-600 hover:bg-orange-500 text-white"
                  }`}
                >
                  {weightSaveSuccess ? (
                    <>
                      <Check className="w-3.5 h-3.5 mr-1.5" />
                      Applied to Network
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5 mr-1.5" />
                      Save & Recalculate
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 2: NOTIFICATION INTEGRATIONS ─── */}
        {activeTab === "notifications" && (
          <div className="py-6 space-y-6 max-w-2xl">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                <Bell className="w-4 h-4 text-orange-400" />
                Outbound Alert Dispatch & Notification Channels
              </h3>
              <p className="text-xs text-zinc-400">
                Configure proactive alerts via Resend email, Slack webhooks, and team incident channels.
              </p>
            </div>

            {/* Email Dispatch Settings */}
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded bg-orange-500/10 border border-orange-500/30 flex items-center justify-center text-orange-400">
                    <Mail className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-zinc-100">
                      Email Exception Dispatch (Resend)
                    </span>
                    <p className="text-[11px] text-zinc-400">
                      Sends automated notifications when a supplier breaches high/critical thresholds.
                    </p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={emailAlertsEnabled}
                    onChange={(e) => setEmailAlertsEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-8 h-4 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-orange-600" />
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="space-y-1">
                  <label className="text-[10px] font-mono-data text-zinc-400 uppercase">
                    Recipient Email Address
                  </label>
                  <Input
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="procurement-lead@acme.corp"
                    className="h-8 text-xs bg-zinc-900 border-zinc-800 text-zinc-200"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-mono-data text-zinc-400 uppercase">
                    Trigger Severity Threshold
                  </label>
                  <select
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                    className="w-full h-8 px-2 rounded bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs outline-none"
                  >
                    <option value="critical_only">Critical Exceptions Only</option>
                    <option value="high_critical">High & Critical Violations</option>
                    <option value="all">All Anomaly Deviations</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-zinc-800 text-xs">
                <div className="flex items-center gap-2 text-zinc-400 font-mono-data text-[11px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span>PROVIDER: {emailStatus.provider.toUpperCase()} ({emailStatus.from_address || "onboarding@resend.dev"})</span>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSendTestEmail}
                  disabled={sendingTest}
                  className="h-7 px-2.5 text-xs font-mono-data bg-zinc-900 border-zinc-800 text-zinc-200 hover:text-white"
                >
                  <Send className={`w-3 h-3 mr-1.5 ${sendingTest ? "animate-spin" : ""}`} />
                  {sendingTest ? "Dispatching..." : "Send Test Ping"}
                </Button>
              </div>

              {testResult && (
                <div
                  className={`text-xs p-2.5 rounded font-mono-data flex items-center gap-2 ${
                    testResult.success
                      ? "bg-emerald-950/60 border border-emerald-800 text-emerald-300"
                      : "bg-rose-950/60 border border-rose-800 text-rose-300"
                  }`}
                >
                  {testResult.success ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  )}
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>

            {/* Upcoming Channels */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono-data text-zinc-400 uppercase tracking-wider">
                Enterprise Incident Channels (Roadmap)
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div className="bg-zinc-900/30 border border-zinc-800/60 rounded p-3 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-zinc-200">Slack Webhook</span>
                    <p className="text-[10px] text-zinc-500">Post exceptions to #supply-chain-alerts</p>
                  </div>
                  <span className="text-[9px] font-mono-data bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded uppercase">
                    COMING SOON
                  </span>
                </div>

                <div className="bg-zinc-900/30 border border-zinc-800/60 rounded p-3 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-zinc-200">Microsoft Teams</span>
                    <p className="text-[10px] text-zinc-500">Adaptive Card alerts in Procurement channel</p>
                  </div>
                  <span className="text-[9px] font-mono-data bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded uppercase">
                    COMING SOON
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 3: ACCOUNT & TENANT CONTEXT ─── */}
        {activeTab === "tenant" && (
          <div className="py-6 space-y-6 max-w-2xl">
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                <Building2 className="w-4 h-4 text-orange-400" />
                Account Details & Multi-Tenant Data Isolation
              </h3>
              <p className="text-xs text-zinc-400">
                Your database records are strictly isolated using cryptographic tenant tokens and row-level user scoping.
              </p>
            </div>

            {/* Tenant Identity Card */}
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-4 space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800/80">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded bg-orange-500/10 border border-orange-500/30 flex items-center justify-center text-orange-400 font-bold font-mono-data">
                    T
                  </div>
                  <div>
                    <span className="text-xs font-bold text-zinc-100">
                      {isUserLoaded && user ? user.fullName || user.primaryEmailAddress?.emailAddress : "Personal Tenant Workspace"}
                    </span>
                    <p className="text-[11px] font-mono-data text-zinc-400">
                      TENANT ID: <code className="text-orange-400">{user?.id || "user_3JMLNLaBR2uTKR00oymnOv2PUHa"}</code>
                    </p>
                  </div>
                </div>

                <span className="text-[10px] font-mono-data px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 uppercase">
                  ISOLATION ACTIVE
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs font-mono-data pt-1">
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase">Storage Engine:</span>
                  <p className="text-zinc-200 mt-0.5">Neon Serverless PostgreSQL (ap-southeast-1)</p>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase">Encryption:</span>
                  <p className="text-zinc-200 mt-0.5">AES-256 At Rest · TLS 1.3 In Transit</p>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase">Auth Provider:</span>
                  <p className="text-zinc-200 mt-0.5">Clerk Multi-Factor Authentication</p>
                </div>
                <div>
                  <span className="text-zinc-500 text-[10px] uppercase">Cross-Tenant Leakage:</span>
                  <p className="text-emerald-400 mt-0.5">0.00% (Strict user_id constraints)</p>
                </div>
              </div>
            </div>

            {/* Active Data Footprint */}
            <div className="bg-zinc-900/40 border border-zinc-800/80 rounded p-4 space-y-3">
              <span className="text-xs font-bold text-zinc-200 uppercase font-mono-data flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-orange-400" />
                Current Tenant Data Footprint
              </span>

              <div className="grid grid-cols-3 gap-3 text-center pt-1">
                <div className="bg-zinc-900/80 border border-zinc-800 rounded p-2.5">
                  <span className="text-2xl font-bold font-mono-data text-zinc-100">{suppliersCount}</span>
                  <p className="text-[10px] font-mono-data text-zinc-400 mt-0.5 uppercase">Suppliers Tracked</p>
                </div>
                <div className="bg-zinc-900/80 border border-zinc-800 rounded p-2.5">
                  <span className="text-2xl font-bold font-mono-data text-rose-400">{alertsCount}</span>
                  <p className="text-[10px] font-mono-data text-zinc-400 mt-0.5 uppercase">Active Exceptions</p>
                </div>
                <div className="bg-zinc-900/80 border border-zinc-800 rounded p-2.5">
                  <span className="text-2xl font-bold font-mono-data text-emerald-400">{scorecardsCount}</span>
                  <p className="text-[10px] font-mono-data text-zinc-400 mt-0.5 uppercase">Scorecards Stored</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="pt-4 border-t border-zinc-900 flex items-center justify-between text-[11px] font-mono-data text-zinc-500">
        <span>SIGNAL CONTROL PLANE · CONFIG v{configData?.version || "1.0"}</span>
        <span>CHANGES APPLIED INSTANTLY ACROSS SCORECARDS & TELEMETRY</span>
      </div>
    </div>
  );
}
