"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

type Health = { reachable: boolean; status: string; provider?: string | null };
type ReportSource = { source_id: string; title: string; publisher: string; url: string | null; published_at: string | null; accessed_at: string; tier: string; simulated: boolean };
type ReportClaim = { claim_id: string; statement: string; kind: string; verification: string; confidence: string; author: string; source_ids: string[]; contradicting_source_ids?: string[]; basis?: { fact_claim_ids: string[]; computation_ids: string[] }; source_claim_type?: string };
type ReportDataset = { dataset_id: string; title: string; measure: string; territory: string; currency: string | null; unit: string; period: { start: string; end: string }; points: Array<{ t: string; value: number | null; status: string }> };
type InquiryReport = {
  report_id?: string; report_version?: number; created_at?: string; data_as_of?: string;
  production_status?: string; simulated?: boolean;
  subject?: { title?: string; market?: string; category?: string; region?: string; language?: string };
  sources?: ReportSource[]; claims?: ReportClaim[]; datasets?: ReportDataset[];
  decisions?: { agent_opinion?: { stance?: string; rationale?: string; is_decision?: boolean } | null; edge_decision?: { decision?: string; decided_by?: string } };
  economics?: { listed_price_dataset_ids?: string[]; realized_sale_dataset_ids?: string[]; availability?: { buyable_verified?: boolean }; fees?: { verified?: boolean }; liquidity?: { claim_ids?: string[] } };
  computations?: Array<{ computation_id: string; method: string; dataset_id: string; t_from: string; t_to: string; result: number; unit: string }>;
};
type SpecialistTask = { agent_id: string; status: string; mode: string; findings?: Array<{ classification: string; statement: string }> ; limitations?: string[] };
type InquiryDossier = {
  contradictions?: Array<{ assertion_key: string; positions: Record<string, string[]> }>;
  unknowns?: string[];
  agent_team?: { tasks?: Array<{ agent_id: string }>; execution_trace?: { task_results?: SpecialistTask[]; contradictions?: unknown[]; paid_calls?: number } };
};
type InquiryResult = {
  status?: string; reason?: string; report?: InquiryReport; dossier?: InquiryDossier;
  violations?: string[]; usage?: { limit?: number; period_utc?: string };
};
const KIND_LABEL: Record<string, string> = { fact: "Fait", interpretation: "Interprétation", hypothesis: "Hypothèse", uncertainty: "Incertitude", limitation: "Limite", invalidated: "Invalidé" };
const VERIFY_LABEL: Record<string, string> = { verified: "Vérifié", unverified: "Non vérifié", contradicted: "Contredit", simulated: "Simulé" };
const CONFIDENCE_LABEL: Record<string, string> = { low: "Faible", medium: "Moyenne", high: "Élevée" };
const MEASURE_LABEL: Record<string, string> = { asking_price: "Prix affiché", sold_price: "Vente conclue", retail_price: "Prix public", market_trend: "Tendance de marché", volume: "Volume", search_interest: "Intérêt de recherche", other: "Autre mesure" };
const RESULT_STATUS_LABEL: Record<string, string> = { REPORT: "Rapport généré", NO_DATA: "Données insuffisantes", AMBIGUOUS: "Question à préciser", INVALID: "Corpus invalide", REJECTED: "Résultat refusé par les contrôles EDGE", OUT_OF_SCOPE: "Hors périmètre TCG" };
function safeHttpUrl(value: string | null): string | null {
  if (!value) return null;
  try { const url = new URL(value); return url.protocol === "https:" ? url.href : null; } catch { return null; }
}
const LOCAL_BASE = "http://127.0.0.1:8765";

