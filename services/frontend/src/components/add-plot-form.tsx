"use client";
import { useActionState } from "react";
import { createPlotAction, type FormState } from "@/app/actions";
import { FormResult } from "@/components/form-result";
import type { Crop, Emitter, Farm, Soil } from "@/lib/services";

type Props = { farms: Farm[]; crops: Crop[]; soils: Soil[]; emitters: Emitter[]; today: string };

export function AddPlotForm({ farms, crops, soils, emitters, today }: Props) {
  const [state, action, pending] = useActionState<FormState, FormData>(createPlotAction, null);
  if (farms.length === 0) return <p className="empty">Add a farm first, then a plot can be attached to it.</p>;
  return (
    <form action={action} className="entry-form">
      <div className="field">
        <label htmlFor="plot-farm">Farm</label>
        <select id="plot-farm" name="farm_id" required defaultValue="">
          <option value="" disabled>Choose a farm</option>
          {farms.map((farm) => <option key={farm.id} value={farm.id}>{farm.name}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="plot-name">Plot name</label>
        <input id="plot-name" name="name" required maxLength={120} autoComplete="off" />
        <span className="hint">Must be unique inside the chosen farm.</span>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="plot-area">Area (m²)</label>
          <input id="plot-area" name="area_m2" type="number" min="1" step="any" required inputMode="decimal" />
        </div>
        <div className="field">
          <label htmlFor="plot-planting">Planting date</label>
          <input id="plot-planting" name="planting_date" type="date" max={today} required />
          <span className="hint">Cannot be in the future.</span>
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="plot-crop">Crop</label>
          <select id="plot-crop" name="crop_id" required defaultValue="">
            <option value="" disabled>Choose a crop</option>
            {crops.map((crop) => <option key={crop.id} value={crop.id}>{crop.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="plot-soil">Soil</label>
          <select id="plot-soil" name="soil_id" required defaultValue="">
            <option value="" disabled>Choose a soil</option>
            {soils.map((soil) => <option key={soil.id} value={soil.id}>{soil.name} ({soil.available_water_mm_per_m} mm/m)</option>)}
          </select>
        </div>
      </div>
      <div className="field">
        <label htmlFor="plot-emitter">Emitter</label>
        <select id="plot-emitter" name="emitter_id" required defaultValue="">
          <option value="" disabled>Choose an emitter</option>
          {emitters.map((emitter) => <option key={emitter.id} value={emitter.id}>{emitter.name} — {emitter.flow_lph} L/h</option>)}
        </select>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="plot-row-spacing">Row spacing (m)</label>
          <input id="plot-row-spacing" name="row_spacing_m" type="number" min="0.01" step="any" required inputMode="decimal" />
        </div>
        <div className="field">
          <label htmlFor="plot-emitter-spacing">Emitter spacing (m)</label>
          <input id="plot-emitter-spacing" name="emitter_spacing_m" type="number" min="0.01" step="any" required inputMode="decimal" />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="plot-lat">Latitude</label>
          <input id="plot-lat" name="lat" type="number" min="-90" max="90" step="any" required inputMode="decimal" />
        </div>
        <div className="field">
          <label htmlFor="plot-lon">Longitude</label>
          <input id="plot-lon" name="lon" type="number" min="-180" max="180" step="any" required inputMode="decimal" />
        </div>
      </div>
      <span className="hint">The forecast, and so the whole plan, is fetched for these coordinates.</span>
      <button type="submit" disabled={pending}>{pending ? "Saving…" : "Add plot"}</button>
      <FormResult state={state} />
    </form>
  );
}
