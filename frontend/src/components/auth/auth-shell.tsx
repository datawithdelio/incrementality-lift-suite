import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand/brand-mark";

export function AuthShell({ mode, children }: { mode: "login" | "register"; children: ReactNode }) {
  const isLogin = mode === "login";
  return (
    <main className="auth-shell">
      <section className="auth-story" aria-label="Product introduction">
        <Link className="auth-brand" href="/" aria-label="Incrementality home">
          <BrandMark inverted />
        </Link>
        <div className="auth-story-copy">
          <p className="eyebrow">Causal measurement, made useful</p>
          <h1>Know what moved the needle.</h1>
          <p>Turn experiments and observational data into decisions your team can defend.</p>
          <div className="auth-proof">
            <span><strong>Five methods</strong>One workflow</span>
            <span><strong>Versioned inputs</strong>Reproducible runs</span>
            <span><strong>Clear diagnostics</strong>Defensible claims</span>
          </div>
        </div>
        <p className="auth-story-note">Built for teams that care about evidence, not vanity metrics.</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-mobile-brand"><BrandMark /></div>
          <p className="auth-kicker">{isLogin ? "Welcome back" : "Start measuring"}</p>
          <h2>{isLogin ? "Sign in to your workspace" : "Create your measurement workspace"}</h2>
          <p className="auth-intro">{isLogin ? "Your analyses, diagnostics, and decisions are waiting." : "Set up your team’s home for trustworthy incrementality in under a minute."}</p>
          {children}
          <p className="auth-terms">By continuing, you agree to responsible, evidence-based measurement.</p>
        </div>
      </section>
    </main>
  );
}
