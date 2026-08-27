"use server";

import { generateTrip, TripApiError } from "../services/tripService.ts";
import { localErrors } from "../lib/safety.ts";
import { invalidateTripsCache } from "../lib/tripCache.ts";
import type { ActionState, FormValues, TripRequest } from "./types.ts";

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

  const body: TripRequest = {
    destination: submitted.destination.trim(),
    country: submitted.country.trim(),
    days: Number(submitted.days),
    budget: Number(submitted.budget),
    currency: submitted.currency,
    travel_month: submitted.travel_month,
  };

  try {
    const trip = await generateTrip(body);
    await invalidateTripsCache();
    return { ok: true, trip, submitted };
  } catch (error) {
    if (error instanceof TripApiError) {
      return {
        ok: false,
        kind: error.kind,
        message: error.message,
        fieldErrors: error.fieldErrors,
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
