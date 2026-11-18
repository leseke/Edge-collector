import type { ListingPage } from "./fixed-offer-ranking";

export async function scanFixedOffers(read: (cursor: string | null) => Promise<ListingPage | null>) {
  const items = new Map<string, ListingPage["items"][number]>();
  const visited = new Set<string>();
  const deadline = Date.now() + 10_000;
  let cursor: string | null = null;
  let pages = 0;
  let oldest = "";
  let status: "end" | "partial" | "limit" = "limit";
  while (pages < 8 && Date.now() < deadline) {
    const page = await read(cursor);
    if (!page || page.page !== pages + 1) { status = "partial"; break; }
    pages++;
    if (!oldest || page.checkedAt < oldest) oldest = page.checkedAt;
    for (const item of page.items) items.set(item.id, item);
    cursor = page.nextCursor;
    if (!cursor) { status = "end"; break; }
    if (visited.has(cursor)) { status = "partial"; break; }
    visited.add(cursor);
  }
  return { items: [...items.values()], pages, oldest, status };
}
