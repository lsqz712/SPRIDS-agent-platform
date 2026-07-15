import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import path from "path";
import { fileURLToPath } from "url";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "/favicon.svg": path.resolve(__dirname, "public", "favicon.svg"),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/assets/styles/variables.scss" as *;`,
      },
    },
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
      // WebSocket 代理（关键！）
      "/api/detection/camera": {
        target: "ws://localhost:8001",
        ws: true,  // 启用 WebSocket 代理
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "happy-dom",
    setupFiles: ["./tests/setup.js"],
    include: ["tests/**/*.{test,spec}.{js,ts}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
    },
    server: {
      deps: {
        inline: ["element-plus"],
      },
    },
  },
});