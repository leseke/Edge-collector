"use client";
import { PwaInstall } from "./PwaInstall";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "Accueil", short: "Accueil", icon: "home" },
  { href: "/explorer", label: "Explorer", short: "Explorer", icon: "search" },
  { href: "/mri", label: "Radar", short: "Radar", icon: "radar" },
];
const administration = { href: "/local", label: "Laboratoire local", short: "Laboratoire", icon: "⚙" };

function NavIcon({name}:{name:string}){
 const paths:Record<string,ReactNode>={
 home:<><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></>,
 search:<><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></>,
 radar:<><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="m12 12 7-7"/><circle cx="12" cy="12" r=".8"/></>,
 settings:<><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2"/></>,
 bell:<><path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5zM10 21h4"/></>
 };
 return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]??paths.settings}</svg>;
}

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
            <span className="side-icon" aria-hidden="true"><NavIcon name={item.icon}/></span><span>{item.label}</span>{active && <span className="active-indicator" />}
          </Link>;
        })}
      </nav>
      <div className="sidebar-bottom">
        <Link href={administration.href} className="side-link" aria-current={pathname.startsWith("/local") ? "page" : undefined}>
          <span className="side-icon" aria-hidden="true"><NavIcon name="settings"/></span><span>{administration.label}</span>
        </Link>
        <small>Fonctions techniques séparées de l'espace investisseur</small>
      </div>
    </aside>
    <div className="app-main">
      <header className="app-topbar">
        <Link className="edge-top-brand" href="/" aria-label="EDGE, accueil"><strong>EDGE<span>.</span></strong><small>COLLECTIBLES INTELLIGENCE</small></Link>
        <div className="breadcrumb"><span>EDGE</span><span className="breadcrumb-sep">/</span><strong>{current?.short ?? "Accueil"}</strong></div>
        <div className="topbar-right"><Link className="edge-header-icon" href="/mri?tab=signaux#edge-radar-notifications" aria-label="Notifications"><NavIcon name="bell"/></Link><Link className="edge-header-icon" href="/local" aria-label="Réglages et laboratoire"><NavIcon name="settings"/></Link><PwaInstall /></div>
      </header>
      <main className="workspace">{children}</main>
    </div>
  </div>;
}
