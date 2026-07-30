import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "0.0.0.0",

    proxy: {
      "/config": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/containers": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/modules": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/monitor": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
