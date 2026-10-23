// Typed client for the FastAPI service. Request and response shapes come from
// api-schema.ts, which is generated from the API's OpenAPI document, so the
// interface cannot drift from the server. Every validation message the user
// sees is the API's own; the interface never checks a range itself.
import createClient from "openapi-fetch";

import type { components, paths } from "./api-schema";

export type CaseCreate = components["schemas"]["CaseCreate"];
export type VisitCreate = components["schemas"]["VisitCreate"];
export type CaseOut = components["schemas"]["CaseOut"];
export type AssessmentOut = components["schemas"]["AssessmentOut"];
export type CaseloadOut = components["schemas"]["CaseloadOut"];
export type SignedIn = components["schemas"]["SignedIn"];
export type AccountOut = components["schemas"]["AccountOut"];
export type GeneratedPassword = components["schemas"]["GeneratedPassword"];
export type AuditOut = components["schemas"]["AuditOut"];

/** One refused value, with the API's reason. */
export type FieldError = { field: string; message: string };

/** Thrown when the API refuses a request; carries every refused field and the status. */
export class Refused extends Error {
  constructor(
    public readonly errors: FieldError[],
    public readonly status = 0,
  ) {
    super(errors.map((e) => e.message).join(" "));
  }
}

/** The parts of the artefact version record the interface reads. */
export type ArtefactRecord = {
  version: string;
  availability_threshold: number;
  availability_screen: Record<string, { available_both_visits: number; passed: boolean }>;
};

export type Health = {
  status: string;
  artefact_version: string;
  artefact_sha256: string;
  data_sha256: string;
  prevalence: number;
  events: number;
  n_features: number;
  reference_caseload_size: number;
};

export type InterfaceText = { banner: string; limitation: string; interval_label: string };

const client = createClient<paths>({ baseUrl: "" });

// The session cookie is HttpOnly, so the page never sees it. Every change also
// carries the session's CSRF token, which the server compares with its own copy.
let csrfToken = "";
export const setCsrfToken = (token: string) => {
  csrfToken = token;
};
client.use({
  onRequest({ request }) {
    if (request.method !== "GET" && csrfToken) request.headers.set("X-CSRF-Token", csrfToken);
    return request;
  },
});

type Detail = { field?: string; message?: string; loc?: (string | number)[]; msg?: string };

// The service answers a refusal with {field, message} items (entry rules,
// missing case, step order); FastAPI's own type checks use {loc, msg}.
function refusal(body: unknown, status: number): Refused {
  const detail = (body as { detail?: unknown } | undefined)?.detail;
  if (!Array.isArray(detail)) {
    return new Refused([{ field: "form", message: `The service refused the request (${status})` }], status);
  }
  return new Refused(
    (detail as Detail[]).map((d) => ({
      field: d.field ?? String(d.loc?.at(-1) ?? "form"),
      message: d.message ?? d.msg ?? "Refused",
    })),
    status,
  );
}

async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result;
  try {
    result = await call;
  } catch {
    throw new Refused([{ field: "form", message: "The service cannot be reached. Is the API running?" }]);
  }
  if (result.error !== undefined || result.data === undefined) {
    throw refusal(result.error, result.response.status);
  }
  return result.data;
}

export const api = {
  health: () => unwrap(client.GET("/health")) as Promise<Health>,
  artefact: () => unwrap(client.GET("/api/artefact")) as Promise<unknown> as Promise<ArtefactRecord>,
  interfaceText: () => unwrap(client.GET("/api/interface-text")) as Promise<InterfaceText>,
  createCase: (body: CaseCreate) => unwrap(client.POST("/api/cases", { body })),
  getCase: (caseId: number) =>
    unwrap(client.GET("/api/cases/{case_id}", { params: { path: { case_id: caseId } } })),
  saveVisit: (caseId: number, visitNumber: 1 | 2, body: VisitCreate) =>
    unwrap(
      client.PUT("/api/cases/{case_id}/visits/{visit_number}", {
        params: { path: { case_id: caseId, visit_number: visitNumber } },
        body,
      }),
    ),
  assess: (caseId: number) =>
    unwrap(
      client.POST("/api/cases/{case_id}/assessment", { params: { path: { case_id: caseId } } }),
    ),
  caseload: () => unwrap(client.GET("/api/caseload")),
  predict: (body: { case: CaseCreate; visit_one: VisitCreate; visit_two: VisitCreate }) =>
    unwrap(client.POST("/api/predict", { body })),
  me: () => unwrap(client.GET("/api/auth/me")),
  signIn: (username: string, password: string) =>
    unwrap(client.POST("/api/auth/sign-in", { body: { username, password } })),
  signOut: async () => {
    await client.POST("/api/auth/sign-out");
  },
  changePassword: async (current_password: string, new_password: string) => {
    const { error, response } = await client.POST("/api/auth/password", {
      body: { current_password, new_password },
    });
    if (error !== undefined || !response.ok) throw refusal(error, response.status);
  },
  users: () => unwrap(client.GET("/api/admin/users")),
  createUser: (username: string, role: string) =>
    unwrap(client.POST("/api/admin/users", { body: { username, role } })),
  resetPassword: (userId: number) =>
    unwrap(
      client.POST("/api/admin/users/{user_id}/reset-password", {
        params: { path: { user_id: userId } },
      }),
    ),
  setActive: async (userId: number, active: boolean) => {
    const { error, response } = await client.POST("/api/admin/users/{user_id}/active", {
      params: { path: { user_id: userId } },
      body: { active },
    });
    if (error !== undefined || !response.ok) throw refusal(error, response.status);
  },
  audit: () => unwrap(client.GET("/api/admin/audit")),
};
