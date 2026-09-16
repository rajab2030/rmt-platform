import { defineConfig } from "@playwright/test";


export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://localhost:15173",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "../backend/.venv/bin/python e2e/start_backend.py",
      url: "http://127.0.0.1:18080/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "RMT_TEST_API_PORT=18080 npm run dev -- --host 127.0.0.1 --port 15173",
      url: "http://127.0.0.1:15173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
