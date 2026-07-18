"use client";

import { useRouter } from "next/navigation";
import {
  type ReactNode,
  useEffect,
} from "react";

import { useAuth } from "./auth-provider";

export function AuthPageGuard({
  children,
}: {
  children: ReactNode;
}) {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (auth.status === "authenticated") {
      router.replace("/");
    }
  }, [
    auth.status,
    router,
  ]);

  if (auth.status === "checking") {
    return (
      <div
        role="status"
        aria-live="polite"
      >
        Checking your session…
      </div>
    );
  }

  if (auth.status === "authenticated") {
    return null;
  }

  return children;
}
