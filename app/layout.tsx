import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "./components/AppShell";
import "./globals.css";
export const metadata: Metadata = { title: "EDGE — TCG Market Intelligence", description: "Intelligence de marché et aide à la décision pour les Trading Card Games.", applicationName: "EDGE" };
export const viewport: Viewport = { themeColor: "#090b12", width: "device-width", initialScale: 1 };
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="fr"><body><AppShell>{children}</AppShell></body></html>;
}
