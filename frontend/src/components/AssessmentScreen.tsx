"use client";

import Link from "next/link";

import { ClassificationPanel } from "@/components/ClassificationPanel";
import { Screen, stepHref } from "@/components/Screen";
import type { AssessmentOut } from "@/lib/api";
import { pctShort } from "@/lib/fields";
import { useCase } from "@/lib/useCase";

const ordinal = (n: number) => {
  const tail = n % 100 >= 11 && n % 100 <= 13 ? "th" : ({ 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th");
  return `${n}${tail}`;
};

/** The design's position card: the share of the development cohort this case ranks above. */
function PositionCard({ a }: { a: AssessmentOut }) {
  const size = a.reference_caseload_size;
  const above = Math.round((100 * (size - a.rank_position + 1)) / size);
  const share = Math.min(100, Math.max(0, above));
  return (
    <div className="card flex flex-col gap-3">
      <div className="kicker">Caseload position</div>
      <div id="position" className="big">
        {ordinal(share)}
      </div>
      <div aria-hidden="true" className="relative h-3 rounded-full bg-green-soft">
        <div className="absolute inset-y-0 left-0 rounded-full bg-green" style={{ width: `${share}%` }} />
        <div className="absolute -top-[3px] h-[18px] w-[3px] rounded-[2px] bg-ink" style={{ left: `calc(${share}% - 1.5px)` }} />
      </div>
      <p className="text-[13px] leading-[1.35] text-muted">
        Higher predicted probability than about {share}% of the {size.toLocaleString()} development
        pregnancies. Rank <span id="rank">{`${a.rank_position.toLocaleString()} of ${(size + 1).toLocaleString()}`}</span>,
        where 1 is the highest.
      </p>
    </div>
  );
}

function ProbabilityCard({ a }: { a: AssessmentOut }) {
  return (
    <div className="card flex flex-col gap-2">
      <div className="kicker">Predicted probability of low birth weight</div>
      <div id="prob" className="big">
        {pctShort(a.probability)}
      </div>
      <p id="interval" className="font-mono text-[13px] text-muted">
        95% interval {pctShort(a.interval_low)} to {pctShort(a.interval_high)}
      </p>
      <p id="interval-label" className="text-xs text-muted">
        {a.interval_label}
      </p>
      <p id="reference" className="text-[13px] leading-[1.35] text-muted">
        Reference event rate in the development records: {pctShort(a.prevalence, 2)} ({a.events} of{" "}
        {a.reference_caseload_size.toLocaleString()}).
      </p>
    </div>
  );
}

/** Screen 4: position and probability, then the label with its confidence (Table 3.10, D6). */
export function AssessmentScreen() {
  const { kase, error, loading } = useCase();
  const a = kase?.latest_assessment ?? null;
  const caseId = kase?.id ?? null;

  return (
    <Screen
      id="assessment"
      title="Assessment"
      lead="The model labels and orders the caseload. It does not decide care."
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
          {kase && <p className="hint">Case: {kase.label}</p>}
          {a && (
            <>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <PositionCard a={a} />
                <ProbabilityCard a={a} />
              </div>
              <ClassificationPanel a={a} />
              <div className="rounded-lg border-l-[3px] border-green bg-green-soft px-4 py-3.5 text-[13px] leading-[1.4]">
                <b className="font-semibold">How to read this. </b>
                The position ranks this pregnancy against the development pregnancies by predicted
                probability, to order a caseload for research. It is not a diagnosis and does not
                decide care.
              </div>
              <p id="version" className="hint">
                Artefact version {a.artefact_version}, SHA 256 {a.artefact_sha256.slice(0, 16)}
                {a.assessed_at && <>, assessed {new Date(a.assessed_at).toLocaleString()}</>}.
              </p>
            </>
          )}
          <div className="flex flex-wrap items-center gap-3">
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
