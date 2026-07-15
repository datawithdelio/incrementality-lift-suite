import Link from "next/link";

export default function Home() {
  return (
    <main className="state-shell"><section className="state-card"><p className="eyebrow">Incrementality</p><h1>Measure what actually changed.</h1><p>Turn your marketing data into causal evidence, clear diagnostics, and business decisions.</p><div className="home-actions"><Link href="/login">Sign in</Link><Link href="/register">Create workspace</Link></div></section></main>
  );
}
