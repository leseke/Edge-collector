// Experimental DeepSeek Harness Cordis plugin, matching upstream tool tutorial.
// Run only inside a disposable, unprivileged dsh profile. No EDGE credentials.
import type { Context } from "@deepseek-ai/cordis";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { inspectObservations } from "../edge-readonly-tool.mjs";

export const name = "edge-market-readonly";
export const inject = ["tools"];
const snapshotFile = fileURLToPath(new URL("../data/observations.json", import.meta.url));
export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: "edge_market_snapshot",
    description: "Inspect a fixed, local EDGE observation export. Returns indicative aggregated prices only, not completed sales. Never makes purchases.",
    parameters: { productId: { type: "string", required: true, description: "EDGE product identifier" } },
    output: {
      schema: { type: "string" },
      render: (_args, value) => [{ type: "text", text: value }],
    },
    async execute(args) {
      const raw = await readFile(snapshotFile, "utf8");
      if (raw.length > 1_000_000) throw new Error("snapshot_too_large");
      const rows: unknown = JSON.parse(raw);
      return JSON.stringify(inspectObservations(rows, args.productId));
    },
  }));
}
