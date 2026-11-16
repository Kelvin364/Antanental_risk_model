"use client";

import { useEffect, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, Refused, type PolicyOut } from "@/lib/api";

// "2026-11-16" as "16 November 2026", read as a calendar date with no time zone shift.
const longDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

/** The Privacy Policy and Terms of Use, served by the API and open without sign in. */
export default function Page() {
  const [policy, setPolicy] = useState<PolicyOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.policy().then(setPolicy, (e: Refused) => setError(e.message));
  }, []);

  return (
    <PlainScreen id="privacy" title="Privacy Policy and Terms of Use" lead="What this prototype stores, for how long, and the rules for using it.">
      {error && (
        <p role="alert" className="text-error">
          {error}
        </p>
      )}
      {policy && (
        <article className="card flex max-w-[760px] flex-col gap-5">
          <p id="policy-version" className="font-mono text-xs text-muted">
            Version {policy.version}, in force from {longDate(policy.version)}
          </p>
          {policy.sections.map((section) => (
            <section key={section.heading} className="flex flex-col gap-1.5">
              <h2 className="text-base font-semibold">{section.heading}</h2>
              <p className="text-sm leading-[1.55]">{section.text}</p>
            </section>
          ))}
        </article>
      )}
    </PlainScreen>
  );
}
