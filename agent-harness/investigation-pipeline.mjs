import { normalizeD1Export } from "./export-d1.mjs";
import { prepareInvestigationBrief } from "./agent-brief.mjs";
import { reviewInvestigation } from "./investigation-review.mjs";

const MAX_RESPONSE_BYTES = 48_000;
const MAX_PRODUCTS = 20;

/**
 * Pure, injected model boundary. The caller owns the provider and any costs.
 * No network, secrets, persistence or purchase capability in this module.
 * An error for one product does not abort the other investigations.
 */
export async function runInvestigations(trustedExport, generate, options = {}) {
  if (typeof generate !== "function") throw new Error("missing_model_adapter");
  const now = options.now ?? new Date().toISOString();
  const rows = normalizeD1Export(trustedExport);
  const allProductIds = [...new Set(rows.map(r => r.product_id))].sort();
  const cursor = options.cursor ?? 0;
  if (!Number.isSafeInteger(cursor) || cursor < 0 || cursor > allProductIds.length) throw new Error("invalid_cursor");
  const maxProducts = options.maxProducts ?? MAX_PRODUCTS;
  if (!Number.isSafeInteger(maxProducts) || maxProducts < 1 || maxProducts > MAX_PRODUCTS) throw new Error("invalid_product_limit");
  const productIds = allProductIds.slice(cursor, cursor + maxProducts);
  const results = [];
  for (const productId of productIds) {
    try {
      const brief = prepareInvestigationBrief(trustedExport, productId, now);
      const response = await generate(structuredClone(brief));
      const serialized = typeof response === "string" ? response : JSON.stringify(response);
      if (typeof serialized !== "string" || Buffer.byteLength(serialized, "utf8") > MAX_RESPONSE_BYTES) throw new Error("oversized_model_response");
      const parsed = typeof response === "string" ? JSON.parse(response) : response;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("invalid_model_response");
      if (parsed.productId !== productId) throw new Error("product_scope_violation");
      const reviewed = reviewInvestigation(parsed, trustedExport, now);
      results.push({ productId, status: reviewed.status, review: reviewed });
    } catch (error) {
      // Only publish a bounded, categorical error, never raw model output or credentials.
      const category = error?.message;
      const safe = new Set(["oversized_model_response","invalid_model_response","product_scope_violation"]);
      results.push({ productId, status: "FAILED_CLOSED", errorCode: safe.has(category) ? category : "MODEL_OR_VALIDATION_ERROR", purchaseAuthorized: false });
    }
  }
  return {
    schemaVersion: 1,
    processedProducts: results.length,
    remainingProducts: Math.max(0, allProductIds.length - cursor - productIds.length),
    nextCursor: cursor + productIds.length < allProductIds.length ? cursor + productIds.length : null,
    results,
    purchaseAuthorized: false,
    modelInvocation: "INJECTED_ADAPTER",
  };
}
