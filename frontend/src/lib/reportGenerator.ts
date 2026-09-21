/**
 * Report Generation Utility
 * Generates downloadable CSV reports and executive print/PDF briefs.
 */

import { type Supplier, type ScorecardMap, type AlertData } from "@/lib/api";

/**
 * Download a generated CSV file in the browser
 */
function downloadCSV(filename: string, csvContent: string) {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export suppliers directory with performance metrics to CSV
 */
export function exportSuppliersCSV(suppliers: Supplier[], scorecardMap: ScorecardMap) {
  const headers = [
    "Supplier ID",
    "Supplier Name",
    "Category",
    "Region",
    "Contact Email",
    "Composite Score",
    "Tier",
    "Trend",
    "Quality Score",
    "Delivery Score",
    "Pricing Score",
    "Communication Score",
    "Reliability Score",
    "Last Computed",
  ];

  const rows = suppliers.map((s) => {
    const sc = scorecardMap[s.id];
    const dims = sc?.dimensions || {};
    const quality = dims["quality"]?.score ?? "N/A";
    const delivery = dims["delivery"]?.score ?? "N/A";
    const pricing = dims["pricing"]?.score ?? "N/A";
    const comm = dims["communication"]?.score ?? "N/A";
    const reliability = dims["reliability"]?.score ?? "N/A";

    return [
      `"${s.id}"`,
      `"${s.name.replace(/"/g, '""')}"`,
      `"${(s.category || "General").replace(/"/g, '""')}"`,
      `"${(s.region || "Global").replace(/"/g, '""')}"`,
      `"${s.contact_email || ""}"`,
      sc?.composite_score !== null && sc?.composite_score !== undefined ? sc.composite_score : "N/A",
      `"${sc?.tier || "N/A"}"`,
      `"${sc?.trend || "N/A"}"`,
      quality,
      delivery,
      pricing,
      comm,
      reliability,
      `"${sc?.computed_at || ""}"`,
    ].join(",");
  });

  const csv = [headers.join(","), ...rows].join("\n");
  const dateStr = new Date().toISOString().split("T")[0];
  downloadCSV(`signal_suppliers_report_${dateStr}.csv`, csv);
}

/**
 * Export network alerts & anomalies to CSV
 */
export function exportAlertsCSV(alerts: AlertData[], suppliers: Supplier[]) {
  const supplierNameMap = new Map(suppliers.map((s) => [s.id, s.name]));

  const headers = [
    "Alert ID",
    "Supplier ID",
    "Supplier Name",
    "Severity",
    "Rule Type",
    "Title",
    "Description",
    "Metric Value",
    "Threshold Value",
    "Suggested Action",
    "Status",
    "Fired At",
  ];

  const rows = alerts.map((a) => {
    const supName = supplierNameMap.get(a.supplier_id) || a.supplier_id;
    return [
      `"${a.id}"`,
      `"${a.supplier_id}"`,
      `"${supName.replace(/"/g, '""')}"`,
      `"${a.severity.toUpperCase()}"`,
      `"${a.rule_type}"`,
      `"${a.title.replace(/"/g, '""')}"`,
      `"${(a.description || "").replace(/"/g, '""')}"`,
      a.metric_value,
      a.threshold_value,
      `"${(a.suggested_action || "").replace(/"/g, '""')}"`,
      a.acknowledged ? "Acknowledged" : "Active",
      `"${a.fired_at}"`,
    ].join(",");
  });

  const csv = [headers.join(","), ...rows].join("\n");
  const dateStr = new Date().toISOString().split("T")[0];
  downloadCSV(`signal_alerts_exceptions_${dateStr}.csv`, csv);
}

/**
 * Export supplier comparison matrix to CSV
 */
export function exportComparisonCSV(selectedSuppliers: Supplier[], scorecardMap: ScorecardMap) {
  const headers = [
    "Metric / Dimension",
    ...selectedSuppliers.map((s) => `"${s.name.replace(/"/g, '""')}"`),
  ];

  const dimensions = ["quality", "delivery", "pricing", "communication", "reliability"];

  const rows = [
    [
      "Composite Index Score",
      ...selectedSuppliers.map((s) => scorecardMap[s.id]?.composite_score ?? "N/A"),
    ].join(","),
    [
      "Performance Tier",
      ...selectedSuppliers.map((s) => `"${scorecardMap[s.id]?.tier || "N/A"}"`),
    ].join(","),
    [
      "Trajectory Trend",
      ...selectedSuppliers.map((s) => `"${scorecardMap[s.id]?.trend || "N/A"}"`),
    ].join(","),
    [
      "Category",
      ...selectedSuppliers.map((s) => `"${s.category || "General"}"`),
    ].join(","),
    [
      "Region",
      ...selectedSuppliers.map((s) => `"${s.region || "Global"}"`),
    ].join(","),
    ...dimensions.map((dim) => {
      const dimTitle = dim.charAt(0).toUpperCase() + dim.slice(1);
      return [
        `${dimTitle} Score`,
        ...selectedSuppliers.map((s) => scorecardMap[s.id]?.dimensions?.[dim]?.score ?? "N/A"),
      ].join(",");
    }),
  ];

  const csv = [headers.join(","), ...rows].join("\n");
  const dateStr = new Date().toISOString().split("T")[0];
  downloadCSV(`signal_supplier_comparison_${dateStr}.csv`, csv);
}

/**
 * Trigger an executive printable intelligence report (opens clean print dialogue / PDF preview)
 */
export function generateExecutiveReport(
  networkHealth: { score: number; trendPct: number; supplierCount: number; statusText: string },
  suppliers: Supplier[],
  scorecardMap: ScorecardMap,
  alerts: AlertData[]
) {
  const activeAlerts = alerts.filter((a) => !a.acknowledged);
  const criticalCount = activeAlerts.filter((a) => a.severity === "critical").length;
  const supplierNameMap = new Map(suppliers.map((s) => [s.id, s.name]));

  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    alert("Please allow popups to generate the executive report.");
    return;
  }

  const suppliersHtml = suppliers
    .slice(0, 15)
    .map((s) => {
      const sc = scorecardMap[s.id];
      return `
      <tr>
        <td style="padding: 6px 10px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">${s.name}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #e5e7eb; font-family: monospace;">${sc?.composite_score ?? "—"}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #e5e7eb; text-transform: uppercase;">${sc?.tier || "—"}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #e5e7eb;">${s.category || "General"}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #e5e7eb;">${s.region || "Global"}</td>
      </tr>
    `;
    })
    .join("");

  const alertsHtml = activeAlerts
    .slice(0, 5)
    .map((a) => {
      const sup = supplierNameMap.get(a.supplier_id) || a.supplier_id;
      return `
      <div style="margin-bottom: 8px; padding: 8px; border-left: 3px solid ${
        a.severity === "critical" ? "#ef4444" : "#f59e0b"
      }; background: #f9fafb;">
        <div style="font-weight: 600; font-size: 13px;">${a.title} &mdash; <span style="font-weight: 400; color: #4b5563;">${sup}</span></div>
        <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">${a.description || ""}</div>
      </div>
    `;
    })
    .join("");

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <title>Signal Executive Intelligence Brief — ${new Date().toLocaleDateString()}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #111827; padding: 36px; line-height: 1.5; }
          .header { display: flex; justify-content: space-between; border-bottom: 2px solid #111827; padding-bottom: 16px; margin-bottom: 24px; }
          .title { font-size: 20px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; }
          .subtitle { font-size: 12px; color: #6b7280; margin-top: 4px; }
          .metric-cards { display: flex; gap: 20px; margin-bottom: 28px; }
          .metric-card { flex: 1; border: 1px solid #e5e7eb; border-radius: 6px; padding: 14px; }
          .metric-val { font-size: 28px; font-weight: 800; font-family: monospace; }
          .metric-lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
          th { text-align: left; padding: 8px 10px; background: #f3f4f6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
          @media print {
            body { padding: 16px; }
            button { display: none !important; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <div class="title">SIGNAL INTELLIGENCE &bull; EXECUTIVE BRIEF</div>
            <div class="subtitle">Autonomous Supplier Performance & Risk Trajectory Report</div>
          </div>
          <div style="text-align: right; font-size: 12px; color: #4b5563;">
            Generated on: <strong>${new Date().toLocaleString()}</strong>
          </div>
        </div>

        <div class="metric-cards">
          <div class="metric-card">
            <div class="metric-lbl">Network Intelligence Index</div>
            <div class="metric-val">${networkHealth.score}</div>
            <div style="font-size: 11px; color: #10b981;">Trend: ${networkHealth.trendPct > 0 ? "+" : ""}${networkHealth.trendPct}% vs prior cycle</div>
          </div>
          <div class="metric-card">
            <div class="metric-lbl">Monitored Suppliers</div>
            <div class="metric-val">${suppliers.length}</div>
            <div style="font-size: 11px; color: #6b7280;">Active network nodes</div>
          </div>
          <div class="metric-card">
            <div class="metric-lbl">Active Exceptions</div>
            <div class="metric-val" style="color: ${criticalCount > 0 ? "#ef4444" : "#111827"}">${activeAlerts.length}</div>
            <div style="font-size: 11px; color: ${criticalCount > 0 ? "#ef4444" : "#6b7280"};">${criticalCount} critical breaches</div>
          </div>
        </div>

        <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px;">Top Exceptions Requiring Action</h3>
        ${alertsHtml || '<div style="font-size: 12px; color: #6b7280; padding: 10px 0;">No active threshold violations detected.</div>'}

        <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 24px; margin-bottom: 6px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px;">Supplier Network Summary</h3>
        <table>
          <thead>
            <tr>
              <th>Supplier Name</th>
              <th>Score</th>
              <th>Tier</th>
              <th>Category</th>
              <th>Region</th>
            </tr>
          </thead>
          <tbody>
            ${suppliersHtml || '<tr><td colspan="5" style="padding: 10px; text-align: center; color: #6b7280;">No suppliers available</td></tr>'}
          </tbody>
        </table>

        <div style="margin-top: 36px; padding-top: 16px; border-top: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center;">
          <div style="font-size: 11px; color: #9ca3af; font-family: monospace;">CONFIDENTIAL &bull; SIGNAL PERFORMANCE AGENT &bull; AUTOMATED TELEMETRY</div>
          <button onclick="window.print()" style="padding: 8px 16px; background: #ea580c; color: white; border: none; border-radius: 4px; font-weight: 600; cursor: pointer;">Print or Save as PDF</button>
        </div>
      </body>
    </html>
  `;

  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
}
