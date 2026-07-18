import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  resolve: { preserveSymlinks: true },
  plugins: [
    react(),
    {
      name: "asterism-dev-csp",
      apply: "serve",
      transformIndexHtml(html) {
        return html.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';");
      },
    },
  ],
  build: {
    sourcemap: false,
    target: "es2020",
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
  },
});
