import { useEffect, useState } from "react";

import {
  getLatestMetric,
  type ObservabilityMetric,
} from "../api/observability";


function ObservabilityPanel() {

  const [metric, setMetric] =
    useState<ObservabilityMetric | null>(null);

  const [error, setError] =
    useState<string | null>(null);


  async function loadMetric() {

    try {

      const data = await getLatestMetric();

      setMetric(data);

    } catch (err) {

      console.error(err);

      setError(
        "Failed to load observability data"
      );
    }
  }


  useEffect(() => {

    loadMetric();

  }, []);


  return (

    <div>

      <h2>
        Platform Observability
      </h2>


      {error && (
        <p>{error}</p>
      )}


      {metric && (

        <div>

          <p>
            Name: {metric.name}
          </p>


          <p>
            Status: {metric.status}
          </p>


          <p>
            CPU:
            {" "}
            {metric.cpu_usage}%
          </p>


          <p>
            Memory:
            {" "}
            {Math.round(
              metric.memory_usage / 1024 / 1024
            )}
            MB
          </p>


          <p>
            Health:
            {" "}
            {metric.health}
          </p>


          <p>
            Updated:
            {" "}
            {new Date(
              metric.timestamp
            ).toLocaleString()}
          </p>

        </div>

      )}

    </div>

  );
}


export default ObservabilityPanel;