export function LocalCompanion() {
  const [token, setToken] = useState("");
  const [question, setQuestion] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [health, setHealth] = useState<Health>({ reachable: false, status: "checking" });
  const [checking, setChecking] = useState(false);
  const [running, setRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Vérification du service local…");
  const [result, setResult] = useState<InquiryResult | null>(null);
  const [error, setError] = useState("");

  const checkHealth = useCallback(async () => {
    setChecking(true);
    try {
      const response = await fetch(LOCAL_BASE + "/health", {
        method: "GET", mode: "cors", credentials: "omit", cache: "no-store",
        redirect: "error", referrerPolicy: "no-referrer",
        signal: AbortSignal.timeout(7000),
      });
      if (!response.ok) throw new Error("Service local indisponible.");
      const body = await response.json() as { status?: string; provider?: string };
      const next = { reachable: true, status: body.status || "unknown", provider: body.provider === "ollama_local" ? body.provider : null };
      setHealth(next);
      if (next.status === "configured") setStatusMessage("Registre de modèle local configuré. Cela ne prouve pas encore que le démon Ollama est disponible.");
      else if (next.status === "model_disabled") setStatusMessage("Service accessible, mais modèle local désactivé. Vérifie EDGE_LOCAL_LLM_ENABLED.");
      else setStatusMessage("Service accessible, mais modèle non configuré ou non vérifié.");
    } catch {
      setHealth({ reachable: false, status: "unreachable" });
      setStatusMessage("Service local inaccessible. Lance le compagnon Python sur ton ordinateur et autorise l’origine exacte du site EDGE.");
    } finally { setChecking(false); }
  }, []);

  useEffect(() => { void checkHealth(); }, [checkHealth]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (token.length < 32) { setError("Le jeton local doit contenir au moins 32 caractères."); return; }
    if (!question.trim() || question.length > 2000) { setError("La question doit contenir entre 1 et 2 000 caractères."); return; }
    if (!file) { setError("Sélectionne un corpus EDGE au format JSON."); return; }
    if (file.size < 1 || file.size > 5 * 1024 * 1024) { setError("Le corpus doit peser entre 1 octet et 5 Mio."); return; }
    let corpus: unknown;
    try { corpus = JSON.parse(await file.text()); }
    catch { setError("Le fichier sélectionné n’est pas un JSON valide."); return; }
    if (!corpus || typeof corpus !== "object" || Array.isArray(corpus)) { setError("Le corpus doit être un objet JSON."); return; }

    setRunning(true);
    setStatusMessage("Enquête en cours sur le service local…");
    try {
      const response = await fetch(LOCAL_BASE + "/v1/inquiry", {
        method: "POST", mode: "cors", credentials: "omit", cache: "no-store",
        redirect: "error", referrerPolicy: "no-referrer",
        signal: AbortSignal.timeout(120000),
        headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: crypto.randomUUID(), question: question.trim(), corpus }),
      });
      let body: InquiryResult;
      try { body = await response.json() as InquiryResult; }
      catch { throw new Error("Réponse invalide du service EDGE local."); }
      if (!response.ok) {
        const messages: Record<number, string> = {
          400: "Demande ou corpus refusé par EDGE.", 401: "Jeton local incorrect.",
          403: "Origine ou hôte refusé par le service local.", 413: "Corpus trop volumineux (maximum 5 Mio).",
          415: "Le service attend une requête JSON.", 429: "Quota local atteint.",
          503: "Ollama ou son registre de modèle n’est pas prêt.",
        };
        throw new Error(messages[response.status] || "Échec du service EDGE local.");
      }
      setResult(body);
      setStatusMessage("Réponse reçue du moteur local. Les conclusions restent soumises aux validations EDGE.");
    } catch (caught) {
      const err = caught as Error;
      setError(err.name === "TimeoutError" || err.name === "AbortError" ? "L’enquête a dépassé le délai de deux minutes." : err.message || "Le service local est inaccessible.");
    } finally { setRunning(false); }
  }

  return <div className="native-dashboard local-dashboard">
    <section className="dashboard-hero">
      <div><p className="native-eyebrow">EDGE / LOCAL INTELLIGENCE</p><h1>Enquêter sans facturation API.</h1><p className="dashboard-subtitle">Le moteur d’analyse tourne sur ton ordinateur via Ollama. Cette page n’appelle aucun fournisseur IA distant.</p></div>
      <div className="dashboard-stamp"><span className={health.reachable ? "status-dot good" : "status-dot warn"} />{health.reachable ? "SERVICE JOIGNABLE" : "SERVICE HORS LIGNE"}</div>
    </section>
    <div className={health.reachable ? "dashboard-warning local-status-ok" : "dashboard-warning"} role="status">
      <strong>{health.reachable ? "Service local détecté" : "Compagnon local non détecté"}</strong><p>{statusMessage}</p>
      <button type="button" className="local-secondary-button" onClick={() => void checkHealth()} disabled={checking}>{checking ? "Vérification…" : "Vérifier à nouveau"}</button>
    </div>
    <div className="local-layout">
      <section className="local-panel">
        <p className="native-eyebrow">NOUVELLE INVESTIGATION</p><h2>Questionner le corpus EDGE.</h2>
        <p className="local-intro">Importe un corpus réel au format <code>edge.corpus.v1</code>. Le service valide les données avant de les transmettre au modèle.</p>
        <form className="local-form" onSubmit={submit}>
          <label htmlFor="local-token">Jeton du service local</label>
          <input id="local-token" type="password" value={token} onChange={e => setToken(e.target.value)} autoComplete="off" spellCheck={false} minLength={32} required placeholder="Lire data/local/auth.token" />
          <small>Utilisé en mémoire uniquement : jamais enregistré dans le navigateur.</small>
          <label htmlFor="local-question">Question TCG</label>
          <textarea id="local-question" value={question} onChange={e => setQuestion(e.target.value)} maxLength={2000} required rows={5} placeholder="Ex. : Quels signaux d’offre, de demande et de catalyseurs ressortent de ce corpus Pokémon ?" />
          <label htmlFor="local-corpus">Corpus EDGE (JSON)</label>
          <input id="local-corpus" type="file" accept=".json,application/json" required onChange={e => setFile(e.target.files?.[0] ?? null)} />
          <small>Maximum 5 Mio. Le format et les références sont contrôlés côté service.</small>
          <div className="local-form-actions"><button type="submit" disabled={running}>{running ? "Enquête en cours…" : "Lancer l’enquête locale"}</button><span>{file ? file.name : "Aucun corpus sélectionné"}</span></div>
        </form>
        {error && <p className="local-error" role="alert">{error}</p>}
      </section>
      <aside className="local-panel local-limits">
        <p className="native-eyebrow">PÉRIMÈTRE ACTUEL</p><h2>Un compagnon local, pas encore le cloud EDGE.</h2>
        <div><strong>Fournisseur</strong><p>Ollama local uniquement, modèle et licence explicitement configurés.</p></div>
        <div><strong>Quota</strong><p>3 tentatives par jour, enregistrées localement dans SQLite.</p></div>
        <div><strong>Persistance</strong><p>Rapports et historique conservés sur cet ordinateur.</p></div>
        <div><strong>Preuves</strong><p>Une sortie IA ne transforme jamais une affirmation en fait vérifié.</p></div>
        <div><strong>Prérequis navigateur</strong><p>Le serveur doit autoriser l’origine HTTPS exacte de cette prévisualisation. Le navigateur peut également demander l’accès au réseau local.</p></div>
      </aside>
    </div>
    {result && <section className="local-panel local-result">
      <div className="report-heading">
        <div><p className="native-eyebrow">RAPPORT D'INVESTIGATION EDGE</p><h2>{result.report?.subject?.title || "Rapport EDGE"}</h2><p className="report-subtitle">{result.report?.subject?.market || "Marché non précisé"} · {result.report?.subject?.region || "Région non précisée"}{result.report?.subject?.language ? ` · ${result.report.subject.language}` : ""}</p></div>
        <span className="report-status">{result.report?.production_status === "partial" ? "Rapport partiel" : result.report?.production_status || result.status || "Statut inconnu"}</span>
      </div>
      <div className="report-overview-grid">
        <div><small>Créé le</small><strong>{result.report?.created_at ? new Date(result.report.created_at).toLocaleString("fr-FR") : "Non renseigné"}</strong></div>
        <div><small>Données arrêtées au</small><strong>{result.report?.data_as_of ? new Date(result.report.data_as_of).toLocaleString("fr-FR") : "Non renseigné"}</strong></div>
        <div><small>Version</small><strong>{result.report?.report_version ?? "—"}</strong></div>
        <div><small>Nature des données</small><strong>{result.report?.simulated ? "Simulation présente" : "Non simulées selon le rapport"}</strong></div>
      </div>
      <section className="report-section">
        <p className="native-eyebrow">1 · CONCLUSION</p>
        <h3>Ce que le moteur permet de conclure</h3>
        <p>{result.report?.decisions?.edge_decision?.decision === "NOT_EVALUATED" ? "Aucune décision d'investissement EDGE n'a été évaluée. Le rapport présente une analyse, pas une recommandation d'achat." : `Décision EDGE : ${result.report?.decisions?.edge_decision?.decision || "Non renseignée"}.`}</p>
        {result.report?.decisions?.agent_opinion && <div className="report-callout"><strong>Avis analytique du modèle : {result.report.decisions.agent_opinion.stance || "Non précisé"}</strong><p>{result.report.decisions.agent_opinion.rationale || "Aucune justification fournie."}</p><small>Cet avis n'est pas une décision EDGE et ne constitue pas une validation des faits.</small></div>}
      </section>
      <section className="report-section">
        <p className="native-eyebrow">2 · AFFIRMATIONS & PREUVES</p><h3>{result.report?.claims?.length ?? 0} élément(s) analysé(s)</h3>
        {result.report?.claims?.length ? <div className="report-claims">{result.report.claims.map((claim) => {
          const sources = (result.report?.sources || []).filter(source => claim.source_ids?.includes(source.source_id));
          const contradicting = (result.report?.sources || []).filter(source => claim.contradicting_source_ids?.includes(source.source_id));
          return <article className="report-claim" key={claim.claim_id}>
            <div className="report-claim-tags"><span>{KIND_LABEL[claim.kind] || claim.kind}</span><span>{VERIFY_LABEL[claim.verification] || claim.verification}</span><span>Confiance {CONFIDENCE_LABEL[claim.confidence] || claim.confidence}</span></div>
            <p>{claim.statement}</p>
            <small>Auteur : {claim.author === "agent" ? "Modèle IA" : claim.author === "edge_engine" ? "Moteur EDGE" : claim.author === "collector" ? "Collecteur" : "Humain"}{claim.source_claim_type ? ` · Nature chez la source : ${claim.source_claim_type}` : ""}</small>
            {sources.length > 0 && <div className="report-source-links"><strong>Sources à l'appui</strong>{sources.map(source => <div key={source.source_id}><span>{source.publisher} · {source.tier === "primary" ? "Primaire" : source.tier === "secondary" ? "Secondaire" : "Non qualifiée"} · consultée le {source.accessed_at}</span>{safeHttpUrl(source.url) ? <a href={safeHttpUrl(source.url)!} target="_blank" rel="noreferrer">{source.title}</a> : <span>{source.title} · lien non disponible</span>}</div>)}</div>}
            {contradicting.length > 0 && <div className="report-conflict"><strong>Sources contradictoires</strong>{contradicting.map(source => <span key={source.source_id}>{source.publisher} : {source.title}</span>)}</div>}
            {claim.basis && <small>Fondement de l'interprétation : {claim.basis.fact_claim_ids.length} fait(s) · {claim.basis.computation_ids.length} calcul(s) EDGE.</small>}
          </article>;
        })}</div> : <p>{result.reason || "Aucune affirmation exploitable dans le rapport."}</p>}
      </section>
      <section className="report-section">
        <p className="native-eyebrow">3 · DONNÉES DE MARCHÉ</p><h3>{result.report?.datasets?.length ?? 0} jeu(x) de données</h3>
        {result.report?.datasets?.length ? <div className="report-datasets">{result.report.datasets.map(dataset => <article key={dataset.dataset_id}><strong>{dataset.title}</strong><span>{MEASURE_LABEL[dataset.measure] || dataset.measure} · {dataset.territory} · {dataset.period.start} → {dataset.period.end}</span><small>{dataset.points.filter(point => point.value !== null).length} point(s) renseigné(s) sur {dataset.points.length} · {dataset.currency || dataset.unit}</small></article>)}</div> : <p>Aucun jeu de données chiffré exploitable dans ce rapport.</p>}
        <div className="report-callout"><strong>Prix affichés et ventes réalisées restent séparés.</strong><p>{result.report?.economics?.listed_price_dataset_ids?.length ?? 0} jeu(x) de prix affichés · {result.report?.economics?.realized_sale_dataset_ids?.length ?? 0} jeu(x) de ventes conclues. La présence d'un jeu de données ne prouve pas à elle seule la qualité de chaque transaction.</p></div>
        {result.report?.computations?.length ? <div className="report-datasets">{result.report.computations.map(item => <article key={item.computation_id}><strong>{item.method === "pct_change" ? "Variation calculée" : item.method} · {item.result.toLocaleString("fr-FR")} {item.unit}</strong><span>{item.t_from} → {item.t_to}</span><small>Calcul exécuté par EDGE · {item.dataset_id}</small></article>)}</div> : null}
      </section>
      <section className="report-section">
        <p className="native-eyebrow">4 · COUVERTURE DE L'ENQUÊTE</p><h3>Spécialistes et limites</h3>
        {result.dossier?.agent_team?.execution_trace?.task_results?.length ? <div className="report-datasets">{result.dossier.agent_team.execution_trace.task_results.map((task, index) => <article key={task.agent_id + index}><strong>{task.agent_id}</strong><span>{task.status === "not_configured" ? "Spécialiste non connecté" : task.status === "completed" ? "Exécution terminée" : task.status}</span><small>{task.mode === "mock" ? "Simulation technique, aucun constat produit." : task.mode === "real" ? `${task.findings?.length ?? 0} constat(s) transmis` : "Aucun adaptateur réel disponible."}</small>{task.limitations?.map((limitation, i) => <small key={i}>{limitation}</small>)}</article>)}</div> : <p>Aucune trace de spécialiste disponible.</p>}
        <div className="report-overview-grid"><div><small>Questions sans réponse</small><strong>{result.dossier?.unknowns?.length ?? 0}</strong></div><div><small>Contradictions recensées</small><strong>{(result.dossier?.contradictions?.length ?? 0) + (result.dossier?.agent_team?.execution_trace?.contradictions?.length ?? 0)}</strong></div></div>
        {result.dossier?.unknowns?.length ? <p>À approfondir : {result.dossier.unknowns.join(", ")}</p> : null}
      </section>
      <section className="report-section">
        <p className="native-eyebrow">5 · PROCHAINES ÉTAPES</p><h3>Ce qui manque avant une décision</h3>
        <ul className="report-next-steps">
          {!result.report?.sources?.length && <li>Ajouter des sources identifiables et datées.</li>}
          {!result.report?.datasets?.length && <li>Collecter des données de marché horodatées.</li>}
          {(result.report?.economics?.realized_sale_dataset_ids?.length ?? 0) === 0 && <li>Rechercher des ventes conclues comparables ; ne pas assimiler les annonces à des transactions.</li>}
          {result.report?.economics?.availability?.buyable_verified !== true && <li>Vérifier la disponibilité réelle et le prix d'entrée exécutable.</li>}
          {result.report?.economics?.fees?.verified !== true && <li>Établir les frais d'acquisition, de vente, d'expédition et de grading applicables.</li>}
          {(result.report?.economics?.liquidity?.claim_ids?.length ?? 0) === 0 && <li>Documenter la liquidité avec des transactions et volumes comparables.</li>}
          {(result.dossier?.unknowns?.length ?? 0) > 0 && <li>Compléter les sous-questions restées sans données.</li>}
          {result.report?.production_status !== "complete" && <li>Le rapport est incomplet : approfondir et faire vérifier les éléments avant toute décision.</li>}
        </ul>
      </section>
      {result.violations?.length ? <section className="report-section"><p className="native-eyebrow">CONTRÔLES</p><h3>Éléments rejetés ou refusés</h3><ul>{result.violations.map((item, i) => <li key={i}>{item}</li>)}</ul></section> : null}
      <p className="report-final-note">Ce rapport décrit l'état des informations au moment de l'enquête. Les éléments non vérifiés restent des pistes d'analyse, pas des faits établis. Fiabilité non vérifiée lorsque les preuves sont insuffisantes.</p>
      {result.usage && <small>Quota : {result.usage.limit ?? "?"} tentatives / jour · {result.usage.period_utc || "période UTC"}</small>}
    </section>}
    <section className="dashboard-method"><p className="native-eyebrow">SÉCURITÉ & LIMITES</p><h2>Ce que cette page ne fait pas.</h2><div className="method-grid"><div><strong>Aucun accès distant</strong><p>Les requêtes sont limitées à 127.0.0.1:8765. Le jeton reste en mémoire et les requêtes n’envoient pas de cookies.</p></div><div><strong>Aucune donnée fabriquée</strong><p>Pas de prix synthétiques ni de ventes inventées. Le moteur doit référencer les éléments présents dans le corpus.</p></div><div><strong>Aucun paiement</strong><p>Cette passerelle ne crée ni compte cloud, ni abonnement Premium, ni facturation.</p></div></div></section>
    <footer className="native-footer">EDGE · Le modèle local ne vérifie pas indépendamment les sources. Toute information non corroborée reste qualifiée comme telle.</footer>
  </div>;
}
