
import ContainerTable from "./components/ContainerTable";
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

import PlatformState from "./components/PlatformState";
import GovernedConsole from "./components/GovernedConsole";
import ObservabilityPanel from "./components/ObservabilityPanel";
import BudgetControl from "./components/BudgetControl";

import type { PlatformState as PlatformStateType } from "./types/platform";

import ContainerDetails from "./components/ContainerDetails";
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
  health: string;
}

function App() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [platformState, setPlatformState] =
    useState<PlatformStateType | null>(null);
  const [activeView, setActiveView] = useState<"containers" | "governed" | "budget">("containers");
  

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
        `${getApiBaseUrl()}/containers/${name}/stats`
      );

      const data = await response.json();

      setContainerStats(data);

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

    const data = await getPlatformState();

    setPlatformState(data);

  } catch (err) {

    console.error(
      "Platform state error:",
      err
    );

  }
}
  useEffect(() => {
    loadContainers();
    loadPlatformState();

  }, []);


  return (
    <div>

      <nav className="app-nav">
        <button onClick={() => setActiveView("containers")}>Containers</button>
        <button onClick={() => setActiveView("governed")}>Governed Ops</button>
        <button onClick={() => setActiveView("budget")}>Budget Control</button>
      </nav>

      {activeView === "budget" ? (
        <BudgetControl />
      ) : activeView === "governed" ? (
        <GovernedConsole />
      ) : (
        <>
      <h1>RMT Platform Control Center</h1>
  {
  platformState && (
    <PlatformState
      state={platformState}
    />
  )
}

      <ObservabilityPanel />

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

        <ContainerTable
         
         containers={containers}

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
            setSelectedContainer(null);
            setContainerStats(null);
            await loadContainers();
          }}

          onClose={() => {
            setSelectedContainer(null);
            setContainerStats(null);
          }}
        />

      )}


        </>
      )}

    </div>
  );
}

export default App;
