export type LanguageResourceMap = Readonly<Record<string, string>>;

export interface LanguageResourceBundle {
  languageTag: string;
  version: string;
  translations: LanguageResourceMap;
  glossary: LanguageResourceMap;
  help: LanguageResourceMap;
  reports: LanguageResourceMap;
}

export interface LanguagePackResourceReader {
  readText(artifact: Uint8Array, resourcePath: string): Promise<string>;
}

export class LanguageResourceLoader {
  constructor(private readonly reader: LanguagePackResourceReader) {}

  async load(
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
    const [translationText, glossaryText, helpText, reportText] = await Promise.all([
      this.reader.readText(artifact, resourcePaths.translation),
      this.reader.readText(artifact, resourcePaths.glossary),
      this.reader.readText(artifact, resourcePaths.help),
      this.reader.readText(artifact, resourcePaths.reports),
    ]);

    return {
      languageTag,
      version,
      translations: parseMap(translationText, "translation"),
      glossary: parseMap(glossaryText, "glossary"),
      help: parseMap(helpText, "help"),
      reports: parseMap(reportText, "reports"),
    };
  }
}

export function resolveMessage(
  bundle: LanguageResourceBundle,
  key: string,
  fallbackBundle?: LanguageResourceBundle,
): string | null {
  return bundle.translations[key] ?? fallbackBundle?.translations[key] ?? null;
}

function parseMap(raw: string, name: string): LanguageResourceMap {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error("INVALID_" + name.toUpperCase() + "_RESOURCE_JSON");
  }

  if (!isStringMap(value)) {
    throw new Error("INVALID_" + name.toUpperCase() + "_RESOURCE_FORMAT");
  }
  return Object.freeze({ ...value });
}

function isStringMap(value: unknown): value is Record<string, string> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  return Object.values(value as Record<string, unknown>).every(
    (item) => typeof item === "string",
  );
}
