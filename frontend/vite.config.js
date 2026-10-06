import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  envDir: resolve(frontendRoot, ".."),
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000", "/thumbs": "http://127.0.0.1:8000", "/accounts": "http://127.0.0.1:8000" } },
  build: { rollupOptions: { input: { app: resolve(frontendRoot, "index.html"), promo: resolve(frontendRoot, "promo.html") } } },
});
