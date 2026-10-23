"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useSession } from "@/lib/session";

/**
 * The design's top bar: the product name with a mono subtitle on the left, the
 * signed in user and their pages on the right. No logo and no circled initials
 * (rule 11), and no facility name, because the prototype holds no real place.
 */
export function AppHeader() {
  const { user, signOut } = useSession();
  const router = useRouter();
  const out = async () => {
    await signOut();
    router.replace("/sign-in/");
  };
  return (
    <header className="border-b border-line bg-surface">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3.5 sm:px-10">
        <div className="mr-auto flex flex-col leading-normal">
          <b className="text-[15px] font-semibold">Antenatal Caseload</b>
          <span className="font-mono text-[11px] text-muted">Research prototype · synthetic cases</span>
        </div>
        <nav aria-label="Account" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-medium">
          <Link href="/about/" className="text-muted hover:text-ink">
            About
          </Link>
          {user && (
            <>
              {user.role === "administrator" && (
                <Link id="nav-admin" href="/admin/" className="text-muted hover:text-ink">
                  Administration
                </Link>
              )}
              <Link id="nav-account" href="/account/" className="text-muted hover:text-ink">
                {user.username} · {user.role}
              </Link>
              <button id="sign-out" type="button" onClick={out} className="cursor-pointer font-semibold text-green">
                Sign out
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
