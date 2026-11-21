import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");

test("Cloudflare build cannot deploy, migrate or provision remotely", () => {
  const content = read(".github/workflows/cloudflare-build.yml");
  assert.match(content, /name: Cloudflare Workers build/);
  assert.match(content, /npm run cf:build/);
  assert.doesNotMatch(content, /wrangler deploy(?!\s+--dry-run)|wrangler secret put|d1 execute[^\n]*--remote|provision-d1:|Publish the authorized isolated preview/);
  assert.doesNotMatch(content, /github\.event\.head_commit\.message\s*==/);
  assert.doesNotMatch(content, /CLOUDFLARE_API_TOKEN|secrets\.|dsh-real-d1-readonly:|verify-cloudflare-access:/);
});

test("D1 provisioning cannot be activated by a push", () => {
  const content = read(".github/workflows/edge-d1-provision.yml");
  assert.match(content, /workflow_dispatch:/);
  assert.doesNotMatch(content, /^  push:/m);
  assert.match(content, /contents: read/);
  assert.doesNotMatch(content, /CLOUDFLARE_API_TOKEN|curl\b|wrangler|--remote|\-X POST|secrets\./);
});
