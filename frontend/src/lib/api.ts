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

/** One refused value, with the API's reason. */
export type FieldError = { field: string; message: string };

/** Thrown when the API refuses a request; carries every refused field. */
export class Refused extends Error {
  constructor(public readonly errors: FieldError[]) {
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

type Detail = { field?: string; message?: string; loc?: (string | number)[]; msg?: string };

// The service answers a refusal with {field, message} items (entry rules,
// missing case, step order); FastAPI's own type checks use {loc, msg}.
function refusal(body: unknown, status: number): Refused {
  const detail = (body as { detail?: unknown } | undefined)?.detail;
  if (!Array.isArray(detail)) {
    return new Refused([{ field: "form", message: `The service refused the request (${status})` }]);
  }
  return new Refused(
    (detail as Detail[]).map((d) => ({
      field: d.field ?? String(d.loc?.at(-1) ?? "form"),
      message: d.message ?? d.msg ?? "Refused",
    })),
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
};
