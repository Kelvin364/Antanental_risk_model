"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Banner } from "@/components/Screen";
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
    <form
      onSubmit={submit}
      noValidate
      className="flex w-full max-w-[440px] flex-col gap-[22px] rounded-2xl border border-line bg-surface p-6 shadow-[0_10px_28px_rgba(22,24,28,0.06)] sm:p-10"
    >
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <p className="text-[13px] leading-[1.35] text-muted">Sign in to record and assess synthetic cases.</p>
      </div>
      <div className="flex flex-col gap-3.5">
        <label className="flex flex-col gap-1.5">
          <span className="field-label">Username</span>
          <input id="username" name="username" autoComplete="username" required className="field-input" />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="field-label">Password</span>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="field-input"
          />
        </label>
      </div>
      <p className="text-right text-xs font-medium text-green">Forgot your password? An administrator can reset it.</p>
      {error && (
        <p id="sign-in-error" role="alert" className="text-sm text-error">
          {error}
        </p>
      )}
      <div className="flex flex-col gap-2.5">
        <button id="sign-in" type="submit" className="btn-primary w-full" disabled={busy}>
          Sign in
        </button>
        <p className="text-center text-[13px] text-muted">Accounts are created by an administrator.</p>
      </div>
      <p className="font-mono text-[10px] leading-[1.4] text-muted">
        Research prototype for a bachelor&rsquo;s capstone. Synthetic data only.
      </p>
    </form>
  );
}

export default function Page() {
  return (
    <main id="sign-in-screen" className="mx-auto flex max-w-[1000px] flex-col items-center gap-8 px-4 pt-9 pb-15">
      <div className="w-full">
        <Banner />
      </div>
      <Suspense>
        <SignInForm />
      </Suspense>
    </main>
  );
}
