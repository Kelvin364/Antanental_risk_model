"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, Refused, setCsrfToken, type SignedIn } from "./api";

type Session = {
  user: SignedIn | null;
  checked: boolean;
  signedIn: (user: SignedIn) => void;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Session>({
  user: null,
  checked: false,
  signedIn: () => undefined,
  signOut: async () => undefined,
});

/** Who is signed in, read once from /api/auth/me and shared by every page. */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<SignedIn | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        setCsrfToken(me.csrf_token);
        setUser(me);
      })
      .catch(() => setUser(null))
      .finally(() => setChecked(true));
  }, []);

  const signedIn = useCallback((me: SignedIn) => {
    setCsrfToken(me.csrf_token);
    setUser(me);
    setChecked(true);
  }, []);

  const signOut = useCallback(async () => {
    await api.signOut();
    setCsrfToken("");
    setUser(null);
  }, []);

  return (
    <SessionContext.Provider value={{ user, checked, signedIn, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

export const useSession = () => useContext(SessionContext);

/** Where a signed in user must go first: the account page for a generated first
 * password, then the consent page until the current Terms of Use are accepted. */
export function firstStop(user: SignedIn): string | null {
  if (user.must_change_password) return "/account/";
  if (!user.terms_accepted) return "/consent/";
  return null;
}

/**
 * Renders its children only for a signed in user. Anyone else is sent to the
 * sign in page, a user with a generated first password to the account page, and
 * a user who has not accepted the current Terms of Use to the consent page.
 * The server enforces the same rules on every request; this only saves a trip.
 */
export function RequireSession({ children, role }: { children: React.ReactNode; role?: string }) {
  const { user, checked } = useSession();
  const router = useRouter();
  const path = usePathname();
  const stop = user ? firstStop(user) : null;
  const elsewhere = stop !== null && path !== stop;

  useEffect(() => {
    if (!checked) return;
    if (!user) router.replace(`/sign-in/?next=${encodeURIComponent(path)}`);
    else if (stop && path !== stop) router.replace(stop);
  }, [checked, user, router, path, stop]);

  if (!checked || !user || elsewhere) {
    return <p className="mx-auto max-w-[980px] px-4 py-8 text-muted">Checking sign in.</p>;
  }
  if (role && user.role !== role) {
    return <p className="mx-auto max-w-[980px] px-4 py-8">Only an administrator can open this page.</p>;
  }
  return <>{children}</>;
}

/** True when a refusal means the session has ended. */
export const sessionEnded = (e: unknown) => e instanceof Refused && e.status === 401;
