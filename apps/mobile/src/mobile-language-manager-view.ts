import type { LanguageManagerClientAdapter } from "../../client-sync/src/language-manager-client-adapter.js";
import type { LanguageManagerUiState } from "../../client-sync/src/language-manager-ui-contract.js";
import type { LanguageManagerState } from "../../client-sync/src/language-manager-controller.js";
import type {
  LanguagePackCatalog,
  LanguagePackCatalogItem,
} from "../../client-sync/src/language-pack-catalog.js";
import {
  isNewerPackAvailable,
  selectCompatiblePack,
} from "../../client-sync/src/language-pack-catalog.js";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "../../client-sync/src/language-pack-download.js";

export type MobileLanguageManagerCopy = {
  title: string;
  ready: string;
  downloading: (language: string) => string;
  language: string;
  installed: string;
  offline: string;
  ai: string;
  voiceIn: string;
  voiceOut: string;
  offlineAi: string;
  selected: string;
  use: string;
  download: string;
  update: string;
  unavailable: string;
  remove: string;
  yes: string;
  no: string;
  missing: string;
  rtl: string;
  ltr: string;
  downloadProgress: string;
};

export type MobileLanguageManagerAction =
  | { kind: "use-installed"; languageTag: string; version: string }
  | { kind: "download"; languageTag: string; version: string }
  | { kind: "remove-installed"; packageId: string; version: string }
  | { kind: "none"; languageTag: string };

export type MobileLanguageManagerRow = {
  languageTag: string;
  displayName: string;
  locale: string;
  direction: "ltr" | "rtl";
  installedVersion: string | null;
  verified: boolean;
  offlineReady: boolean;
  aiText: boolean;
  voiceInput: boolean;
  voiceOutput: boolean;
  offlineAi: boolean;
  selected: boolean;
  action: MobileLanguageManagerAction;
  actionLabel: string;
  removeAction: MobileLanguageManagerAction | null;
};

export type MobileLanguageManagerSurface = {
  title: string;
  uiLanguage: string;
  direction: "ltr" | "rtl";
  status: "ready" | "downloading" | "error";
  statusText: string;
  errorKey: string | null;
  progressPercent: number | null;
  progressLabel: string;
  rows: readonly MobileLanguageManagerRow[];
};

export type MobileLanguageManagerHost = {
  render(
    surface: MobileLanguageManagerSurface,
    dispatch: (action: MobileLanguageManagerAction) => Promise<void>,
  ): void;
  announceError?(errorKey: string): void;
};

export type MobileLanguageManagerOptions = {
  adapter: LanguageManagerClientAdapter;
  catalog: LanguagePackCatalog;
  appVersion: string;
  host: MobileLanguageManagerHost;
  copy: MobileLanguageManagerCopy;
  createDownloadTransport: () => LanguagePackDownloadTransport;
  createVerifier: () => LanguagePackVerifier;
  onActivateInstalledLanguage?: (
    languageTag: string,
    version: string,
  ) => Promise<void>;
  translateError?: (key: string) => string;
};

export function displayMobileLanguageName(
  languageTag: string,
  uiLocale = languageTag,
): string {
  try {
    const displayNames = new Intl.DisplayNames([uiLocale], { type: "language" });
    return displayNames.of(languageTag) ?? languageTag;
  } catch {
    return languageTag;
  }
}

export function buildMobileLanguageManagerSurface(
  state: LanguageManagerUiState,
  catalog: LanguagePackCatalog,
  appVersion: string,
  copy: MobileLanguageManagerCopy,
  translateError?: (key: string) => string,
): MobileLanguageManagerSurface {
  const selectedRow =
    state.rows.find((row) => row.selected) ??
    state.rows.find((row) => row.languageTag === state.selectedLanguage);
  const uiLanguage = selectedRow?.languageTag ?? state.selectedLanguage;
  const direction = selectedRow?.direction ?? "ltr";
  const statusText = state.errorKey
    ? (translateError?.(state.errorKey) ?? state.errorKey)
    : state.activeDownloadLanguage
      ? copy.downloading(
          displayMobileLanguageName(state.activeDownloadLanguage, uiLanguage),
        )
      : copy.ready;

  return {
    title: copy.title,
    uiLanguage,
    direction,
    status: state.status,
    statusText,
    errorKey: state.errorKey,
    progressPercent: state.progressPercent,
    progressLabel: copy.downloadProgress,
    rows: state.rows.map((row) =>
      toMobileRow(row, catalog, appVersion, uiLanguage, copy),
    ),
  };
}

