"use client";

import { useRouter } from "next/navigation";
import {
  type ReactNode,
  useEffect,
  useState,
} from "react";

import { useAuth } from "./auth-provider";

export function AuthPageGuard({
  children,
}: {
  children: ReactNode;
}) {
  const auth = useAuth();
  const router = useRouter();
  const [isTakingLonger, setIsTakingLonger] = useState(false);

  useEffect(() => {
    if (auth.status === "authenticated") {
      router.replace("/");
    }
  }, [
    auth.status,
    router,
  ]);

  useEffect(() => {
    if (auth.status !== "checking") return;

    const timer = window.setTimeout(() => {
      setIsTakingLonger(true);
    }, 6_000);

    return () => window.clearTimeout(timer);
  }, [auth.status]);

  if (auth.status === "checking") {
    return (
      <main className="auth-checking-shell">
        <div className="auth-checking-card" role="status" aria-live="polite">
          <span aria-hidden="true" />
          <strong>
            {isTakingLonger
              ? "Starting the secure demo"
              : "Checking your session…"}
          </strong>
          {isTakingLonger ? (
            <p>The first visit may take a little longer while the server wakes up.</p>
          ) : null}
        </div>
      </main>
    );
  }

  if (auth.status === "authenticated") {
    return null;
  }

  return children;
}
