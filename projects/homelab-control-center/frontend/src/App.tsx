import { useEffect, useState } from "react";
import { getContainers } from "./api/client";
import "./App.css";

interface Container {
  name: string;
  image: string;
  status: string;
}

interface ContainerStats {
  name: string;
  status: string;
  memory_usage: number;
  cpu_usage: number;
  started_at: string;
}

function StatusBadge({ status }: { status: string }) {
  const isRunning = status === "running";

  return (
    <span className={isRunning ? "status running" : "status stopped"}>
      {isRunning ? "🟢 Running" : "🔴 Exited"}
    </span>
  );
}

function App() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedContainer, setSelectedContainer] =
    useState<Container | null>(null);

  const [containerStats, setContainerStats] =
    useState<ContainerStats | null>(null);

  const runningCount = containers.filter(
    (container) => container.status === "running"
  ).length;

  const stoppedCount = containers.length - runningCount;

  async function loadContainers() {
    setLoading(true);
    setError(null);

    try {
      const data = await getContainers();
      setContainers(data);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch containers");
    } finally {
      setLoading(false);
    }
  }

  async function loadContainerStats(name: string) {
    try {
      const response = await fetch(
        `http://192.168.142.128:8000/containers/${name}/stats`
      );

      const data = await response.json();

      setContainerStats(data);

    } catch (err) {
      console.error(err);
      setContainerStats(null);
    }
  }

  useEffect(() => {
    loadContainers();
  }, []);

  return (
    <div>

      <h1>RMT Platform Control Center</h1>

      <h2>Containers</h2>

      <button onClick={loadContainers}>
        Refresh Containers
      </button>

      <div>
        <p>Total Containers: {containers.length}</p>
        <p>Running: {runningCount}</p>
        <p>Stopped: {stoppedCount}</p>
      </div>

      {loading && <p>Loading...</p>}

      {error && <p>{error}</p>}

      {!loading && !error && (

        <table>

          <thead>
            <tr>
              <th>Name</th>
              <th>Image</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>

            {containers.map((container) => (

              <tr key={container.name}>

                <td>

                  <button
                    onClick={() => {
                      setSelectedContainer(container);
                      loadContainerStats(container.name);
                    }}
                  >
                    {container.name}
                  </button>

                </td>

                <td>
                  {container.image}
                </td>

                <td>
                  <StatusBadge status={container.status} />
                </td>

              </tr>

            ))}

          </tbody>

        </table>

      )}

      {selectedContainer && (

        <div>

          <h2>Container Details</h2>

          <p>
            Name: {selectedContainer.name}
          </p>

          <p>
            Image: {selectedContainer.image}
          </p>

          <p>
            Status: {selectedContainer.status}
          </p>


          {containerStats && (

            <div>

              <p>
                Memory:
                {" "}
                {Math.round(
                  containerStats.memory_usage / 1024 / 1024
                )}
                MB
              </p>


              <p>
                CPU:
                {" "}
                {containerStats.cpu_usage}%
              </p>


              <p>
                Started:
                {" "}
                {new Date(
                  containerStats.started_at
                ).toLocaleString()}
              </p>

            </div>

          )}


          <button
            onClick={() => {
              setSelectedContainer(null);
              setContainerStats(null);
            }}
          >
            Close
          </button>

        </div>

      )}

    </div>
  );
}

export default App;
