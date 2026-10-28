import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.ASTRAFORGE_BACKEND_URL || 'https://astraforge-backend-7t9l.onrender.com',
        changeOrigin: true,
        secure: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        ws: true,
        headers: process.env.ASTRAFORGE_API_KEY
          ? { 'X-AstraForge-Key': process.env.ASTRAFORGE_API_KEY }
          : {},
      },
    },
  },
});
