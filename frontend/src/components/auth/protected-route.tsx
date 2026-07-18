"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect } from "react";

import { useAuth } from "./auth-provider";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const router = useRouter();
  const auth = useAuth();

  useEffect(() => {
    if (auth.status === "unauthenticated") {
      router.replace("/login");
    }
  }, [auth.status, router]);

  if (auth.status === "checking") {
    return (
      <div role="status" aria-live="polite">
        Checking your session…
      </div>
    );
  }

  if (auth.status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
