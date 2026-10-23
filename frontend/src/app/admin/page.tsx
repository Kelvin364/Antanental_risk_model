"use client";

import { Suspense, useCallback, useEffect, useState } from "react";

import { PlainScreen } from "@/components/Screen";
import { api, Refused, type AccountOut, type AuditOut, type GeneratedPassword } from "@/lib/api";
import { RequireSession } from "@/lib/session";

const cell = "[&>td]:border-b [&>td]:border-line [&>td]:px-2 [&>td]:py-2";
const head = "[&>th]:border-b [&>th]:border-line [&>th]:px-2 [&>th]:py-2";

function Administration() {
  const [accounts, setAccounts] = useState<AccountOut[]>([]);
  const [events, setEvents] = useState<AuditOut[]>([]);
  const [issued, setIssued] = useState<GeneratedPassword | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.users().then(setAccounts, (e: Refused) => setError(e.message));
    api.audit().then(setEvents, (e: Refused) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  const act = (work: Promise<unknown>) =>
    work.then(load, (e: Refused) => setError(e.message));

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    try {
      setIssued(await api.createUser(String(form.get("username")), String(form.get("role"))));
      load();
    } catch (e) {
      setError((e as Refused).message);
    }
  }

  return (
    <>
      {error && (
        <p id="admin-error" role="alert" className="mb-4 text-error">
          {error}
        </p>
      )}
      {issued && (
        <div id="issued" className="card border-green">
          <p className="font-semibold">
            Password for {issued.username}: <span className="font-mono">{issued.password}</span>
          </p>
          <p className="text-sm text-muted">{issued.note}</p>
        </div>
      )}
      <form onSubmit={create} className="card flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="new-username" className="block font-semibold">
            Username
          </label>
          <input id="new-username" name="username" className="mt-1 rounded-lg border border-line bg-surface px-3 py-2.5" />
        </div>
        <div>
          <label htmlFor="new-role" className="block font-semibold">
            Role
          </label>
          <select id="new-role" name="role" className="mt-1 rounded-lg border border-line bg-surface px-3 py-2.5">
            <option value="researcher">Researcher</option>
            <option value="administrator">Administrator</option>
          </select>
        </div>
        <button id="create-account" type="submit" className="btn-primary">
          Create account
        </button>
      </form>
      <div className="card overflow-x-auto">
        <h2 className="mb-2 text-lg font-bold">Accounts</h2>
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className={head}>
              <th>Username</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="accounts">
            {accounts.map((a) => (
              <tr key={a.id} className={cell}>
                <td>{a.username}</td>
                <td>{a.role}</td>
                <td>{a.active ? (a.must_change_password ? "Active, first password" : "Active") : "Deactivated"}</td>
                <td className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary px-3 py-1.5"
                    onClick={() => api.resetPassword(a.id).then(setIssued, (e: Refused) => setError(e.message))}>
                    Reset password
                  </button>
                  <button type="button" className="btn-secondary px-3 py-1.5"
                    onClick={() => act(api.setActive(a.id, !a.active))}>
                    {a.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card overflow-x-auto">
        <h2 className="mb-2 text-lg font-bold">Audit trail</h2>
        <p className="mb-2 text-sm text-muted">The latest 200 events. No clinical value is ever recorded here.</p>
        <table className="w-full border-collapse text-left text-sm">
          <thead>
            <tr className={head}>
              <th>When</th>
              <th>Event</th>
              <th>User</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody id="audit">
            {events.map((e, i) => (
              <tr key={i} className={cell}>
                <td>{new Date(e.at).toLocaleString()}</td>
                <td>{e.event.replaceAll("_", " ")}</td>
                <td>{e.username}</td>
                <td>{e.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Page() {
  return (
    <PlainScreen id="administration" title="Administration" lead="Create and manage accounts, and read the audit trail.">
      <Suspense>
        <RequireSession role="administrator">
          <Administration />
        </RequireSession>
      </Suspense>
    </PlainScreen>
  );
}
