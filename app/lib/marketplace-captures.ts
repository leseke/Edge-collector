export type ReviewedMarketplaceCapture = {
  cardVariant: string;
  day: string;
  platform: "vinted" | "leboncoin";
  searchUrl: string;
  activeListingUrls: string[];
};

function canonicalListingId(value: string, platform: ReviewedMarketplaceCapture["platform"]) {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.port) return null;
    const vinted = platform === "vinted";
    const domain = vinted ? "vinted.fr" : "leboncoin.fr";
    if (url.hostname !== domain && url.hostname !== "www." + domain) return null;
    const match = url.pathname.match(vinted ? /^\/items\/(\d+)(?:-[^/]+)?\/?$/ : /^\/ad\/[^/]+\/(\d+)\/?$/);
    return match ? `${platform}:${match[1]}` : null;
  } catch { return null; }
}

export function readMarketplaceCaptures(captures: ReviewedMarketplaceCapture[], cardVariant: string) {
  return captures.filter(capture => capture.cardVariant === cardVariant).flatMap(capture => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(capture.day)) return [];
    const day = new Date(capture.day + "T00:00:00Z");
    if (!Number.isFinite(+day) || day.toISOString().slice(0, 10) !== capture.day) return [];
    if (capture.platform !== "vinted" && capture.platform !== "leboncoin") return [];
    const platform = capture.platform;
    const domain = platform === "vinted" ? "www.vinted.fr" : "www.leboncoin.fr";
    let scope: string;
    try {
      const url = new URL(capture.searchUrl);
      if (url.origin !== "https://" + domain || url.username || url.password ||
          url.pathname !== (platform === "vinted" ? "/catalog" : "/recherche")) return [];
      const query = url.searchParams.get(platform === "vinted" ? "search_text" : "text");
      if (!query?.trim()) return [];
      url.searchParams.sort();
      scope = url.origin + url.pathname + url.search;
    } catch { return []; }
    const ids = capture.activeListingUrls.map(url => canonicalListingId(url, platform));
    const valid = ids.filter((id): id is string => id !== null);
    if (valid.length !== ids.length) return [];
    return [{ day: capture.day, scope, listingIds: [...new Set(valid)] }];
  });
}

// Populate only after reviewing a dated search capture against the exact card variant.
export const reviewedMarketplaceCaptures: ReviewedMarketplaceCapture[] = [];
