"use client";
import { useEffect, useState } from "react";

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
        !/^\/[a-zA-Z0-9_./-]+$/.test(url.pathname)) return [];
    const base = url.href.replace(IMAGE_SUFFIX, "");
    const urls = base === url.href ? [...IMAGE_VARIANTS.map(variant => base.replace(/\/$/, "") + variant), url.href]
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

function CatalogueImageFallback({ cardId, name }: { cardId: string; name: string }) {
  const [image, setImage] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/catalog/image?" + new URLSearchParams({ id: cardId }), { signal: controller.signal })
      .then(async response => {
        if (!response.ok) return;
        const data: { image: string | null } = await response.json();
        if (!controller.signal.aborted) setImage(data.image);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [cardId]);
  if (!image) return <Placeholder name={name} reason="missing" />;
  return <>
    <ResolvedImage src={image} name={name + " (édition anglaise)"} />
    <small>Illustration EN</small>
  </>;
}

export function AssetImage({ src, name, catalogueId, catalogueLanguage }: {
  src: string | null; name: string; catalogueId?: string; catalogueLanguage?: string;
}) {
  if (!src && catalogueId && catalogueLanguage !== "en") {
    return <CatalogueImageFallback key={catalogueId} cardId={catalogueId} name={name} />;
  }
  if (!src) return <Placeholder name={name} reason="missing" />;
  return <ResolvedImage key={src} src={src} name={name} />;
}
