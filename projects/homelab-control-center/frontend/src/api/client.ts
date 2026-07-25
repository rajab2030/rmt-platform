const API_URL = "http://192.168.142.128:8000";

export async function getContainers() {
  const response = await fetch(`${API_URL}/containers`);

  if (!response.ok) {
    throw new Error("Failed to fetch containers");
  }

  return response.json();
}


export async function startContainer(name: string) {
  const response = await fetch(
    `${API_URL}/containers/${name}/start`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to start container");
  }

  return response.json();
}


export async function stopContainer(name: string) {
  const response = await fetch(
    `${API_URL}/containers/${name}/stop`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to stop container");
  }

  return response.json();
}


export async function restartContainer(name: string) {
  const response = await fetch(
    `${API_URL}/containers/${name}/restart`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to restart container");
  }

  return response.json();
}


export async function removeContainer(name: string) {
  const response = await fetch(
    `${API_URL}/containers/${name}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to remove container");
  }

  return response.json();
}
