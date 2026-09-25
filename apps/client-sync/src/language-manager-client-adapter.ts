import type { LanguageManagerController } from "./language-manager-controller.ts";
import type {
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
    return this.capture(await this.controller.refresh());
  }

  async select(languageTag: string): Promise<LanguageManagerUiState> {
    this.controller.select(languageTag);
    return this.capture(await this.controller.refresh());
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
    const viewState = toUiState({
      selectedLanguage: state.selectedLanguage,
      downloading: null,
      progress: null,
      error: null,
      items: state.items,
    });
    this.last = viewState;
    return viewState;
  }
}
