

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

interface Props {
  container: Container;

  stats: ContainerStats | null;

  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onRemove: () => void;
  onClose: () => void;
}


export default function ContainerDetails({
  container,
  stats,
  onStart,
  onStop,
  onRestart,
  onRemove,
  onClose,
}: Props) {


  return (

    <div>

      <h2>Container Details</h2>


      <p>
        Name: {container.name}
      </p>


      <p>
        Image: {container.image}
      </p>


      <p>
        Status: {container.status}
      </p>


      {stats && (

        <div>

          <p>
            Memory:
            {" "}
            {Math.round(
              stats.memory_usage / 1024 / 1024
            )}
            MB
          </p>


          <p>
            CPU:
            {" "}
            {stats.cpu_usage}%
          </p>


          <p>
            Health:
            {" "}
            {stats.health === "healthy"
              ? "🟢 Healthy"
              : stats.health}
          </p>


          <p>
            Started:
            {" "}
            {new Date(
              stats.started_at
            ).toLocaleString()}
          </p>

        </div>

      )}


      <h3>Actions</h3>


      {container.status === "running" ? (

        <>
          <button onClick={onStop}>
            Stop
          </button>


          <button onClick={onRestart}>
            Restart
          </button>
        </>

      ) : (

        <button onClick={onStart}>
          Start
        </button>

      )}


      <button onClick={onRemove}>
        Remove
      </button>


      <button onClick={onClose}>
        Close
      </button>


    </div>

  );
}
