"use client";

import type { NumberField } from "@/lib/fields";
import { useRanges } from "@/lib/useRanges";

export type Errors = Record<string, string>;

/**
 * A number entry box in the design's field style: label, monospaced input, and a
 * hint with the unit and the range the API enforces. The API's own message for
 * the field replaces nothing; it is shown beneath in red.
 */
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
  const range = useRanges()[field.key];
  const hint = [field.unit, range ? `${range.low} to ${range.high}` : ""].filter(Boolean).join(" · ");
  return (
    <label className="flex flex-col gap-1.5">
      <span className="field-label">{field.label}</span>
      <input
        id={id}
        type="number"
        step="any"
        inputMode="decimal"
        value={props.value}
        disabled={props.disabled}
        aria-invalid={error ? true : false}
        aria-describedby={`hint-${id} err-${id}`}
        onChange={(e) => props.onChange(e.target.value)}
        className="field-input"
      />
      <span id={`hint-${id}`} className="hint">
        {hint}
      </span>
      {error && (
        <span id={`err-${id}`} className="text-xs text-error">
          {error}
        </span>
      )}
    </label>
  );
}

/** Fields in the design's three column rows; one column on a phone. */
export function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">{children}</div>;
}

/** Messages that do not belong to one entry box, shown beside the action button. */
export function FormStatus({ id, errors, known }: { id: string; errors: Errors; known: string[] }) {
  const general = Object.entries(errors)
    .filter(([field]) => !known.includes(field))
    .map(([, message]) => message);
  return (
    <span id={id} role="alert" className="text-sm text-error">
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
