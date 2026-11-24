import type { FormState } from "@/app/actions";

export function FormResult({ state }: { state: FormState }) {
  if (!state) return null;
  return (
    <p className={state.ok ? "form-ok" : "form-error"} role="status" aria-live="polite">
      {state.message}
    </p>
  );
}
