import type { AssessmentOut } from "@/lib/api";
import { pct } from "@/lib/fields";

type Classification = AssessmentOut["classification"];
type Estimate = Classification["sensitivity"];

const per100 = (e: Estimate) =>
  `${Math.round(100 * e.estimate)} (95 percent interval ${Math.round(100 * e.low)} to ${Math.round(100 * e.high)})`;

/**
 * Where the case's 95 percent interval sits against the threshold, drawn on a
 * probability scale. The sentence beside it says the same thing in words, so
 * the drawing is hidden from screen readers.
 */
function IntervalScale({ a }: { a: AssessmentOut }) {
  const c = a.classification;
  const top = Math.max(0.3, (Number.isFinite(a.interval_high) ? a.interval_high : a.probability) * 1.15);
  const at = (v: number) => `${Math.min(100, (100 * v) / top)}%`;
  const hasInterval = Number.isFinite(a.interval_low) && Number.isFinite(a.interval_high);
  return (
    <div aria-hidden="true" className="relative mt-4 mb-6 h-8">
      <div className="absolute top-3.5 right-0 left-0 h-1 rounded bg-line" />
      {hasInterval && (
        <div
          className="absolute top-2.5 h-3 rounded bg-green-soft ring-1 ring-green"
          style={{ left: at(a.interval_low), width: `calc(${at(a.interval_high)} - ${at(a.interval_low)})` }}
        />
      )}
      <div className="absolute top-1.5 h-5 w-1 bg-green" style={{ left: at(a.probability) }} />
      <div className="absolute top-0 h-8 border-l-2 border-dashed border-ink" style={{ left: at(c.threshold) }} />
      <span className="absolute top-8 -translate-x-1/2 text-xs whitespace-nowrap text-muted" style={{ left: at(c.threshold) }}>
        threshold {pct(c.threshold)}
      </span>
    </div>
  );
}

/** The label at the fixed threshold, how settled it is for this case, and how often it is right. */
export function ClassificationPanel({ a }: { a: AssessmentOut }) {
  const c = a.classification;
  const forLabel = c.likely
    ? `Of every 100 development pregnancies given this label, ${per100(c.ppv)} had low birth weight.`
    : `Of every 100 development pregnancies given this label, ${per100(c.npv)} did not have low birth weight.`;
  return (
    <>
      <div className="card" id="classification">
        <div className="kicker">Classification at the fixed threshold</div>
        <div id="class-label" className="mt-2 text-2xl font-semibold sm:text-[28px]">
          {c.label}
        </div>
        <p id="threshold" className="mt-2 text-[13px] leading-[1.4] text-muted">
          The label is &ldquo;likely&rdquo; when the predicted probability is {pct(c.threshold)} or more. That
          threshold marks the highest {c.budget_percent} percent of predictions on the development records and
          was fixed before any further analysis.
        </p>
        <IntervalScale a={a} />
        <p id="certainty" className="text-[13px] leading-[1.4]">{c.certainty_statement}</p>
        <p id="label-confidence" className="mt-2 text-sm font-semibold">
          {forLabel}
        </p>
      </div>
      <div className="card" id="reliability">
        <div className="kicker">How often the label is right at this threshold</div>
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[13px] leading-[1.4]">
          <li id="sensitivity">
            Finds {per100(c.sensitivity)} of every 100 low birth weight births (sensitivity).
          </li>
          <li id="specificity">
            Correctly labels {per100(c.specificity)} of every 100 pregnancies without low birth weight as not
            likely (specificity).
          </li>
          <li id="ppv">
            Of every 100 labelled likely, {per100(c.ppv)} had low birth weight (positive predictive value).
          </li>
          <li id="npv">
            Of every 100 labelled not likely, {per100(c.npv)} did not (negative predictive value).
          </li>
        </ul>
        <p id="reliability-source" className="hint mt-3 leading-[1.4]">
          From out of fold predictions on {c.n.toLocaleString()} development pregnancies with {c.events} low
          birth weight births, with group bootstrap intervals. Not yet checked on the held out records.
        </p>
      </div>
    </>
  );
}
