const supportedCards = [
  { id: "swsh7-215", name: "Noctali", set: "Evolution Celeste", number: "215/203", releasedOn: "2021-08-27", grades: ["PCA 9", "PCA 9.5", "PSA 10"] },
  { id: "swsh8-157", name: "Ectoplasma", set: "Poing de Fusion", number: "157/264", releasedOn: "2021-11-12", grades: ["PCA 9.5", "PSA 10"] },
];

export function gccVariantKey(identity, day) {
  const languageCodes = { french: "fr", francais: "fr", english: "en", anglais: "en", japanese: "ja", japonais: "ja",
    german: "de", allemand: "de", spanish: "es", espagnol: "es", italian: "it", italien: "it" };
  const metadata = identity.match(/\bPokemon\s*•\s*([a-z]+)\s*•\s*(\d{4})\s*•\s*([^•]{2,80}?)\s*•\s*(Unlimited|First Edition)\s*(?:•\s*#((?:[a-z0-9]+\/[a-z0-9]+|[a-z]{1,8}\d{1,5})(?=\s|$)))?/i);
  if (!metadata) return null;
  const [, rawLanguage, year, set, edition, number] = metadata;
  const lang = languageCodes[rawLanguage.toLowerCase()];
  if (!lang || year > day.slice(0, 4)) return null;
  const title = identity.slice(0, metadata.index).trim();
  const graded = title.match(/(?:^|\s)(PCA|PSA|CA|CCC|CGC|BGS|SGC)\s+(10|[1-9](?:\.5)?)\s+([a-z0-9][a-z0-9 '’.-]{1,100})$/i);
  const keyPart = (value) => value.trim().toLowerCase().replace(/[^a-z0-9./]+/g, "-");
  const normalizedEdition = keyPart(edition);
  const card = supportedCards.find(x => x.set.toLowerCase() === set.toLowerCase() && x.number === number);
  if (card && day < card.releasedOn) return null;
  let key;
  if (number && graded) {
    const [, grader, score, name] = graded;
    const grade = grader.toUpperCase() + " " + score;
    key = card && lang === "fr" && normalizedEdition === "unlimited" &&
      name.toLowerCase() === (card.name + " vmax").toLowerCase() && card.grades.some(value => value === grade)
      ? card.id + ":fr:unlimited:" + grader.toLowerCase() + ":" + score
      : ["carte", year, keyPart(set), keyPart(number), keyPart(name), lang, normalizedEdition, keyPart(grader), score].join(":");
  } else if (!number) {
    const sealed = title.match(/(?:^|\s)((?:booster|blister|display|coffret|etb|upc|elite trainer box|ultra premium collection)\s+[^<>]{3,100}?)\s+(?:scelle|sealed)$/i)?.[1];
    if (!sealed || /\b(?:lot|ouvert|opened|vide|empty|reconditionne|resealed|sans|without)\b/i.test(sealed)) return null;
    const category = /^(?:booster|blister|display)\b/i.test(sealed) ? "booster" : "coffret";
    key = [category, year, keyPart(set), keyPart(sealed), lang, normalizedEdition, "scelle"].join(":");
  } else {
    return null; // A raw card without a verified condition remains a lead.
  }
  return key;
}
