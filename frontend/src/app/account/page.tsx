"use client";

import { useRouter } from "next/navigation";
import { Suspense, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, fill, Refused } from "@/lib/api";
import { usePolicy } from "@/lib/usePolicy";
import { firstStop, RequireSession, useSession } from "@/lib/session";

function PasswordForm() {
  const { user, signedIn } = useSession();
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    try {
      await api.changePassword(String(form.get("current")), String(form.get("new")));
      const changed = user ? { ...user, must_change_password: false } : null;
      if (changed) signedIn(changed);
      setMessage("Password changed.");
      router.replace((changed && firstStop(changed)) ?? "/register/");
    } catch (e) {
      setError((e as Refused).message);
    }
  }

  return (
    <form onSubmit={submit} className="card max-w-[440px]" noValidate>
      {user?.must_change_password && (
        <p id="must-change" className="mb-4 font-semibold">
          This account still has its generated first password. Choose your own before working with cases.
        </p>
      )}
      <label htmlFor="current" className="field-label block">
        Current password
      </label>
      <input id="current" name="current" type="password" autoComplete="current-password"
        className="field-input mt-1.5 mb-4" />
      <label htmlFor="new" className="field-label block">
        New password, at least 12 characters
      </label>
      <input id="new" name="new" type="password" autoComplete="new-password"
        className="field-input mt-1.5 mb-4" />
      {error && (
        <p id="password-error" role="alert" className="mb-3 text-error">
          {error}
        </p>
      )}
      {message && <p className="mb-3">{message}</p>}
      <button id="change-password" type="submit" className="btn-primary">
        Change password
      </button>
    </form>
  );
}

/** "Remove my account": a request that an administrator completes. */
function RemoveAccount() {
  const { user, signedIn } = useSession();
  const policy = usePolicy();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function request() {
    if (!user) return;
    setBusy(true);
    setError(null);
    try {
      await api.requestRemoval();
      signedIn({ ...(await api.me()) });
    } catch (e) {
      setError((e as Refused).message);
    } finally {
      setBusy(false);
    }
  }

  const requested = user?.deletion_requested_at;
  return (
    <section id="remove-account" className="card flex max-w-[560px] flex-col gap-3">
      <h2 className="kicker">Remove my account</h2>
      <p className="text-sm">{policy?.sentences.removal_explained}</p>
      {requested ? (
        <p id="removal-pending" className="text-sm font-semibold">
          {fill(policy?.sentences.removal_pending ?? "", { date: new Date(requested).toLocaleDateString() })}
        </p>
      ) : (
        <div>
          <button id="request-removal" type="button" className="btn-outline" disabled={busy} onClick={request}>
            Request removal
          </button>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-error">
          {error}
        </p>
      )}
    </section>
  );
}

export default function Page() {
  return (
    <PlainScreen id="account" title="Account" lead="Change your password, or ask for your account to be removed.">
      <Suspense>
        <RequireSession>
          <PasswordForm />
          <RemoveAccount />
          <p>
            <a id="privacy-link" href="/privacy/" className="text-sm font-semibold text-green underline">
              Privacy Policy and Terms of Use
            </a>
          </p>
        </RequireSession>
      </Suspense>
    </PlainScreen>
  );
}
