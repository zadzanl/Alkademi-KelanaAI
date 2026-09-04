import { getApiBaseUrl, getSessionCookieHeader, TripApiError } from "./tripService.ts";
import type { Conversation, ConversationCreateResponse, Message } from "../types/chat.ts";

const CHAT_READ_TIMEOUT_MS = 10_000;
const CHAT_SEND_TIMEOUT_MS = 60_000;
export const CHAT_IDEMPOTENCY_MARKER = "v1";
export const CHAT_IDEMPOTENCY_HEADER = "X-KelanaAI-Chat-Idempotency";
const SAFE_CHAT_CODES = new Set(["idempotency_key_invalid", "idempotency_key_conflict", "idempotency_key_in_progress", "chat_generation_unavailable", "chat_request_integrity_error"]);
const SAFE_CHAT_MESSAGES: Record<string, string> = {
  idempotency_key_invalid: "Idempotency-Key must be a UUIDv4.",
  idempotency_key_conflict: "This Idempotency-Key was already used for different message content.",
  idempotency_key_in_progress: "A message with this Idempotency-Key is still being processed. Retry with the same key.",
  chat_generation_unavailable: "The assistant could not complete this message. Retry with the same Idempotency-Key.",
  chat_request_integrity_error: "The assistant response could not be verified. Refresh and try again.",
};

export function chatIdempotencyEnabled(): boolean {
  return process.env.NEXT_PUBLIC_CHAT_IDEMPOTENCY_ENABLED?.trim().toLowerCase() === "true" && process.env.CHAT_IDEMPOTENCY_ENABLED?.trim().toLowerCase() === "true";
}

async function handleChatResponse<T>(response: Response, keyed: boolean, fallback: string): Promise<T> {
  if (keyed && response.headers.get(CHAT_IDEMPOTENCY_HEADER) !== CHAT_IDEMPOTENCY_MARKER) {
    throw new TripApiError("upstream", "Keyed retry is not available in this deployment. Refresh and try again.", response.status, undefined, "chat_idempotency_unavailable");
  }
  if (response.ok) return response.json();
  let code: string | undefined;
  try {
    const payload = await response.json() as { detail?: { code?: unknown } };
    if (typeof payload.detail?.code === "string" && SAFE_CHAT_CODES.has(payload.detail.code)) code = payload.detail.code;
  } catch { /* use fixed local copy */ }
  const retryAfterValue = Number(response.headers.get("Retry-After"));
  const retryAfterSeconds = Number.isInteger(retryAfterValue)
    ? Math.min(120, Math.max(1, retryAfterValue))
    : undefined;
  throw new TripApiError(response.status === 401 ? "unauthorized" : "upstream", code ? SAFE_CHAT_MESSAGES[code] : fallback, response.status, undefined, code, retryAfterSeconds);
}

export async function createConversation(title?: string): Promise<ConversationCreateResponse> {
  const baseUrl = getApiBaseUrl();
  const sessionCookie = await getSessionCookieHeader();
  if (!sessionCookie) {
    throw new TripApiError("unauthorized", "Sign in to use the AI chat assistant.", 401);
  }

  const response = await fetch(`${baseUrl}/api/v1/conversations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: sessionCookie,
    },
    body: JSON.stringify(title ? { title } : {}),
    signal: AbortSignal.timeout(CHAT_READ_TIMEOUT_MS),
  });

  if (response.status === 401) {
    throw new TripApiError("unauthorized", "Sign in to use the AI chat assistant.", 401);
  }
  if (!response.ok) {
    throw new TripApiError("upstream", "Failed to create conversation.", response.status);
  }

  return response.json();
}

export async function listConversations(): Promise<Conversation[]> {
  const baseUrl = getApiBaseUrl();
  const sessionCookie = await getSessionCookieHeader();
  if (!sessionCookie) {
    throw new TripApiError("unauthorized", "Sign in to view conversations.", 401);
  }

  const response = await fetch(`${baseUrl}/api/v1/conversations`, {
    method: "GET",
    headers: {
      Cookie: sessionCookie,
    },
    signal: AbortSignal.timeout(CHAT_READ_TIMEOUT_MS),
  });

  if (response.status === 401) {
    throw new TripApiError("unauthorized", "Sign in to view conversations.", 401);
  }
  if (!response.ok) {
    throw new TripApiError("upstream", "Failed to load conversations.", response.status);
  }

  return response.json();
}

export async function getConversationMessages(conversationId: number): Promise<Message[]> {
  const baseUrl = getApiBaseUrl();
  const sessionCookie = await getSessionCookieHeader();
  if (!sessionCookie) {
    throw new TripApiError("unauthorized", "Sign in to view messages.", 401);
  }

  const response = await fetch(`${baseUrl}/api/v1/conversations/${conversationId}/messages`, {
    method: "GET",
    headers: {
      Cookie: sessionCookie,
    },
    signal: AbortSignal.timeout(CHAT_READ_TIMEOUT_MS),
  });

  if (response.status === 401) {
    throw new TripApiError("unauthorized", "Sign in to view messages.", 401);
  }
  if (response.status === 404) {
    throw new TripApiError("upstream", "Conversation not found.", 404);
  }
  if (!response.ok) {
    throw new TripApiError("upstream", "Failed to load conversation messages.", response.status);
  }

  return response.json();
}

export async function sendConversationMessage(conversationId: number, content: string, idempotencyKey?: string): Promise<Message> {
  if (idempotencyKey && !chatIdempotencyEnabled()) {
    throw new TripApiError("upstream", "Keyed retry is not available in this deployment. Refresh and try again.", undefined, undefined, "chat_idempotency_unavailable");
  }
  const baseUrl = getApiBaseUrl();
  const sessionCookie = await getSessionCookieHeader();
  if (!sessionCookie) {
    throw new TripApiError("unauthorized", "Sign in to send messages.", 401);
  }

  const headers: Record<string, string> = { "Content-Type": "application/json", Cookie: sessionCookie };
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  const response = await fetch(`${baseUrl}/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers,
    body: JSON.stringify({ content }),
    signal: AbortSignal.timeout(CHAT_SEND_TIMEOUT_MS),
  });

  return handleChatResponse<Message>(response, Boolean(idempotencyKey), "Failed to send message.");
}

export async function renameConversation(conversationId: number, title: string): Promise<Conversation> {
  const baseUrl = getApiBaseUrl();
  const sessionCookie = await getSessionCookieHeader();
  if (!sessionCookie) {
    throw new TripApiError("unauthorized", "Sign in to rename conversations.", 401);
  }

  const response = await fetch(`${baseUrl}/api/v1/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Cookie: sessionCookie,
    },
    body: JSON.stringify({ title }),
    signal: AbortSignal.timeout(CHAT_READ_TIMEOUT_MS),
  });

  if (response.status === 401) {
    throw new TripApiError("unauthorized", "Sign in to rename conversations.", 401);
  }
  if (response.status === 404) {
    throw new TripApiError("upstream", "Conversation not found.", 404);
  }
  if (!response.ok) {
    throw new TripApiError("upstream", "Failed to rename conversation.", response.status);
  }

  return response.json();
}
