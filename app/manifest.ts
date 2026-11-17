import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "EDGE — Intelligence de marché",
    short_name: "EDGE",
    description: "Radar de marché, suivi des collectibles et intelligence d'investissement.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#090b12",
    theme_color: "#090b12",
    lang: "fr",
    categories: ["finance", "shopping", "productivity"],
    icons: [
      { src: "/edge-icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }
    ]
  };
}
