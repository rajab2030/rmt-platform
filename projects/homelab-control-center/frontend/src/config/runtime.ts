export interface RuntimeConfig {
    platform_name: string;
    platform_version: string;
    environment: string;
    api_host: string;
    api_port: number;
    runtime_engine: string;
}


let runtimeConfig: RuntimeConfig | null = null;


export async function loadRuntimeConfig(): Promise<RuntimeConfig> {

    const response = await fetch("/config");

    if (!response.ok) {
        throw new Error(
            "Failed to load runtime configuration"
        );
    }

    const config: RuntimeConfig = await response.json();

    runtimeConfig = config;

    return config;

}


export function getRuntimeConfig(): RuntimeConfig {

    if (runtimeConfig === null) {
        throw new Error(
            "Runtime configuration not loaded"
        );
    }

    return runtimeConfig!;
}
