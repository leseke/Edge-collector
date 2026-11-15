"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

type Health = { reachable: boolean; status: string; provider?: string | null };
type InquiryResult = {
  status?: string;
  reason?: string;
  report?: {
    subject?: { title?: string };
    production_status?: string;
    claims?: Array<{ statement?: string; verification?: string; kind?: string }>;
  };
  violations?: string[];
  usage?: { limit?: number; period_utc?: string };
};
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
      <p className="native-eyebrow">RÉSULTAT DE L'ENQUÊTE</p><h2>{result.report?.subject?.title || "Rapport EDGE"}</h2>
      <p>Statut EDGE : <strong>{result.status || "Non précisé"}</strong> · Production : <strong>{result.report?.production_status || "Non précisée"}</strong></p>
      <h3>{result.report?.claims?.length ?? 0} affirmation(s) analysée(s)</h3>
      {result.report?.claims?.length ? <ul>{result.report.claims.map((claim, i) => <li key={i}><p>{claim.statement || "Élément sans texte."}</p><small>Qualification : {claim.verification || "non précisée"} · Type : {claim.kind || "non précisé"}</small></li>)}</ul> : <p>{result.reason || "Aucune affirmation exploitable dans le rapport."}</p>}
      {result.violations?.length ? <div><h3>Contrôles</h3><ul>{result.violations.map((item, i) => <li key={i}>{item}</li>)}</ul></div> : null}
      {result.usage && <small>Quota : {result.usage.limit ?? "?"} tentatives / jour · {result.usage.period_utc || "période UTC"}</small>}
    </section>}
    <section className="dashboard-method"><p className="native-eyebrow">SÉCURITÉ & LIMITES</p><h2>Ce que cette page ne fait pas.</h2><div className="method-grid"><div><strong>Aucun accès distant</strong><p>Les requêtes sont limitées à 127.0.0.1:8765. Le jeton reste en mémoire et les requêtes n’envoient pas de cookies.</p></div><div><strong>Aucune donnée fabriquée</strong><p>Pas de prix synthétiques ni de ventes inventées. Le moteur doit référencer les éléments présents dans le corpus.</p></div><div><strong>Aucun paiement</strong><p>Cette passerelle ne crée ni compte cloud, ni abonnement Premium, ni facturation.</p></div></div></section>
    <footer className="native-footer">EDGE · Le modèle local ne vérifie pas indépendamment les sources. Toute information non corroborée reste qualifiée comme telle.</footer>
  </div>;
}
