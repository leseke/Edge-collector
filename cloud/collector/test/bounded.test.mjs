import test from "node:test";
import assert from "node:assert/strict";
import { readBoundedText } from "../src/bounded.mjs";

test("reads valid small JSON body", async () => {
  const r = new Response('{"price":1}');
  assert.equal(await readBoundedText(r, 100), '{"price":1}');
});
test("rejects oversized declared length", async () => {
  const r = new Response("small", { headers: { "content-length": "999" } });
  await assert.rejects(readBoundedText(r, 10), /oversize/);
});
test("rejects oversized streamed body even without content length", async () => {
  const r = new Response(new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(8));
      controller.enqueue(new Uint8Array(8));
      controller.close();
    },
  }));
  await assert.rejects(readBoundedText(r, 10), /oversize/);
});
test("rejects invalid UTF-8", async () => {
  const r = new Response(new Uint8Array([0xff]));
  await assert.rejects(readBoundedText(r), TypeError);
});
