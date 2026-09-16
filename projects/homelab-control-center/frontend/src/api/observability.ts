import { getApiBaseUrl } from "../config/runtime";


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
    `${getApiBaseUrl()}/observability/latest`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch latest metric");
  }

  return response.json();
}


export async function getMetricHistory(): Promise<ObservabilityMetric[]> {

  const response = await fetch(
    `${getApiBaseUrl()}/observability/history`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch metric history");
  }

  return response.json();
}
