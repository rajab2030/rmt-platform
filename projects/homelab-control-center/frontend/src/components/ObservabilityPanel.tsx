import { useEffect, useState } from "react";

import { getLatestMetric, type ObservabilityMetric } from "../api/observability";

function ObservabilityPanel() {
  const [metric, setMetric] = useState<ObservabilityMetric | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadMetric() {
    try {
      setMetric(await getLatestMetric());
    } catch (err) {
      console.error(err);
      setError("Failed to load observability data");
    }
  }

  useEffect(() => {
    loadMetric();
  }, []);

  return (
    <article className="card">
      <div className="card-head">
        <h2>Platform Observability</h2>
        {metric && <span className="pill">{metric.status}</span>}
      </div>

      {error && <p className="msg msg-error">{error}</p>}

      {!error && !metric && <p className="muted">No metrics recorded yet.</p>}

      {metric && (
        <dl className="facts">
          <dt>Source</dt>
          <dd>{metric.name}</dd>
          <dt>CPU</dt>
          <dd>{metric.cpu_usage}%</dd>
          <dt>Memory</dt>
          <dd>{Math.round(metric.memory_usage / 1024 / 1024)} MB</dd>
          <dt>Health</dt>
          <dd>{metric.health}</dd>
          <dt>Updated</dt>
          <dd>{new Date(metric.timestamp).toLocaleString()}</dd>
        </dl>
      )}
    </article>
  );
}

export default ObservabilityPanel;
