// Public navigation pointer only, not an authentication token or data source.
// The destination Worker enforces independent Cloudflare Access JWT checks.
export function verifiedOutlookOffersUrl(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 2048) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !url.hostname ||
        url.username || url.password || url.port ||
        url.pathname !== "/internal/outlook/offers" ||
        url.search || url.hash) return null;
    return url.toString();
  } catch {
    return null;
  }
}
