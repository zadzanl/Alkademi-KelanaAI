import { getApiBaseUrl, getSessionCookieHeader } from "./tripService.ts";
import type { TripRequest } from "../types/trip.ts";
import type { RagComparisonResponse } from "../types/knowledge.ts";

export const RAG_COMPARE_TIMEOUT_MS = 60_000;

export async function compareRagRecommendation(body: TripRequest): Promise<RagComparisonResponse> {
  const headers: Record<string, string> = {
    "content-type": "application/json",
    accept: "application/json",
  };
  const cookie = await getSessionCookieHeader();
  if (cookie) headers.cookie = cookie;

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}/api/v1/knowledge/compare`, {
      method: "POST", headers, body: JSON.stringify(body), cache: "no-store",
      signal: AbortSignal.timeout(RAG_COMPARE_TIMEOUT_MS),
    });
  } catch (error) {
    const isTimeout = error instanceof Error &&
      (error.name === "TimeoutError" || error.name === "AbortError");
    throw new Error(isTimeout
      ? "Comparison timed out. Please try again."
      : "We could not reach the comparison service. Please try again.");
  }

  if (!response.ok) {
    const message = response.status === 429
      ? "Comparison rate limit reached. Please wait a minute."
      : "The comparison service could not complete that request.";
    throw new Error(message);
  }

  return await response.json() as RagComparisonResponse;
}