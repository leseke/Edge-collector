import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { advanceCoverage } from "../src/gcc-coverage.ts";

test("coverage deduplicates across pages, survives retries, and retains the last confirmed completion", async () => {
  const sqlite = new DatabaseSync(":memory:");
  sqlite.exec(readFileSync(new URL("../schema.sql", import.meta.url), "utf8"));
  sqlite.exec(readFileSync(new URL("../migrations/011_gcc_lot_images.sql", import.meta.url), "utf8"));
  const db = {
    prepare(sql) { return { bind(...args) { const stmt = sqlite.prepare(sql);
      return { run: () => stmt.run(...args), first: () => stmt.get(...args) }; } }; },
    batch(stmts) { sqlite.exec("BEGIN"); try { for (const stmt of stmts) stmt.run(); sqlite.exec("COMMIT"); }
      catch (error) { sqlite.exec("ROLLBACK"); throw error; } },
  };
  const row = n => ({ id: "01234567-89ab-4cde-8fab-" + String(n).padStart(12,"0"), item: {
    title: "Carte", rectoImageKey: "item/photo-"+n, collectible: { category: "Pokemon" } }, status: "SOLD" });
  const page = (currentPage, nextCursor, ids, total) => async () => Response.json({
    info: { currentPage, nextCursor, counts: { total } }, results: ids.map(row),
  });
  const read = () => sqlite.prepare("SELECT * FROM gcc_coverage").get();
  const first = page(1,"valid_cursor_2",[1,2],3);
  await Promise.all([advanceCoverage(db,"closed",first),advanceCoverage(db,"closed",first)]);
  assert.equal(read().observed,2);
  await assert.rejects(advanceCoverage(db,"closed",async () => new Response(null,{ status:503 })));
  assert.equal(read().page,1);
  await advanceCoverage(db,"closed",page(2,null,[2,3]));
  assert.equal(read().observed,3);
  assert.equal(sqlite.prepare("SELECT count(*) AS n FROM gcc_lot_images").get().n,3);
  assert.match(sqlite.prepare("SELECT image_url FROM gcc_lot_images ORDER BY lot_id LIMIT 1").get().image_url,/\/item\/photo-1$/);
  assert.throws(()=>sqlite.exec("DELETE FROM gcc_lot_images"),/immutable_lot_image/);
  const completed = read().last_complete;
  assert.ok(completed);
  await advanceCoverage(db,"closed",page(1,null,[4],7));
  assert.equal(read().observed,1);
  assert.equal(read().last_complete,completed);
  sqlite.close();
});
