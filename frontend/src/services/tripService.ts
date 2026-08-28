import { parse422, parseTripId } from "../lib/safety.ts";
import type {
  TripListResponse,
  TripRequest,
  TripResponse,
} from "../types/trip.ts";

const DB_READ_TIMEOUT_MS = 8_000;
const AI_GENERATION_TIMEOUT_MS = 120_000;
const MAX_PAYLOAD_BYTES = 1_000_000;

export type TripErrorKind =
  | "validation"
  | "timeout"
  | "network"
  | "upstream"
  | "malformed"
  | "unauthorized";

export class TripApiError extends Error {
  readonly kind: TripErrorKind;
  readonly status?: number;
  readonly fieldErrors?: Partial<Record<string, string>>;

  constructor(
    kind: TripErrorKind,
    message: string,
    status?: number,
    fieldErrors?: Partial<Record<string, string>>,
  ) {
    super(message);
    this.name = "TripApiError";
    this.kind = kind;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

export async function getSessionCookieHeader(): Promise<string | null> {
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const cookieName = process.env.AUTH_SESSION_COOKIE?.trim() || "kelana_session";
    const session = cookieStore.get(cookieName);
    return session ? `${cookieName}=${session.value}` : null;
  } catch {
    return null;
  }
}

export function getApiBaseUrl(): string {
  const rawUrl = process.env.API_URL?.trim() || "http://127.0.0.1:8000";
  if (!/^https?:\/\//i.test(rawUrl)) {
    throw new TripApiError(
      "upstream",
      "The planner is not connected to its trip service yet.",
    );
  }
  return rawUrl.replace(/\/$/, "");
}

function isTimeoutError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const name = (error as { name?: string }).name;
  const causeName = (error as { cause?: { name?: string } }).cause?.name;
  return (
    name === "TimeoutError" ||
    name === "AbortError" ||
    causeName === "TimeoutError" ||
    causeName === "AbortError"
  );
}

function mapFetchError(error: unknown, timeoutMessage: string): never {
  if (error instanceof TripApiError) {
    throw error;
  }
  if (isTimeoutError(error)) {
    throw new TripApiError("timeout", timeoutMessage);
  }
  throw new TripApiError(
    "network",
    "We could not reach the trip service. Check that it is running, then try again.",
  );
}

/**
 * Read a response body with a streaming size cap.
 * Enforces MAX_PAYLOAD_BYTES during the read, not just via content-length header
 * or post-hoc buffer length. Prevents unbounded memory consumption from
 * headerless/chunked oversized responses.
 */
async function readBodyWithCap(response: Response): Promise<string> {
  if (!response.body) {
    return "";
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let result = "";
  let totalBytes = 0;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      totalBytes += value.byteLength;
      if (totalBytes > MAX_PAYLOAD_BYTES) {
        await reader.cancel();
        throw new TripApiError(
          "malformed",
          "The trip service returned an unexpected result.",
          response.status,
        );
      }
      result += decoder.decode(value, { stream: true });
    }
    result += decoder.decode();
  } finally {
    reader.releaseLock();
  }

  return result;
}

async function handleResponsePayload<T>(response: Response): Promise<T> {
  const contentLength = response.headers.get("content-length");
  if (contentLength && Number(contentLength) > MAX_PAYLOAD_BYTES) {
    throw new TripApiError(
      "malformed",
      "The trip service returned an unexpected result.",
      response.status,
    );
  }

  // Intercept known retryable / upstream gateway statuses before parsing body
  if ([408, 425, 429, 500, 502, 503, 504].includes(response.status)) {
    throw new TripApiError(
      "upstream",
      "The trip service is taking a moment. Please try again.",
      response.status,
    );
  }

  const rawPayload = await readBodyWithCap(response);

  let payload: unknown;
  try {
    payload = JSON.parse(rawPayload || "null");
  } catch {
    if (!response.ok) {
      if (response.status === 401) {
        throw new TripApiError(
          "unauthorized",
          "Sign in required to view or manage your trips.",
          401,
        );
      }
      throw new TripApiError(
        "upstream",
        "The trip service could not complete that request.",
        response.status,
      );
    }
    throw new TripApiError(
      "malformed",
      "The trip service returned an unexpected result.",
      response.status,
    );
  }

  if (response.status === 401) {
    throw new TripApiError(
      "unauthorized",
      "Sign in required to view or manage your trips.",
      401,
    );
  }

  if (response.status === 422) {
    throw new TripApiError(
      "validation",
      "The trip service found something to adjust.",
      422,
      parse422(payload),
    );
  }

  if (!response.ok) {
    throw new TripApiError(
      "upstream",
      "The trip service could not complete that request.",
      response.status,
    );
  }

  return payload as T;
}

/**
 * Validate that a parsed payload conforms to the full 14-field TripResponse contract.
 * The backend source of truth is the Pydantic `TripResponse` model in `backend/main.py`.
 * This guard ensures contract drift fails loudly rather than rendering undefined fields.
 */
