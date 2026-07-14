import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Analysis Results · Incrementality",
  description: "Clear, diagnostic-backed causal measurement results.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
