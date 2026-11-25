import "server-only";
import { z } from "zod";
import { config } from "./config";

export type Service = "Registry" | "Weather" | "Planner";
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };
const urls: Record<Service, string> = { Registry: config.REGISTRY_URL, Weather: config.WEATHER_URL, Planner: config.PLANNER_URL };
const farmSchema = z.object({ id: z.string().min(1), name: z.string().min(1) });
const plotSchema = z.object({
  id: z.string().min(1), farm_id: z.string().min(1), name: z.string().min(1),
  area_m2: z.number().positive(), crop_id: z.string(),
});
const cropSchema = z.object({ id: z.string().min(1), name: z.string().min(1) });
const soilSchema = z.object({ id: z.string().min(1), name: z.string().min(1), available_water_mm_per_m: z.number() });
const emitterSchema = z.object({ id: z.string().min(1), name: z.string().min(1), flow_lph: z.number() });
const nonnegative = z.number().nonnegative();
const daySchema = z.object({
  date: z.iso.date(), et0_mm: nonnegative, kc: nonnegative, litres: nonnegative,
  run_minutes: nonnegative, stale: z.boolean(), bucket_mm: nonnegative, bucket_pct: nonnegative,
});
const planSchema = z.object({ plot_id: z.string().min(1), days: z.array(daySchema).length(7) }).superRefine((plan, context) => {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: config.PLAN_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  if (plan.days[0]?.date !== today) context.addIssue({ code: "custom", message: "Plan must begin today in the planner time zone" });
  for (let i = 1; i < plan.days.length; i++) {
    const difference = Date.parse(plan.days[i].date) - Date.parse(plan.days[i - 1].date);
    if (difference !== 86400000) context.addIssue({ code: "custom", message: "Plan dates must be consecutive" });
  }
});
export type Plot = z.infer<typeof plotSchema>;
export type Plan = z.infer<typeof planSchema>;
export type Farm = z.infer<typeof farmSchema>;
export type Crop = z.infer<typeof cropSchema>;
export type Soil = z.infer<typeof soilSchema>;
export type Emitter = z.infer<typeof emitterSchema>;

async function request<T>(service: Service, path: string, schema: z.ZodType<T>): Promise<Result<T>> {
  try {
    const response = await fetch(`${urls[service].replace(/\/$/, "")}${path}`, {
      cache: "no-store", signal: AbortSignal.timeout(config.SERVICE_TIMEOUT_MS),
      headers: { Accept: "application/json" }, redirect: "error",
    });
    if (!response.ok) {
      let detail = "";
      try {
        const error: unknown = await response.json();
        if (error && typeof error === "object" && "detail" in error && typeof error.detail === "string") {
          // Only known dependency names are surfaced; never expose arbitrary upstream internals.
          const upstream = ["registry-service", "weather-service", "planner-service"].find((name) => error.detail && String(error.detail).toLowerCase().includes(name));
          if (upstream) detail = ` ${upstream} is unavailable.`;
        }
      } catch { /* Status is sufficient when the error body is not JSON. */ }
      const reason = response.status === 404 ? "The requested plot was not found." : response.status === 422 ? "The service rejected this request." : "Please try again shortly.";
      return { ok: false, message: `${service} service returned HTTP ${response.status}.${detail} ${reason}` };
    }
    const parsed = schema.safeParse(await response.json());
    if (!parsed.success) return { ok: false, message: `${service} service returned incomplete or invalid data. No recommendation can be shown safely. Try again shortly.` };
    return { ok: true, data: parsed.data };
  } catch {
    return { ok: false, message: `${service} service could not be reached, timed out, or returned unreadable data. Try again shortly.` };
  }
}

// Writes surface the registry's problem+json `detail` for 422/409, because that text tells the
// grower which field to correct. Reads deliberately hide upstream detail (see `request`).
async function mutate<T>(path: string, body: unknown, schema: z.ZodType<T>): Promise<Result<T>> {
  try {
    const response = await fetch(`${config.REGISTRY_URL.replace(/\/$/, "")}${path}`, {
      method: "POST", cache: "no-store", signal: AbortSignal.timeout(config.SERVICE_TIMEOUT_MS),
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body), redirect: "error",
    });
    if (!response.ok) {
      let detail = "";
      if (response.status === 422 || response.status === 409) {
        try {
          const problem: unknown = await response.json();
          if (problem && typeof problem === "object" && "detail" in problem && typeof problem.detail === "string") {
            detail = problem.detail.replace(/^body\./, "").slice(0, 300);
          }
        } catch { /* Fall through to the generic message below. */ }
      }
      return { ok: false, message: detail || `The registry rejected this request (HTTP ${response.status}). Please check the values and try again.` };
    }
    const parsed = schema.safeParse(await response.json());
    if (!parsed.success) return { ok: false, message: "The registry saved the record but returned an unexpected response. Reload to confirm." };
    return { ok: true, data: parsed.data };
  } catch {
    return { ok: false, message: "Registry service could not be reached or timed out. Nothing was saved. Try again shortly." };
  }
}

export const createFarm = (name: string) => mutate("/v1/farms", { name }, farmSchema);
export const createPlot = (plot: Record<string, unknown>) => mutate("/v1/plots", plot, plotSchema);

export async function deletePlot(id: string): Promise<{ ok: boolean; message?: string }> {
  try {
    const response = await fetch(`${config.REGISTRY_URL.replace(/\/$/, "")}/v1/plots/${encodeURIComponent(id)}`, {
      method: "DELETE", cache: "no-store", signal: AbortSignal.timeout(config.SERVICE_TIMEOUT_MS),
      headers: { Accept: "application/json" }, redirect: "error",
    });
    if (response.status === 204) return { ok: true };
    if (response.status === 404) return { ok: false, message: "This plot no longer exists." };
    return { ok: false, message: `The registry refused the delete (HTTP ${response.status}).` };
  } catch {
    return { ok: false, message: "Registry service could not be reached or timed out. Nothing was deleted." };
  }
}
export const getCrops = () => request("Registry", "/v1/crops", z.array(cropSchema));
export const getSoils = () => request("Registry", "/v1/soils", z.array(soilSchema));
export const getEmitters = () => request("Registry", "/v1/emitters", z.array(emitterSchema));
export const getFarms = () => request("Registry", "/v1/farms", z.array(farmSchema));
export const getPlots = () => request("Registry", "/v1/plots", z.array(plotSchema));
export const getPlot = (id: string) => request("Registry", `/v1/plots/${encodeURIComponent(id)}`, plotSchema);
export async function getPlan(id: string): Promise<Result<Plan>> {
  const result = await request("Planner", `/v1/plots/${encodeURIComponent(id)}/plan?days=7`, planSchema);
  if (result.ok && result.data.plot_id !== id) return { ok: false, message: "Planner service returned a plan for a different plot. No recommendation can be shown safely." };
  return result;
}
export async function getHealth() {
  return Promise.all((["Registry", "Weather", "Planner"] as const).map(async (service) => {
    const result = await request(service, "/health", z.object({ status: z.literal("ok") }));
    return { service, up: result.ok };
  }));
}
