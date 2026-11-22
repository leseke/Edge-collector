// Resolve Cloudflare Access application audience without leaking or guessing it.
// Older operator setup uses CF_ACCESS_AUD; existing code used CF_ACCESS_APP_AUD.
// Refuse conflicting values rather than silently accepting the wrong app.
export function resolveCloudflareAccessAudience(env={}) {
  const primary=env.CF_ACCESS_APP_AUD;
  const legacy=env.CF_ACCESS_AUD;
  const acceptable=value=>typeof value==="string" && /^[a-zA-Z0-9_-]{8,128}$/.test(value);
  if(primary!==undefined && !acceptable(primary))return null;
  if(legacy!==undefined && !acceptable(legacy))return null;
  if(primary && legacy && primary!==legacy)return null;
  return primary || legacy || null;
}
