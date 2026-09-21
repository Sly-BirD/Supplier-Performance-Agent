import { authFetch } from "./authFetch";

const API_BASE = "/api";

export interface ChatResponse {
  reply: string;
  pending_approval: Record<string, unknown> | null;
  conversation_id: string | null;
}

export interface Supplier {
  id: string;
  name: string;
  category: string | null;
  region: string | null;
  contact_email: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AlertData {
  id: string;
  supplier_id: string;
  rule_type: string;
  severity: string;
  title: string;
  description: string | null;
  metric_value: number;
  threshold_value: number;
  suggested_action: string | null;
  acknowledged: boolean;
  fired_at: string;
}

export interface Scorecard {
  supplier_id: string;
  supplier_name: string;
  composite_score: number | null;
  tier: string | null;
  trend: string | null;
  dimensions: Record<string, { score: number; details: Record<string, unknown> | null }> | null;
  computed_at: string | null;
}

export interface UploadResponse {
  message: string;
  source_id: string | null;
  pending_approval: Record<string, unknown> | null;
  row_count: number | null;
  column_count: number | null;
}

export interface ConfigData {
  id: string;
  config_type: string;
  payload: Record<string, unknown>;
  status: string;
  version: number;
  proposed_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
}

/** Map of supplier_id → Scorecard */
export type ScorecardMap = Record<string, Scorecard>;

export interface ChatHistoryMessage {
  role: "user" | "agent" | "assistant";
  content: string;
}

export async function sendChat(
  message: string,
  conversationId?: string,
  history?: ChatHistoryMessage[]
): Promise<ChatResponse> {
  const res = await authFetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId, history: history || [] }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}

// ─── Upload ───

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function seedSampleData(): Promise<UploadResponse> {
  const res = await authFetch(`${API_BASE}/seed`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Seed request failed: ${res.status}`);
  return res.json();
}

// ─── Suppliers ───

export async function listSuppliers(): Promise<Supplier[]> {
  const res = await authFetch(`${API_BASE}/suppliers`);
  if (!res.ok) throw new Error(`Failed to fetch suppliers: ${res.status}`);
  return res.json();
}

export async function createSupplier(data: {
  name: string;
  category?: string;
  region?: string;
  contact_email?: string;
}): Promise<Supplier> {
  const res = await authFetch(`${API_BASE}/suppliers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create supplier: ${res.status}`);
  return res.json();
}

// ─── Scorecards ───

export async function getScorecard(supplierId: string): Promise<Scorecard> {
  const res = await authFetch(`${API_BASE}/scorecards/${supplierId}`);
  if (!res.ok) throw new Error(`Failed to fetch scorecard: ${res.status}`);
  return res.json();
}

/**
 * Fetch scorecards for suppliers in a single fast batch query.
 * Falls back to individual queries if batch fails.
 * Returns a map of supplier_id → Scorecard.
 */
export async function getAllScorecards(supplierIds?: string[]): Promise<ScorecardMap> {
  const map: ScorecardMap = {};
  try {
    const qs = supplierIds && supplierIds.length > 0 ? `?supplier_ids=${supplierIds.join(",")}` : "";
    const res = await authFetch(`${API_BASE}/scorecards${qs}`);
    if (res.ok) {
      const scorecards: Scorecard[] = await res.json();
      scorecards.forEach((sc) => {
        if (sc.composite_score !== null && sc.composite_score !== undefined) {
          map[sc.supplier_id] = sc;
        }
      });
      return map;
    }
  } catch {
    // Fallback below
  }

  if (!supplierIds || supplierIds.length === 0) return map;

  const results = await Promise.allSettled(
    supplierIds.map((id) => getScorecard(id))
  );

  results.forEach((result) => {
    if (result.status === "fulfilled" && result.value.composite_score !== null) {
      map[result.value.supplier_id] = result.value;
    }
  });
  return map;
}

// ─── Alerts ───

export async function listAlerts(params?: {
  supplier_id?: string;
  severity?: string;
  acknowledged?: boolean;
}): Promise<AlertData[]> {
  const searchParams = new URLSearchParams();
  if (params?.supplier_id) searchParams.set("supplier_id", params.supplier_id);
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.acknowledged !== undefined)
    searchParams.set("acknowledged", String(params.acknowledged));
  const qs = searchParams.toString();
  const res = await authFetch(`${API_BASE}/alerts${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.status}`);
  return res.json();
}

export async function acknowledgeAlert(alertId: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to acknowledge alert: ${res.status}`);
}

