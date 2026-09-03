"use server";

import { generateTrip, TripApiError } from "../services/tripService.ts";
import { localErrors } from "../lib/safety.ts";
import { invalidateTripsCache } from "../lib/tripCache.ts";
import { compareRagRecommendation } from "../services/knowledgeService.ts";
import type { RagComparisonResponse } from "../types/knowledge.ts";
import type { ActionState, FormValues, TripRequest } from "./types.ts";
import { authFetch, clearLocalSession, getCurrentUser, parseAuthMode, parsePublicUser, persistUpstreamSession, type AuthMode, type AuthResult } from "../services/authService.ts";
export type AuthActionState = AuthResult & { submittedUsername?: string; authMode?: AuthMode };

function authSubmitted(formData: FormData): string {
  return String(formData.get("username") ?? "").trim();
}

async function authAction(formData: FormData, authMode: AuthMode): Promise<AuthActionState> {
  const username = authSubmitted(formData);
  const password = String(formData.get("password") ?? "");
  if (!username || password.length < 8) {
    return { ok: false, message: "Enter a username and a password of at least 8 characters.", submittedUsername: username, authMode };
  }
  const path = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
  let success: AuthActionState | null = null;
  try {
    const response = await authFetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      if (authMode === "login") await clearLocalSession();
      return { ok: false, message: authMode === "login" ? "Invalid username or password." : "We could not create that account. Check the username and try again.", submittedUsername: username, authMode };
    }
    let user: ReturnType<typeof parsePublicUser>;
    try {
      user = parsePublicUser(await response.json());
    } catch {
      await clearLocalSession();
      return { ok: false, message: "The authentication service returned an unexpected result.", submittedUsername: username, authMode };
    }
    if (!user) {
      await clearLocalSession();
      return { ok: false, message: "The authentication service returned an unexpected result.", submittedUsername: username, authMode };
    }
    if (authMode === "login" && !await persistUpstreamSession(response)) {
      await clearLocalSession();
      return { ok: false, message: "We could not establish a secure session. Please try again.", submittedUsername: username, authMode };
    }
    if (authMode === "register") await clearLocalSession();
    success = { ok: true, user, submittedUsername: username, authMode };
    if (authMode === "register") return success;
  } catch {
    return { ok: false, message: "We could not reach the authentication service. Try again.", submittedUsername: username, authMode };
  }

  const { redirect } = await import("next/navigation");
  redirect("/trips");
  return success!;
}

export async function authenticate(_previous: AuthActionState | null, formData: FormData): Promise<AuthActionState> {
  const authMode = parseAuthMode(formData.get("authMode"));
  if (!authMode) {
    return { ok: false, message: "Choose sign in or registration and try again.", submittedUsername: authSubmitted(formData) };
  }
  return authAction(formData, authMode);
}

export async function logout(): Promise<AuthActionState> {
  try {
    const response = await authFetch("/api/v1/auth/logout", { method: "POST" });
    if (!response.ok) return { ok: false, message: "We could not sign you out. Please try again." };
    await clearLocalSession();
    return { ok: true, user: { id: 0, username: "", created_at: "" } };
  } catch {
    return { ok: false, message: "We could not sign you out. Please try again." };
  }
}

export async function logoutFormAction(): Promise<void> {
  "use server";
  await logout();
}

export async function currentUser(): Promise<AuthResult> {
  const user = await getCurrentUser();
  return user ? { ok: true, user } : { ok: false, message: "Not signed in." };
}

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
      if (error.kind === "unauthorized" || error.status === 401) {
        return {
          ok: false,
          kind: "unauthorized",
          message: "Please sign in to save your travel itinerary.",
          submitted,
        };
      }

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

export async function compareRagRecommendationAction(body: TripRequest): Promise<RagComparisonResponse | { error: string }> {
  try { return await compareRagRecommendation(body); }
  catch (error) { return { error: error instanceof Error ? error.message : "Comparison failed. Please try again." }; }
}
