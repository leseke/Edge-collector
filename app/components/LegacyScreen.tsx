"use client";
import { useCallback } from "react";
type LegacyScreenProps = { src: string; title: string };
export function LegacyScreen({ src, title }: LegacyScreenProps) {
  const adaptLegacyDocument = useCallback((frame: HTMLIFrameElement) => {
    try {
      const doc = frame.contentDocument;
      if (!doc || doc.getElementById("edge-native-shell-adapter")) return;
      const style = doc.createElement("style");
      style.id = "edge-native-shell-adapter";
      style.textContent = ".top, body > footer { display:none !important; } main { padding-top:24px !important; } @media(max-width:760px){main{padding-top:16px !important;}}";
      doc.head.appendChild(style);
    } catch { /* Keep the original screen usable if adaptation is unavailable. */ }
  }, []);
  return <div className="legacy-viewport"><iframe className="legacy-frame" src={src} title={title} onLoad={(event) => adaptLegacyDocument(event.currentTarget)} loading="eager" allow="clipboard-read; clipboard-write" /></div>;
}
