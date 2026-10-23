"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Screen, Section, stepHref } from "@/components/Screen";
import { api, Refused, type CaseloadOut } from "@/lib/api";
import { pctShort } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

const HEAD = "px-3 py-3 text-[10.5px] font-semibold tracking-[0.04em] text-muted uppercase sm:px-5";
const CELL = "px-3 py-3.5 sm:px-5";

/** Screen 5: assessed synthetic cases ordered by predicted probability, each with its label. */
export function CaseloadScreen() {
  const { kase } = useCase();
  const [data, setData] = useState<CaseloadOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.caseload().then(setData, (e: Refused) => setError(e.message));
  }, []);

  const likely = data?.rows.filter((r) => r.classification.startsWith("Likely")).length ?? 0;
  return (
    <Screen
      id="caseload"
      title="Caseload"
      lead="Your assessed synthetic cases, ordered by predicted probability, highest first."
      kase={kase}
    >
      {error && <p className="text-error">{error}</p>}
      <Section
        title={
          data
            ? `${data.rows.length} assessed ${data.rows.length === 1 ? "case" : "cases"} · ${likely} labelled likely`
            : "Assessed cases"
        }
      />
      <div className="overflow-x-auto rounded-[14px] border border-line bg-surface">
        <table className="w-full min-w-[760px] border-collapse text-left">
          <thead className="bg-surface-2">
            <tr>
              <th className={HEAD}>#</th>
              <th className={HEAD}>Case</th>
              <th className={HEAD}>GA v2</th>
              <th className={`${HEAD} text-right`}>Probability</th>
              <th className={`${HEAD} text-right`}>95% interval</th>
              <th className={HEAD}>Classification</th>
              <th className={`${HEAD} text-right`}>Rank among reference</th>
            </tr>
          </thead>
          <tbody id="caseload-body">
            {data?.rows.map((row) => (
              <tr
                key={row.case_id}
                aria-current={row.case_id === kase?.id ? "true" : undefined}
                className="border-t border-line aria-current:bg-green-soft"
              >
                <td className={`${CELL} font-mono text-[13px] font-medium text-muted`}>{row.caseload_position}</td>
                <td className={`${CELL} text-sm font-semibold`}>
                  <Link href={stepHref("assessment", row.case_id)} className="hover:underline">
                    {row.label}
                  </Link>
                </td>
                <td className={`${CELL} font-mono text-[13px] text-muted`}>
                  {row.gestational_week_v2 === null || row.gestational_week_v2 === undefined
                    ? ""
                    : `${row.gestational_week_v2} wks`}
                </td>
                <td className={`${CELL} text-right font-mono text-sm font-medium`}>{pctShort(row.probability)}</td>
                <td className={`${CELL} text-right font-mono text-[13px] text-muted`}>
                  {pctShort(row.interval_low)} to {pctShort(row.interval_high)}
                </td>
                <td className={CELL}>
                  <span
                    className={`inline-block rounded-md px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap ${
                      row.classification.startsWith("Likely") ? "bg-green text-green-ink" : "bg-surface-2 text-muted"
                    }`}
                  >
                    {row.classification}
                  </span>
                  {row.certainty === "interval_crosses" && (
                    <span className="mt-1 block text-[11px] text-muted">uncertain: interval crosses the threshold</span>
                  )}
                </td>
                <td className={`${CELL} text-right font-mono text-[13px] text-muted`}>
                  {row.reference_rank_position.toLocaleString()} of {(data.reference_caseload_size + 1).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.rows.length === 0 && (
          <p id="caseload-empty" className="px-5 py-4 text-sm text-muted">
            No assessed cases yet.
          </p>
        )}
      </div>
      {data && (
        <p id="caseload-reference" className="text-xs text-muted">
          {data.interval_label} Labels use the fixed threshold of {pctShort(data.classification_threshold)}.
          Reference: {pctShort(data.prevalence, 2)} low birth weight, {data.events} events.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Link id="register-more" href="/register/" className="btn-primary">
          Register a case
        </Link>
      </div>
      <p className="limit">
        {data && `Frozen model ${data.artefact_version} · logistic regression, feature set C · synthetic cases only`}
      </p>
      <p id="limit-caseload" className="limit">
        {data?.limitation}
      </p>
    </Screen>
  );
}