function toMobileRow(
  row: LanguageManagerUiState["rows"][number],
  catalog: LanguagePackCatalog,
  appVersion: string,
  uiLanguage: string,
  copy: MobileLanguageManagerCopy,
): MobileLanguageManagerRow {
  const compatible = selectCompatiblePack(catalog, row.languageTag, appVersion);
  const action = getAction(row, compatible);
  const removeAvailable =
    !row.selected && Boolean(row.installedPackageId && row.installedVersion);

  return {
    languageTag: row.languageTag,
    displayName: displayMobileLanguageName(row.languageTag, uiLanguage),
    locale: row.locale,
    direction: row.direction,
    installedVersion: row.installedVersion,
    verified: row.verified,
    offlineReady: row.offlineReady,
    aiText: row.aiText,
    voiceInput: row.voiceInput,
    voiceOutput: row.voiceOutput,
    offlineAi: row.offlineAi,
    selected: row.selected,
    action,
    actionLabel: getActionLabel(action, copy),
    removeAction: removeAvailable
      ? {
          kind: "remove-installed",
          packageId: row.installedPackageId!,
          version: row.installedVersion!,
        }
      : null,
  };
}

function getAction(
  row: LanguageManagerUiState["rows"][number],
  compatible: LanguagePackCatalogItem | null,
): MobileLanguageManagerAction {
  if (row.selected) {
    return { kind: "none", languageTag: row.languageTag };
  }
  if (
    row.installedVersion &&
    row.verified &&
    compatible &&
    isNewerPackAvailable(row.installedVersion, compatible.version)
  ) {
    return {
      kind: "download",
      languageTag: row.languageTag,
      version: compatible.version,
    };
  }
  if (row.installedVersion && row.verified) {
    return {
      kind: "use-installed",
      languageTag: row.languageTag,
      version: row.installedVersion,
    };
  }
  if (compatible) {
    return {
      kind: "download",
      languageTag: row.languageTag,
      version: compatible.version,
    };
  }
  return { kind: "none", languageTag: row.languageTag };
}

function getActionLabel(
  action: MobileLanguageManagerAction,
  copy: MobileLanguageManagerCopy,
): string {
  switch (action.kind) {
    case "use-installed":
      return copy.use;
    case "download":
      return copy.download;
    case "remove-installed":
      return copy.remove;
    case "none":
      return copy.unavailable;
  }
}

function makeManifest(item: LanguagePackCatalogItem): LanguagePackDownloadManifest {
  return {
    packageId: item.packageId,
    languageTag: item.languageTag,
    version: item.version,
    minAppVersion: item.minAppVersion,
    maxAppVersion: item.maxAppVersion,
    compressedSizeBytes: item.compressedSizeBytes,
    downloadUri: item.downloadUri,
    checksum: item.checksum,
    signature: item.signature,
    resourcePaths: item.resourcePaths,
  };
}

export class MobileLanguageManagerView {
  private currentSurface: MobileLanguageManagerSurface | null = null;
  private busyLanguage: string | null = null;

  constructor(private readonly options: MobileLanguageManagerOptions) {}

  async mount(): Promise<void> {
    await this.refresh();
  }

  async refresh(): Promise<MobileLanguageManagerSurface> {
    return this.render(
      stateToUiState(await this.options.adapter.refresh()),
    );
  }

  surface(): MobileLanguageManagerSurface | null {
    return this.currentSurface;
  }

