import type { PlatformState as PlatformStateType } from "../types/platform";


interface Props {
  state: PlatformStateType;
}


export default function PlatformState({
  state,
}: Props) {

  return (
    <div className="platform-card">

      <h2>
        Platform State
      </h2>

      <p>
        Platform:
        {" "}
        {state.platform}
      </p>


      <p>
        Git Branch:
        {" "}
        {state.git.branch}
      </p>


      <p>
        Commit:
        {" "}
        {state.git.commit}
      </p>


      <p>
        Health:
        {" "}
        {state.health.status}
      </p>


      <p>
        Containers:
        {" "}
        {state.containers.running}
        {" "}
        running
      </p>


      <p>
        Backup:
        {" "}
        {state.backup.latest}
      </p>

    </div>
  );
}
