const API_URL = "http://192.168.142.128:8000";

export async function getContainers() {
  const response = await fetch(`${API_URL}/containers`);

  if (!response.ok) {
    throw new Error("Failed to fetch containers");
  }

  return response.json();
}
