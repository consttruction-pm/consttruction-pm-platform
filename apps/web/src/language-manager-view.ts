import type { LanguageManagerController } from "../../client-sync/src/language-manager-controller.js";
import type { LanguagePackCatalog } from "../../client-sync/src/language-pack-catalog.js";
import type { LanguagePackDownloadManifest } from "../../client-sync/src/language-pack-download.js";
import { isNewerPackAvailable, selectCompatiblePack } from "../../client-sync/src/language-pack-catalog.js";
import { displayLanguageName } from "./language-display-name.js";
import { toUiState, type LanguageManagerUiState } from "../../client-sync/src/language-manager-ui-contract.js";

export type LanguageManagerWebOptions = {
  root: HTMLElement;
  controller: LanguageManagerController;
  catalog: LanguagePackCatalog;
  appVersion: string;
  createDownloadTransport: () => Parameters<LanguageManagerController["download"]>[1];
  createVerifier: () => Parameters<LanguageManagerController["download"]>[2];
  onActivateInstalledLanguage?: (languageTag: string, version: string) => Promise<void>;
};

export class WebLanguageManagerView {
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

    const heading = document.createElement("h2");
    const currentLanguage = state.rows.find((row) => row.selected)?.languageTag ?? state.selectedLanguage;
    heading.textContent = displayLanguageName(currentLanguage);
    root.append(heading);

    const status = document.createElement("p");
    status.setAttribute("role", "status");
    status.textContent = state.errorMessage
      ? state.errorMessage
      : state.activeDownloadLanguage
        ? "Downloading " + state.activeDownloadLanguage + "…"
        : "Ready";
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
    table.setAttribute("aria-label", "Supported languages");

    const header = document.createElement("tr");
    for (const label of [
      "Language",
      "Locale",
      "Direction",
      "Installed",
      "Offline",
      "AI",
      "Voice In",
      "Voice Out",
      "Offline AI",
      "Action",
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
        row.direction.toUpperCase(),
        row.installedVersion ?? "—",
        row.offlineReady ? "Ready" : "No",
        row.aiText ? "Yes" : "No",
        row.voiceInput ? "Yes" : "No",
        row.voiceOutput ? "Yes" : "No",
        row.offlineAi ? "Yes" : "No",
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
        button.textContent = "Selected";
        button.disabled = true;
      } else if (row.installedVersion && row.verified && compatible &&
                 isNewerPackAvailable(row.installedVersion, compatible.version)) {
        button.textContent = "Update";
        button.addEventListener("click", () => {
          void this.download(compatible);
        });
      } else if (row.installedVersion && row.verified) {
        button.textContent = "Use";
        button.addEventListener("click", () => {
          void this.useInstalled(row.languageTag, row.installedVersion!);
        });
      } else if (compatible) {
        button.textContent = "Download";
        button.addEventListener("click", () => {
          void this.download(compatible);
        });
      } else {
        button.textContent = "Unavailable";
        button.disabled = true;
      }

      actionCell.append(button);

      if (!row.selected && row.installedVersion && row.verified && row.installedPackageId) {
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "Remove";
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
      await this.options.onActivateInstalledLanguage?.(languageTag, version);
      await this.options.controller.persistSelection(languageTag);
      await this.refresh();
    } catch (error) {
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
      await this.refresh();
    } catch (error) {
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
      await this.refresh();
    } catch (error) {
      this.options.root.dispatchEvent(
        new CustomEvent("language-manager-error", {
          detail: error instanceof Error ? error.message : String(error),
        }),
      );
      await this.refresh();
    }
  }
}
