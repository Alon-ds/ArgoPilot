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
async function fillPlot(page: import("@playwright/test").Page) {
  await page.getByLabel("Farm", { exact: true }).selectOption({ label: "Negev farm" });
  await page.getByLabel("Plot name").fill("West block");
  await page.getByLabel("Area (m²)").fill("1200");
  await page.getByLabel("Planting date").fill("2026-03-01");
  await page.getByLabel("Crop").selectOption("tomato");
  await page.getByLabel("Soil", { exact: true }).selectOption("loam");
  await page.getByLabel("Emitter", { exact: true }).selectOption("dripnet-pc-1.0");
  await page.getByLabel("Row spacing (m)").fill("1.5");
  await page.getByLabel("Emitter spacing (m)").fill("0.4");
  await page.getByLabel("Latitude").fill("31.25");
  await page.getByLabel("Longitude").fill("34.79");
}

test("saves a farm from the form, and the browser calls no service directly", async ({ page }) => {
  const serviceRequests: string[] = [];
  page.on("request", (r) => { if (r.url().includes(":18080")) serviceRequests.push(r.url()); });
  await page.goto("/manage");
  await page.getByLabel("Farm name").fill("Golan farm");
  await page.getByRole("button", { name: "Add farm" }).click();
  await expect(page.getByText('Farm "Golan farm" saved.')).toBeVisible();
  expect(serviceRequests).toEqual([]);
});

test("saves a plot with catalogue values chosen from the registry", async ({ page }) => {
  await page.goto("/manage");
  await fillPlot(page);
  await page.getByRole("button", { name: "Add plot" }).click();
  await expect(page.getByText('Plot "West block" saved.')).toBeVisible();
});

test("375 px: the entry form fits and submits", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto("/manage");
  await expect(page.getByRole("button", { name: "Add plot" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/manage-mobile.png", fullPage: true });
  await page.getByLabel("Farm name").fill("Phone farm");
  await page.getByRole("button", { name: "Add farm" }).click();
  await expect(page.getByText('Farm "Phone farm" saved.')).toBeVisible();
});

test("the registry's validation message reaches the grower", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=reject");
  await page.goto("/manage");
  await fillPlot(page);
  await page.getByRole("button", { name: "Add plot" }).click();
  await expect(page.getByText(/planting_date must not be in the future/)).toBeVisible();
  await expect(page.getByText(/saved\./)).toHaveCount(0);
});

test("an out-of-range field is cleared on error while the rest is kept", async ({ page }) => {
  await page.goto("/manage");
  await fillPlot(page);
  await page.getByLabel("Row spacing (m)").fill("50"); // above the 5 m bound
  await page.getByRole("button", { name: "Add plot" }).click();
  await expect(page.getByText(/Row spacing must be at most 5/)).toBeVisible();
  await expect(page.getByLabel("Plot name")).toHaveValue("West block"); // kept
  await expect(page.getByLabel("Soil", { exact: true })).toHaveValue("loam"); // kept
  await expect(page.getByLabel("Row spacing (m)")).toHaveValue(""); // only this cleared
});

test("a duplicate plot name is reported, not silently dropped", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=conflict");
  await page.goto("/manage");
  await fillPlot(page);
  await page.getByRole("button", { name: "Add plot" }).click();
  await expect(page.getByText("A plot with this name already exists in the farm.")).toBeVisible();
});

test("an unreadable success response never claims a save", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=garbled");
  await page.goto("/manage");
  await page.getByLabel("Farm name").fill("Garbled farm");
  await page.getByRole("button", { name: "Add farm" }).click();
  await expect(page.getByText(/returned an unexpected response/)).toBeVisible();
});

test("client-side bounds stop an impossible latitude before the registry", async ({ page }) => {
  await page.goto("/manage");
  await fillPlot(page);
  await page.getByLabel("Latitude").fill("999");
  await page.getByRole("button", { name: "Add plot" }).click();
  await expect(page.getByText(/saved\./)).toHaveCount(0);
});

test("a down registry hides the entry form instead of offering a dead one", async ({ page, request }) => {
  await request.get("http://127.0.0.1:18080/mode?value=registry-down");
  await page.goto("/manage");
  await expect(page.locator('[data-slot="alert"]').first()).toBeVisible();
  await expect(page.getByText("The form opens once the registry answers.")).toBeVisible();
});

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
