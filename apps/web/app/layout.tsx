import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "AGCP Control Plane",
  description: "Agent Governance Control Plane"
};

const navigationItems = [
  { href: "/", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/human-approvals", label: "Human Approvals" },
  { href: "/evidence", label: "Evidence" },
  { href: "/audit", label: "Audit" },
  { href: "/policies", label: "Policies" },
  { href: "/access-data", label: "Access & Data" },
  { href: "/runtime-gateway", label: "Runtime Gateway" },
  { href: "/integrations", label: "Integrations" },
  { href: "/settings", label: "Settings" }
];

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar" aria-label="Primary navigation">
            <div className="brand">
              <Link className="brand-mark" href="/">
                AGCP
              </Link>
              <h1>Agent Governance Control Plane</h1>
              <p>
                Govern agents, runtime decisions, approvals, and evidence
                without replacing external orchestrators.
              </p>
            </div>
            <nav className="nav" aria-label="Application sections">
              {navigationItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>

          <div className="workspace">
            <header className="topbar">
              <strong>Governance workspace</strong>
              <span className="environment-pill">Local / development</span>
            </header>
            <main className="content">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
