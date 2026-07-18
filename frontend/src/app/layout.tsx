import type { Metadata } from "next";

import { AuthProvider } from "@/components/auth/auth-provider";

import "./globals.css";
import "./app-shell.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: {
    default: "Incrementality | Causal measurement for marketing teams",
    template: "%s | Incrementality",
  },
  description:
    "Measure marketing lift with reproducible causal methods, diagnostic evidence, and decision-ready business impact.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
