"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import {
  AuthenticationError,
  login,
  register,
  SESSION_TOKEN_KEY,
  WORKSPACE_ID_KEY,
} from "../../lib/auth/api";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);

    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");

    try {
      let destination = "/";
      if (mode === "register") {
        const result = await register({
          displayName: String(data.get("displayName") ?? "").trim(),
          organizationName: String(data.get("organizationName") ?? "").trim(),
          email,
          password,
        });
        localStorage.setItem(WORKSPACE_ID_KEY, result.workspace_id);
        destination = `/workspaces/${result.workspace_id}/results-dashboard`;
      }

      const session = await login(email, password);
      localStorage.setItem(SESSION_TOKEN_KEY, session.session_token);
      localStorage.setItem("incrementality_session_expires_at", session.expires_at);
      router.push(destination);
    } catch (caught) {
      setError(caught instanceof AuthenticationError ? caught.message : "Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  const isLogin = mode === "login";

  return (
    <form className="auth-form" onSubmit={submit}>
      {!isLogin && (
        <div className="auth-field-row">
          <label className="auth-field">
            <span>Your name</span>
            <input name="displayName" autoComplete="name" placeholder="Avery Stone" required />
          </label>
          <label className="auth-field">
            <span>Organization</span>
            <input name="organizationName" autoComplete="organization" placeholder="Northstar Labs" required />
          </label>
        </div>
      )}

      <label className="auth-field">
        <span>Work email</span>
        <input name="email" type="email" autoComplete="email" placeholder="you@company.com" required />
      </label>

      <label className="auth-field">
        <span>Password</span>
        <span className="password-control">
          <input
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete={isLogin ? "current-password" : "new-password"}
            placeholder={isLogin ? "Enter your password" : "At least 12 characters"}
            minLength={isLogin ? 1 : 12}
            required
          />
          <button type="button" onClick={() => setShowPassword((visible) => !visible)}>
            {showPassword ? "Hide" : "Show"}
          </button>
        </span>
      </label>

      {error && <p className="auth-error" role="alert">{error}</p>}

      <button className="auth-submit" type="submit" disabled={pending}>
        <span>{pending ? (isLogin ? "Signing in…" : "Building workspace…") : (isLogin ? "Sign in" : "Create workspace")}</span>
        {!pending && <span aria-hidden="true">→</span>}
      </button>

      <p className="auth-switch">
        {isLogin ? "New to Incrementality?" : "Already have an account?"}{" "}
        <Link href={isLogin ? "/register" : "/login"}>{isLogin ? "Create your workspace" : "Sign in"}</Link>
      </p>
    </form>
  );
}
