import { getRuntimeConfig } from "../config/runtime";


function getApiUrl(): string {

  const config = getRuntimeConfig();

  return `http://${window.location.hostname}:${config.api_port}`;
}

export async function getContainers() {
  const response = await fetch(`${getApiUrl()}/containers`);

  if (!response.ok) {
    throw new Error("Failed to fetch containers");
  }

  return response.json();
}


export async function startContainer(name: string) {
  const response = await fetch(
    `${getApiUrl()}/containers/${name}/start`,
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
    `${getApiUrl()}/containers/${name}/stop`,
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
    `${getApiUrl()}/containers/${name}/restart`,
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
    `${getApiUrl()}/containers/${name}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to remove container");
  }

  return response.json();
}
