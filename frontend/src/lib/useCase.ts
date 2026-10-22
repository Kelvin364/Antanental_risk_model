"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, Refused, type CaseOut } from "./api";

/** The case named by ?case= in the address, read from the API. */
export function useCase() {
  const raw = useSearchParams().get("case");
  const caseId = raw && /^\d+$/.test(raw) ? Number(raw) : null;
  const [kase, setKase] = useState<CaseOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(caseId !== null);

  useEffect(() => {
    if (caseId === null) {
      setKase(null);
      setLoading(false);
      return;
    }
    let live = true;
    setLoading(true);
    setError(null);
    api
      .getCase(caseId)
      .then((found) => live && setKase(found))
      .catch((e: Refused) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [caseId]);

  return { caseId, kase, error, loading };
}
