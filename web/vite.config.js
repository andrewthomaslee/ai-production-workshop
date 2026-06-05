import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev (`npm run dev`), proxy API + WebSocket to the FastAPI backend so the
// client can use same-origin relative URLs (/api/*, /ws) everywhere. In prod the
// built app is served BY FastAPI, so those relative URLs just work.
const BACKEND = process.env.BACKEND || "http://127.0.0.1:8000";

// Generous timeouts so a long request (running the eval suite takes ~30s+) is
// never cut by the proxy. 10 minutes is well beyond any real run.
const LONG = 600000;

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true, timeout: LONG, proxyTimeout: LONG },
      "/healthz": { target: BACKEND, changeOrigin: true },
      "/ws": { target: BACKEND, ws: true, changeOrigin: true },
    },
  },
});
