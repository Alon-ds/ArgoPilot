"use client";
import { useActionState } from "react";
import { deletePlotAction, type FormState } from "@/app/actions";

export function DeletePlotButton({ id, name }: { id: string; name: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(deletePlotAction, null);
  return (
    <form
      action={action}
      className="plot-delete-form"
      onSubmit={(event) => {
        // A plot delete removes its history with it, so a typed confirmation
        // is the minimum friction before the write is sent.
        if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) event.preventDefault();
      }}
    >
      <input type="hidden" name="id" value={id} />
      <button
        type="submit"
        disabled={pending}
        className="plot-delete"
        aria-label={`Delete ${name}`}
        title="Delete this plot"
      >
        {pending ? "…" : "Delete"}
      </button>
      {state && !state.ok && <span className="plot-delete-error" role="alert">{state.message}</span>}
    </form>
  );
}
