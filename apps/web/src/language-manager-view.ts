import type { LanguageManagerController } from "../../client-sync/src/language-manager-controller.js";
import type { LanguagePackCatalog } from "../../client-sync/src/language-pack-catalog.js";
import type { LanguagePackDownloadManifest } from "../../client-sync/src/language-pack-download.js";
import { isNewerPackAvailable, selectCompatiblePack } from "../../client-sync/src/language-pack-catalog.js";
import { displayLanguageName } from "./language-display-name.js";
import { toUiState, type LanguageManagerUiState } from "../../client-sync/src/language-manager-ui-contract.js";

export type LanguageManagerCopy = {
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
  rtl: string;
  ltr: string;
};

export type LanguageManagerWebOptions = {
  root: HTMLElement;
  controller: LanguageManagerController;
  catalog: LanguagePackCatalog;
  appVersion: string;
  createDownloadTransport: () => Parameters<LanguageManagerController["download"]>[1];
  createVerifier: () => Parameters<LanguageManagerController["download"]>[2];
  copy: LanguageManagerCopy;
  translateError?: (key: string) => string;
  onActivateInstalledLanguage?: (languageTag: string, version: string) => Promise<void>;
};

export class WebLanguageManagerView {
  private localErrorKey: string | null = null;

  constructor(private readonly options: LanguageManagerWebOptions) {}

  async mount(): Promise<void> {
    this.options.root.setAttribute("data-language-manager", "true");
    await this.refresh();
  }

  async refresh(): Promise<void> {
    const state = toUiState(await this.options.controller.refresh());
    this.render(state);
  }

  private render(state: LanguageManagerUiState): void {
    const { root, catalog, appVersion } = this.options;

    root.replaceChildren();

    const copy = this.options.copy;
    const heading = document.createElement("h2");
    const currentLanguage = state.rows.find((row) => row.selected)?.languageTag ?? state.selectedLanguage;
    heading.textContent = copy.title;
    root.append(heading);

    const status = document.createElement("p");
    status.setAttribute("role", "status");
    const errorKey = this.localErrorKey ?? state.errorKey;
    status.textContent = errorKey
      ? (this.options.translateError?.(errorKey) ?? errorKey)
      : state.activeDownloadLanguage
        ? copy.downloading(displayLanguageName(state.activeDownloadLanguage, currentLanguage))
        : copy.ready;
    root.append(status);

    if (state.progressPercent !== null) {
      const progress = document.createElement("progress");
      progress.max = 100;
      progress.value = state.progressPercent;
      progress.setAttribute(
        "aria-label",
        "Language pack download progress",
      );
      root.append(progress);
    }

    const table = document.createElement("table");
    table.setAttribute("aria-label", copy.supportedLanguages);

    const header = document.createElement("tr");
    for (const label of [
      copy.language,
      copy.locale,
      copy.direction,
      copy.installed,
      copy.offline,
      copy.ai,
      copy.voiceIn,
      copy.voiceOut,
      copy.offlineAi,
      copy.use,
    ]) {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = label;
      header.append(cell);
    }
    const thead = document.createElement("thead");
    thead.append(header);
    table.append(thead);

    const body = document.createElement("tbody");
    for (const row of state.rows) {
      const tr = document.createElement("tr");
      tr.dataset.languageTag = row.languageTag;
      tr.dir = row.direction;

      const values = [
        displayLanguageName(row.languageTag, currentLanguage),
        row.locale,
        row.direction === "rtl" ? copy.rtl : copy.ltr,
        row.installedVersion ?? copy.missing,
        row.offlineReady ? copy.ready : copy.no,
        row.aiText ? copy.yes : copy.no,
        row.voiceInput ? copy.yes : copy.no,
        row.voiceOutput ? copy.yes : copy.no,
        row.offlineAi ? copy.yes : copy.no,
      ];

      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        tr.append(cell);
      }

      const actionCell = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";

      const compatible = selectCompatiblePack(
        catalog,
        row.languageTag,
        appVersion,
      );

      if (row.selected) {
        button.textContent = copy.selected;
        button.disabled = true;
      } else if (row.installedVersion && row.verified && compatible &&
                 isNewerPackAvailable(row.installedVersion, compatible.version)) {
        button.textContent = copy.update;
        button.addEventListener("click", () => {
          void this.download(compatible);
        });
      } else if (row.installedVersion && row.verified) {
        button.textContent = copy.use;
        button.addEventListener("click", () => {
          void this.useInstalled(row.languageTag, row.installedVersion!);
        });
      } else if (compatible) {
        button.textContent = copy.download;
        button.addEventListener("click", () => {
          void this.download(compatible);
        });
      } else {
        button.textContent = copy.unavailable;
        button.disabled = true;
      }

      actionCell.append(button);

      if (!row.selected && row.installedVersion && row.verified && row.installedPackageId) {
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = copy.remove;
        removeButton.addEventListener("click", () => {
          void this.removeInstalled(
            row.installedPackageId!,
            row.installedVersion!,
          );
        });
        actionCell.append(removeButton);
      }
      tr.append(actionCell);
      body.append(tr);
    }

    table.append(body);
    root.append(table);
  }

  private async useInstalled(languageTag: string, version: string): Promise<void> {
    try {
      if (!this.options.onActivateInstalledLanguage) {
        throw new Error("LANGUAGE_ACTIVATION_NOT_CONFIGURED");
      }
      await this.options.onActivateInstalledLanguage(languageTag, version);
      await this.options.controller.persistSelection(languageTag);
      this.localErrorKey = null;
      await this.refresh();
    } catch (error) {
      const errorKey = error instanceof Error ? error.message : String(error);
      this.localErrorKey = errorKey;
      this.options.root.dispatchEvent(
        new CustomEvent("language-manager-error", {
          detail: error instanceof Error ? error.message : String(error),
        }),
      );
    }
  }

  private async removeInstalled(packageId: string, version: string): Promise<void> {
    try {
      await this.options.controller.removeInstalledPack(packageId, version);
      this.localErrorKey = null;
      await this.refresh();
    } catch (error) {
      const errorKey = error instanceof Error ? error.message : String(error);
      this.localErrorKey = errorKey;
      this.options.root.dispatchEvent(
        new CustomEvent("language-manager-error", {
          detail: error instanceof Error ? error.message : String(error),
        }),
      );
    }
  }

  private async download(
    item: LanguagePackCatalog["items"][number],
  ): Promise<void> {
    const manifest: LanguagePackDownloadManifest = {
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

    try {
      await this.options.controller.download(
        manifest,
        this.options.createDownloadTransport(),
        this.options.createVerifier(),
        (progress) => {
          const percent =
            progress.totalBytes > 0
              ? Math.min(
                  100,
                  Math.round(
                    (progress.bytesReceived / progress.totalBytes) * 100,
                  ),
                )
              : null;

          const event = new CustomEvent("language-manager-progress", {
            detail: {
              languageTag: progress.languageTag,
              version: progress.version,
              phase: progress.phase,
              percent,
            },
          });
          this.options.root.dispatchEvent(event);
        },
      );
      this.localErrorKey = null;
      await this.refresh();
    } catch (error) {
      const errorKey = error instanceof Error ? error.message : String(error);
      this.localErrorKey = errorKey;
      this.options.root.dispatchEvent(
        new CustomEvent("language-manager-error", {
          detail: error instanceof Error ? error.message : String(error),
        }),
      );
      await this.refresh();
    }
  }
}
