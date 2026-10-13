import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Anything the browser requests at /api is forwarded to the FastAPI server.
// This keeps the frontend code free of hard-coded URLs and avoids CORS issues.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
