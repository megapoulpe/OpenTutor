"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api/client";
import { buildAuthHeaders } from "@/lib/auth";
import { clearSession, renewSession, saveSession } from "@/lib/auth-session";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"loading" | "local" | "login" | "ready" | "error">("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        const response = await fetch(`${API_BASE}/features`);
        if (!response.ok) throw new Error("Cannot connect to OpenTutor.");
        const config = await response.json();
        if (!active) return;
        if (!config.auth_enabled) { setState("local"); return; }
        if (await renewSession()) {
          const me = await fetch(`${API_BASE}/auth/me`, { headers: buildAuthHeaders() });
          if (me.ok) sessionStorage.setItem("opentutor-user-id", (await me.json()).id);
          if (active) setState(me.ok ? "ready" : "login");
        } else if (active) setState("login");
      } catch { if (active) setState("error"); }
    }
    void initialize();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (state !== "ready") return;
    const interval = setInterval(async () => {
      if (!await renewSession() && !sessionStorage.getItem("access_token")) setState("login");
    }, 60_000);
    return () => clearInterval(interval);
  }, [state]);

  async function login(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      if (!response.ok) throw new Error("Sign-in failed. Check your credentials or try again later.");
      saveSession(await response.json());
      const me = await fetch(`${API_BASE}/auth/me`, { headers: buildAuthHeaders() });
      if (!me.ok) { clearSession(); throw new Error("This account cannot access OpenTutor."); }
      sessionStorage.setItem("opentutor-user-id", (await me.json()).id);
      setState("ready");
    } catch (e) { setError(e instanceof Error ? e.message : "Sign-in failed."); }
    finally { setBusy(false); }
  }

  if (state === "loading") return <p role="status" className="p-8">Connecting to OpenTutor…</p>;
  if (state === "error") return <div role="alert" className="p-8">Cannot connect to OpenTutor. <button onClick={() => location.reload()}>Retry</button></div>;
  if (state === "login") return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">Sign in to OpenTutor</h1>
      <p className="text-sm text-muted-foreground">Use the account provided by your family administrator.</p>
      <form onSubmit={login} className="flex flex-col gap-4">
        <label>Email<input className="mt-1 w-full rounded border p-2" name="email" type="email" autoComplete="username" required /></label>
        <label>Password<input className="mt-1 w-full rounded border p-2" name="password" type="password" autoComplete="current-password" required /></label>
        {error && <p role="alert">{error}</p>}
        <button className="rounded bg-primary p-2 text-primary-foreground" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
  return <>{state === "ready" && <button className="fixed bottom-3 right-3 z-50 rounded border bg-background px-3 py-1 text-sm" onClick={async () => {
    try { await fetch(`${API_BASE}/auth/logout`, { method: "POST", headers: buildAuthHeaders() }); }
    finally { clearSession(); location.reload(); }
  }}>Sign out</button>}{children}</>;
}
