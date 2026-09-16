import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiPort = process.env.RMT_TEST_API_PORT || "8000";
const apiTarget = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  plugins: [react()],

  server: {
    host: "0.0.0.0",

    proxy: {
      "/config": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/ops": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/approve": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/homelab": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/agent": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/health": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/metrics": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/containers": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/modules": {
        target: apiTarget,
        changeOrigin: true,
      },

      "/monitor": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
