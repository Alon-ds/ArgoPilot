"use server";
import { revalidatePath } from "next/cache";
import { z } from "zod";
import { createFarm, createPlot } from "@/lib/services";

export type FormState = { ok: boolean; message: string } | null;

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
  row_spacing_m: number("Row spacing", Number.MIN_VALUE),
  emitter_spacing_m: number("Emitter spacing", Number.MIN_VALUE),
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
  const parsed = plotForm.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false, message: firstIssue(parsed.error) };
  const result = await createPlot(parsed.data);
  if (!result.ok) return { ok: false, message: result.message };
  revalidatePath("/");
  revalidatePath("/manage");
  return { ok: true, message: `Plot "${result.data.name}" saved.` };
}
