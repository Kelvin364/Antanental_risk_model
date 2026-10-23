"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useSession } from "@/lib/session";

/** The title bar: who is signed in, their pages, and sign out. No logo (rule 11). */
export function AppHeader() {
  const { user, signOut } = useSession();
  const router = useRouter();
  const out = async () => {
    await signOut();
    router.replace("/sign-in/");
  };
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[980px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3.5">
        <b className="mr-auto text-[17px]">Antenatal Caseload</b>
        <nav aria-label="Account" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          <Link href="/about/" className="text-green underline">
            About
          </Link>
          {user && (
            <>
              {user.role === "administrator" && (
                <Link id="nav-admin" href="/admin/" className="text-green underline">
                  Administration
                </Link>
              )}
              <Link id="nav-account" href="/account/" className="text-green underline">
                {user.username} ({user.role})
              </Link>
              <button id="sign-out" type="button" onClick={out} className="cursor-pointer text-green underline">
                Sign out
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
