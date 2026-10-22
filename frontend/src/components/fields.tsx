"use client";

import type { NumberField } from "@/lib/fields";

export type Errors = Record<string, string>;

/** A number entry box with its unit and the API's message for it, if any. */
export function NumberInput<K extends string>(props: {
  prefix: string;
  field: NumberField<K>;
  value: string;
  error?: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const { prefix, field, error } = props;
  const id = `${prefix}-${field.key}`;
  return (
    <label className="flex flex-col gap-1 text-sm">
      {field.label}
      <input
        id={id}
        type="number"
        step="any"
        inputMode="decimal"
        value={props.value}
        disabled={props.disabled}
        aria-invalid={error ? true : false}
        aria-describedby={`err-${id}`}
        onChange={(e) => props.onChange(e.target.value)}
        className="rounded-lg border border-line bg-bg px-2.5 py-2 text-base text-ink aria-invalid:border-error disabled:opacity-70"
      />
      <span className="text-xs text-muted">{field.unit}</span>
      <span id={`err-${id}`} className="min-h-[1em] text-[13px] text-error">
        {error}
      </span>
    </label>
  );
}

/** Messages that do not belong to one entry box, shown beside the action button. */
export function FormStatus({ id, errors, known }: { id: string; errors: Errors; known: string[] }) {
  const general = Object.entries(errors)
    .filter(([field]) => !known.includes(field))
    .map(([, message]) => message);
  return (
    <span id={id} role="alert" className="text-error">
      {general.join(" ")}
    </span>
  );
}

/** A refusal's field errors keyed by field name. */
export function byField(errors: { field: string; message: string }[]): Errors {
  const out: Errors = {};
  for (const e of errors) out[e.field] = out[e.field] ? `${out[e.field]} ${e.message}` : e.message;
  return out;
}
