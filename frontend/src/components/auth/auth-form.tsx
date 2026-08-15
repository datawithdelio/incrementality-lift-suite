"use client";

import { ArrowRightIcon } from "@phosphor-icons/react/ArrowRight";
import { CircleNotchIcon } from "@phosphor-icons/react/CircleNotch";
import { WarningCircleIcon } from "@phosphor-icons/react/WarningCircle";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  AuthenticationError,
  login,
  register,
  RegistrationConflictError,
} from "../../lib/auth/api";
import { useAuth } from "./auth-provider";

type AuthMode = "login" | "register";
const SLOW_AUTH_NOTICE_MS = 6_000;

type AuthFeedback = {
  title: string;
  message: string;
  field?: "email";
  signInAction?: boolean;
};

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const auth = useAuth();
  const [pending, setPending] = useState(false);
  const [isTakingLonger, setIsTakingLonger] = useState(false);
  const [error, setError] = useState<AuthFeedback | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const slowNoticeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (slowNoticeTimerRef.current !== null) {
        window.clearTimeout(slowNoticeTimerRef.current);
      }
    };
  }, []);

  function startPending() {
    setPending(true);
    setIsTakingLonger(false);
    slowNoticeTimerRef.current = window.setTimeout(() => {
      setIsTakingLonger(true);
    }, SLOW_AUTH_NOTICE_MS);
  }

  function finishPending() {
    if (slowNoticeTimerRef.current !== null) {
      window.clearTimeout(slowNoticeTimerRef.current);
      slowNoticeTimerRef.current = null;
    }
    setPending(false);
    setIsTakingLonger(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startPending();
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
      toast.success(isLogin ? "Welcome back" : "Account created", {
        description: "Your measurement workspace is ready.",
      });
      router.push("/");
    } catch (caught) {
      const registrationConflict =
        caught instanceof RegistrationConflictError;
      const title = registrationConflict
        ? "Email already registered"
        : isLogin
          ? "Sign in failed"
          : "Account not created";
      const message =
        caught instanceof AuthenticationError
          ? caught.message
          : "Something went wrong. Please try again.";

      setError({
        title,
        message,
        field: registrationConflict ? "email" : undefined,
        signInAction: registrationConflict,
      });
      toast.error(title, { description: message });
    } finally {
      finishPending();
    }
  }

  const isLogin = mode === "login";
  const visibleError =
    error ?? (
      isLogin && auth.sessionNotice
        ? {
            title: "Sign in required",
            message: auth.sessionNotice,
          }
        : null
    );

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
        <input
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          aria-invalid={error?.field === "email"}
          aria-describedby={
            error?.field === "email"
              ? "authentication-error"
              : undefined
          }
          onChange={() => {
            if (error?.field === "email") {
              setError(null);
            }
          }}
          required
        />
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
        <div
          id="authentication-error"
          className="auth-error"
          role="alert"
        >
          <WarningCircleIcon
            size={20}
            weight="fill"
            aria-hidden="true"
          />
          <div>
            <strong>{visibleError.title}</strong>
            <span>{visibleError.message}</span>
            {visibleError.signInAction && (
              <Link href="/login">
                Sign in instead
              </Link>
            )}
          </div>
        </div>
      )}

      <button className="auth-submit" type="submit" disabled={pending}>
        <span>{pending ? (isLogin ? "Signing in…" : "Creating account…") : (isLogin ? "Sign in" : "Create account")}</span>
        {pending ? <CircleNotchIcon className="auth-spinner" size={18} aria-hidden="true" /> : <ArrowRightIcon size={18} aria-hidden="true" />}
      </button>

      {isTakingLonger ? (
        <p className="auth-slow-start" role="status">
          Starting the secure demo server. The first visit may take a little
          longer, so please keep this screen open.
        </p>
      ) : null}

      <p className="auth-switch">
        {isLogin ? "New to Incrementality?" : "Already have an account?"}{" "}
        <Link href={isLogin ? "/register" : "/login"}>{isLogin ? "Create an account" : "Sign in"}</Link>
      </p>
    </form>
  );
}
