import type {
  LanguageManagerClientAdapter,
} from "../../client-sync/src/language-manager-client-adapter.js";
import type {
  LanguageManagerUiState,
  LanguageManagerRow,
} from "../../client-sync/src/language-manager-ui-contract.js";
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

export type DesktopLanguageManagerCopy = {
  title: string;
  ready: string;
  downloading: (language: string) => string;
  supportedLanguages: string;
  language: string;
  locale: string;
  direction: string;
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
  action: string;
  downloadProgress: string;
  rtl: string;
  ltr: string;
};

export type DesktopLanguageManagerAction =
  | {
      kind: "use-installed";
      languageTag: string;
      version: string;
    }
  | {
      kind: "download";
      languageTag: string;
      version: string;
    }
  | {
      kind: "remove-installed";
      packageId: string;
      version: string;
    }
  | {
      kind: "none";
      languageTag: string;
    };

export type DesktopLanguageManagerRow = LanguageManagerRow & {
  displayName: string;
  action: DesktopLanguageManagerAction;
  actionLabel: string;
  removeAvailable: boolean;
  removeAction: DesktopLanguageManagerAction | null;
};

export type DesktopLanguageManagerSurface = {
  title: string;
  uiLanguage: string;
  direction: "ltr" | "rtl";
  status: "ready" | "downloading" | "error";
  statusText: string;
  errorKey: string | null;
  progressPercent: number | null;
  progressLabel: string;
  rows: readonly DesktopLanguageManagerRow[];
};

export type DesktopLanguageManagerHost = {
  render(
    surface: DesktopLanguageManagerSurface,
    dispatch: (action: DesktopLanguageManagerAction) => Promise<void>,
  ): void;
  announceError?(errorKey: string): void;
};

export type DesktopLanguageManagerOptions = {
  adapter: LanguageManagerClientAdapter;
  catalog: LanguagePackCatalog;
  appVersion: string;
  host: DesktopLanguageManagerHost;
  copy: DesktopLanguageManagerCopy;
  createDownloadTransport: () => LanguagePackDownloadTransport;
  createVerifier: () => LanguagePackVerifier;
  onActivateInstalledLanguage?: (
    languageTag: string,
    version: string,
  ) => Promise<void>;
  translateError?: (key: string) => string;
};

export function displayDesktopLanguageName(
  languageTag: string,
  uiLocale = languageTag,
): string {
  try {
    const displayNames = new Intl.DisplayNames([uiLocale], {
      type: "language",
    });
    return displayNames.of(languageTag) ?? languageTag;
  } catch {
    return languageTag;
  }
}

export function buildDesktopLanguageManagerSurface(
  state: LanguageManagerUiState,
  catalog: LanguagePackCatalog,
  appVersion: string,
  copy: DesktopLanguageManagerCopy,
  translateError?: (key: string) => string,
): DesktopLanguageManagerSurface {
  const selectedRow =
    state.rows.find((row) => row.selected) ??
    state.rows.find((row) => row.languageTag === state.selectedLanguage);
  const uiLanguage = selectedRow?.languageTag ?? state.selectedLanguage;
  const direction = selectedRow?.direction ?? "ltr";

  const errorKey = state.errorKey;
  const statusText = errorKey
    ? (translateError?.(errorKey) ?? errorKey)
    : state.activeDownloadLanguage
      ? copy.downloading(
          displayDesktopLanguageName(state.activeDownloadLanguage, uiLanguage),
        )
      : copy.ready;

  const rows = state.rows.map((row) =>
    toDesktopRow(row, catalog, appVersion, uiLanguage, copy),
  );

  return {
    title: copy.title,
    uiLanguage,
    direction,
    status: state.status,
    statusText,
    errorKey,
    progressPercent: state.progressPercent,
    progressLabel: copy.downloadProgress,
    rows,
  };
}

function toDesktopRow(
  row: LanguageManagerRow,
  catalog: LanguagePackCatalog,
  appVersion: string,
  uiLanguage: string,
  copy: DesktopLanguageManagerCopy,
): DesktopLanguageManagerRow {
  const compatible = selectCompatiblePack(catalog, row.languageTag, appVersion);
  const action = getAction(row, compatible);
  const actionLabel = getActionLabel(action, copy);

  const removeAvailable =
    !row.selected && Boolean(row.installedPackageId && row.installedVersion);

  return {
    ...row,
    displayName: displayDesktopLanguageName(row.languageTag, uiLanguage),
    action,
    actionLabel,
    removeAvailable,
    removeAction:
      removeAvailable
        ? {
            kind: "remove-installed",
            packageId: row.installedPackageId!,
            version: row.installedVersion!,
          }
        : null,
  };
}

function getAction(
  row: LanguageManagerRow,
  compatible: LanguagePackCatalogItem | null,
): DesktopLanguageManagerAction {
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
  action: DesktopLanguageManagerAction,
  copy: DesktopLanguageManagerCopy,
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

function makeManifest(
  item: LanguagePackCatalogItem,
): LanguagePackDownloadManifest {
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

export class DesktopLanguageManagerView {
  private currentSurface: DesktopLanguageManagerSurface | null = null;
  private busyLanguage: string | null = null;

  constructor(private readonly options: DesktopLanguageManagerOptions) {}

  async mount(): Promise<void> {
    await this.refresh();
  }

  async refresh(): Promise<DesktopLanguageManagerSurface> {
    const state = await this.options.adapter.refresh();
    return this.render(stateToUiState(state));
  }

  surface(): DesktopLanguageManagerSurface | null {
    return this.currentSurface;
  }

  async dispatch(action: DesktopLanguageManagerAction): Promise<void> {
    if (this.busyLanguage) {
      return;
    }

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

  private render(state: LanguageManagerUiState): DesktopLanguageManagerSurface {
    const surface = buildDesktopLanguageManagerSurface(
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

  private async useInstalled(
    languageTag: string,
    version: string,
  ): Promise<void> {
    try {
      if (!this.options.onActivateInstalledLanguage) {
        throw new Error("LANGUAGE_ACTIVATION_NOT_CONFIGURED");
      }
      await this.options.onActivateInstalledLanguage(languageTag, version);
      await this.options.adapter.persistSelection(languageTag);
      await this.refresh();
    } catch (error) {
      await this.handleError(error);
    }
  }

  private async removeInstalled(
    packageId: string,
    version: string,
  ): Promise<void> {
    try {
      const next = await this.options.adapter.removeInstalledPack(
        packageId,
        version,
      );
      await this.render(next);
    } catch (error) {
      await this.handleError(error);
    }
  }

  private async download(
    languageTag: string,
    version: string,
  ): Promise<void> {
    const item = this.options.catalog.items.find(
      (candidate) =>
        candidate.languageTag === languageTag &&
        candidate.version === version,
    );
    if (!item) {
      await this.handleError(new Error("LANGUAGE_PACK_NOT_IN_CATALOG"));
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
              displayDesktopLanguageName(
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
      await this.handleError(error);
    } finally {
      this.busyLanguage = null;
    }
  }

  private async handleError(error: unknown): Promise<void> {
    const errorKey = error instanceof Error ? error.message : String(error);
    const current = this.currentSurface;
    if (current) {
      await this.render({
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
