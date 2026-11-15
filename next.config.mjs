import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

// Enables OpenNext Cloudflare bindings when running the app with Next.js dev.
initOpenNextCloudflareForDev();

/** @type {import("next").NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
