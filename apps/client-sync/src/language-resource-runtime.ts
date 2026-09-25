import {
  LanguageResourceLoader,
  type LanguageResourceBundle,
  type LanguagePackResourceReader,
  resolveMessage,
} from "./language-resource-loader.ts";

export class LanguageResourceRuntime {
  private readonly loader: LanguageResourceLoader;
  private readonly bundles = new Map<string, LanguageResourceBundle>();

  constructor(reader: LanguagePackResourceReader) {
    this.loader = new LanguageResourceLoader(reader);
  }

  async installBundle(
    languageTag: string,
    version: string,
    artifact: Uint8Array,
    resourcePaths: {
      translation: string;
      glossary: string;
      help: string;
      reports: string;
    },
  ): Promise<LanguageResourceBundle> {
    const bundle = await this.loader.load(
      languageTag,
      version,
      artifact,
      resourcePaths,
    );
    this.bundles.set(bundleKey(languageTag, version), bundle);
    return bundle;
  }

  getBundle(languageTag: string, version: string): LanguageResourceBundle | null {
    return this.bundles.get(bundleKey(languageTag, version)) ?? null;
  }

  removeBundle(languageTag: string, version: string): void {
    this.bundles.delete(bundleKey(languageTag, version));
  }

  translate(
    languageTag: string,
    version: string,
    key: string,
    fallback: { languageTag: string; version: string } | null = null,
  ): string | null {
    const bundle = this.getBundle(languageTag, version);
    if (!bundle) return null;

    const fallbackBundle = fallback
      ? this.getBundle(fallback.languageTag, fallback.version) ?? undefined
      : undefined;
    return resolveMessage(bundle, key, fallbackBundle);
  }
}

function bundleKey(languageTag: string, version: string): string {
  return languageTag + "@" + version;
}
