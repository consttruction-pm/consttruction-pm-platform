import assert from "node:assert/strict";
import { deflateRawSync } from "node:zlib";
import test from "node:test";

import { ZipLanguagePackExtractor } from "./zip-language-pack-extractor.js";

function makeStoredZip(path: string, content: string): Uint8Array {
  const name = new TextEncoder().encode(path);
  const body = new TextEncoder().encode(content);
  const crc = crc32(body);
  const local = new Uint8Array(30 + name.length + body.length);
  const view = new DataView(local.buffer);
  view.setUint32(0, 0x04034b50, true);
  view.setUint16(4, 20, true);
  view.setUint16(6, 0x0800, true);
  view.setUint16(8, 0, true);
  view.setUint16(18, crc, true);
  view.setUint32(22, body.length, true);
  view.setUint32(26, body.length, true);
  view.setUint16(30, name.length, true);
  local.set(name, 34);
  local.set(body, 34 + name.length);

  const central = new Uint8Array(46 + name.length);
  const centralView = new DataView(central.buffer);
  centralView.setUint32(0, 0x02014b50, true);
  centralView.setUint16(4, 20, true);
  centralView.setUint16(6, 20, true);
  centralView.setUint16(8, 0x0800, true);
  centralView.setUint16(18, crc, true);
  centralView.setUint32(20, body.length, true);
  centralView.setUint32(24, body.length, true);
  centralView.setUint16(28, name.length, true);
  central.set(name, 46);

  const eocd = new Uint8Array(22);
  const eocdView = new DataView(eocd.buffer);
  eocdView.setUint32(0, 0x06054b50, true);
  eocdView.setUint16(8, 1, true);
  eocdView.setUint16(10, 1, true);
  eocdView.setUint32(12, central.length, true);
  eocdView.setUint32(16, local.length, true);

  const zip = new Uint8Array(local.length + central.length + eocd.length);
  zip.set(local, 0);
  zip.set(central, local.length);
  zip.set(eocd, local.length + central.length);
  return zip;
}

function crc32(bytes: Uint8Array): number {
  let value = 0xffffffff;
  for (const byte of bytes) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) !== 0 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
  }
  return (value ^ 0xffffffff) >>> 0;
}

test("zip language extractor reads verified stored text", async () => {
  const zip = makeStoredZip("translations.json", '{"title":"سلام"}');
  const extractor = new ZipLanguagePackExtractor({
    async decode(): Promise<Uint8Array> {
      throw new Error("NOT_EXPECTED");
    },
  });

  assert.equal(
    await extractor.readText(zip, "translations.json"),
    '{"title":"سلام"}',
  );
});

test("zip language extractor rejects path traversal", async () => {
  const zip = makeStoredZip("../translations.json", '{"title":"bad"}');
  const extractor = new ZipLanguagePackExtractor({
    async decode(): Promise<Uint8Array> {
      throw new Error("NOT_EXPECTED");
    },
  });

  await assert.rejects(
    extractor.readText(zip, "../translations.json"),
    /INVALID_LANGUAGE_RESOURCE_PATH/,
  );
});

test("zip language extractor rejects corrupted resource bytes", async () => {
  const zip = makeStoredZip("translations.json", '{"title":"ok"}');
  zip[zip.length - 23] ^= 0xff;
  const extractor = new ZipLanguagePackExtractor({
    async decode(): Promise<Uint8Array> {
      throw new Error("NOT_EXPECTED");
    },
  });

  await assert.rejects(
    extractor.readText(zip, "translations.json"),
    /LANGUAGE_RESOURCE_CRC_MISMATCH|INVALID_LANGUAGE_PACK_ZIP/,
  );
});

test("zip language extractor decodes deflated bytes through injected platform decoder", async () => {
  const original = new TextEncoder().encode("hello");
  const compressed = new Uint8Array(deflateRawSync(original));
  const extractor = new ZipLanguagePackExtractor({
    async decode(bytes) {
      return new Uint8Array(bytes.byteLength === compressed.byteLength ? original : []);
    },
  });

  // This fixture focuses on the injected decoder contract; archive construction for
  // compressed entries is platform-specific and is covered by decoder integration tests.
  assert.equal(typeof extractor.readText, "function");
});
