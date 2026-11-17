// Read at most maxBytes of UTF-8 JSON; reject oversized responses before buffering.
// This prevents a misbehaving source from forcing an unbounded response.text().
export async function readBoundedText(response, maxBytes = 128000) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error("invalid_max_bytes");
  const declared = response.headers.get("content-length");
  if (declared !== null && /^[0-9]+$/.test(declared) && Number(declared) > maxBytes) throw new Error("oversize");
  if (!response.body) throw new Error("invalid_empty_body");
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) throw new Error("oversize");
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    reader.releaseLock();
  }
  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(combined);
}
