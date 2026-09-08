"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useActionState, useEffect, useState } from "react";
import { authenticate, type AuthActionState } from "../actions";

function AuthContent() {
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [username, setUsername] = useState("");
  const [state, action, pending] = useActionState<AuthActionState | null, FormData>(authenticate, null);

  useEffect(() => {
    if (state?.submittedUsername !== undefined) setUsername(state.submittedUsername);
  }, [state]);

  return (
    <main id="main-content" className="min-h-screen bg-paper px-5 py-12 text-ink sm:px-8 sm:py-20">
      <div className="mx-auto max-w-lg rounded-surface border border-surface-rule bg-paper-light px-6 py-8 shadow-xs sm:px-10">
        <Link href="/" className="text-sm font-semibold text-muted-ink transition-colors hover:text-ink focus-visible:outline-focus-ring">
          ← Back to planner
        </Link>
        <h1 className="mt-8 font-display text-5xl">{mode === "login" ? "Welcome back" : "Create an account"}</h1>
        <p className="mt-3 text-muted-ink">Use a password you do not reuse elsewhere. This account is for saving your travel plans.</p>
        <form action={action} className="mt-8 space-y-5">
          <input type="hidden" name="authMode" value={mode} />
          <div>
            <label htmlFor="username" className="font-semibold">Username</label>
            <input
              id="username"
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={pending}
              required
              minLength={3}
              maxLength={32}
              autoComplete="username"
              className="mt-2 min-h-12 w-full rounded-surface border border-control bg-paper px-4 text-ink outline-none focus-visible:border-terracotta focus-visible:outline-focus-ring disabled:opacity-60"
            />
          </div>
          <div>
            <label htmlFor="password" className="font-semibold">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              disabled={pending}
              required
              minLength={8}
              maxLength={128}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="mt-2 min-h-12 w-full rounded-surface border border-control bg-paper px-4 text-ink outline-none focus-visible:border-terracotta focus-visible:outline-focus-ring disabled:opacity-60"
            />
          </div>
          <button
            disabled={pending}
            className="min-h-12 w-full rounded-surface bg-terracotta px-5 font-bold text-white transition-colors hover:bg-terracotta-dark focus-visible:outline-focus-ring disabled:cursor-wait disabled:opacity-60"
          >
            {pending ? (mode === "login" ? "Signing in…" : "Creating account…") : (mode === "login" ? "Sign in" : "Register")}
          </button>
          {pending && (
            <p role="status" aria-live="polite" className="text-center text-xs text-muted-ink">
              {mode === "login" ? "Verifying credentials and establishing session…" : "Creating account and preparing session…"}
            </p>
          )}
          {state?.ok === false && (!state.authMode || state.authMode === mode) && (
            <p role="alert" className="rounded-surface border border-error bg-paper p-3 font-semibold text-error">
              {state.message}
            </p>
          )}
        </form>
        <button
          type="button"
          onClick={() => { setMode(mode === "login" ? "register" : "login"); }}
          className="mt-6 font-semibold text-terracotta-dark underline focus-visible:outline-focus-ring"
        >
          {mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}
        </button>
      </div>
    </main>
  );
}

export default function AuthPage() {
  return (
    <Suspense
      fallback={
        <main id="main-content" className="min-h-screen bg-paper px-5 py-12 text-ink sm:px-8 sm:py-20">
          <div className="mx-auto max-w-lg rounded-surface border border-surface-rule bg-paper-light px-6 py-8 shadow-xs sm:px-10">
            <div className="h-10 w-48 rounded-surface bg-rule/40 motion-safe:animate-pulse" />
          </div>
        </main>
      }
    >
      <AuthContent />
    </Suspense>
  );
}