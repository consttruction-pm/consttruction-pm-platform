import { ZipLanguagePackExtractor, type RawDeflateDecoder } from "../../client-sync/src/zip-language-pack-extractor.js";

export class WebRawDeflateDecoder implements RawDeflateDecoder {
  async decode(compressed: Uint8Array): Promise<Uint8Array> {
    const Constructor = (globalThis as typeof globalThis & {
      DecompressionStream?: new (
        format: "deflate-raw",
      ) => {
        writable: WritableStream<Uint8Array>;
        readable: ReadableStream<Uint8Array>;
      };
    }).DecompressionStream;

    if (!Constructor) {
      throw new Error("WEB_RAW_DEFLATE_UNAVAILABLE");
    }

    const stream = new Blob([compressed]).stream().pipeThrough(
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
