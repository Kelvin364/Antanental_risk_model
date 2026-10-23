"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { byField, FieldGrid, FormStatus, NumberInput, type Errors } from "@/components/fields";
import { Screen, Section, stepHref } from "@/components/Screen";
import { api, Refused, type CaseCreate } from "@/lib/api";
import { FLAGS, HISTORY, MOTHER, REGISTRATION, toNumber, toText } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

type Flags = Partial<Record<(typeof FLAGS)[number]["key"], boolean>>;

/** Screen 1: registration characteristics, feature set A, in the design's sections. */
export function RegisterScreen() {
  const router = useRouter();
  const { caseId, kase, error } = useCase();
  const [label, setLabel] = useState("");
  const [numbers, setNumbers] = useState<Record<string, string>>({});
  const [flags, setFlags] = useState<Flags>({});
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const saved = kase !== null;

  // An open case shows what was registered; the API has no edit for it.
  useEffect(() => {
    if (!kase) return;
    setLabel(kase.label);
    setNumbers(Object.fromEntries(REGISTRATION.map((f) => [f.key, toText(kase[f.key])])));
    setFlags(Object.fromEntries(FLAGS.map((f) => [f.key, Boolean(kase[f.key])])));
  }, [kase]);

  async function save() {
    if (saved) {
      router.push(stepHref("visit1", kase.id));
      return;
    }
    setErrors({});
    setBusy(true);
    const body: CaseCreate = {
      synthetic: true,
      label: label.trim() || null,
      ...Object.fromEntries(REGISTRATION.map((f) => [f.key, toNumber(numbers[f.key])])),
      ...flags,
    } as CaseCreate;
    try {
      const created = await api.createCase(body);
      router.push(stepHref("visit1", created.id));
    } catch (refused) {
      setErrors(byField((refused as Refused).errors));
      setBusy(false);
    }
  }

  const fields = (list: typeof MOTHER) =>
    list.map((field) => (
      <NumberInput
        key={field.key}
        prefix="reg"
        field={field}
        value={numbers[field.key] ?? ""}
        error={errors[field.key]}
        disabled={saved}
        onChange={(v) => setNumbers((n) => ({ ...n, [field.key]: v }))}
      />
    ));

  return (
    <Screen
      id="register"
      title="Register the pregnancy"
      lead="Booking details known before the second visit, as in feature set A of the study."
      kase={kase}
    >
      {caseId !== null && error && <p className="text-error">{error}</p>}
      {saved && (
        <p className="rounded-lg border-l-[3px] border-green bg-green-soft px-4 py-3.5 text-[13px]">
          Saved as {kase.label}. Registration values cannot be changed once saved; register another
          case to use different values.
        </p>
      )}
      <Section title="Mother" />
      <FieldGrid>{fields(MOTHER)}</FieldGrid>
      <Section title="Pregnancy history" />
      <FieldGrid>
        {fields(HISTORY)}
        <label className="flex flex-col gap-1.5">
          <span className="field-label">Case label (optional, never a name)</span>
          <input
            id="reg-label"
            type="text"
            maxLength={80}
            value={label}
            disabled={saved}
            onChange={(e) => setLabel(e.target.value)}
            className="field-input"
          />
          <span className="hint">{errors.label ?? "shown in the caseload"}</span>
        </label>
      </FieldGrid>
      <Section title="Medical history" />
      <div className="grid grid-cols-1 gap-x-5 gap-y-2.5 sm:grid-cols-3">
        {FLAGS.map((flag) => (
          <label key={flag.key} className="flex items-center gap-2 text-[13px]">
            <input
              id={`reg-${flag.key}`}
              type="checkbox"
              className="size-4 accent-green"
              checked={flags[flag.key] ?? false}
              disabled={saved}
              onChange={(e) => setFlags((f) => ({ ...f, [flag.key]: e.target.checked }))}
            />
            {flag.label}
          </label>
        ))}
      </div>
      <label className="flex items-center gap-2 text-[13px] font-semibold">
        <input id="synthetic" type="checkbox" className="size-4 accent-green" checked disabled />
        Synthetic case (required, cannot be changed)
      </label>
      {errors.synthetic && (
        <div id="err-synthetic" className="text-xs text-error">
          {errors.synthetic}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <button id="save-register" className="btn-primary" disabled={busy} onClick={save}>
          Continue to visit one
        </button>
        <Link href="/caseload/" className="btn-secondary">
          View caseload
        </Link>
        <FormStatus
          id="status-register"
          errors={errors}
          known={["label", "synthetic", ...REGISTRATION.map((f) => f.key)]}
        />
      </div>
    </Screen>
  );
}
