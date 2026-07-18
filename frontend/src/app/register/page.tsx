import type { Metadata } from "next";

import { AuthPageGuard } from "@/components/auth/auth-page-guard";
import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export const metadata: Metadata = { title: "Create workspace" };

export default function RegisterPage() {
  return (
    <AuthPageGuard>
      <AuthShell mode="register">
        <AuthForm mode="register" />
      </AuthShell>
    </AuthPageGuard>
  );
}
