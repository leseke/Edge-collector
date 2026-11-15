import { checkLocalEdgeStatus, runLocalEdgeInquiry } from "../assets/edge-local.mjs";

const statusNode = document.getElementById("local-status");
const form = document.getElementById("inquiry-form");
const submitButton = document.getElementById("run-inquiry");
const checkButton = document.getElementById("check-local");
const resultSection = document.getElementById("inquiry-result");
const resultContent = document.getElementById("result-content");

function setStatus(kind, title, detail) {
  statusNode.className = "notice" + (kind === "ok" ? " good" : kind === "bad" ? " bad" : "");
  statusNode.replaceChildren();
  const strong = document.createElement("strong");
  strong.textContent = title;
  const p = document.createElement("p");
  p.textContent = detail;
  statusNode.append(strong, p);
}

async function refreshStatus() {
  checkButton.disabled = true;
  try {
    const state = await checkLocalEdgeStatus();
    if (!state.reachable) {
      setStatus("bad", "Service local inaccessible", "Lance intelligence.local_service sur cet ordinateur et autorise explicitement l'origine exacte du site EDGE.");
    } else if (state.status === "configured") {
      setStatus("ok", "Configuration du modèle vérifiée", "Le registre local contient une entrée de licence autorisée. La disponibilité réelle du démon Ollama sera confirmée lors de l'enquête.");
    } else if (state.status === "model_disabled") {
      setStatus("warn", "Modèle local désactivé", "EDGE_LOCAL_LLM_ENABLED doit être activé après vérification de la licence du modèle.");
    } else {
      setStatus("warn", "Modèle local non configuré", "Vérifie le nom exact du modèle, son registre de licence et son empreinte SHA-256.");
    }
  } finally {
    checkButton.disabled = false;
  }
}

function addText(parent, tag, value) {
  const node = document.createElement(tag);
  node.textContent = String(value);
  parent.append(node);
  return node;
}

function renderResult(result) {
  resultSection.hidden = false;
  resultContent.replaceChildren();
  addText(resultContent, "p", "Statut EDGE : " + (result.status || "inconnu"));
  if (result.report && typeof result.report === "object") {
    const report = result.report;
    addText(resultContent, "h3", report.subject?.title || "Rapport EDGE");
    addText(resultContent, "p", "Production : " + (report.production_status || "non précisée"));
    const claims = Array.isArray(report.claims) ? report.claims : [];
    addText(resultContent, "p", claims.length + " affirmation(s) / élément(s) analysé(s).");
    if (claims.length) {
      const list = document.createElement("ul");
      for (const claim of claims) {
        const item = document.createElement("li");
        const statement = document.createElement("span");
        statement.textContent = claim.statement || "Élément sans texte.";
        const verification = document.createElement("small");
        verification.textContent = "Qualification : " + (claim.verification || "non précisée")
          + " · Type : " + (claim.kind || "non précisé");
        item.append(statement, verification);
        list.append(item);
      }
      resultContent.append(list);
    }
  } else if (result.reason) {
    addText(resultContent, "p", result.reason);
  }
  if (Array.isArray(result.violations) && result.violations.length) {
    addText(resultContent, "h3", "Contrôles");
    for (const violation of result.violations) addText(resultContent, "p", violation);
  }
  if (result.usage) {
    addText(resultContent, "small", "Quota : " + result.usage.limit + " tentatives / jour · " + result.usage.period_utc);
  }
}

checkButton.addEventListener("click", refreshStatus);
form.addEventListener("submit", async event => {
  event.preventDefault();
  submitButton.disabled = true;
  resultSection.hidden = false;
  resultContent.replaceChildren();
  addText(resultContent, "p", "Enquête en cours…");
  try {
    const token = document.getElementById("local-token").value;
    const question = document.getElementById("local-question").value;
    const file = document.getElementById("local-corpus").files?.[0];
    if (!file) throw new Error("Sélectionne un fichier corpus JSON.");
    if (file.size < 1 || file.size > 5 * 1024 * 1024) {
      throw new Error("Le corpus doit peser entre 1 octet et 5 Mio.");
    }
    let corpus;
    try {
      corpus = JSON.parse(await file.text());
    } catch {
      throw new Error("Le fichier sélectionné n'est pas un JSON valide.");
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);
    let result;
    try {
      result = await runLocalEdgeInquiry({
        token,
        requestId: crypto.randomUUID(),
        question,
        corpus,
        signal: controller.signal
      });
    } finally {
      clearTimeout(timeout);
    }
    renderResult(result);
  } catch (error) {
    resultContent.replaceChildren();
    addText(resultContent, "p", error?.name === "AbortError"
      ? "L'enquête a dépassé le délai de deux minutes."
      : (error?.message || "L'enquête locale a échoué."));
  } finally {
    submitButton.disabled = false;
  }
});

refreshStatus();
