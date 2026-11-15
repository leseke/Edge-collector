/** Browser transport for the EDGE Local Companion.
 *
 * The token is passed by the caller and is never persisted by this module.
 * The endpoint is fixed to loopback; callers cannot provide arbitrary URLs.
 */
const BASE = "http://127.0.0.1:8765";

export async function checkLocalEdgeStatus() {
  let response;
  try {
    response = await fetch(BASE + "/health", {
      method: "GET",
      mode: "cors",
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer"
    });
  } catch {
    return { reachable: false, status: "unreachable" };
  }
  if (!response.ok) return { reachable: false, status: "unavailable" };
  const body = await response.json();
  return {
    reachable: true,
    status: body.status === "ready" ? "ready" : "model_disabled",
    provider: body.provider === "ollama_local" ? body.provider : null
  };
}

export async function runLocalEdgeInquiry({ token, requestId, question, corpus, signal }) {
  if (typeof token !== "string" || token.length < 32) {
    throw new TypeError("Jeton local EDGE invalide.");
  }
  if (typeof requestId !== "string" || !requestId.trim() || requestId.length > 128) {
    throw new TypeError("Identifiant de requête invalide.");
  }
  if (typeof question !== "string" || !question.trim() || question.length > 2000) {
    throw new TypeError("Question invalide.");
  }
  if (!corpus || typeof corpus !== "object" || Array.isArray(corpus)) {
    throw new TypeError("Corpus EDGE invalide.");
  }

  let response;
  try {
    response = await fetch(BASE + "/v1/inquiry", {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
      signal,
      headers: {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ request_id: requestId, question, corpus })
    });
  } catch {
    throw new Error("Le service EDGE local est inaccessible ou son accès réseau local a été refusé.");
  }

  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error("Réponse invalide du service EDGE local.");
  }
  if (!response.ok) {
    const messages = {
      400: "La demande ou le corpus a été refusé par EDGE.",
      401: "Jeton local EDGE incorrect.",
      403: "Origine ou hôte refusé par le service local.",
      413: "Corpus trop volumineux (maximum 5 Mio).",
      415: "Le service attend une requête JSON.",
      429: "Quota local EDGE atteint.",
      503: "Ollama ou son registre de modèle n'est pas prêt."
    };
    throw new Error(messages[response.status] || "Échec du service EDGE local.");
  }
  return body;
}
