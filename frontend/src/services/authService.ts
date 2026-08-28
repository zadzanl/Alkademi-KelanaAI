const AUTH_COOKIE_NAME = process.env.AUTH_SESSION_COOKIE?.trim() || "kelana_session";

export type PublicUser = { id: number; username: string; created_at: string };
export type AuthResult = { ok: true; user: PublicUser } | { ok: false; message: string };
export type AuthMode = "login" | "register";

export function parseAuthMode(value: FormDataEntryValue | null): AuthMode | null {
  return value === "login" || value === "register" ? value : null;
}

async function requestCookies() {
  const { cookies } = await import("next/headers");
  return cookies();
}

function baseUrl(): string {
  return (process.env.API_URL?.trim() || "http://127.0.0.1:8000").replace(/\/$/, "");
}

export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const session = (await requestCookies()).get(AUTH_COOKIE_NAME);
  const headers = new Headers(init.headers);
  if (session) headers.set("cookie", `${AUTH_COOKIE_NAME}=${session.value}`);
  return fetch(`${baseUrl()}${path}`, { ...init, headers, cache: "no-store" });
}

export function upstreamSessionCookie(response: Response): string | null {
  return upstreamSessionCookieHeader(response)?.split(";", 1)[0] ?? null;
}

function upstreamSessionCookieHeader(response: Response): string | null {
  const values = response.headers.getSetCookie?.() ?? [response.headers.get("set-cookie") ?? ""];
  return values.find((value) => {
    const pair = value.split(";", 1)[0];
    return pair.startsWith(`${AUTH_COOKIE_NAME}=`) && pair.length > AUTH_COOKIE_NAME.length + 1;
  }) ?? null;
}

export function upstreamSessionMaxAge(response: Response): number | undefined {
  const header = upstreamSessionCookieHeader(response);
  if (!header) return undefined;
  const maxAge = /(?:^|;\s*)Max-Age=(-?\d+)/i.exec(header);
  if (maxAge) return Number(maxAge[1]);
  const expires = /(?:^|;\s*)Expires=([^;]+)/i.exec(header);
  if (!expires) return undefined;
  const expiresAt = Date.parse(expires[1]);
  return Number.isNaN(expiresAt) ? undefined : Math.floor((expiresAt - Date.now()) / 1000);
}

export function parsePublicUser(value: unknown): PublicUser | null {
  if (!value || typeof value !== "object") return null;
  const user = value as Record<string, unknown>;
  return typeof user.id === "number" && typeof user.username === "string" && typeof user.created_at === "string"
    ? { id: user.id, username: user.username, created_at: user.created_at }
    : null;
}

export async function getCurrentUser(): Promise<PublicUser | null> {
  try {
    const response = await authFetch("/api/v1/auth/me");
    if (!response.ok) return null;
    return parsePublicUser(await response.json());
  } catch {
    return null;
  }
}

export async function persistUpstreamSession(response: Response): Promise<boolean> {
  const header = upstreamSessionCookieHeader(response);
  if (!header) return false;
  const pair = header.split(";", 1)[0];
  const [name, ...valueParts] = pair.split("=");
  const value = valueParts.join("=");
  const maxAge = upstreamSessionMaxAge(response);
  if (maxAge === undefined || !Number.isFinite(maxAge) || maxAge <= 0) return false;
  (await requestCookies()).set(name, value, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  });
  return true;
}

export async function clearLocalSession(): Promise<void> {
  (await requestCookies()).set(AUTH_COOKIE_NAME, "", { expires: new Date(0), path: "/" });
}