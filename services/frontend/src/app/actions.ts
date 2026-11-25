"use server";
import { revalidatePath } from "next/cache";
import { z } from "zod";
import { createFarm, createPlot } from "@/lib/services";

export type FormState =
  | { ok: boolean; message: string; values?: Record<string, string>; invalid?: string[]; submittedAt?: number }
  | null;

const farmForm = z.object({ name: z.string().trim().min(1, "Enter a farm name.") });

const number = (label: string, min: number, max?: number) =>
  z.coerce.number({ error: `${label} must be a number.` })
    .refine((value) => Number.isFinite(value), `${label} must be a number.`)
    .refine((value) => value >= min, `${label} must be greater than ${min}.`)
    .refine((value) => max === undefined || value <= max, `${label} must be at most ${max}.`);

const plotForm = z.object({
  farm_id: z.string().uuid("Choose a farm."),
  name: z.string().trim().min(1, "Enter a plot name."),
  area_m2: number("Area", Number.MIN_VALUE),
  crop_id: z.string().min(1, "Choose a crop."),
  planting_date: z.iso.date("Enter the planting date as YYYY-MM-DD."),
  soil_id: z.string().min(1, "Choose a soil."),
  row_spacing_m: number("Row spacing", Number.MIN_VALUE, 5),
  emitter_spacing_m: number("Emitter spacing", Number.MIN_VALUE, 2),
  emitter_id: z.string().min(1, "Choose an emitter."),
  lat: number("Latitude", -90, 90),
  lon: number("Longitude", -180, 180),
  initial_soil_pct: number("Initial soil moisture", 0, 100),
});

function firstIssue(error: z.ZodError): string {
  return error.issues[0]?.message ?? "Check the values and try again.";
}

export async function createFarmAction(_previous: FormState, formData: FormData): Promise<FormState> {
  const parsed = farmForm.safeParse({ name: formData.get("name") });
  if (!parsed.success) return { ok: false, message: firstIssue(parsed.error) };
  const result = await createFarm(parsed.data.name);
  if (!result.ok) return { ok: false, message: result.message };
  revalidatePath("/");
  revalidatePath("/manage");
  return { ok: true, message: `Farm "${result.data.name}" saved.` };
}

export async function createPlotAction(_previous: FormState, formData: FormData): Promise<FormState> {
  const values = Object.fromEntries(
    [...formData.entries()].map(([key, value]) => [key, String(value)]),
  );
  // A fresh nonce each submit lets the form remount so every field — inputs and
  // selects alike — re-reads its defaultValue (React does not re-apply a changed
  // defaultValue to an uncontrolled <select> on form reset).
  const submittedAt = Date.now();
  const parsed = plotForm.safeParse(values);
  if (!parsed.success) {
    // Keep what the grower typed; only the out-of-range fields are cleared so
    // they can be re-entered, instead of wiping the whole form.
    const invalid = [...new Set(parsed.error.issues.map((issue) => String(issue.path[0])))];
    return { ok: false, message: firstIssue(parsed.error), values, invalid, submittedAt };
  }
  const result = await createPlot(parsed.data);
  if (!result.ok) return { ok: false, message: result.message, values, invalid: [], submittedAt };
  revalidatePath("/");
  revalidatePath("/manage");
  return { ok: true, message: `Plot "${result.data.name}" saved.`, submittedAt };
}
