"use client";
import { useState } from "react";

export function AssetImage({ src, name }: { src: string | null; name: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) return <div className="edge-asset-placeholder" role="img" aria-label={`Image indisponible pour ${name}`}><span aria-hidden="true">◇</span><small>Image indisponible</small></div>;
  return <img src={src} alt={`Illustration de ${name}`} loading="lazy" onError={() => setFailed(true)} />;
}
