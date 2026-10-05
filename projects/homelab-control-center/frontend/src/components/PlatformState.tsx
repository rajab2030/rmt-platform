import type { PlatformState as PlatformStateType } from "../types/platform";

interface Props {
  state: PlatformStateType;
}

export default function PlatformState({ state }: Props) {
  const healthy = state.health.status === "healthy";

  return (
    <article className="card">
      <div className="card-head">
        <h2>Platform State</h2>
        <span className={`pill ${healthy ? "pill-ok" : "pill-bad"}`}>{state.health.status}</span>
      </div>

      <dl className="facts">
        <dt>Platform</dt>
        <dd>{state.platform}</dd>
        <dt>Branch</dt>
        <dd><code>{state.git.branch}</code></dd>
        <dt>Commit</dt>
        <dd><code>{state.git.commit}</code></dd>
        <dt>Containers</dt>
        <dd>{state.containers.running} running</dd>
        <dt>Last backup</dt>
        <dd>{state.backup.latest}</dd>
      </dl>
    </article>
  );
}