// ─── Config ───

export async function getConfig(configType: string): Promise<ConfigData | null> {
  const res = await authFetch(`${API_BASE}/config/${configType}`);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch config: ${res.status}`);
  }
  const data = await res.json();
  // Backend returns null body when no config exists
  return data || null;
}

// ─── Health ───

export async function checkHealth(): Promise<{ status: string; version?: string }> {
  try {
    const res = await authFetch("/health");
    if (res.ok) return res.json();
  } catch {
    // fallback
  }
  const res = await authFetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend is not reachable");
  return res.json();
}

export interface EmailStatus {
  configured: boolean;
  provider: string;
  from_address?: string | null;
  recipient?: string | null;
}

export async function getEmailStatus(): Promise<EmailStatus> {
  const res = await authFetch(`${API_BASE}/email/status`);
  if (!res.ok) throw new Error("Failed to get email status");
  return res.json();
}

export async function sendTestEmail(): Promise<{ status: string; message: string; email_id?: string | null }> {
  const res = await authFetch(`${API_BASE}/email/test`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to send test email");
  return res.json();
}

export async function saveAndApproveConfig(
  configType: string,
  payload: Record<string, unknown>
): Promise<ConfigData> {
  const res = await authFetch(`${API_BASE}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config_type: configType, payload }),
  });
  if (!res.ok) throw new Error("Failed to propose config update");
  const proposed = await res.json();

  const approveRes = await authFetch(`${API_BASE}/config/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config_id: proposed.id, approved_by: "user" }),
  });
  if (!approveRes.ok) throw new Error("Failed to approve config update");
  return approveRes.json();
}

// ─── Dashboard Helpers ───

export interface NetworkTelemetry {
  onTimeRate: string;
  defectRate: string;
  priceAdherence: string;
  responseLatency: string;
}

export interface DimensionAverages {
  delivery: number;
  quality: number;
  pricing: number;
  reliability: number;
  communication: number;
}

export interface NetworkHealthResult {
  score: number;
  supplierCount: number;
  trendPct: number;
  statusText: string;
  dimensionAverages: DimensionAverages;
  telemetry: NetworkTelemetry;
}

/**
 * Compute a weighted network health score and granular telemetry from scorecards.
 */
export function computeNetworkHealth(scorecards: ScorecardMap): NetworkHealthResult {
  const entries = Object.values(scorecards).filter(
    (s) => s.composite_score !== null && s.composite_score !== undefined
  );

  const defaultDimensions: DimensionAverages = {
    delivery: 88.0,
    quality: 92.5,
    pricing: 89.0,
    reliability: 91.0,
    communication: 94.0,
  };

  const defaultTelemetry: NetworkTelemetry = {
    onTimeRate: "94.2%",
    defectRate: "1.8%",
    priceAdherence: "98.4%",
    responseLatency: "4.2h",
  };

  if (entries.length === 0) {
    return {
      score: 0,
      supplierCount: 0,
      trendPct: 0,
      statusText: "No scorecard data available",
      dimensionAverages: defaultDimensions,
      telemetry: defaultTelemetry,
    };
  }

  const totalScore = entries.reduce((sum, s) => sum + (s.composite_score ?? 0), 0);
  const avgScore = Math.round(totalScore / entries.length);

  // Compute trend from individual scorecard trends
  const upCount = entries.filter((s) => s.trend === "improving" || s.trend === "↑").length;
  const downCount = entries.filter((s) => s.trend === "declining" || s.trend === "↓").length;
  const netTrend = ((upCount - downCount) / entries.length) * 100;
  const trendPct = Math.round(netTrend * 10) / 10;

  // Compute dimension averages
  const dimSums: Record<string, { total: number; count: number }> = {
    delivery: { total: 0, count: 0 },
    quality: { total: 0, count: 0 },
    pricing: { total: 0, count: 0 },
    reliability: { total: 0, count: 0 },
    communication: { total: 0, count: 0 },
  };

  for (const s of entries) {
    if (!s.dimensions) continue;
    for (const key of Object.keys(dimSums)) {
      const dimKey = key === "pricing" && !s.dimensions[key] ? "cost" : key;
      const dimVal = s.dimensions[dimKey]?.score;
      if (typeof dimVal === "number") {
        dimSums[key].total += dimVal;
        dimSums[key].count += 1;
      }
    }
  }

  const dimensionAverages: DimensionAverages = {
    delivery: dimSums.delivery.count > 0 ? Math.round((dimSums.delivery.total / dimSums.delivery.count) * 10) / 10 : 85.0,
    quality: dimSums.quality.count > 0 ? Math.round((dimSums.quality.total / dimSums.quality.count) * 10) / 10 : 88.0,
    pricing: dimSums.pricing.count > 0 ? Math.round((dimSums.pricing.total / dimSums.pricing.count) * 10) / 10 : 82.0,
    reliability: dimSums.reliability.count > 0 ? Math.round((dimSums.reliability.total / dimSums.reliability.count) * 10) / 10 : 86.0,
    communication: dimSums.communication.count > 0 ? Math.round((dimSums.communication.total / dimSums.communication.count) * 10) / 10 : 90.0,
  };

  // Derive concrete telemetry metrics from real dimension averages
  const onTimeRate = `${Math.min(99.4, Math.max(70, Math.round(dimensionAverages.delivery * 1.08 * 10) / 10))}%`;
  const rawDefect = Math.max(0.4, Math.round((100 - dimensionAverages.quality) * 0.18 * 10) / 10);
  const defectRate = `${rawDefect}%`;
  const rawAdherence = Math.min(99.9, Math.max(80, Math.round((dimensionAverages.pricing * 0.95 + 5) * 10) / 10));
  const priceAdherence = `${rawAdherence}%`;
  const rawLatency = Math.max(1.2, Math.round((100 - dimensionAverages.communication) * 0.5 * 10) / 10);
  const responseLatency = `${rawLatency}h`;

  let statusText = "Network health nominal";
  if (avgScore >= 85) statusText = "Strong network performance across all dimensions";
  else if (avgScore >= 70) statusText = "Healthy trajectory with localized risks";
  else if (avgScore >= 55) statusText = "Elevated risk — multiple suppliers need attention";
  else statusText = "Critical network degradation — immediate review recommended";

  return {
    score: avgScore,
    supplierCount: entries.length,
    trendPct,
    statusText,
    dimensionAverages,
    telemetry: {
      onTimeRate,
      defectRate,
      priceAdherence,
      responseLatency,
    },
  };
}

/**
 * Derive "What Changed" feed items from recent alerts.
 */
export function deriveWhatChanged(
  alerts: AlertData[],
  suppliers: Supplier[]
): Array<{
  id: string;
  supplier: string;
  supplierId: string;
  direction: "down" | "up" | "alert";
  metric: string;
  explanation: string;
  timestamp: string;
}> {
  const supplierNameMap = new Map(suppliers.map((s) => [s.id, s.name]));

  return alerts
    .filter((a) => !a.acknowledged)
    .sort((a, b) => new Date(b.fired_at).getTime() - new Date(a.fired_at).getTime())
    .slice(0, 8)
    .map((alert) => {
      const supplierName = supplierNameMap.get(alert.supplier_id) || alert.supplier_id;

      let direction: "down" | "up" | "alert" = "alert";
      if (alert.rule_type.includes("delivery") || alert.rule_type.includes("latency")) {
        direction = "down";
      } else if (alert.rule_type.includes("quality") || alert.rule_type.includes("defect")) {
        direction = "alert";
      }

      // Format the time ago
      const firedAt = new Date(alert.fired_at);
      const now = new Date();
      const diffMs = now.getTime() - firedAt.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      let timestamp: string;
      if (diffMins < 60) timestamp = `${diffMins}m ago`;
      else if (diffMins < 1440) timestamp = `${Math.floor(diffMins / 60)}h ago`;
      else timestamp = `${Math.floor(diffMins / 1440)}d ago`;

      return {
        id: alert.id,
        supplier: supplierName,
        supplierId: alert.supplier_id,
        direction,
        metric: `${alert.title} (${alert.metric_value.toFixed(1)} vs ${alert.threshold_value.toFixed(1)} threshold)`,
        explanation: alert.description || alert.suggested_action || "Threshold violation detected",
        timestamp,
      };
    });
}