function isTripResponse(data: unknown): data is TripResponse {
  if (!data || typeof data !== "object") {
    return false;
  }
  const t = data as Record<string, unknown>;
  return (
    typeof t.id === "number" &&
    typeof t.destination === "string" &&
    typeof t.country === "string" &&
    typeof t.days === "number" &&
    typeof t.budget === "number" &&
    typeof t.currency === "string" &&
    typeof t.travel_month === "string" &&
    typeof t.daily_budget === "number" &&
    typeof t.travel_season === "string" &&
    typeof t.category === "string" &&
    Array.isArray(t.recommended_places) &&
    typeof t.recommended_transportation === "string" &&
    typeof t.created_at === "string" &&
    (typeof t.ai_recommendation === "string" || t.ai_recommendation === null)
  );
}

/**
 * These bounds mirror `backend/main.py` list_trips Query constraints. Keep both
 * sides in sync if page validation changes: page >= 1 and page_size 1..100.
 */
function isTripListResponse(data: unknown): data is TripListResponse {
  if (!data || typeof data !== "object") {
    return false;
  }
  const list = data as Record<string, unknown>;
  return (
    Array.isArray(list.items) &&
    list.items.every(isTripResponse) &&
    Number.isInteger(list.total) &&
    (list.total as number) >= 0 &&
    Number.isInteger(list.page) &&
    (list.page as number) >= 1 &&
    Number.isInteger(list.page_size) &&
    (list.page_size as number) >= 1 &&
    (list.page_size as number) <= 100
  );
}

/**
 * Fetch one newest-first page of persisted trip records from PostgreSQL.
 * Callers pass a positive integer page and pageSize in 1..100. Values are sent
 * unchanged because FastAPI is the authoritative request validator and returns
 * a classified 422 validation error for invalid values.
 * Throws `TripApiError("malformed")` when the envelope or any item drifts from
 * the response contract, and TripApiError on 5xx/network failure so Next.js
 * error.tsx can present a retry interface.
 */
export async function getTrips(
  page = 1,
  pageSize = 10,
): Promise<TripListResponse> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  const cookieHeader = await getSessionCookieHeader();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (cookieHeader) {
    headers["cookie"] = cookieHeader;
  }
  try {
    const response = await fetch(
      `${baseUrl}/api/v1/trips?${query}`,
      {
        method: "GET",
        headers,
        cache: "no-store",
        signal: AbortSignal.timeout(DB_READ_TIMEOUT_MS),
      },
    );

    const data = await handleResponsePayload<TripListResponse>(response);
    if (!isTripListResponse(data)) {
      throw new TripApiError(
        "malformed",
        "The trip service returned an invalid list structure.",
      );
    }
    return data;
  } catch (error) {
    return mapFetchError(
      error,
      "That took longer than expected. Please try again.",
    );
  }
}

/**
 * Fetch a single trip record by ID.
 *
 * Contract:
 * - Returns `null` when the ID is syntactically invalid (fails `parseTripId`) or when the
 *   backend responds 404 (trip does not exist) or 401 (unauthorized / expired session).
 * - Returns the full `TripResponse` on success.
 * - Throws `TripApiError("malformed")` when the backend returns a 2xx body that does not
 *   conform to the 14-field `TripResponse` shape (contract drift).
 * - Throws `TripApiError` on 5xx, timeout, or network failure so Next.js `error.tsx` handles it.
 */
export async function getTrip(id: number | string): Promise<TripResponse | null> {
  const numericId = parseTripId(id);
  if (numericId === null) {
    return null;
  }

  const baseUrl = getApiBaseUrl();
  const cookieHeader = await getSessionCookieHeader();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (cookieHeader) {
    headers["cookie"] = cookieHeader;
  }
  try {
    const response = await fetch(`${baseUrl}/api/v1/trips/${numericId}`, {
      method: "GET",
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(DB_READ_TIMEOUT_MS),
    });

    if (response.status === 404 || response.status === 401) {
      return null;
    }

    const data = await handleResponsePayload<TripResponse>(response);
    if (!isTripResponse(data)) {
      throw new TripApiError(
        "malformed",
        "The trip service returned an unexpected result.",
      );
    }

    return data;
  } catch (error) {
    return mapFetchError(
      error,
      "That took longer than expected. Please try again.",
    );
  }
}

/**
 * Generate a new trip snapshot with synchronous AI narrative and persist in PostgreSQL.
 */
export async function generateTrip(body: TripRequest): Promise<TripResponse> {
  const baseUrl = getApiBaseUrl();
  const cookieHeader = await getSessionCookieHeader();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (cookieHeader) {
    headers["cookie"] = cookieHeader;
  }
  try {
    const response = await fetch(`${baseUrl}/api/v1/trips`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(AI_GENERATION_TIMEOUT_MS),
    });

    const data = await handleResponsePayload<TripResponse>(response);
    if (!isTripResponse(data)) {
      throw new TripApiError(
        "malformed",
        "The trip service returned an unexpected result.",
      );
    }

    return data;
  } catch (error) {
    return mapFetchError(
      error,
      "That took longer than expected. Your details are saved here. Try again when ready.",
    );
  }
}
