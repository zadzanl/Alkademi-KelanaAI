import { months } from "../types/trip.ts";
import type { FormValues } from "../types/trip.ts";

const fields = [
  "destination",
  "country",
  "days",
  "budget",
  "currency",
  "travel_month",
] as const;

const monthsSet = new Set(months);

const textLimits = { destination: 100, country: 100 } as const;
const MAX_POSTGRES_INT4 = 2_147_483_647; // 2^31 - 1
const POSITIVE_INT_REGEX = /^[1-9]\d{0,9}$/;

/**
 * Validates and parses an untrusted route parameter string into a safe positive integer.
 * Rejects floats, scientific notation, hex, negative numbers, zero, leading zeros,
 * whitespace, trailing characters, and integers exceeding PostgreSQL's 32-bit signed int max.
 */
export function parseTripId(rawId: unknown): number | null {
  if (typeof rawId !== "string" && typeof rawId !== "number") {
    return null;
  }

  const str = String(rawId).trim();
  if (!POSITIVE_INT_REGEX.test(str)) {
    return null;
  }

  const num = Number(str);
  if (!Number.isSafeInteger(num) || num <= 0 || num > MAX_POSTGRES_INT4) {
    return null;
  }

  return num;
}

/**
 * Validate that a URL uses only permitted, safe protocols.
 * Blocks dangerous schemes (javascript:, vbscript:, data:, file:, blob:) to prevent XSS.
 *
 * For links: allows http:, https:, mailto:
 * For images: allows http:, https: only
 *
 * Note on backslash normalization: The WHATWG URL parser (`new URL()`) normalizes
 * backslashes in special-scheme URLs (http:, https:) to forward slashes per the
 * standard's host/path parsing rules. For example, `https:\\evil.com` is parsed
 * as `https://evil.com`. Since we only allow `http:`/`https:`/`mailto:` protocols,
 * backslash-containing URLs that parse successfully are returned as the parser's
 * serialized `href`, not as ambiguous raw input. URLs that fail to parse return
 * `undefined`. This behavior is covered by regression tests.
 */
export function safeUrl(url: string, images = false): string | undefined {
  if (typeof url !== "string") {
    return undefined;
  }

  const trimmed = url.trim();
  if (!trimmed) {
    return undefined;
  }

  try {
    const parsed = new URL(trimmed);
    const allowed = images
      ? ["http:", "https:"]
      : ["http:", "https:", "mailto:"];
    return allowed.includes(parsed.protocol) ? parsed.href : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Validate user form inputs locally before submitting to the backend.
 */
export function localErrors(
  values: FormValues,
): Partial<Record<keyof FormValues, string>> {
  const errors: Partial<Record<keyof FormValues, string>> = {};

  for (const key of ["destination", "country"] as const) {
    if (!values[key]?.trim()) {
      errors[key] = key === "country" ? "Please enter a country." : "Please enter a destination.";
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

  if (!monthsSet.has(values.travel_month)) {
    errors.travel_month = "Choose a valid month.";
  }

  return errors;
}

/**
 * Parse FastAPI 422 validation error responses into a structured field-error map.
 * Defends against prototype pollution and truncates error messages to prevent UI DoS.
 */
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

