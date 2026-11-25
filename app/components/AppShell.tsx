"use client";
import { PwaInstall } from "./PwaInstall";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navigation = [
  { href: "/", label: "Accueil", short: "Accueil", icon: "home" },
  { href: "/explorer", label: "Explorer", short: "Explorer", icon: "search" },
  { href: "/mri", label: "Radar", short: "Radar", icon: "radar" },
  { href: "/portfolio", label: "Portefeuille", short: "Portefeuille", icon: "wallet" },
];
const administration = { href: "/local", label: "Laboratoire local", short: "Laboratoire", icon: "settings" };

function NavIcon({name}:{name:string}) {
 const paths:Record<string,ReactNode>={
 home:<><path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/></>,
 search:<><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
 radar:<><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="m12 12 7-7"/><circle cx="12" cy="12" r="1"/></>,
 wallet:<><rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 8h18m0 4h-6a2 2 0 0 0 0 4h6"/><circle cx="16" cy="14" r=".5"/></>,
 settings:<><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M19 5l-2 2M7 17l-2 2"/></>,
 bell:<><path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5z"/><path d="M10 20h4"/></>
 };
 return <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
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
