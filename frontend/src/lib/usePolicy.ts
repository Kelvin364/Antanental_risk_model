"use client";

import { useEffect, useState } from "react";

import { api, type PolicyOut } from "./api";

let cached: Promise<PolicyOut> | null = null;

/** The policy and its fixed sentences from GET /api/policy, fetched once per page load. */
export function usePolicy() {
  const [policy, setPolicy] = useState<PolicyOut | null>(null);
  useEffect(() => {
    cached ??= api.policy();
    cached.then(setPolicy, () => {
      cached = null;
    });
  }, []);
  return policy;
}
