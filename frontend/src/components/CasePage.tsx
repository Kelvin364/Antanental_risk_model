"use client";

import { useSearchParams } from "next/navigation";
import { Fragment, Suspense } from "react";

import { RequireSession } from "@/lib/session";

// Remount the screen when the open case changes, so no entry carries over.
function Keyed({ children }: { children: React.ReactNode }) {
  const caseId = useSearchParams().get("case") ?? "new";
  return <Fragment key={caseId}>{children}</Fragment>;
}

/**
 * A screen that reads ?case= from the address, shown only to a signed in user
 * (decision D1); static export needs the Suspense boundary.
 */
export function CasePage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense>
      <RequireSession>
        <Keyed>{children}</Keyed>
      </RequireSession>
    </Suspense>
  );
}
