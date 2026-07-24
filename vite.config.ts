import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Target http://localhost:8000 when local, and production backend URL when in production
  const env = loadEnv(mode, process.cwd(), "");

  const targetUrl =
    env.VITE_API_BASE_URL ||
    process.env.VITE_API_BASE_URL ||
    (mode === "production"
      ? "https://invoice-extractor-g0g6.onrender.com"
      : "http://localhost:8000");

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    optimizeDeps: {
      exclude: ["lucide-react"],
    },
    server: {
      proxy: {
        "/api": {
          target: targetUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
