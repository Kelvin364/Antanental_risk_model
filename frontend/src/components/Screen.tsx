"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type CaseOut } from "@/lib/api";

export type Step = "register" | "visit1" | "visit2" | "assessment" | "caseload";

const STEPS: { id: Step; label: string; path: string }[] = [
  { id: "register", label: "Register", path: "/register/" },
  { id: "visit1", label: "Visit one", path: "/visit-one/" },
  { id: "visit2", label: "Visit two", path: "/visit-two/" },
  { id: "assessment", label: "Assessment", path: "/assessment/" },
  { id: "caseload", label: "Caseload", path: "/caseload/" },
];

// The banner text the API serves; shown before the request returns.
const BANNER = "Synthetic cases only. Do not enter any real pregnancy.";

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

function Steps({ current, kase }: { current: Step; kase: CaseOut | null }) {
  const furthest = reached(kase);
  return (
    <nav aria-label="Steps" className="border-b border-line bg-surface">
      <ol className="mx-auto flex max-w-[980px] list-none flex-wrap gap-x-1 px-4">
        {STEPS.map((step, i) => {
          const open = i <= furthest || step.id === "caseload";
          const here = step.id === current;
          const style = `block border-b-[3px] px-1.5 py-2.5 text-sm whitespace-nowrap sm:px-2.5 sm:py-3 sm:text-base ${
            here ? "border-green font-semibold text-ink" : "border-transparent text-muted"
          }`;
          const text = (
            <>
              <span className="mr-1.5 font-mono">{i + 1}</span>
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

export function Banner() {
  const [text, setText] = useState(BANNER);
  useEffect(() => {
    api.interfaceText().then((t) => setText(t.banner), () => undefined);
  }, []);
  return (
    <div
      id="banner"
      role="status"
      className="sticky top-0 z-10 mb-4.5 rounded-lg bg-banner px-3.5 py-2.5 text-sm font-semibold text-banner-ink"
    >
      {text}
    </div>
  );
}

/** One of the five screens: steps, the synthetic banner, a heading and its content. */
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
      <main className="mx-auto max-w-[980px] px-4 pt-5 pb-12">
        <Banner />
        <section id={props.id}>
          <h1 className="mb-1 text-[26px] font-bold">{props.title}</h1>
          <p className="mb-4.5 text-muted">{props.lead}</p>
          {props.children}
        </section>
      </main>
    </>
  );
}

/** A page outside the five steps (sign in, account, administration, about), with the banner. */
export function PlainScreen(props: { id: string; title: string; lead: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto max-w-[980px] px-4 pt-5 pb-12">
      <Banner />
      <section id={props.id}>
        <h1 className="mb-1 text-[26px] font-bold">{props.title}</h1>
        <p className="mb-4.5 text-muted">{props.lead}</p>
        {props.children}
      </section>
    </main>
  );
}
