"use client";

import { useState } from "react";

import { api, fill, Refused } from "@/lib/api";
import { usePolicy } from "@/lib/usePolicy";

/**
 * "Delete this case" with a confirmation shown in the page, never a browser dialog.
 * Only the owner can delete; the API answers 404 for anyone else.
 */
export function DeleteCase({ caseId, label, onDeleted, compact = false }: {
  caseId: number;
  label: string;
  onDeleted: () => void;
  compact?: boolean;
}) {
  const policy = usePolicy();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const size = compact ? "px-3 py-1.5 text-xs" : "";

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteCase(caseId);
      onDeleted();
    } catch (e) {
      setError((e as Refused).message);
    } finally {
      setBusy(false);
    }
  }

  if (!asking) {
    return (
      <button type="button" id={`delete-case-${caseId}`} className={`btn-outline delete-case ${size}`} onClick={() => setAsking(true)}>
        Delete this case
      </button>
    );
  }
  return (
    <div id={`confirm-delete-${caseId}`} role="group" aria-label="Confirm deletion"
      className="confirm-delete flex flex-col gap-2 rounded-lg border border-green bg-green-soft px-4 py-3 text-sm">
      <p>{fill(policy?.sentences.delete_confirm ?? "", { label })}</p>
      {error && (
        <p role="alert" className="text-error">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" className={`btn-primary confirm ${size}`} disabled={busy} onClick={confirm}>
          Delete
        </button>
        <button type="button" className={`btn-secondary keep ${size}`} onClick={() => setAsking(false)}>
          Keep
        </button>
      </div>
    </div>
  );
}
