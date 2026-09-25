import {
  ZipLanguagePackExtractor,
  type RawDeflateDecoder,
} from "../../client-sync/src/zip-language-pack-extractor.js";

export class WebRawDeflateDecoder implements RawDeflateDecoder {
  async decode(compressed: Uint8Array): Promise<Uint8Array> {
    const Constructor = (globalThis as { DecompressionStream?: any })
      .DecompressionStream as
      | (new (format: "deflate-raw") => any)
      | undefined;

    if (!Constructor) {
      throw new Error("WEB_RAW_DEFLATE_UNAVAILABLE");
    }

    const buffer = new ArrayBuffer(compressed.byteLength);
    new Uint8Array(buffer).set(compressed);
    const stream = new Blob([buffer]).stream().pipeThrough(
      new Constructor("deflate-raw"),
    );
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
}

export class WebZipLanguagePackExtractor extends ZipLanguagePackExtractor {
  constructor(decoder: RawDeflateDecoder = new WebRawDeflateDecoder()) {
    super(decoder);
  }
}
