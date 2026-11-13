import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  // In dev, forward /api to the local FastAPI server; in production FastAPI serves this app itself.
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
});
