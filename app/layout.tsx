import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "./components/AppShell";
import "./globals.css";
import "./dashboard.css";
import "./design-v3.css";
export const metadata: Metadata = { title: "EDGE — TCG Market Intelligence", description: "Intelligence de marché et aide à la décision pour les Trading Card Games.", applicationName: "EDGE", appleWebApp: { capable: true, title: "EDGE", statusBarStyle: "black-translucent" }, manifest: "/manifest.webmanifest" };
export const viewport: Viewport = { themeColor: "#080e19", width: "device-width", initialScale: 1 };
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="fr"><body><AppShell>{children}</AppShell></body></html>;
}
