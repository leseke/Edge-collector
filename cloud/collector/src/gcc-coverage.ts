import { gccCursor, gccPageUrl, readGccPage, type GccListingKind } from "../../../app/lib/gcc-active-listings.ts";
import { readBoundedText } from "./bounded.mjs";

type State = { cycle: number; page: number; cursor: string | null; announced: number | null; finished: number };

export async function advanceCoverage(db: D1Database, kind: GccListingKind, request = fetch, now = new Date()) {
  await db.prepare("INSERT OR IGNORE INTO gcc_coverage(kind) VALUES (?)").bind(kind).run();
  const state = await db.prepare("SELECT * FROM gcc_coverage WHERE kind=?").bind(kind).first<State>();
  if (!state) throw new Error("coverage_state_missing");
  const first = !state.page || Boolean(state.finished);
  const response = await request(gccPageUrl(kind, first ? null : state.cursor), {
    headers: { Accept: "application/json" }, redirect: "error", signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error("coverage_source_unavailable");
  const raw = JSON.parse(await readBoundedText(response, 1_500_000));
  const page = readGccPage(raw, kind, now);
  const expectedPage = first ? 1 : state.page + 1;
  if (page.page !== expectedPage || (raw.info.nextCursor != null && !gccCursor(raw.info.nextCursor)) ||
      (raw.info.nextPage != null && (!page.nextCursor || raw.info.nextPage !== page.page + 1)) ||
      (page.nextCursor && page.nextCursor === state.cursor)) throw new Error("coverage_invalid_page");

  // All writes use the same checkpoint. A concurrent reader of the old page becomes a no-op.
  const guard = "kind=? AND cycle=? AND page=?";
  const args = [kind, state.cycle, state.page];
  const exists = "EXISTS (SELECT 1 FROM gcc_coverage WHERE " + guard + ")";
  const batch = [];
  if (first) batch.push(db.prepare("DELETE FROM gcc_coverage_ids WHERE kind=? AND " + exists).bind(kind, ...args));
  batch.push(db.prepare("INSERT OR IGNORE INTO gcc_coverage_ids(kind,lot_id) SELECT ?,value FROM json_each(?) WHERE " + exists)
    .bind(kind, JSON.stringify(page.items.map(item => item.id)), ...args));
  if (kind !== "closed") {
    const observations = page.items.map(item => ({ ...item, source: "https://gradedcardcenter.com/item/" + item.id }));
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_offer_observations
      (kind,lot_id,observed_at,cycle,page,variant_key,title,price_cents,ends_at,source_url)
      SELECT ?,json_extract(value,'$.id'),?,?,?,json_extract(value,'$.variantKey'),json_extract(value,'$.title'),
      json_extract(value,'$.cents'),json_extract(value,'$.ends'),json_extract(value,'$.source')
      FROM json_each(?) WHERE ${exists}`)
      .bind(kind, now.toISOString(), state.cycle + Number(Boolean(state.finished)), page.page, JSON.stringify(observations), ...args));
  }
  const count = "(SELECT count(*) FROM gcc_coverage_ids WHERE kind=?)";
  const announced = first ? page.total : state.announced;
  batch.push(db.prepare(`UPDATE gcc_coverage SET cycle=?,page=?,cursor=?,announced=?,observed=${count},checked_at=?,finished=?,
    last_complete=CASE WHEN ? AND ${count}=? THEN ? ELSE last_complete END WHERE ${guard}`)
    .bind(state.cycle + Number(Boolean(state.finished)), page.page, page.nextCursor, announced, kind, now.toISOString(),
      Number(!page.nextCursor), Number(!page.nextCursor), kind, announced, now.toISOString(), ...args));
  await db.batch(batch);
  return Boolean(page.nextCursor);
}

export async function collectCoverage(db: D1Database) {
  await Promise.all((["closed", "fixed", "auction"] as const).map(async kind => {
    for (let page = 0; page < 4; page++) if (!await advanceCoverage(db, kind)) break;
  }));
}
