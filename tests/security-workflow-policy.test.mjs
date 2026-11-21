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

test("Deployment review remains offline and cannot load cloud credentials", () => {
  const content = read(".github/workflows/deployment-review.yml");
  assert.match(content, /workflow_dispatch:/);
  assert.match(content, /contents: read/);
  assert.doesNotMatch(content, /^  push:|^  pull_request:/m);
  assert.doesNotMatch(content, /CLOUDFLARE_API_TOKEN|secrets\.|wrangler deploy|wrangler d1|curl\b|\-X POST/);
  assert.match(content, /"deployed":False/);
});

test("Scheduled collectors do not persist checkout credentials", () => {
  for (const [filename, publishStep] of [
    ["commercial-history.yml", "Append evidence to isolated data branch"],
    ["tcgdex-research.yml", "Append verified snapshot to isolated history branch"],
  ]) {
    const workflow = read(".github/workflows/" + filename);
    assert.match(workflow, /permissions:\n  contents: read/);
    assert.match(workflow, /jobs:\n  collect:\n    permissions:\n      contents: write/);
    assert.match(workflow, /persist-credentials: false/);
    assert.doesNotMatch(workflow, /persist-credentials: true/);
    const marker = workflow.indexOf("- name: " + publishStep);
    assert.ok(marker > 0, filename + ": missing publish step");
    assert.doesNotMatch(workflow.slice(0, marker), /GH_PUSH_TOKEN|secrets\.GITHUB_TOKEN/);
    assert.match(workflow.slice(marker), /GH_PUSH_TOKEN: \$\{\{ secrets\.GITHUB_TOKEN \}\}/);
    assert.match(workflow.slice(marker), /GIT_ASKPASS/);
    assert.match(workflow.slice(marker), /git push origin/);
  }
});

test("Outlook bootstrap is manual, revision-bound and environment-gated", () => {
  const content = read(".github/workflows/outlook-bootstrap-deploy.yml");
  assert.match(content, /workflow_dispatch:/);
  assert.match(content, /reviewed_commit_sha:/);
  assert.match(content, /change_reference:/);
  assert.match(content, /github\.event_name == 'workflow_dispatch'/);
  assert.doesNotMatch(content, /^  push:/m);
  assert.doesNotMatch(content, /github\.event\.head_commit\.message/);
  assert.match(content, /name: edge-outlook-bootstrap/);
  assert.match(content, /git rev-parse HEAD/);
  assert.match(content, /persist-credentials: false/);
  assert.match(content, /wrangler deploy --dry-run/);
  assert.match(content, /wrangler deploy --config/);
});
