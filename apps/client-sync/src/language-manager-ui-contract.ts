import type { LanguageManagerViewState } from "./language-manager-view-model.ts";

export type LanguageManagerRow = {
  languageTag: string;
  locale: string;
  direction: "ltr" | "rtl";
  installedPackageId: string | null;
  installedVersion: string | null;
  verified: boolean;
  offlineReady: boolean;
  aiText: boolean;
  voiceInput: boolean;
  voiceOutput: boolean;
  offlineAi: boolean;
  selected: boolean;
};

export type LanguageManagerUiState = {
  selectedLanguage: string;
  rows: readonly LanguageManagerRow[];
  activeDownloadLanguage: string | null;
  progressPercent: number | null;
  status: "ready" | "downloading" | "error";
  errorMessage: string | null;
};

export function toUiState(
  state: LanguageManagerViewState,
): LanguageManagerUiState {
  const progress = state.progress;
  const total = progress?.totalBytes ?? 0;
  const received = progress?.bytesReceived ?? 0;
  const progressPercent =
    total > 0 ? Math.min(100, Math.round((received / total) * 100)) : null;

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
    activeDownloadLanguage: state.downloading,
    progressPercent,
    status: state.error
      ? "error"
      : state.downloading
        ? "downloading"
        : "ready",
    errorMessage: state.error,
  };
}
