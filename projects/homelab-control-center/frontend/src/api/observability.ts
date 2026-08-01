import { getRuntimeConfig } from "../config/runtime";


function getApiUrl(): string {

  const config = getRuntimeConfig();

  return `http://${window.location.hostname}:${config.api_port}`;
}


export interface ObservabilityMetric {
  name: string;
  status: string;
  cpu_usage: number;
  memory_usage: number;
  health: string;
  timestamp: string;
}


export async function getLatestMetric(): Promise<ObservabilityMetric> {

  const response = await fetch(
    `${getApiUrl()}/observability/latest`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch latest metric");
  }

  return response.json();
}


export async function getMetricHistory(): Promise<ObservabilityMetric[]> {

  const response = await fetch(
    `${getApiUrl()}/observability/history`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch metric history");
  }

  return response.json();
}
