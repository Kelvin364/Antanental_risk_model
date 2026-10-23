"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Screen, stepHref } from "@/components/Screen";
import { api, Refused, type CaseloadOut } from "@/lib/api";
import { pct } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

/** Screen 5: assessed synthetic cases ordered by predicted probability, with each label. */
export function CaseloadScreen() {
  const { kase } = useCase();
  const [data, setData] = useState<CaseloadOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.caseload().then(setData, (e: Refused) => setError(e.message));
  }, []);

  return (
    <Screen
      id="caseload"
      title="Caseload"
      lead="Assessed synthetic cases, ordered by predicted probability."
      kase={kase}
    >
      {error && <p className="mb-4 text-error">{error}</p>}
      <div className="card overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm tabular-nums">
          <thead>
            <tr className="[&>th]:border-b [&>th]:border-line [&>th]:px-2 [&>th]:py-2.5">
              <th>Position</th>
              <th>Case</th>
              <th>Classification</th>
              <th>Probability</th>
              <th>95 percent interval</th>
              <th>Rank among reference</th>
            </tr>
          </thead>
          <tbody id="caseload-body">
            {data?.rows.map((row) => (
              <tr
                key={row.case_id}
                aria-current={row.case_id === kase?.id ? "true" : undefined}
                className="aria-current:bg-green-soft [&>td]:border-b [&>td]:border-line [&>td]:px-2 [&>td]:py-2.5"
              >
                <td>{row.caseload_position}</td>
                <td>
                  <Link href={stepHref("assessment", row.case_id)} className="text-green underline">
                    {row.label}
                  </Link>
                </td>
                <td>
                  {row.classification}
                  {row.certainty === "interval_crosses" && (
                    <span className="block text-xs text-muted">uncertain: interval crosses the threshold</span>
                  )}
                </td>
                <td>{pct(row.probability)}</td>
                <td>
                  {pct(row.interval_low)} to {pct(row.interval_high)}
                </td>
                <td>
                  {row.reference_rank_position.toLocaleString()} of{" "}
                  {(data.reference_caseload_size + 1).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.rows.length === 0 && <p id="caseload-empty">No assessed cases yet.</p>}
        {data && (
          <p id="caseload-reference" className="mt-2 text-xs text-muted">
            {data.interval_label} Labels use the fixed threshold of {pct(data.classification_threshold)}.
            Reference: {pct(data.prevalence)} low birth weight, {data.events} events, artefact version{" "}
            {data.artefact_version}.
          </p>
        )}
      </div>
      <div className="mt-4.5 flex flex-wrap items-center gap-2.5">
        <Link id="register-more" href="/register/" className="btn-primary">
          Register a case
        </Link>
      </div>
      <p id="limit-caseload" className="limit">
        {data?.limitation}
      </p>
    </Screen>
  );
}
