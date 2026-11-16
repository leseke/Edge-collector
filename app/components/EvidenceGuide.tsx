import type { ReactNode } from "react";

export type EvidenceLevel = "FACT" | "WEAK_SIGNAL" | "INFERENCE" | "BET";

const EVIDENCE: Record<EvidenceLevel, { label: string; explanation: string; tone: string }> = {
  FACT: { label: "Fait documenté", explanation: "Une source identifiable étaye directement cette information. Le fait peut rester à vérifier indépendamment.", tone: "fact" },
  WEAK_SIGNAL: { label: "Signal faible", explanation: "Un indice mérite une surveillance, mais il est trop isolé ou incomplet pour soutenir une conclusion.", tone: "signal" },
  INFERENCE: { label: "Déduction", explanation: "Une interprétation construite à partir de plusieurs observations. Ce n'est pas une preuve directe.", tone: "inference" },
  BET: { label: "Hypothèse risquée", explanation: "Une thèse d'investissement possible, qui assume une incertitude et peut être invalidée.", tone: "bet" },
};

export function EvidenceGuide({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`evidence-guide${compact ? " evidence-guide-compact" : ""}`} aria-labelledby="evidence-guide-title">
      <div className="evidence-guide-heading">
        <p className="native-eyebrow">LIRE LES CONCLUSIONS</p>
        <h2 id="evidence-guide-title">Une preuve n'est pas une prédiction.</h2>
        <p>EDGE sépare ce qui est observé, ce qui semble se dessiner et ce qui relève encore d'un pari.</p>
      </div>
      <div className="evidence-guide-grid">
        {(Object.entries(EVIDENCE) as [EvidenceLevel, typeof EVIDENCE[EvidenceLevel]][]).map(([key, item]) => (
          <div className="evidence-guide-item" key={key}>
            <span className={`evidence-chip evidence-${item.tone}`}>{item.label}</span>
            <p>{item.explanation}</p>
          </div>
        ))}
      </div>
      <p className="evidence-guide-footnote">Une information classée « fait documenté » n'est pas automatiquement une vente vérifiée, une rareté prouvée ou une garantie de rendement. Chaque rapport doit conserver ses sources et ses limites.</p>
    </section>
  );
}

export function ReportPrinciple({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="report-principle">
      <h3>{title}</h3>
      <div>{children}</div>
    </section>
  );
}

export function DataLimit({ children }: { children: ReactNode }) {
  return <p className="data-limit"><strong>Limite des données :</strong> {children}</p>;
}
