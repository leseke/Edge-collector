import Link from "next/link";
import portfolio from "../../portfolio.json";
export const dynamic="force-dynamic";
type Position={id:string;name:string;cost_cents:number;quantity:number};
function validPosition(value:unknown):value is Position{
 if(!value||typeof value!=="object")return false;
 const p=value as Record<string,unknown>;
 return typeof p.id==="string"&&p.id.length>0&&typeof p.name==="string"&&p.name.trim().length>0&&typeof p.cost_cents==="number"&&Number.isSafeInteger(p.cost_cents)&&p.cost_cents>=0&&typeof p.quantity==="number"&&Number.isSafeInteger(p.quantity)&&p.quantity>0&&Number.isSafeInteger(p.cost_cents*p.quantity);
}
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
export default function PortfolioPage(){
 const raw:unknown[]=Array.isArray(portfolio.positions)?portfolio.positions:[];
 const positions=raw.filter(validPosition);
 const total=positions.reduce((sum,p)=>sum+p.cost_cents*p.quantity,0);
 const complete=positions.length===raw.length&&new Set(positions.map(p=>p.id)).size===positions.length&&Number.isSafeInteger(total);
 return <div className="native-dashboard edge-portfolio">
 <header className="edge-portfolio-heading"><p className="native-eyebrow">ESPACE INVESTISSEUR</p><h1>Portefeuille<span>.</span></h1><p>Vos acquisitions enregistrées, distinctes des opportunités du Radar.</p></header>
 <section className="edge-portfolio-hero" aria-label="Synthèse financière"><span>Capital disponible</span><strong>Non renseigné</strong><p>Aucun solde de trésorerie vérifié n’est raccordé à cet espace.</p><div className="edge-portfolio-metrics"><div><span>Coût des positions</span><b>{complete?money.format(total/100):"—"}</b></div><div><span>Valorisation estimée</span><b>—</b></div><div><span>Performance latente</span><b>—</b></div><div><span>Positions enregistrées</span><b>{complete?positions.length:"—"}</b></div></div></section>
 <section className="edge-portfolio-panel"><h2>Mes acquisitions</h2>{!complete?<p>Le registre contient des positions dont le format doit être vérifié. Aucun total partiel n’est présenté comme complet.</p>:positions.length===0?<div className="edge-portfolio-empty"><strong>Aucune acquisition enregistrée</strong><p>Les opportunités détectées ne deviennent pas automatiquement des achats.</p><Link href="/mri?tab=signaux">Explorer les opportunités →</Link></div>:<ul>{positions.map(p=><li key={p.id}><div><strong>{p.name}</strong><small>{p.quantity} unité(s)</small></div><b>{money.format(p.cost_cents*p.quantity/100)}</b></li>)}</ul>}</section>
 <section className="edge-portfolio-panel"><h2>Évolution du portefeuille</h2><p>Aucun historique de valorisation comparable n’est raccordé. Les performances réalisées et latentes ne sont pas calculées à partir de simples prix affichés.</p></section>
 <p className="edge-portfolio-note">Registre en lecture seule. La gestion privée du capital et l’enregistrement des acquisitions nécessitent un stockage authentifié ; aucune donnée financière personnelle n’est enregistrée dans le navigateur ou publiée automatiquement.</p>
 </div>
}
