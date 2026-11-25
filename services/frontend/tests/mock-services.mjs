import { createServer } from "node:http";
const farm = { id: "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001", name: "Negev farm" };
const plot = { id: "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f2001", farm_id: farm.id, name: "South tomato block", area_m2: 1000, crop_id: "tomato", planting_date: "2026-03-01", soil_id: "loam", row_spacing_m: 1.5, emitter_spacing_m: 0.4, emitter_id: "drip", lat: 31.25, lon: 34.79 };
const crops = [{ id: "tomato", name: "Tomato" }, { id: "bell-pepper", name: "Bell pepper" }];
const soils = [{ id: "loam", name: "Loam", available_water_mm_per_m: 175 }, { id: "sand", name: "Sand", available_water_mm_per_m: 83 }];
const emitters = [{ id: "dripnet-pc-1.0", name: "DripNet PC", flow_lph: 1 }, { id: "dripnet-pc-1.6", name: "DripNet PC", flow_lph: 1.6 }];
const problem = (status, title, detail, code) => ({ type: "about:blank", title, status, detail, code });
let mode = "normal";

function handle(req, res, body) {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/mode") { mode = url.searchParams.get("value"); res.end("ok"); return; }
  res.setHeader("Content-Type", "application/json");
  const send = (data, status = 200) => { res.statusCode = status; res.end(JSON.stringify(data)); };
  if (url.pathname.endsWith("/health")) {
    if (mode === "health-down" && url.pathname.startsWith("/weather")) return send({ status: "error" }, 503);
    return send({ status: "ok" });
  }
  if (mode === "registry-down" && url.pathname.startsWith("/registry")) return send({ detail: "Database unavailable" }, 503);
  if (req.method === "POST" && url.pathname.startsWith("/registry/v1/")) {
    if (mode === "reject") return send(problem(422, "Unprocessable Entity", "planting_date: planting_date must not be in the future", "VALIDATION"), 422);
    if (mode === "conflict") return send(problem(409, "Conflict", "A plot with this name already exists in the farm.", "CONFLICT"), 409);
    if (mode === "garbled") return send({ unexpected: true }, 201);
    let parsed;
    try { parsed = JSON.parse(body); } catch { return send(problem(422, "Unprocessable Entity", "Body is not JSON", "VALIDATION"), 422); }
    return send({ id: url.pathname.endsWith("/farms") ? "created-farm" : "created-plot", ...parsed }, 201);
  }
  if (url.pathname === "/registry/v1/crops") return send(crops);
  if (url.pathname === "/registry/v1/soils") return send(soils);
  if (url.pathname === "/registry/v1/emitters") return send(emitters);
  if (url.pathname === "/registry/v1/farms") return send([farm, { id: "empty-farm", name: "New farm" }]);
  if (url.pathname === "/registry/v1/plots") return send([plot]);
  if (url.pathname.startsWith("/registry/v1/plots/")) return send(plot);
  if (url.pathname.includes("/plan")) {
    if (mode === "timeout") return;
    if (mode === "error") return send({ code: "UPSTREAM_UNAVAILABLE", detail: "weather-service is unavailable" }, 503);
    if (mode === "unknown") return send({ detail: "Plot not found", code: "NOT_FOUND" }, 404);
    const date = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
    const today = Date.parse(`${date}T00:00:00Z`) - (mode === "yesterday" ? 86400000 : 0);
    const days = Array.from({ length: 7 }, (_, i) => ({ date: new Date(today + i * 86400000).toISOString().slice(0, 10), et0_mm: 6, kc: 1.15, litres: i === 0 && mode !== "dry" ? 6900 : 0, run_minutes: i === 0 && mode !== "dry" ? 38 : 0, stale: mode === "stale", bucket_mm: 35, bucket_pct: 50 }));
    if (mode === "invalid") delete days[0].run_minutes;
    return send({ plot_id: mode === "mismatch" ? "different-plot" : plot.id, days: mode === "short" ? days.slice(0, 1) : days });
  }
  send({ detail: "Not found" }, 404);
}

createServer((req, res) => {
  const chunks = [];
  req.on("data", (chunk) => chunks.push(chunk));
  req.on("end", () => handle(req, res, Buffer.concat(chunks).toString()));
}).listen(18080, "127.0.0.1");
