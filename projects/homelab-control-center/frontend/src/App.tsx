import { useEffect, useState } from "react";
import { getContainers } from "./api/client";
import "./App.css";

interface Container {
  name: string;
  image: string;
  status: string;
}

function App() {
  const [containers, setContainers] = useState<Container[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getContainers()
      .then((data) => {
        setContainers(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to fetch containers");
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <h1>RMT Platform Control Center</h1>

      <h2>Containers</h2>

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
                <td>{container.name}</td>
                <td>{container.image}</td>
                <td>{container.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
