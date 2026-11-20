import { test, expect } from "@playwright/test";
const plotPath = "/plots/b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f2001";
test.beforeEach(async ({ request }) => { await request.get("http://127.0.0.1:18080/mode?value=normal"); });
test("lists farms, their plot links and empty farms", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Negev farm" })).toBeVisible();
  await expect(page.getByText("No plots registered for this farm.")).toBeVisible();
  await page.getByRole("link", { name: /South tomato block/ }).click();
  await expect(page.getByRole("heading", { name: "Water for 38 minutes" })).toBeVisible();
});
test("375 px: today is above the fold, table fits, browser calls no services", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  const serviceRequests: string[] = [];
  page.on("request", (r) => { if (r.url().includes(":18080")) serviceRequests.push(r.url()); });
  await page.goto(plotPath);
  const today = page.getByRole("heading", { name: "Water for 38 minutes" });
  await expect(today).toBeInViewport();
  await expect(page.getByLabel("Planning assumption")).toContainText("no sensor readings or irrigation history");
  await expect(page.getByRole("row")).toHaveCount(8);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(serviceRequests).toEqual([]);
  await page.screenshot({ path: "test-results/plot-mobile.png", fullPage: true });
});
test("stale labels accompany today and each affected row", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=stale");
  await page.goto(plotPath);
  await expect(page.getByText("Older forecast", { exact: true })).toHaveCount(8);
  await expect(page.getByRole("heading", { name: "Water for 38 minutes" })).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/plot-stale-mobile.png", fullPage: true });
});
test("zero irrigation is explicit", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=dry");
  await page.goto(plotPath);
  await expect(page.getByRole("heading", { name: "No irrigation today" })).toBeVisible();
});
for (const mode of ["error", "invalid", "short", "timeout", "unknown", "yesterday", "mismatch"]) {
  test(`fails safely for ${mode}`, async ({ page, request }) => {
    await request.get(`http://127.0.0.1:18080/mode?value=${mode}`);
    await page.goto(plotPath);
    await expect(page.locator('[data-slot="alert"]')).toBeVisible();
    await expect(page.getByText("No irrigation today", { exact: true })).toHaveCount(0);
    if (mode === "error") await expect(page.locator('[data-slot="alert"]')).toContainText("weather-service");
    if (mode === "error") await page.screenshot({ path: "test-results/plot-error-mobile.png", fullPage: true });
  });
}
test("shows all three health checks and down state", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=health-down");
  await page.goto("/");
  await expect(page.getByText("Registry: up", { exact: true })).toBeVisible();
  await expect(page.getByText("Weather: down", { exact: true })).toBeVisible();
  await expect(page.getByText("Planner: up", { exact: true })).toBeVisible();
});
test("registry errors are visible but do not hide an available plan", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=registry-down");
  await page.goto("/");
  await expect(page.locator('[data-slot="alert"]')).toHaveCount(2);
  await expect(page.locator('[data-slot="alert"]').first()).toContainText("Registry");
  await page.goto(plotPath);
  await expect(page.getByRole("heading", { name: "Water for 38 minutes" })).toBeVisible();
});
