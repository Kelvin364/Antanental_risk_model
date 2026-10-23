"use client";

import { useRouter } from "next/navigation";
import { Suspense, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, Refused } from "@/lib/api";
import { RequireSession, useSession } from "@/lib/session";

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
      if (user) signedIn({ ...user, must_change_password: false });
      setMessage("Password changed.");
      router.replace("/register/");
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

export default function Page() {
  return (
    <PlainScreen id="account" title="Account" lead="Change your password.">
      <Suspense>
        <RequireSession>
          <PasswordForm />
        </RequireSession>
      </Suspense>
    </PlainScreen>
  );
}
