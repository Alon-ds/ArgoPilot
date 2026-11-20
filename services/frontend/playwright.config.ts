import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", fullyParallel: false, workers: 1,
  use: { baseURL: "http://127.0.0.1:3100", ...devices["Desktop Chrome"], viewport: { width: 375, height: 667 } },
  webServer: [
    { command: "node tests/mock-services.mjs", port: 18080, reuseExistingServer: false },
    { command: "npm run start -- --hostname 127.0.0.1 --port 3100", port: 3100,
      reuseExistingServer: false,
      env: { REGISTRY_URL: "http://127.0.0.1:18080/registry", WEATHER_URL: "http://127.0.0.1:18080/weather", PLANNER_URL: "http://127.0.0.1:18080/planner", SERVICE_TIMEOUT_MS: "500", PLAN_TIMEZONE: "Asia/Jerusalem" } },
  ],
});