  async dispatch(action: MobileLanguageManagerAction): Promise<void> {
    if (this.busyLanguage) return;
    switch (action.kind) {
      case "none":
        return;
      case "use-installed":
        await this.useInstalled(action.languageTag, action.version);
        return;
      case "download":
        await this.download(action.languageTag, action.version);
        return;
      case "remove-installed":
        await this.removeInstalled(action.packageId, action.version);
        return;
    }
  }

  private render(
    state: LanguageManagerUiState,
  ): MobileLanguageManagerSurface {
    const surface = buildMobileLanguageManagerSurface(
      state,
      this.options.catalog,
      this.options.appVersion,
      this.options.copy,
      this.options.translateError,
    );
    this.currentSurface = surface;
    this.options.host.render(surface, (action) => this.dispatch(action));
    if (surface.errorKey) {
      this.options.host.announceError?.(surface.errorKey);
    }
    return surface;
  }

  private async useInstalled(languageTag: string, version: string): Promise<void> {
    try {
      if (!this.options.onActivateInstalledLanguage) {
        throw new Error("LANGUAGE_ACTIVATION_NOT_CONFIGURED");
      }
      await this.options.onActivateInstalledLanguage(languageTag, version);
      await this.options.adapter.persistSelection(languageTag);
      await this.refresh();
    } catch (error) {
      this.handleError(error);
    }
  }

  private async removeInstalled(packageId: string, version: string): Promise<void> {
    try {
      const next = await this.options.adapter.removeInstalledPack(packageId, version);
      await this.render(next);
    } catch (error) {
      this.handleError(error);
    }
  }

  private async download(languageTag: string, version: string): Promise<void> {
    const item = this.options.catalog.items.find(
      (candidate) =>
        candidate.languageTag === languageTag &&
        candidate.version === version,
    );
    if (!item) {
      this.handleError(new Error("LANGUAGE_PACK_NOT_IN_CATALOG"));
      return;
    }

    this.busyLanguage = languageTag;
    try {
      const next = await this.options.adapter.download(
        makeManifest(item),
        this.options.createDownloadTransport(),
        this.options.createVerifier(),
        (progress) => {
          const total = progress.totalBytes;
          const received = progress.bytesReceived;
          const percent =
            total > 0
              ? Math.min(100, Math.round((received / total) * 100))
              : null;
          const current = this.currentSurface;
          if (!current) return;
          this.render({
            ...current,
            status: "downloading",
            statusText: this.options.copy.downloading(
              displayMobileLanguageName(
                progress.languageTag,
                current.uiLanguage,
              ),
            ),
            progressPercent: percent,
          });
        },
      );
      await this.render(next);
    } catch (error) {
      this.handleError(error);
    } finally {
      this.busyLanguage = null;
    }
  }

  private handleError(error: unknown): void {
    const errorKey = error instanceof Error ? error.message : String(error);
    const current = this.currentSurface;
    if (current) {
      this.render({
        ...current,
        status: "error",
        statusText: this.options.translateError?.(errorKey) ?? errorKey,
        errorKey,
        progressPercent: null,
      });
    } else {
      this.options.host.announceError?.(errorKey);
    }
  }
}

function stateToUiState(state: LanguageManagerState): LanguageManagerUiState {
  return {
    selectedLanguage: state.selectedLanguage,
    rows: state.items.map((item) => ({
      languageTag: item.languageTag,
      locale: item.locale,
      direction: item.direction,
      installedPackageId: item.installedPackageId,
      installedVersion: item.installedVersion,
      verified: item.verified,
      offlineReady: item.offlineReady,
      aiText: item.capabilities.aiText,
      voiceInput: item.capabilities.voiceInput,
      voiceOutput: item.capabilities.voiceOutput,
      offlineAi: item.capabilities.offlineAi,
      selected: item.languageTag === state.selectedLanguage,
    })),
    activeDownloadLanguage: null,
    progressPercent: null,
    status: "ready",
    errorKey: null,
  };
}
