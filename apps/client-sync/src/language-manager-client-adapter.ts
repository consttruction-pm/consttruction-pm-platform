import type {
  LanguageManagerController,
  LanguageManagerState,
} from "./language-manager-controller.ts";
import type {
  LanguagePackDownloadManifest,
  LanguagePackDownloadProgress,
  LanguagePackDownloadTransport,
  LanguagePackVerifier,
} from "./language-pack-download.ts";
import type { LanguageManagerUiState } from "./language-manager-ui-contract.ts";
import { toUiState } from "./language-manager-ui-contract.ts";

export class LanguageManagerClientAdapter {
  private last: LanguageManagerUiState | null = null;

  constructor(private readonly controller: LanguageManagerController) {}

  async refresh(): Promise<LanguageManagerUiState> {
    const state = await this.controller.refresh();
    return this.capture(state);
  }

  select(languageTag: string): LanguageManagerUiState {
    const state = this.controller.select(languageTag);
    return this.capture({
      selectedLanguage: state.languageTag,
      items: this.last?.rows.map((row) => ({
        languageTag: row.languageTag,
        direction: row.direction,
        locale: row.locale,
        installedPackageId: row.installedPackageId,
        installedVersion: row.installedVersion,
        verified: row.verified,
        offlineReady: row.offlineReady,
        capabilities: {
          ui: row.offlineReady,
          help: false,
          aiText: row.aiText,
          voiceInput: row.voiceInput,
          voiceOutput: row.voiceOutput,
          offlineAi: row.offlineAi,
        },
      })) ?? [],
    });
  }

  async persistSelection(languageTag: string): Promise<LanguageManagerUiState> {
    return this.capture(await this.controller.persistSelection(languageTag));
  }

  async removeInstalledPack(
    packageId: string,
    version: string,
  ): Promise<LanguageManagerUiState> {
    return this.capture(
      await this.controller.removeInstalledPack(packageId, version),
    );
  }

  async download(
    manifest: LanguagePackDownloadManifest,
    transport: LanguagePackDownloadTransport,
    verifier: LanguagePackVerifier,
    onProgress?: (progress: LanguagePackDownloadProgress) => void,
  ): Promise<LanguageManagerUiState> {
    return this.capture(
      await this.controller.download(
        manifest,
        transport,
        verifier,
        onProgress,
      ),
    );
  }

  snapshot(): LanguageManagerUiState | null {
    return this.last;
  }

  private capture(state: LanguageManagerState): LanguageManagerUiState {
    // Controller state is the source of truth; presentation stays framework-neutral.
    const currentItems = this.last?.rows ?? [];
    const lookup = new Map(
      currentItems.map((row) => [row.languageTag, row]),
    );
    const viewState = toUiState({
      selectedLanguage: state.selectedLanguage,
      downloading: null,
      progress: null,
      error: null,
      items: state.items.map((item) => ({
        installedPackageId:
          item.installedPackageId ??
          lookup.get(item.languageTag)?.installedPackageId ??
          null,
        languageTag: item.languageTag,
        direction: item.direction,
        locale: item.locale,
        installedVersion: item.installedVersion,
        verified: item.verified,
        offlineReady: item.offlineReady,
        capabilities: item.capabilities,
      })),
    });
    this.last = viewState;
    return viewState;
  }
}
