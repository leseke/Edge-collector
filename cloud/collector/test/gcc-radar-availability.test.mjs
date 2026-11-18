import assert from "node:assert/strict";
import test from "node:test";
import { readGccActiveListings } from "../../../app/lib/gcc-active-listings.ts";

const now = new Date("2026-11-18T19:04:00Z");
const card = (button, extra = "", metadata = "Pokemon • French • 2021 • Poing de Fusion • #157/264") => `
<div class="bg-surface-2 relative flex flex-col overflow-hidden rounded-[10px] h-full">
  <a href="/item/01234567-89ab-4cde-8fab-0123456789ab"></a>
  <p class="text-base font-semibold text-white truncate">Ectoplasma &amp; VMAX</p>
  <p class="text-[11px] font-medium text-gray-100 truncate">${metadata}</p>
  <p class="text-2xl font-semibold text-white">1'250,50€</p>
  ${extra}${button}
</div>`;

test("fixed-price offers preserve the variant and reject other games or inactive buttons", () => {
  const [offer] = readGccActiveListings(card("<button>Acheter</button>"), "fixed", now);
  assert.equal(offer.cents, 125050);
  assert.equal(offer.title, "Ectoplasma & VMAX");
  assert.match(offer.variant, /^Français/);
  assert.equal(offer.ends, null);
  assert.deepEqual(readGccActiveListings(card("<button disabled>Acheter</button>"), "fixed", now), []);
  assert.deepEqual(readGccActiveListings(card("<button>Acheter</button>", "", "Magic • French"), "fixed", now), []);
});

test("auctions require an open action and a future Paris time", () => {
  const listing = end => card("<button>Enchérir</button>", "7 enchères • Fin le " + end);
  assert.equal(readGccActiveListings(listing("18/11 @ 20h05"), "auction", now)[0].ends, "18/11 @ 20h05");
  assert.deepEqual(readGccActiveListings(listing("18/11 @ 20h04"), "auction", now), []);
  assert.deepEqual(readGccActiveListings(listing("31/11 @ 20h09"), "auction", now), []);
  assert.deepEqual(readGccActiveListings(listing("18/11 @ 20h09"), "fixed", now), []);
  assert.throws(() => readGccActiveListings("<html>Maintenance</html>", "fixed", now), /unavailable/);
});
