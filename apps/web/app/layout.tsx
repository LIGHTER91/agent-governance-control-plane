import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

const navItems = [
  { label: "Overview", href: "/" },
  { label: "Agents", href: "/agents" },
  { label: "Policies", href: "/policies" },
  { label: "Runtime Gateway", href: "/runtime-gateway" },
  { label: "Human Approvals", href: "/human-approvals" },
  { label: "Evidence", href: "/evidence" },
  { label: "Audit", href: "/audit" },
  { label: "Settings", href: "/settings" }
];

export const metadata: Metadata = {
  title: "AGCP Dashboard",
  description: "Agent Governance Control Plane dashboard shell"
};

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
              <div className="brand-mark">AGCP</div>
              <h1>Agent Governance Control Plane</h1>
              <p>Registry, runtime decisions, human oversight, and evidence.</p>
            </div>
            <nav className="nav">
              {navItems.map((item) => (
                <Link href={item.href} key={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <div className="workspace">
            <header className="topbar">
              <strong>Governance dashboard shell</strong>
              <span className="environment-pill">V0 backend foundation</span>
            </header>
            <main className="content">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
