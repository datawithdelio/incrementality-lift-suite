import type { Metadata } from "next";

import { AuthForm } from "@/components/auth/auth-form";
import { AuthShell } from "@/components/auth/auth-shell";

export const metadata: Metadata = { title: "Sign in · Incrementality" };

export default function LoginPage() {
  return <AuthShell mode="login"><AuthForm mode="login" /></AuthShell>;
}
