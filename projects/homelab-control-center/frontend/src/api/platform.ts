import { getRuntimeConfig } from "../config/runtime";
import type { PlatformState } from "../types/platform";


function getApiUrl(): string {
  const config = getRuntimeConfig();

  return `http://${window.location.hostname}:${config.api_port}`;
}


export async function getPlatformState(): Promise<PlatformState> {

  const response = await fetch(
    `${getApiUrl()}/platform/state`
  );


  if (!response.ok) {
    throw new Error(
      "Failed to fetch platform state"
    );
  }


  return response.json();
}
