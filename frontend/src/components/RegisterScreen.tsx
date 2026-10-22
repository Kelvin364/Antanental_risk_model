"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { byField, FormStatus, NumberInput, type Errors } from "@/components/fields";
import { Screen, stepHref } from "@/components/Screen";
import { api, Refused, type CaseCreate } from "@/lib/api";
import { FLAGS, REGISTRATION, toNumber, toText } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

type Flags = Partial<Record<(typeof FLAGS)[number]["key"], boolean>>;

/** Screen 1: registration characteristics, feature set A. */
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

  return (
    <Screen
      id="register"
      title="Register a synthetic pregnancy"
      lead="Registration characteristics, as in feature set A of the study."
      kase={kase}
    >
      {caseId !== null && error && <p className="mb-4 text-error">{error}</p>}
      {saved && (
        <p className="mb-4 rounded-md border-l-4 border-green bg-green-soft px-3.5 py-3">
          Saved as {kase.label}. Registration values cannot be changed once saved; register another
          case to use different values.
        </p>
      )}
      <div className="card">
        <label className="mb-4 flex max-w-sm flex-col gap-1 text-sm">
          Case label (optional, never a name)
          <input
            id="reg-label"
            type="text"
            maxLength={80}
            value={label}
            disabled={saved}
            onChange={(e) => setLabel(e.target.value)}
            className="rounded-lg border border-line bg-bg px-2.5 py-2 text-base text-ink disabled:opacity-70"
          />
          <span className="min-h-[1em] text-[13px] text-error">{errors.label}</span>
        </label>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-3.5">
          {REGISTRATION.map((field) => (
            <NumberInput
              key={field.key}
              prefix="reg"
              field={field}
              value={numbers[field.key] ?? ""}
              error={errors[field.key]}
              disabled={saved}
              onChange={(v) => setNumbers((n) => ({ ...n, [field.key]: v }))}
            />
          ))}
        </div>
        <div className="mt-1.5 grid grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-2">
          {FLAGS.map((flag) => (
            <label key={flag.key} className="flex items-center gap-2 text-sm">
              <input
                id={`reg-${flag.key}`}
                type="checkbox"
                checked={flags[flag.key] ?? false}
                disabled={saved}
                onChange={(e) => setFlags((f) => ({ ...f, [flag.key]: e.target.checked }))}
              />
              {flag.label}
            </label>
          ))}
        </div>
        <label className="mt-3.5 flex items-center gap-2 font-semibold">
          <input id="synthetic" type="checkbox" checked disabled />
          Synthetic case (required, cannot be changed)
        </label>
        <div id="err-synthetic" className="min-h-[1em] text-[13px] text-error">
          {errors.synthetic}
        </div>
      </div>
      <div className="mt-4.5 flex flex-wrap items-center gap-2.5">
        <button id="save-register" className="btn-primary" disabled={busy} onClick={save}>
          {saved ? "Continue to visit one" : "Save and continue"}
        </button>
        <FormStatus
          id="status-register"
          errors={errors}
          known={["label", "synthetic", ...REGISTRATION.map((f) => f.key)]}
        />
      </div>
    </Screen>
  );
}
