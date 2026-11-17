"use client";
import { useState } from "react";

type ImageStatus = "loading" | "loaded";
const IMAGE_SUFFIX = /\/(?:high|low)\.(?:webp|png|jpg)$/;
const IMAGE_VARIANTS = ["/high.webp", "/low.webp", "/high.png", "/low.png"] as const;

/** Only use TCGdex-hosted HTTPS images. Never synthesize prices or unrelated image URLs. */
export function tcgdexImageCandidates(src: string | null): string[] {
  if (!src) return [];
  try {
    const url = new URL(src);
    if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net" ||
        url.username || url.password || url.search || url.hash ||
        !/^\/[a-zA-Z0-9_/-]+(?:\.(?:webp|png|jpg))?$/.test(url.pathname)) return [];
    const base = url.href.replace(IMAGE_SUFFIX, "");
    const urls = base === url.href ? [url.href, ...IMAGE_VARIANTS.map(variant => base.replace(/\/$/, "") + variant)]
      : [url.href, ...IMAGE_VARIANTS.map(variant => base + variant)];
    return [...new Set(urls)];
  } catch {
    return [];
  }
}

function Placeholder({ name, reason }: { name: string; reason: "missing" | "failed" }) {
  const label = reason === "missing" ? "Image non référencée" : "Image inaccessible";
  return <div className="edge-asset-placeholder" role="img" aria-label={`${label} pour ${name}`}>
    <span aria-hidden="true">◇</span><small>{label}</small>
  </div>;
}

function ResolvedImage({ src, name }: { src: string; name: string }) {
  const urls = tcgdexImageCandidates(src);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState<ImageStatus>("loading");
  if (!urls.length) return <Placeholder name={name} reason="failed" />;
  if (index >= urls.length) return <Placeholder name={name} reason="failed" />;
  return <>
    {status === "loading" && <div className="edge-asset-placeholder" role="status" aria-label={`Chargement de l'image de ${name}`}><span aria-hidden="true">◇</span><small>Chargement…</small></div>}
    <img key={urls[index]} src={urls[index]} alt={`Illustration de ${name}`} loading="lazy"
      style={status === "loaded" ? undefined : { opacity: 0, position: "absolute", pointerEvents: "none" }}
      onLoad={() => setStatus("loaded")}
      onError={() => { setStatus("loading"); setIndex(previous => previous + 1); }} />
  </>;
}

export function AssetImage({ src, name }: { src: string | null; name: string }) {
  if (!src) return <Placeholder name={name} reason="missing" />;
  return <ResolvedImage key={src} src={src} name={name} />;
}
