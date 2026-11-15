import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";
import type { NextConfig } from "next";

// Enables the OpenNext Cloudflare development bindings when running locally.
// The standard Next.js dev server remains the default development workflow.
initOpenNextCloudflareForDev();

/** @type {NextConfig} */
const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
