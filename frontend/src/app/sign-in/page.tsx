"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, Refused } from "@/lib/api";
import { useSession } from "@/lib/session";

function SignInForm() {
  const { signedIn } = useSession();
  const router = useRouter();
  const next = useSearchParams().get("next");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const me = await api.signIn(String(form.get("username")), String(form.get("password")));
      signedIn(me);
      const safe = next && next.startsWith("/") && !next.startsWith("//") ? next : "/register/";
      router.replace(me.must_change_password ? "/account/" : safe);
    } catch (e) {
      setError((e as Refused).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card max-w-md" noValidate>
      <label htmlFor="username" className="block font-semibold">
        Username
      </label>
      <input id="username" name="username" autoComplete="username" required
        className="mt-1 mb-4 w-full rounded-lg border border-line bg-surface px-3 py-2.5" />
      <label htmlFor="password" className="block font-semibold">
        Password
      </label>
      <input id="password" name="password" type="password" autoComplete="current-password" required
        className="mt-1 mb-4 w-full rounded-lg border border-line bg-surface px-3 py-2.5" />
      {error && (
        <p id="sign-in-error" role="alert" className="mb-3 text-error">
          {error}
        </p>
      )}
      <button id="sign-in" type="submit" className="btn-primary" disabled={busy}>
        Sign in
      </button>
      <p className="mt-4 text-sm text-muted">
        Accounts are created by an administrator. There is no self registration.
      </p>
    </form>
  );
}

export default function Page() {
  return (
    <PlainScreen id="sign-in-screen" title="Sign in" lead="Sign in to record and assess synthetic cases.">
      <Suspense>
        <SignInForm />
      </Suspense>
    </PlainScreen>
  );
}
