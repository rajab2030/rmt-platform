import { getApiBaseUrl } from "../config/runtime";
import type { PlatformState } from "../types/platform";


export async function getPlatformState(): Promise<PlatformState> {

  const response = await fetch(
    `${getApiBaseUrl()}/platform/state`
  );


  if (!response.ok) {
    throw new Error(
      "Failed to fetch platform state"
    );
  }


  return response.json();
}
