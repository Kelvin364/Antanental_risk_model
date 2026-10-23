// Field lists of the five screens, in the order of feature sets A to C.
// Labels and units only: ranges and timing rules live in the API.
import type { CaseCreate, VisitCreate } from "./api";

export type NumberField<K extends string> = { key: K; label: string; unit: string };

type CaseNumber = "age" | "gravidity" | "prior_deliveries" | "height_cm" | "registration_weight";
type CaseFlag = Exclude<keyof CaseCreate, CaseNumber | "synthetic" | "label">;
export type VisitKey = keyof VisitCreate;

// The design groups registration into "Mother" and "Pregnancy history".
export const MOTHER: NumberField<CaseNumber>[] = [
  { key: "age", label: "Age", unit: "years" },
  { key: "height_cm", label: "Height", unit: "cm" },
  { key: "registration_weight", label: "Weight at booking", unit: "kg" },
];

export const HISTORY: NumberField<CaseNumber>[] = [
  { key: "gravidity", label: "Total pregnancies", unit: "gravidity" },
  { key: "prior_deliveries", label: "Prior deliveries", unit: "count" },
];

export const REGISTRATION: NumberField<CaseNumber>[] = [...MOTHER, ...HISTORY];

export const FLAGS: { key: CaseFlag; label: string }[] = [
  { key: "prior_caesarean", label: "Prior caesarean" },
  { key: "prior_hypertension_pregnancy", label: "Hypertension in a previous pregnancy" },
  { key: "chronic_hypertension", label: "Chronic hypertension" },
  { key: "diabetes", label: "Diabetes" },
  { key: "hiv", label: "HIV" },
  { key: "tuberculosis", label: "Tuberculosis" },
  { key: "sickle_cell", label: "Sickle cell or haematological disorder" },
  { key: "smoking", label: "Smoking" },
  { key: "intimate_partner_violence", label: "Intimate partner violence" },
];

export const VISIT: NumberField<VisitKey>[] = [
  { key: "gestational_week", label: "Gestational age", unit: "weeks" },
  { key: "systolic", label: "Systolic BP", unit: "mmHg" },
  { key: "diastolic", label: "Diastolic BP", unit: "mmHg" },
  { key: "weight_kg", label: "Weight", unit: "kg" },
  { key: "pulse", label: "Pulse rate (optional)", unit: "bpm" },
  { key: "haemoglobin", label: "Haemoglobin (optional)", unit: "g/dL" },
];

/** A probability as the screens print it, e.g. "6.3 percent". */
export const pct = (value: number) => `${(100 * value).toFixed(1)} percent`;

/** A probability in the design's compact form, e.g. "6.3%". */
export const pctShort = (value: number, digits = 1) => `${(100 * value).toFixed(digits)}%`;

/** An entry box's text as the number the API expects, or null when empty. */
export const toNumber = (text: string | undefined) =>
  text === undefined || text.trim() === "" ? null : Number(text);

/** A stored number back into an entry box. */
export const toText = (value: number | null | undefined) =>
  value === null || value === undefined ? "" : String(value);
