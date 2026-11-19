"use client";

import Link from "next/link";
import { api, type CaseOut } from "@/lib/api";

export type Step = "register" | "visit1" | "visit2" | "assessment" | "caseload";

const STEPS: { id: Step; label: string; path: string }[] = [
  { id: "register", label: "Register", path: "/register/" },
  { id: "visit1", label: "Visit one", path: "/visit-one/" },
  { id: "visit2", label: "Visit two", path: "/visit-two/" },
  { id: "assessment", label: "Assessment", path: "/assessment/" },
  { id: "caseload", label: "Caseload", path: "/caseload/" },
];

/** Link to a step, keeping the open case. */
export function stepHref(step: Step, caseId: number | null) {
  const path = STEPS.find((s) => s.id === step)!.path;
  return caseId === null ? path : `${path}?case=${caseId}`;
}

// How far the open case has got: a step opens once the one before it is saved.
function reached(kase: CaseOut | null) {
  if (!kase) return 0;
  if (kase.latest_assessment) return 3;
  return kase.visits.some((v) => v.visit_number === 1) ? 2 : 1;
}

/** The design's tab bar: number and label, underlined in green on the current step. */
function Steps({ current, kase }: { current: Step; kase: CaseOut | null }) {
  const furthest = reached(kase);
  return (
    <nav aria-label="Steps" className="border-b border-line bg-surface">
      <ol className="flex list-none flex-wrap gap-x-5 px-4 pt-2.5 sm:gap-x-[30px] sm:px-10">
        {STEPS.map((step, i) => {
          const open = i <= furthest || step.id === "caseload";
          const here = step.id === current;
          const style = `flex items-center gap-[7px] border-b-2 pt-1 pb-2.5 text-[13px] whitespace-nowrap ${
            here ? "border-green font-semibold text-ink" : "border-transparent font-medium text-muted"
          }`;
          const text = (
            <>
              <span className={`font-mono text-[10px] ${here ? "text-green" : ""}`}>{i + 1}</span>
              {step.label}
            </>
          );
          return (
            <li key={step.id}>
              {open ? (
                <Link
                  href={stepHref(step.id, kase?.id ?? null)}
                  aria-current={here ? "step" : undefined}
                  className={style}
                >
                  {text}
                </Link>
              ) : (
                <span aria-disabled="true" className={`${style} cursor-not-allowed opacity-45`}>
                  {text}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** An uppercase section heading with a rule beneath, as in the design. */
export function Section({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="kicker">{title}</h2>
      <div className="h-px bg-line" />
    </div>
  );
}

function Heading({ title, lead }: { title: string; lead: string }) {
  return (
    <div className="flex flex-col gap-[5px]">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-sm leading-[1.35] text-muted">{lead}</p>
    </div>
  );
}

/** One of the five screens: steps, a heading and its content. */
export function Screen(props: {
  id: Step;
  title: string;
  lead: string;
  kase: CaseOut | null;
  children: React.ReactNode;
}) {
  return (
    <>
      <Steps current={props.id} kase={props.kase} />
      <main className="mx-auto max-w-[1000px] px-4 pt-9 pb-15">
        <section id={props.id} className="flex flex-col gap-5">
          <Heading title={props.title} lead={props.lead} />
          {props.children}
        </section>
      </main>
    </>
  );
}

/** A page outside the five steps (account, administration, about). */
export function PlainScreen(props: { id: string; title: string; lead: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-[1000px] px-4 pt-9 pb-15">
      <section id={props.id} className="flex flex-col gap-5">
        <Heading title={props.title} lead={props.lead} />
        {props.children}
      </section>
    </main>
  );
}
