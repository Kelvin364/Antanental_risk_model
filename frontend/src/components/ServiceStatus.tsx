"use client";

import { useEffect, useState } from "react";

import { api, type Health } from "@/lib/api";

/** Footer line from /health: which artefact is serving and that its checksum passed. */
export function ServiceStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    api.health().then(setHealth, () => setDown(true));
  }, []);

  if (down) {
    return (
      <p id="service-status" className="text-error">
        The scoring service cannot be reached.
      </p>
    );
  }
  if (!health) return <p id="service-status">Checking the scoring service.</p>;
  return (
    <p id="service-status">
      Scoring service {health.status}: artefact version {health.artefact_version}, SHA 256{" "}
      <span className="font-mono">{health.artefact_sha256.slice(0, 16)}</span>, checksum verified
      at start up, {health.n_features} features.
    </p>
  );
}
