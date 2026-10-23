"use client";

import { useEffect, useState } from "react";

import { api, type Range } from "./api";

let cached: Record<string, Range> | null = null;

/** The entry ranges the API enforces, read once and shared, for the hints under each field. */
export function useRanges() {
  const [ranges, setRanges] = useState<Record<string, Range>>(cached ?? {});
  useEffect(() => {
    if (cached) return;
    api.interfaceText().then((t) => {
      cached = t.ranges;
      setRanges(t.ranges);
    }, () => undefined);
  }, []);
  return ranges;
}
