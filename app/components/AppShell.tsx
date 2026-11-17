"use client";
import { PwaInstall } from "./PwaInstall";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "Accueil", short: "Accueil", icon: "⌂" },
  { href: "/explorer", label: "Explorer", short: "Explorer", icon: "⌕" },
  { href: "/mri", label: "Radar", short: "Radar", icon: "⌁" },
];
const administration = { href: "/local", label: "Laboratoire local", short: "Laboratoire", icon: "⚙" };

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const current = [...navigation, administration].find(item => item.href === pathname || (item.href !== "/" && pathname.startsWith(item.href)));
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Navigation EDGE">
      <Link className="brand-lockup" href="/" aria-label="EDGE, accueil">
        <span className="brand-mark">E</span><span className="brand-copy"><strong>EDGE</strong><small>INVESTISSEMENT & RECHERCHE</small></span>
      </Link>
      <div className="sidebar-label">MON ESPACE</div>
      <nav className="side-nav" aria-label="Espace investisseur">
        {navigation.map(item => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return <Link key={item.href} href={item.href} className={active ? "side-link active" : "side-link"} aria-current={active ? "page" : undefined}>
            <span className="side-icon" aria-hidden="true">{item.icon}</span><span>{item.label}</span>{active && <span className="active-indicator" />}
          </Link>;
        })}
      </nav>
      <div className="sidebar-bottom">
        <Link href={administration.href} className="side-link" aria-current={pathname.startsWith("/local") ? "page" : undefined}>
          <span className="side-icon" aria-hidden="true">{administration.icon}</span><span>{administration.label}</span>
        </Link>
        <small>Fonctions techniques séparées de l'espace investisseur</small>
      </div>
    </aside>
    <div className="app-main">
      <header className="app-topbar">
        <div className="breadcrumb"><span>EDGE</span><span className="breadcrumb-sep">/</span><strong>{current?.short ?? "Accueil"}</strong></div>
        <div className="topbar-right"><Link className="edge-admin-link" href="/local" aria-label="Ouvrir le laboratoire technique">Réglages</Link><PwaInstall /></div>
      </header>
      <main className="workspace">{children}</main>
    </div>
  </div>;
}
