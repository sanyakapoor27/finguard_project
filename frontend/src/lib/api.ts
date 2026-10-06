const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchMetrics() {
  const res = await fetch(`${API}/api/v1/metrics/executive`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function querycopilot(question: string, source: string) {
  const res = await fetch(`${API}/api/v1/copilot/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, source }),
  });
  return res.json();
}

export async function fetchLineage(alertId: string) {
  const res = await fetch(`${API}/api/v1/lineage/${alertId}`);
  if (!res.ok) throw new Error("Alert not found");
  return res.json();
}

export async function runStressTest(params: {
  haircut_adjustment_pct: number;
  default_rate_spike_pct: number;
  outflow_speed_pct: number;
}) {
  const res = await fetch(`${API}/api/v1/sandbox/stress-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function exportAudit(alertId: string) {
  const res = await fetch(`${API}/api/v1/audit/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alert_id: alertId }),
  });
  return res.blob();
}
