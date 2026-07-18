import type { Metadata } from "next";

import { AuthPageGuard } from "@/components/auth/auth-page-guard";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthPageGuard>
      <AuthShell mode="login">
        <AuthForm mode="login" />
      </AuthShell>
    </AuthPageGuard>
  );
}
