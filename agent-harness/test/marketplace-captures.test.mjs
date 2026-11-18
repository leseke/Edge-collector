import assert from "node:assert/strict";
import test from "node:test";
import { readMarketplaceCaptures } from "../../app/lib/marketplace-captures.ts";
const common = {
  cardVariant: "swsh7-215:fr:unlimited:pca:9", day: "2026-11-18", platform: "vinted",
  searchUrl: "https://www.vinted.fr/catalog?search_text=noctali",
  activeListingUrls: ["https://www.vinted.fr/items/123-noctali", "https://www.vinted.fr/items/123?ref=other"],
};
test("deduplicates direct listing URLs within a reviewed variant and search scope", () => {
  assert.deepEqual(readMarketplaceCaptures([common], common.cardVariant), [{
    day: "2026-11-18", scope: common.searchUrl, listingIds: ["vinted:123"],
  }]);
  assert.deepEqual(readMarketplaceCaptures([common], "other"), []);
});
test("rejects invalid captures and keeps an explicitly reviewed empty capture", () => {
  for (const capture of [
    { ...common, day: "2026-02-31" },
    { ...common, searchUrl: "https://example.com/catalog?search_text=noctali" },
    { ...common, activeListingUrls: [common.searchUrl] },
  ]) assert.deepEqual(readMarketplaceCaptures([capture], common.cardVariant), []);
  assert.deepEqual(readMarketplaceCaptures([{ ...common, activeListingUrls: [] }], common.cardVariant)[0].listingIds, []);
});
