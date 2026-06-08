import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AGCPStudioShell } from "./agcp-studio/AGCPStudio";
import "./globals.css";

export const metadata: Metadata = {
  title: "AGCP Studio",
  description: "Agent Governance Control Plane Studio"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AGCPStudioShell>{children}</AGCPStudioShell>
      </body>
    </html>
  );
}
