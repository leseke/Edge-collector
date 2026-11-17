import { PwaInstall } from "./PwaInstall";
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
const navigation = [
  { href: "/", label: "Vue d'ensemble", short: "Marché", icon: "◫" },
  { href: "/mri", label: "Intelligence de marché", short: "Analyses", icon: "⌁" },
  { href: "/local", label: "Enquête locale", short: "Enquête locale", icon: "⌘" },
];
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const current = navigation.find((item) => item.href === pathname || (item.href !== "/" && pathname.startsWith(item.href)));
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Navigation EDGE">
      <Link className="brand-lockup" href="/" aria-label="EDGE, accueil">
        <span className="brand-mark">E</span><span className="brand-copy"><strong>EDGE</strong><small>TCG INTELLIGENCE</small></span>
      </Link>
      <div className="sidebar-label">ESPACE DE TRAVAIL</div>
      <nav className="side-nav">
        {navigation.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return <Link key={item.href} href={item.href} className={active ? "side-link active" : "side-link"} aria-current={active ? "page" : undefined}>
            <span className="side-icon" aria-hidden="true">{item.icon}</span><span>{item.label}</span>{active && <span className="active-indicator" />}
          </Link>;
        })}
      </nav>
      <div className="sidebar-bottom"><span className="connection-dot" /><span>Socle applicatif actif</span><small>PREVIEW · NEXT.JS</small></div>
    </aside>
    <div className="app-main">
      <header className="app-topbar">
        <div className="breadcrumb"><span>EDGE</span><span className="breadcrumb-sep">/</span><strong>{current?.short ?? "Marché"}</strong></div>
        <div className="topbar-right"><PwaInstall /><span className="environment"><i /> ENVIRONNEMENT DE PRÉVISUALISATION</span></div>
      </header>
      <main className="workspace">{children}</main>
    </div>
  </div>;
}
