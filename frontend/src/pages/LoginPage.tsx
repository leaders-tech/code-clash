/*
This file shows login and registration for Code Clash.
Edit this file when auth form behavior or redirect behavior changes.
Copy this file as a starting point for another simple form page.
*/

import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../app/auth";

export function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, password);
      }
      navigate("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Auth failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto grid max-w-4xl gap-5 md:grid-cols-[1.1fr_0.9fr]">
      <div className="border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Code Clash</p>
        <h2 className="mt-2 text-3xl font-semibold text-slate-950">Program a bot. Enter a tournament. Watch it compete.</h2>
        <p className="mt-4 text-sm leading-6 text-slate-700">
          Code Clash is a classroom-friendly arena where students upload Python or C++ bots. Matches run automatically, rankings update with Elo, and finished games can be replayed step by step.
        </p>
        <div className="mt-5 grid gap-3 text-sm text-slate-700">
          <p className="border border-slate-100 bg-slate-50 p-3">Start by creating an account or logging in.</p>
          <p className="border border-slate-100 bg-slate-50 p-3">After login, create a bot, upload source code, then enter or create a Snake tournament.</p>
        </div>
      </div>
      <div className="border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex gap-2">
        <button className={mode === "login" ? "bg-slate-900 px-3 py-2 text-white" : "border px-3 py-2"} onClick={() => setMode("login")} type="button">
          Login
        </button>
        <button className={mode === "register" ? "bg-slate-900 px-3 py-2 text-white" : "border px-3 py-2"} onClick={() => setMode("register")} type="button">
          Register
        </button>
      </div>
      <h2 className="text-2xl font-semibold">{mode === "login" ? "Login" : "Create account"}</h2>
      <form className="mt-5 space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Username</span>
          <input className="w-full border border-slate-300 px-3 py-2" onChange={(event) => setUsername(event.target.value)} value={username} />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Password</span>
          <input className="w-full border border-slate-300 px-3 py-2" onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
        </label>
        {error ? <p className="bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
        <button className="w-full bg-slate-900 px-3 py-2 font-semibold text-white" disabled={busy} type="submit">
          {busy ? "Working..." : mode === "login" ? "Login" : "Register"}
        </button>
      </form>
      </div>
    </section>
  );
}
