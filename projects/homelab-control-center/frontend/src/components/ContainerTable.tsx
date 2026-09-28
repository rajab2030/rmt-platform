interface Container {
  name: string;
  image: string;
  status: string;
}

interface Props {
  containers: Container[];
  loading: boolean;
  selected: string | null;
  onSelect: (container: Container) => void;
}

export function StatusPill({ status }: { status: string }) {
  const tone = status === "running" ? "pill-ok" : status === "exited" ? "pill-bad" : "pill-warn";
  return <span className={`pill ${tone}`}>{status}</span>;
}

export default function ContainerTable({ containers, loading, selected, onSelect }: Props) {
  if (!loading && containers.length === 0) {
    return <p className="empty">No containers found.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Image</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {loading
            ? [0, 1, 2].map((row) => (
                <tr key={row} aria-hidden="true">
                  <td><span className="skeleton" style={{ width: "8rem" }} /></td>
                  <td><span className="skeleton" style={{ width: "12rem" }} /></td>
                  <td><span className="skeleton" style={{ width: "4rem" }} /></td>
                </tr>
              ))
            : containers.map((container) => (
                <tr
                  key={container.name}
                  className={container.name === selected ? "selected" : undefined}
                >
                  <td>
                    <button className="link" onClick={() => onSelect(container)}>
                      {container.name}
                    </button>
                  </td>
                  <td>
                    <code>{container.image}</code>
                  </td>
                  <td>
                    <StatusPill status={container.status} />
                  </td>
                </tr>
              ))}
        </tbody>
      </table>
    </div>
  );
}
