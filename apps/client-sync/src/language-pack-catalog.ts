export type LanguagePackCatalogItem = {
  packageId: string;
  languageTag: string;
  version: string;
  minAppVersion: string;
  maxAppVersion: string | null;
  compressedSizeBytes: number;
  downloadUri: string;
  checksum: string;
  signature: string;
  capabilities: {
    ui: boolean;
    help: boolean;
    aiText: boolean;
    voiceInput: boolean;
    voiceOutput: boolean;
    offlineAi: boolean;
  };
};

export type LanguagePackCatalog = {
  schemaVersion: string;
  generatedAt: string;
  defaultLanguage: string;
  items: readonly LanguagePackCatalogItem[];
};

export function selectCompatiblePack(
  catalog: LanguagePackCatalog,
  languageTag: string,
  appVersion: string,
): LanguagePackCatalogItem | null {
  const candidates = catalog.items.filter(
    (item) =>
      item.languageTag === languageTag &&
      compareVersions(appVersion, item.minAppVersion) >= 0 &&
      (item.maxAppVersion === null ||
        compareVersions(appVersion, item.maxAppVersion) <= 0),
  );

  return [...candidates].sort((a, b) => compareVersions(b.version, a.version))[0] ?? null;
}

function compareVersions(left: string, right: string): number {
  const a = normalizeVersion(left);
  const b = normalizeVersion(right);
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    const av = a[i] ?? 0;
    const bv = b[i] ?? 0;
    if (av !== bv) return av - bv;
  }
  return 0;
}

function normalizeVersion(version: string): number[] {
  const core = version.trim().split("+")[0].split("-");
  if (!core[0]) throw new Error("INVALID_VERSION");
  return core[0].split(".").map((part) => {
    if (!/^\d+$/.test(part)) throw new Error("INVALID_VERSION");
    return Number(part);
  });
}
