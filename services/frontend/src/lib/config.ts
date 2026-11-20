import "server-only";
import { z } from "zod";

const serviceUrl = z.url().refine((value) => ["http:", "https:"].includes(new URL(value).protocol), "Use an HTTP(S) URL");
const schema = z.object({
  REGISTRY_URL: serviceUrl,
  WEATHER_URL: serviceUrl,
  PLANNER_URL: serviceUrl,
  SERVICE_TIMEOUT_MS: z.coerce.number().int().min(100).max(60000).default(5000),
  PLAN_TIMEZONE: z.string().default("Asia/Jerusalem").refine((value) => {
    try { new Intl.DateTimeFormat("en", { timeZone: value }); return true; } catch { return false; }
  }, "Use a valid IANA time zone matching the planner"),
});
// Validated when the server starts loading its routes, before any service request.
const parsed = schema.safeParse({
  REGISTRY_URL: process.env.REGISTRY_URL,
  WEATHER_URL: process.env.WEATHER_URL,
  PLANNER_URL: process.env.PLANNER_URL,
  SERVICE_TIMEOUT_MS: process.env.SERVICE_TIMEOUT_MS,
  PLAN_TIMEZONE: process.env.PLAN_TIMEZONE,
});
if (!parsed.success) {
  throw new Error(`Frontend configuration invalid. Check .env.local: ${parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; ")}`);
}
export const config = parsed.data;
