
interface Container {
  name: string;
  image: string;
  status: string;
}

interface Props {
  containers: Container[];

  onSelect: (
    container: Container
  ) => void;
}


function StatusBadge({
  status,
}: {
  status: string;
}) {

  const isRunning =
    status === "running";

  return (
    <span
      className={
        isRunning
          ? "status running"
          : "status stopped"
      }
    >
      {isRunning
        ? "🟢 Running"
        : "🔴 Exited"}
    </span>
  );
}


export default function ContainerTable({
  containers,
  onSelect,
}: Props) {


  return (

    <table>

      <thead>

        <tr>
          <th>Name</th>
          <th>Image</th>
          <th>Status</th>
        </tr>

      </thead>


      <tbody>

        {containers.map(
          (container) => (

            <tr
              key={container.name}
            >

              <td>

                <button
                  onClick={() =>
                    onSelect(container)
                  }
                >
                  {container.name}
                </button>

              </td>


              <td>
                {container.image}
              </td>


              <td>
                <StatusBadge
                  status={
                    container.status
                  }
                />
              </td>

            </tr>

          )
        )}

      </tbody>

    </table>

  );
}
