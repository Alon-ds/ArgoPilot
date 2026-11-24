"use client";
import { useActionState } from "react";
import { createFarmAction, type FormState } from "@/app/actions";
import { FormResult } from "@/components/form-result";

export function AddFarmForm() {
  const [state, action, pending] = useActionState<FormState, FormData>(createFarmAction, null);
  return (
    <form action={action} className="entry-form">
      <div className="field">
        <label htmlFor="farm-name">Farm name</label>
        <input id="farm-name" name="name" required maxLength={120} autoComplete="off" />
      </div>
      <button type="submit" disabled={pending}>{pending ? "Saving…" : "Add farm"}</button>
      <FormResult state={state} />
    </form>
  );
}
