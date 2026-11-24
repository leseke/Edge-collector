import { prepareOpportunityEvents } from "./gcc-opportunity-memory";
import { resaleFeePercent } from "../../../app/lib/listing-analysis";
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
  if (kind === "fixed") {
    const events = await prepareOpportunityEvents(db, page.items, now.toISOString());
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_opportunity_events
      (lot_id,cycle,page,observed_at,variant_key,title,asking_cents,median_cents,comparable_count,headroom_cents,status,evidence_json,resale_fee_percent)
      SELECT json_extract(value,'$.id'),?,?,?,json_extract(value,'$.variant'),json_extract(value,'$.title'),
      json_extract(value,'$.ask'),json_extract(value,'$.median'),json_extract(value,'$.count'),json_extract(value,'$.headroom'),
      json_extract(value,'$.status'),json_extract(value,'$.evidence'),? FROM json_each(?) WHERE ${exists}`)
      .bind(state.cycle + Number(Boolean(state.finished)),page.page,now.toISOString(),resaleFeePercent,JSON.stringify(events),...args));
  }
  const count = "(SELECT count(*) FROM gcc_coverage_ids WHERE kind=?)";
  const announced = first ? page.total : state.announced;
  // A missing lot is only a visibility observation after a count-matched full cycle.
  // Only previously observed lots qualify; absence is never a paid-sale assertion.
  if (kind === "fixed") {
    const cycle = state.cycle + Number(Boolean(state.finished));
    const seen = JSON.stringify(page.items.map(item => item.id));
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_lifecycle_events(lot_id,cycle,observed_at,event)
      SELECT value,?,?,'FIRST_SEEN' FROM json_each(?) WHERE ${exists}
      AND NOT EXISTS (SELECT 1 FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.lot_id=value AND (o.cycle<? OR (o.cycle=? AND o.page<?)))`)
      .bind(cycle,now.toISOString(),seen,...args,cycle,cycle,page.page));
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_lifecycle_events(lot_id,cycle,observed_at,event)
      SELECT value,?,?,'REAPPEARED' FROM json_each(?) WHERE ${exists}
      AND (SELECT event FROM gcc_lifecycle_events e WHERE e.lot_id=value AND e.cycle<? ORDER BY e.cycle DESC LIMIT 1)='NOT_SEEN'`)
      .bind(cycle,now.toISOString(),seen,...args,cycle));
    if (!page.nextCursor && announced !== null && cycle > 1) {
      batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_lifecycle_events(lot_id,cycle,observed_at,event)
        SELECT DISTINCT o.lot_id,?,?,'NOT_SEEN' FROM gcc_offer_observations o
        WHERE o.kind='fixed' AND o.cycle=? AND ${exists}
        AND (SELECT count(*) FROM gcc_coverage_ids WHERE kind='fixed')=?
        AND NOT EXISTS (SELECT 1 FROM gcc_coverage_ids i WHERE i.kind='fixed' AND i.lot_id=o.lot_id)
        AND NOT EXISTS (SELECT 1 FROM paid_market_sales s WHERE s.lot_id='gcc-'||o.lot_id)`)
        .bind(cycle,now.toISOString(),cycle-1,...args,announced));
    }
  }
  if (kind === "fixed") {
    const cycle = state.cycle + Number(Boolean(state.finished));
    // Compare with the last alerted price as well as the previous evaluation:
    // a series of small reductions can accumulate into a meaningful signal.
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_research_alerts
      (lot_id,cycle,page,observed_at,reason,asking_cents,previous_cents,status)
      WITH candidates AS (
        SELECT e.*,
          (SELECT p.status FROM gcc_opportunity_events p WHERE p.lot_id=e.lot_id
           AND (p.cycle<e.cycle OR (p.cycle=e.cycle AND p.page<e.page))
           ORDER BY p.cycle DESC,p.page DESC LIMIT 1) AS prior_status,
          (SELECT a.asking_cents FROM gcc_research_alerts a WHERE a.lot_id=e.lot_id
           ORDER BY a.cycle DESC,a.page DESC LIMIT 1) AS alerted_price,
          (SELECT p.asking_cents FROM gcc_opportunity_events p WHERE p.lot_id=e.lot_id
           AND (p.cycle<e.cycle OR (p.cycle=e.cycle AND p.page<e.page))
           ORDER BY p.cycle DESC,p.page DESC LIMIT 1) AS prior_price
        FROM gcc_opportunity_events e WHERE e.cycle=? AND e.page=? AND ${exists}
      ), classified AS (
        SELECT *, CASE
          WHEN status='INVESTIGATE' AND alerted_price IS NULL THEN 'NEW_OPPORTUNITY'
          WHEN status='INVESTIGATE' AND prior_status IS NOT NULL AND prior_status<>'INVESTIGATE' THEN 'STATUS_IMPROVED'
          WHEN status IN ('INVESTIGATE','THIN_MARGIN') AND EXISTS (
            SELECT 1 FROM gcc_lifecycle_events l WHERE l.lot_id=candidates.lot_id AND l.cycle=candidates.cycle AND l.event='REAPPEARED'
          ) AND NOT EXISTS (SELECT 1 FROM gcc_research_alerts a WHERE a.lot_id=candidates.lot_id AND a.cycle=candidates.cycle AND a.reason='REAPPEARED') THEN 'REAPPEARED'
          WHEN COALESCE(alerted_price,prior_price)-asking_cents>=500
            AND asking_cents<=COALESCE(alerted_price,prior_price)*0.9 THEN 'PRICE_DROP'
        END AS alert_reason FROM candidates
      )
      SELECT lot_id,cycle,page,observed_at,alert_reason,asking_cents,
        CASE WHEN alert_reason='PRICE_DROP' THEN COALESCE(alerted_price,prior_price) ELSE prior_price END,status
      FROM classified WHERE alert_reason IS NOT NULL`)
      .bind(cycle,page.page,...args));
  }
  if (kind !== "closed" && !page.nextCursor && announced !== null) {
    const cycle = state.cycle + Number(Boolean(state.finished));
    // Verify the observation archive itself contains every distinct lot, including
    // cycles that started before the observation migration was activated.
    batch.push(db.prepare(`INSERT OR IGNORE INTO gcc_complete_cycles(kind,cycle,completed_at,announced)
      SELECT ?,?,?,? WHERE ${exists}
      AND (SELECT COUNT(*) FROM gcc_coverage_ids WHERE kind=?)=?
      AND (SELECT COUNT(DISTINCT lot_id) FROM gcc_offer_observations WHERE kind=? AND cycle=?)=?`)
      .bind(kind,cycle,now.toISOString(),announced,...args,kind,announced,kind,cycle,announced));
  }
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
