import { StatusPill } from "./ContainerTable";

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
    <article className="card">
      <div className="card-head">
        <h2>{container.name}</h2>
        <StatusPill status={container.status} />
      </div>

      <dl className="facts">
        <dt>Image</dt>
        <dd><code>{container.image}</code></dd>
        {stats && (
          <>
            <dt>Memory</dt>
            <dd>{Math.round(stats.memory_usage / 1024 / 1024)} MB</dd>
            <dt>CPU</dt>
            <dd>{stats.cpu_usage}%</dd>
            <dt>Health</dt>
            <dd>{stats.health}</dd>
            <dt>Started</dt>
            <dd>{new Date(stats.started_at).toLocaleString()}</dd>
          </>
        )}
      </dl>

      <div className="actions">
        {container.status === "running" ? (
          <>
            <button onClick={onStop}>Stop</button>
            <button onClick={onRestart}>Restart</button>
          </>
        ) : (
          <button className="primary" onClick={onStart}>
            Start
          </button>
        )}
        <button className="danger" onClick={onRemove}>
          Remove
        </button>
        <button onClick={onClose}>Close</button>
      </div>
    </article>
  );
}
