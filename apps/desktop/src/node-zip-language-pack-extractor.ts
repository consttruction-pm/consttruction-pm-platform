import { promisify } from "node:util";
import { inflateRaw } from "node:zlib";

import {
  ZipLanguagePackExtractor,
  type RawDeflateDecoder,
} from "../../client-sync/src/zip-language-pack-extractor.js";

const inflateRawAsync = promisify(inflateRaw);

export class NodeRawDeflateDecoder implements RawDeflateDecoder {
  async decode(compressed: Uint8Array): Promise<Uint8Array> {
    const result = await inflateRawAsync(compressed);
    return new Uint8Array(result);
  }
}

export class NodeZipLanguagePackExtractor extends ZipLanguagePackExtractor {
  constructor(decoder: RawDeflateDecoder = new NodeRawDeflateDecoder()) {
    super(decoder);
  }
}
