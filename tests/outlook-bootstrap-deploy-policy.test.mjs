import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("Outlook bootstrap requires a manual reviewed revision", () => {
  const src=readFileSync(new URL("../.github/workflows/outlook-bootstrap-deploy.yml",import.meta.url),"utf8");
  assert.match(src,/workflow_dispatch:/);
  assert.match(src,/reviewed_commit_sha:/);
  assert.match(src,/change_reference:/);
  assert.match(src,/github\.event_name == 'workflow_dispatch'/);
  assert.doesNotMatch(src,/^  push:/m);
  assert.doesNotMatch(src,/github\.event\.head_commit\.message/);
  assert.match(src,/name: edge-outlook-bootstrap/);
  assert.match(src,/git rev-parse HEAD/);
  assert.match(src,/persist-credentials: false/);
  assert.match(src,/workers_dev/);
});
