import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ServiceStatus } from "@/components/service-status";
import "./globals.css";
export const metadata: Metadata = { title: { default: "AgroPilot · Your irrigation plan", template: "%s · AgroPilot" }, description: "Daily irrigation recommendations for your farm plots." };
export const dynamic = "force-dynamic";
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header"><div className="shell header-inner"><Link href="/" className="brand"><svg viewBox="0 0 28 28" width="28" height="28" fill="none" aria-hidden="true"><path d="M14 3C10 9 5 13 5 18a9 9 0 0 0 18 0c0-5-5-9-9-15Z" stroke="currentColor" strokeWidth="2" /><path d="M9 18c0 3 2 5 5 5M14 10v7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>AgroPilot</Link><span className="header-note">Daily irrigation</span></div></header>
    <main id="main" className="shell">{children}</main>
    <div className="shell"><Suspense fallback={<p className="service-status">Checking services…</p>}><ServiceStatus /></Suspense></div>
  </body></html>;
}
