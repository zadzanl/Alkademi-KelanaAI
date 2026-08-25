import type { FormValues } from "./types.ts";

const fields = [
  "destination",
  "country",
  "days",
  "budget",
  "currency",
  "travel_month",
] as const;
const months = new Set([
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]);
const textLimits = { destination: 100, country: 100 } as const;

export function localErrors(
  values: FormValues,
): Partial<Record<keyof FormValues, string>> {
  const errors: Partial<Record<keyof FormValues, string>> = {};

  for (const key of ["destination", "country"] as const) {
    if (!values[key].trim()) {
      errors[key] = "Please enter a destination.";
    } else if (values[key].length > textLimits[key]) {
      errors[key] = "Keep this to 100 characters or fewer.";
    }
  }

  const days = Number(values.days);
  const budget = Number(values.budget);

  if (!Number.isInteger(days) || days < 1 || days > 365) {
    errors.days = "Enter a whole number from 1 to 365.";
  }

  if (!Number.isFinite(budget) || budget <= 0) {
    errors.budget = "Enter a budget greater than zero.";
  }

  if (!["IDR", "USD"].includes(values.currency)) {
    errors.currency = "Choose IDR or USD.";
  }

  if (!months.has(values.travel_month)) {
    errors.travel_month = "Choose a valid month.";
  }

  return errors;
}

export function parse422(
  payload: unknown,
): Partial<Record<keyof FormValues, string>> {
  const details =
    payload &&
    typeof payload === "object" &&
    Array.isArray((payload as { detail?: unknown }).detail)
      ? (payload as { detail: unknown[] }).detail
      : [];
  const errors: Partial<Record<keyof FormValues, string>> = {};

  for (const item of details) {
    if (!item || typeof item !== "object") {
      continue;
    }

    const detail = item as { loc?: unknown; msg?: unknown };
    const loc = Array.isArray(detail.loc) ? detail.loc : [];
    const key =
      loc[0] === "body" && typeof loc[1] === "string" ? loc[1] : null;

    if (
      key &&
      fields.includes(key as (typeof fields)[number]) &&
      typeof detail.msg === "string"
    ) {
      errors[key as keyof FormValues] = detail.msg.slice(0, 180);
    }
  }

  return errors;
}

export function safeUrl(url: string, images = false): string | undefined {
  try {
    const parsed = new URL(url);
    const allowed = images
      ? ["http:", "https:"]
      : ["http:", "https:", "mailto:"];
    return allowed.includes(parsed.protocol) ? url : undefined;
  } catch {
    return undefined;
  }
}