import type { Metadata } from "next";

import { AuthProvider } from "@/components/auth/auth-provider";
import { AppToaster } from "@/components/ui/app-toaster";

import "./globals.css";
import "./app-shell.css";
import "./design-system.css";
import "./project-lifecycle.css";
import "./premium-polish.css";
import "./dataset-upload.css";
import "./data-explorer.css";

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
        <AuthProvider>
          {children}
          <AppToaster />
        </AuthProvider>
      </body>
    </html>
  );
}
