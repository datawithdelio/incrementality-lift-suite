"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import {
  AuthenticationError,
  login,
  register,
} from "../../lib/auth/api";
import { useAuth } from "./auth-provider";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const auth = useAuth();
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
      if (mode === "register") {
        await register({
          displayName: String(data.get("displayName") ?? "").trim(),
          email,
          password,
        });
      }

      const session = await login(email, password);
      auth.establishSession(session);
      router.push("/");
    } catch (caught) {
      setError(caught instanceof AuthenticationError ? caught.message : "Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  const isLogin = mode === "login";
  const visibleError =
    error ?? (isLogin ? auth.sessionNotice : null);

  return (
    <form className="auth-form" onSubmit={submit}>
      {!isLogin && (
        <label className="auth-field">
          <span>Your name</span>
          <input name="displayName" autoComplete="name" placeholder="Avery Stone" required />
        </label>
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

      {visibleError && (
        <p
          className="auth-error"
          role="alert"
        >
          {visibleError}
        </p>
      )}

      <button className="auth-submit" type="submit" disabled={pending}>
        <span>{pending ? (isLogin ? "Signing in…" : "Creating account…") : (isLogin ? "Sign in" : "Create account")}</span>
        {!pending && <span aria-hidden="true">→</span>}
      </button>

      <p className="auth-switch">
        {isLogin ? "New to Incrementality?" : "Already have an account?"}{" "}
        <Link href={isLogin ? "/register" : "/login"}>{isLogin ? "Create an account" : "Sign in"}</Link>
      </p>
    </form>
  );
}
