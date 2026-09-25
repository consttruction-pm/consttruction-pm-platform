import type { LanguagePackResourceReader } from "../../client-sync/src/language-resource-loader.js";

export interface WebLanguagePackExtractor {
  readText(
    artifact: Uint8Array,
    resourcePath: string,
  ): Promise<string>;
}

export class WebLanguageResourceReader implements LanguagePackResourceReader {
  constructor(private readonly extractor: WebLanguagePackExtractor) {}

  async readText(
    artifact: Uint8Array,
    resourcePath: string,
  ): Promise<string> {
    return this.extractor.readText(artifact, resourcePath);
  }
}
