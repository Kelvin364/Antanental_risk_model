"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { byField, FieldGrid, FormStatus, NumberInput, type Errors } from "@/components/fields";
import { Screen, Section, stepHref } from "@/components/Screen";
import { api, Refused, type CaseOut, type VisitCreate } from "@/lib/api";
import { pct, toNumber, toText, VISIT } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

const COPY = {
  1: {
    id: "visit1",
    title: "First antenatal visit",
    lead: "The earlier of the two visits, at or before 28 weeks.",
    section: "Measurements at visit one",
    action: "Continue to visit two",
    back: "register",
  },
  2: {
    id: "visit2",
    title: "Second antenatal visit",
    lead: "The prediction moment. Visit two must be later than visit one and within 28 weeks.",
    section: "Measurements at visit two",
    action: "Run assessment",
    back: "visit1",
  },
} as const;

// Why the visit two form still asks for haemoglobin although its change is not used.
function ScreenNote() {
  const [note, setNote] = useState("");
  useEffect(() => {
    api.artefact().then((a) => {
      const hb = a.availability_screen.hb;
      setNote(
        `Availability screen: haemoglobin was recorded at both visits for ` +
          `${pct(hb.available_both_visits)} of development records, below the ` +
          `${pct(a.availability_threshold)} threshold, so only its visit two value is used.`,
      );
    }, () => undefined);
  }, []);
  return (
    <p id="screen-note" className="hint">
      {note}
    </p>
  );
}

const CHANGES: { key: keyof VisitCreate; label: string; unit: string; digits: number }[] = [
  { key: "systolic", label: "Δ systolic BP", unit: "mmHg", digits: 0 },
  { key: "diastolic", label: "Δ diastolic BP", unit: "mmHg", digits: 0 },
  { key: "gestational_week", label: "Δ gestational age", unit: "weeks", digits: 0 },
  { key: "weight_kg", label: "Δ weight", unit: "kg", digits: 1 },
];

/** Visit two minus visit one for display; the model computes its own inputs on the server. */
function ChangeSinceVisitOne({ kase, values }: { kase: CaseOut; values: Record<string, string> }) {
  const first = kase.visits.find((v) => v.visit_number === 1);
  if (!first) return null;
  return (
    <>
      <Section title="Change since visit one (computed)" />
      <div id="change-since-visit-one" className="card grid grid-cols-2 gap-5 sm:grid-cols-4">
        {CHANGES.map(({ key, label, unit, digits }) => {
          const now = toNumber(values[key]);
          const before = first[key];
          const change = now === null || before === null || before === undefined ? null : now - before;
          return (
            <div key={key} className="flex flex-col gap-[3px]">
              <span className="text-xs text-muted">{label}</span>
              <span className="font-mono text-[17px] font-medium">
                {change === null ? "not entered" : `${change >= 0 ? "+" : ""}${change.toFixed(digits)} ${unit}`}
              </span>
            </div>
          );
        })}
      </div>
    </>
  );
}

/** Screens 2 and 3: the measurements of one antenatal visit. */
export function VisitScreen({ number }: { number: 1 | 2 }) {
  const router = useRouter();
  const { caseId, kase, error, loading } = useCase();
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const copy = COPY[number];
  const prefix = `v${number}`;

  // A visit already recorded opens with its values, ready to adjust.
  useEffect(() => {
    const stored = kase?.visits.find((v) => v.visit_number === number);
    if (stored) setValues(Object.fromEntries(VISIT.map((f) => [f.key, toText(stored[f.key])])));
  }, [kase, number]);

  async function save() {
    if (!kase) return;
    setErrors({});
    setBusy(true);
    const body = Object.fromEntries(
      VISIT.map((f) => [f.key, toNumber(values[f.key])]),
    ) as VisitCreate;
    try {
      await api.saveVisit(kase.id, number, body);
      if (number === 2) await api.assess(kase.id);
      router.push(stepHref(number === 1 ? "visit2" : "assessment", kase.id));
    } catch (refused) {
      setErrors(byField((refused as Refused).errors));
      setBusy(false);
    }
  }

  if (!loading && !kase) {
    return (
      <Screen id={copy.id} title={copy.title} lead={copy.lead} kase={kase}>
        <p className="card">
          {error ?? (caseId === null ? "No case is open." : "")}{" "}
          <Link href="/register/" className="font-semibold text-green underline">
            Register a synthetic pregnancy first.
          </Link>
        </p>
      </Screen>
    );
  }
  return (
    <Screen id={copy.id} title={copy.title} lead={copy.lead} kase={kase}>
      {kase && <p className="hint">Case: {kase.label}</p>}
      <Section title={copy.section} />
      <FieldGrid>
        {VISIT.map((field) => (
          <NumberInput
            key={field.key}
            prefix={prefix}
            field={field}
            value={values[field.key] ?? ""}
            error={errors[field.key]}
            onChange={(v) => setValues((s) => ({ ...s, [field.key]: v }))}
          />
        ))}
      </FieldGrid>
      {number === 2 && <ScreenNote />}
      {number === 2 && kase && <ChangeSinceVisitOne kase={kase} values={values} />}
      <div className="flex flex-wrap items-center gap-3">
        <button id={`save-visit${number}`} className="btn-primary" disabled={busy || !kase} onClick={save}>
          {copy.action}
        </button>
        <Link href={stepHref(copy.back, kase?.id ?? null)} className="btn-secondary">
          Back
        </Link>
        <FormStatus id={`status-visit${number}`} errors={errors} known={VISIT.map((f) => f.key)} />
      </div>
    </Screen>
  );
}
