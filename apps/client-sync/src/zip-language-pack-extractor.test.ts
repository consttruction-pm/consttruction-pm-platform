import assert from "node:assert/strict";
import { deflateRawSync, inflateRawSync } from "node:zlib";
import test from "node:test";

import { ZipLanguagePackExtractor } from "./zip-language-pack-extractor.js";

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

function makeZip(
  path: string,
  content: string,
  method: 0 | 8,
): Uint8Array {
  const name = new TextEncoder().encode(path);
  const body = new TextEncoder().encode(content);
  const compressed =
    method === 0 ? body : new Uint8Array(deflateRawSync(body));
  const crc = crc32(body);

  const local = new Uint8Array(30 + name.length + compressed.length);
  const localView = new DataView(local.buffer);
  localView.setUint32(0, 0x04034b50, true);
  localView.setUint16(4, 20, true);
  localView.setUint16(6, 0x0800, true);
  localView.setUint16(8, method, true);
  localView.setUint32(14, 0, true);
  localView.setUint32(18, crc, true);
  localView.setUint32(22, compressed.length, true);
  localView.setUint32(26, body.length, true);
  localView.setUint16(30, name.length, true);
  local.set(name, 34);
  local.set(compressed, 34 + name.length);

  const central = new Uint8Array(46 + name.length);
  const centralView = new DataView(central.buffer);
  centralView.setUint32(0, 0x02014b50, true);
  centralView.setUint16(4, 20, true);
  centralView.setUint16(6, 20, true);
  centralView.setUint16(8, 0x0800, true);
  centralView.setUint16(10, method, true);
  centralView.setUint32(16, crc, true);
  centralView.setUint32(20, compressed.length, true);
  centralView.setUint32(24, body.length, true);
  centralView.setUint16(28, name.length, true);
  centralView.setUint32(42, 0, true);
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

test("zip language extractor reads stored UTF-8 text", async () => {
  const zip = makeZip("translations.json", '{"title":"سلام"}', 0);
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

test("zip language extractor decodes a real deflated resource through the platform decoder", async () => {
  const zip = makeZip("translations.json", '{"title":"hello"}', 8);
  let decoderCalls = 0;
  const extractor = new ZipLanguagePackExtractor({
    async decode(bytes) {
      decoderCalls += 1;
      return new Uint8Array(inflateRawSync(bytes));
    },
  });

  assert.equal(
    await extractor.readText(zip, "translations.json"),
    '{"title":"hello"}',
  );
  assert.equal(decoderCalls, 1);
});

test("zip language extractor rejects path traversal before archive access", async () => {
  const zip = makeZip("translations.json", '{"title":"bad"}', 0);
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

test("zip language extractor rejects an archive entry with path traversal", async () => {
  const zip = makeZip("../translations.json", '{"title":"bad"}', 0);
  const extractor = new ZipLanguagePackExtractor({
    async decode(): Promise<Uint8Array> {
      throw new Error("NOT_EXPECTED");
    },
  });

  await assert.rejects(
    extractor.readText(zip, "../translations.json"),
    /INVALID_LANGUAGE_PACK_ENTRY_PATH/,
  );
});

test("zip language extractor rejects corrupted stored resource bytes by CRC", async () => {
  const zip = makeZip("translations.json", '{"title":"ok"}', 0);
  const localDataOffset = 30 + "translations.json".length;
  zip[localDataOffset] ^= 0xff;

  const extractor = new ZipLanguagePackExtractor({
    async decode(): Promise<Uint8Array> {
      throw new Error("NOT_EXPECTED");
    },
  });

  await assert.rejects(
    extractor.readText(zip, "translations.json"),
    /LANGUAGE_RESOURCE_CRC_MISMATCH/,
  );
});
