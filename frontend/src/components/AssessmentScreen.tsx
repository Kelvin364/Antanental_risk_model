"use client";

import Link from "next/link";

import { Screen, stepHref } from "@/components/Screen";
import { pct } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

/** Screen 4: rank position and predicted probability with its interval (Table 3.10). */
export function AssessmentScreen() {
  const { kase, error, loading } = useCase();
  const a = kase?.latest_assessment ?? null;
  const caseId = kase?.id ?? null;

  return (
    <Screen
      id="assessment"
      title="Assessment"
      lead="The model orders the caseload. It does not decide care."
      kase={kase}
    >
      {!loading && !a ? (
        <p className="card">
          {error ?? "This case has no assessment yet. Record both visits to score it."}{" "}
          <Link href={stepHref("register", caseId)} className="font-semibold text-green underline">
            Go to the case.
          </Link>
        </p>
      ) : (
        <>
          {kase && <p className="mb-3 text-sm text-muted">Case: {kase.label}</p>}
          <div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">
            <div className="card">
              <div className="kicker">Rank position</div>
              <div id="rank" className="big">
                {a ? `${a.rank_position.toLocaleString()} of ${(a.reference_caseload_size + 1).toLocaleString()}` : "-"}
              </div>
              {a && (
                <p id="rank-text">
                  Position among {a.reference_caseload_size.toLocaleString()} development
                  pregnancies plus this case, ordered from the highest predicted probability.
                  Position 1 is the highest.
                </p>
              )}
            </div>
            <div className="card">
              <div className="kicker">Predicted probability of low birth weight</div>
              <div id="prob" className="big">
                {a ? pct(a.probability) : "-"}
              </div>
              {a && (
                <>
                  <p id="interval">
                    95 percent interval {pct(a.interval_low)} to {pct(a.interval_high)}
                  </p>
                  <p id="interval-label" className="text-xs text-muted">
                    {a.interval_label}
                  </p>
                </>
              )}
            </div>
          </div>
          {a && (
            <div className="card">
              <p id="reference">
                Low birth weight in the development records: {pct(a.prevalence)} ({a.events} events
                among {a.reference_caseload_size.toLocaleString()} pregnancies).
              </p>
              <p id="version">
                Artefact version {a.artefact_version}, SHA 256{" "}
                <span className="font-mono">{a.artefact_sha256.slice(0, 16)}</span>
                {a.assessed_at && <>, assessed {new Date(a.assessed_at).toLocaleString()}</>}.
              </p>
            </div>
          )}
          <div className="mt-4.5 flex flex-wrap items-center gap-2.5">
            <Link id="to-caseload" href={stepHref("caseload", caseId)} className="btn-primary">
              Open caseload
            </Link>
            <Link id="adjust" href={stepHref("visit2", caseId)} className="btn-secondary">
              Adjust measurements
            </Link>
            <Link id="new-case" href="/register/" className="btn-secondary">
              Register another case
            </Link>
          </div>
          <p id="limit-assessment" className="limit">
            {a?.limitation}
          </p>
        </>
      )}
    </Screen>
  );
}
