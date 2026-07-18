import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    reducedMotion: "reduce",
  },
  webServer: [
    {
      command: ".\\.venv\\Scripts\\python.exe -m uvicorn asterism_api.main:app --app-dir apps\\api --host 127.0.0.1 --port 8000",
      cwd: "../..",
      env: {
        ASTERISM_DATABASE_URL: "sqlite:///./apps/web/test-results/e2e.db",
        ASTERISM_ARTIFACT_ROOT: "./apps/web/test-results/artifacts",
      },
      url: "http://127.0.0.1:8000/health/ready",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
