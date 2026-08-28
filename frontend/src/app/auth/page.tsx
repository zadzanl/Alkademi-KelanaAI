"use client";

import Link from "next/link";
import { useActionState, useEffect, useState } from "react";
import { authenticate, type AuthActionState } from "../actions";

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [state, action, pending] = useActionState<AuthActionState | null, FormData>(authenticate, null);
  useEffect(() => { if (state?.submittedUsername !== undefined) setUsername(state.submittedUsername); }, [state]);

  return <main className="min-h-screen bg-paper px-5 py-12 text-ink sm:px-8 sm:py-20">
    <div className="mx-auto max-w-lg border-t border-ink bg-paper-light px-6 py-8 sm:px-10">
      <Link href="/" className="text-sm font-semibold text-muted-ink hover:text-ink">← Back to planner</Link>
      <h1 className="mt-8 font-display text-5xl">{mode === "login" ? "Welcome back" : "Create an account"}</h1>
      <p className="mt-3 text-muted-ink">Use a dummy username-password. Credentials are hashed, but nowhere near safe.</p>
      <form action={action} className="mt-8 space-y-5">
        <input type="hidden" name="authMode" value={mode} />
        <div><label htmlFor="username" className="font-semibold">Username</label><input id="username" name="username" value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} maxLength={32} autoComplete="username" className="mt-2 min-h-12 w-full border border-control bg-paper px-4" /></div>
        <div><label htmlFor="password" className="font-semibold">Password</label><input id="password" name="password" type="password" required minLength={8} maxLength={128} autoComplete={mode === "login" ? "current-password" : "new-password"} className="mt-2 min-h-12 w-full border border-control bg-paper px-4" /></div>
        <button disabled={pending} className="min-h-12 w-full bg-terracotta px-5 font-bold text-white disabled:opacity-60">{pending ? "Working..." : mode === "login" ? "Sign in" : "Register"}</button>
        {state?.ok === false && (!state.authMode || state.authMode === mode) && <p role="alert" className="border-y border-error p-3 font-semibold text-error">{state.message}</p>}
        {state?.ok === true && state.authMode === "register" && mode === "register" && <p role="status" className="border-y border-success p-3 font-semibold text-success">Account created. Switch to sign in with your new account.</p>}
      </form>
      <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); }} className="mt-6 font-semibold text-terracotta-dark underline">{mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}</button>
    </div>
  </main>;
}