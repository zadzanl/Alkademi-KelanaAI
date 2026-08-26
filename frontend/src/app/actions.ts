"use server";

import { localErrors, parse422 } from "./safety.ts";
import type { ActionState, FormValues, TripRequest, TripResponse } from "./types.ts";

// The API currently waits for synchronous AI narration before returning the
// saved trip. Keep this bounded, but longer than the provider's observed local
// response time so successful trip details can reach the UI.
const TRIP_REQUEST_TIMEOUT_MS = 120_000;

function submittedFrom(formData: FormData): FormValues {
  return {
    destination: String(formData.get("destination") ?? ""),
    country: String(formData.get("country") ?? ""),
    days: String(formData.get("days") ?? ""),
    budget: String(formData.get("budget") ?? ""),
    currency: String(
      formData.get("currency") ?? "USD",
    ) as FormValues["currency"],
    travel_month: String(formData.get("travel_month") ?? ""),
  };
}

export async function createTrip(
  _previous: ActionState | null,
  formData: FormData,
): Promise<ActionState> {
  const submitted = submittedFrom(formData);
  const errors = localErrors(submitted);

  if (Object.keys(errors).length) {
    return {
      ok: false,
      kind: "validation",
      message: "Check the highlighted fields and try again.",
      fieldErrors: errors,
      submitted,
    };
  }

  const apiUrl = process.env.API_URL?.trim();

  if (!apiUrl || !/^https?:\/\//i.test(apiUrl)) {
    return {
      ok: false,
      kind: "upstream",
      message: "The planner is not connected to its trip service yet.",
      submitted,
    };
  }

  const body: TripRequest = {
    destination: submitted.destination.trim(),
    country: submitted.country.trim(),
    days: Number(submitted.days),
    budget: Number(submitted.budget),
    currency: submitted.currency,
    travel_month: submitted.travel_month,
  };

  try {
    const response = await fetch(
      `${apiUrl.replace(/\/$/, "")}/api/v1/trips`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(TRIP_REQUEST_TIMEOUT_MS),
      },
    );
    const contentLength = response.headers.get("content-length");

    if (contentLength && Number(contentLength) > 1_000_000) {
      return {
        ok: false,
        kind: "malformed",
        message: "The trip service returned an unexpected result.",
        submitted,
      };
    }

    const rawPayload = await response.text();

    if (rawPayload.length > 1_000_000) {
      return {
        ok: false,
        kind: "malformed",
        message: "The trip service returned an unexpected result.",
        submitted,
      };
    }

    let payload: unknown;

    try {
      payload = JSON.parse(rawPayload || "null");
    } catch {
      return {
        ok: false,
        kind: "malformed",
        message: "The trip service returned an unexpected result.",
        submitted,
      };
    }

    if (response.status === 422) {
      return {
        ok: false,
        kind: "validation",
        message: "The trip service found something to adjust.",
        fieldErrors: parse422(payload),
        submitted,
      };
    }

    if ([408, 425, 429, 500, 502, 503, 504].includes(response.status)) {
      return {
        ok: false,
        kind: "upstream",
        message: "The trip service is taking a moment. Please try again.",
        submitted,
      };
    }

    if (!response.ok) {
      return {
        ok: false,
        kind: "upstream",
        message: "The trip service could not complete that request.",
        submitted,
      };
    }

    if (
      !payload ||
      typeof payload !== "object" ||
      typeof (payload as TripResponse).id !== "number" ||
      (typeof (payload as TripResponse).ai_recommendation !== "string" &&
        (payload as TripResponse).ai_recommendation !== null)
    ) {
      return {
        ok: false,
        kind: "malformed",
        message: "The trip service returned an unexpected result.",
        submitted,
      };
    }

    return { ok: true, trip: payload as TripResponse, submitted };
  } catch (error) {
    if (
      error instanceof Error &&
      (error.name === "TimeoutError" || error.name === "AbortError")
    ) {
      return {
        ok: false,
        kind: "timeout",
        message:
          "That took longer than expected. Your details are saved here. Try again when ready.",
        submitted,
      };
    }

    return {
      ok: false,
      kind: "network",
      message:
        "We could not reach the trip service. Check that it is running, then try again.",
      submitted,
    };
  }
}
