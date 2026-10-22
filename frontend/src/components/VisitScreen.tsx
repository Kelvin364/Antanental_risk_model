"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { byField, FormStatus, NumberInput, type Errors } from "@/components/fields";
import { Screen, stepHref } from "@/components/Screen";
import { api, Refused, type VisitCreate } from "@/lib/api";
import { pct, toNumber, toText, VISIT } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

const COPY = {
  1: {
    id: "visit1",
    title: "Visit one",
    lead: "First antenatal visit, at or before 28 weeks.",
    action: "Save and continue",
  },
  2: {
    id: "visit2",
    title: "Visit two",
    lead: "The prediction point. Must be later than visit one and at or before 28 weeks.",
    action: "Save and assess",
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
    <p id="screen-note" className="mt-2 text-xs text-muted">
      {note}
    </p>
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

  const missing = !loading && !kase;
  return (
    <Screen id={copy.id} title={copy.title} lead={copy.lead} kase={kase}>
      {missing ? (
        <p className="card">
          {error ?? (caseId === null ? "No case is open." : "")}{" "}
          <Link href="/register/" className="font-semibold text-green underline">
            Register a synthetic pregnancy first.
          </Link>
        </p>
      ) : (
        <>
          <div className="card">
            {kase && <p className="mb-3 text-sm text-muted">Case: {kase.label}</p>}
            <div className="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-3.5">
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
            </div>
            {number === 2 && <ScreenNote />}
          </div>
          <div className="mt-4.5 flex flex-wrap items-center gap-2.5">
            <button
              id={`save-visit${number}`}
              className="btn-primary"
              disabled={busy || !kase}
              onClick={save}
            >
              {copy.action}
            </button>
            <FormStatus
              id={`status-visit${number}`}
              errors={errors}
              known={VISIT.map((f) => f.key)}
            />
          </div>
        </>
      )}
    </Screen>
  );
}
