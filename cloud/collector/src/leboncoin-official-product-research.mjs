// Official Pokémon product research references; independently linked to
// public manufacturer product pages. They are NOT reviewed GCC variant keys
// and must never promote a market candidate to VERIFIED automatically.
export const officialPokemonResearchSources=Object.freeze([
  Object.freeze({
    productFamily:"ETB",series:"prismatic-evolutions",productSlug:"elite-trainer-box",
    canonicalName:"Scarlet & Violet—Prismatic Evolutions Elite Trainer Box",
    announcedRelease:"2025-01-17",sourceLocale:"us-en",
    sourceUrl:"https://www.pokemon.com/us/pokemon-tcg/product-gallery/scarlet-violet-prismatic-evolutions-elite-trainer-box",
    referenceStatus:"OFFICIAL_PRODUCT_PAGE_ONLY"
  }),
  Object.freeze({
    productFamily:"UPC",series:"celebrations",productSlug:"ultra-premium-collection",
    canonicalName:"Celebrations Ultra-Premium Collection",
    announcedRelease:null,sourceLocale:"us-en",
    sourceUrl:"https://www.pokemon.com/us/pokemon-tcg/product-gallery/celebrations-ultra-premium-collection",
    referenceStatus:"OFFICIAL_PRODUCT_PAGE_ONLY"
  }),
  Object.freeze({
    productFamily:"UPC",series:"mega-charizard-x",productSlug:"ultra-premium-collection",
    canonicalName:"Mega Charizard X ex Ultra-Premium Collection",
    announcedRelease:"2025-11-14",sourceLocale:"us-en",
    sourceUrl:"https://www.pokemon.com/us/pokemon-tcg/product-gallery/pokemon-tcg-mega-charizard-x-ex-ultra-premium-collection",
    referenceStatus:"OFFICIAL_PRODUCT_PAGE_ONLY"
  })
]);
// Only discover manufacturer research sources when family + exact series +
// explicit locale agree. Never equate a US/English release with a FR one.
export function officialResearchForCandidate(candidate,sources=officialPokemonResearchSources){
  if(!candidate || candidate.status!=="CANDIDATE_UNVERIFIED"||
     !Array.isArray(sources))return [];
  const type={etb:"ETB",upc:"UPC",display:"DISPLAY",coffret:"COFFRET"}[candidate.packaging];
  const locale={en:"us-en"}[candidate.language];
  if(!type||!locale)return [];
  return sources.filter(x=>
    x.referenceStatus==="OFFICIAL_PRODUCT_PAGE_ONLY" &&
    x.productFamily===type && x.series===candidate.series &&
    x.productSlug===candidate.product &&
    x.sourceLocale===locale &&
    typeof x.canonicalName==="string" &&
    typeof x.sourceUrl==="string" &&
    /^https:\/\/www\.pokemon\.com\/us\/pokemon-tcg\/product-gallery\/[a-z0-9-]+$/.test(x.sourceUrl)
  ).map(x=>({status:"RESEARCH_LEAD_ONLY",title:x.canonicalName,
    sourceUrl:x.sourceUrl,sourceLocale:x.sourceLocale,
    announcedRelease:x.announcedRelease}));
}
