import { useEffect, useState } from "react";

import {
  getContainers,
  startContainer,
  stopContainer,
  restartContainer,
  removeContainer,
} from "./api/client";
import { getPlatformState } from "./api/platform";
import { getApiBaseUrl } from "./config/runtime";

import BudgetControl from "./components/BudgetControl";
import ContainerDetails from "./components/ContainerDetails";
import ContainerTable from "./components/ContainerTable";
import GovernedConsole from "./components/GovernedConsole";
import ObservabilityPanel from "./components/ObservabilityPanel";
import PlatformState from "./components/PlatformState";

import type { PlatformState as PlatformStateType } from "./types/platform";

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
  health: string;
}

type ActiveView = "containers" | "governed" | "budget";

const VIEWS: { id: ActiveView; label: string }[] = [
  { id: "containers", label: "Containers" },
  { id: "governed", label: "Governed Ops" },
  { id: "budget", label: "Budget Control" },
];

function App() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [platformState, setPlatformState] = useState<PlatformStateType | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("containers");
  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [containerStats, setContainerStats] = useState<ContainerStats | null>(null);

  const runningCount = containers.filter((container) => container.status === "running").length;
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
      const response = await fetch(`${getApiBaseUrl()}/containers/${name}/stats`);
      setContainerStats(await response.json());
    } catch (err) {
      console.error(err);
      setContainerStats(null);
    }
  }

  async function refreshAfterAction() {
    await loadContainers();

    if (selectedContainer) {
      await loadContainerStats(selectedContainer.name);
    }
  }

  async function loadPlatformState() {
    try {
      setPlatformState(await getPlatformState());
    } catch (err) {
      console.error("Platform state error:", err);
    }
  }

  function closeDetails() {
    setSelectedContainer(null);
    setContainerStats(null);
  }

  useEffect(() => {
    loadContainers();
    loadPlatformState();
  }, []);

  return (
    <>
      <header className="app-bar">
        <div className="brand">
          <img src="/favicon.svg" alt="" />
          <span>
            RMT <small>Control Center</small>
          </span>
        </div>
        <nav className="tabs" aria-label="Views">
          {VIEWS.map((view) => (
            <button
              key={view.id}
              aria-current={activeView === view.id ? "page" : undefined}
              onClick={() => setActiveView(view.id)}
            >
              {view.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {activeView === "budget" ? (
          <BudgetControl />
        ) : activeView === "governed" ? (
          <GovernedConsole />
        ) : (
          <section className="page">
            <header className="page-head">
              <div>
                <p className="eyebrow">RMT · homelab domain</p>
                <h1>Containers</h1>
              </div>
              <button onClick={loadContainers} disabled={loading}>
                Refresh
              </button>
            </header>

            <div className="stats">
              <div className="stat">
                <div className="stat-label">Total</div>
                <div className="stat-value">{loading ? "–" : containers.length}</div>
              </div>
              <div className="stat stat-ok">
                <div className="stat-label">Running</div>
                <div className="stat-value">{loading ? "–" : runningCount}</div>
              </div>
              <div className={stoppedCount > 0 ? "stat stat-bad" : "stat"}>
                <div className="stat-label">Stopped</div>
                <div className="stat-value">{loading ? "–" : stoppedCount}</div>
              </div>
            </div>

            {error && <p className="msg msg-error">{error}</p>}

            {!error && (
              <ContainerTable
                containers={containers}
                loading={loading}
                selected={selectedContainer?.name ?? null}
                onSelect={(container) => {
                  setSelectedContainer(container);
                  loadContainerStats(container.name);
                }}
              />
            )}

            {selectedContainer && (
              <ContainerDetails
                container={selectedContainer}
                stats={containerStats}
                onStart={async () => {
                  await startContainer(selectedContainer.name);
                  await refreshAfterAction();
                }}
                onStop={async () => {
                  await stopContainer(selectedContainer.name);
                  await refreshAfterAction();
                }}
                onRestart={async () => {
                  await restartContainer(selectedContainer.name);
                  await refreshAfterAction();
                }}
                onRemove={async () => {
                  await removeContainer(selectedContainer.name);
                  closeDetails();
                  await loadContainers();
                }}
                onClose={closeDetails}
              />
            )}

            <div className="card-grid">
              {platformState && <PlatformState state={platformState} />}
              <ObservabilityPanel />
            </div>
          </section>
        )}
      </main>
    </>
  );
}

export default App;
