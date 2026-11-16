"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, fill, Refused, type PolicyOut } from "@/lib/api";
import { RequireSession, useSession } from "@/lib/session";

/** The Terms of Use, one square checkbox and one green button, disabled until ticked. */
function ConsentForm() {
  const { user, signedIn } = useSession();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [policy, setPolicy] = useState<PolicyOut | null>(null);
  const [ticked, setTicked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.policy().then(setPolicy, (e: Refused) => setError(e.message));
  }, []);

  async function agree() {
    if (!policy || !user) return;
    setBusy(true);
    setError(null);
    try {
      await api.consent(policy.version);
      signedIn({ ...user, terms_accepted: true, terms_version: policy.version, terms_accepted_at: new Date().toISOString() });
      const safe = next && next.startsWith("/") && !next.startsWith("//") ? next : "/register/";
      router.replace(safe);
    } catch (e) {
      setError((e as Refused).message);
      api.policy().then(setPolicy, () => undefined);
    } finally {
      setBusy(false);
    }
  }

  const accepted = user?.terms_accepted && user.terms_accepted_at;
  return (
    <div className="card flex max-w-[720px] flex-col gap-4">
      <p className="text-sm text-muted">{policy?.sentences.consent_lead}</p>
      <h2 className="kicker">Terms of Use, version {policy?.version}</h2>
      <p id="terms-of-use" className="text-sm leading-[1.5]">
        {policy?.terms_of_use}
      </p>
      <a href="/privacy/" className="text-sm font-semibold text-green underline">
        Read the full Privacy Policy and Terms of Use
      </a>
      {accepted ? (
        <p id="consent-done" className="text-sm font-semibold">
          {fill(policy?.sentences.consent_done ?? "", {
            date: new Date(user.terms_accepted_at!).toLocaleDateString(),
          })}
        </p>
      ) : (
        <>
          <label className="flex items-start gap-3 text-sm">
            <input
              id="consent-box"
              type="checkbox"
              checked={ticked}
              onChange={(e) => setTicked(e.target.checked)}
              className="mt-0.5 size-[18px] shrink-0 rounded-none accent-green"
            />
            <span>{policy?.consent_sentence}</span>
          </label>
          {error && (
            <p id="consent-error" role="alert" className="text-sm text-error">
              {error}
            </p>
          )}
          <div>
            <button id="agree" type="button" className="btn-primary" disabled={!ticked || busy || !policy} onClick={agree}>
              I agree
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <PlainScreen id="consent" title="Before you continue" lead="Terms of Use for this research prototype.">
      <Suspense>
        <RequireSession>
          <ConsentForm />
        </RequireSession>
      </Suspense>
    </PlainScreen>
  );
}
