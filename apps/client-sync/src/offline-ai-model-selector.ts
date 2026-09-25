export type DeviceCapabilityProfile = {
  ramMb: number;
  storageFreeMb: number;
  offlineAiAllowed: boolean;
};

export type OfflineModelPack = {
  packageId: string;
  languageTag: string;
  modelType: "ai_text" | "voice_input" | "voice_output";
  version: string;
  minAppVersion: string;
  maxAppVersion: string | null;
  sizeBytes: number;
  checksum: string;
  signature: string;
  offline: boolean;
  minRamMb: number;
  minStorageMb: number;
  verified: boolean;
};

export type PreferredLanguageModels = {
  aiText: OfflineModelPack | null;
  voiceInput: OfflineModelPack | null;
  voiceOutput: OfflineModelPack | null;
};

export function selectOfflineModels(
  preferredLanguage: string,
  appVersion: string,
  device: DeviceCapabilityProfile,
  installed: readonly OfflineModelPack[],
): PreferredLanguageModels {
  const candidates = installed.filter(
    (model) =>
      model.languageTag === preferredLanguage &&
      model.verified &&
      model.offline &&
      appVersionAtLeast(appVersion, model.minAppVersion) &&
      (model.maxAppVersion === null ||
        versionCompare(appVersion, model.maxAppVersion) <= 0) &&
      model.minRamMb <= device.ramMb &&
      model.minStorageMb <= device.storageFreeMb,
  );

  return {
    aiText: newest(candidates, "ai_text"),
    voiceInput: device.offlineAiAllowed
      ? newest(candidates, "voice_input")
      : null,
    voiceOutput: device.offlineAiAllowed
      ? newest(candidates, "voice_output")
      : null,
  };
}

function newest(
  candidates: readonly OfflineModelPack[],
  modelType: OfflineModelPack["modelType"],
): OfflineModelPack | null {
  return [...candidates]
    .filter((model) => model.modelType === modelType)
    .sort((a, b) => versionCompare(b.version, a.version))[0] ?? null;
}

function appVersionAtLeast(actual: string, minimum: string): boolean {
  return versionCompare(actual, minimum) >= 0;
}

function versionCompare(left: string, right: string): number {
  const a = normalize(left);
  const b = normalize(right);
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    const av = a[i] ?? 0;
    const bv = b[i] ?? 0;
    if (av !== bv) return av - bv;
  }
  return 0;
}

function normalize(version: string): number[] {
  const core = version.trim().split("-")[0].split("+")[0];
  if (!core) throw new Error("INVALID_VERSION");
  return core.split(".").map((segment) => {
    if (!/^\d+$/.test(segment)) throw new Error("INVALID_VERSION");
    return Number(segment);
  });
}
