"use client";
import { useEffect, useState } from "react";

function candidates(src: string | null): string[] {
  if (!src) return [];
  try {
    const url = new URL(src);
    if (url.protocol !== "https:" || url.hostname !== "assets.tcgdex.net") return [];
    const base = url.href.replace(/\/(?:high|low)\.(?:webp|png|jpg)$/, "");
    if (base === url.href) return [url.href];
    return [url.href, base + "/low.webp", base + "/high.png", base + "/low.png"].filter((value, index, list) => list.indexOf(value) === index);
  } catch { return []; }
}

export function AssetImage({ src, name }: { src: string | null; name: string }) {
  const urls = candidates(src);
  const [index, setIndex] = useState(0);
  useEffect(() => { setIndex(0); }, [src]);
  if (index >= urls.length) return <div className="edge-asset-placeholder" role="img" aria-label={`Image indisponible pour ${name}`}><span aria-hidden="true">◇</span><small>Image indisponible</small></div>;
  return <img key={urls[index]} src={urls[index]} alt={`Illustration de ${name}`} loading="lazy" onError={() => setIndex(previous => previous + 1)} />;
}
