import type { LanguagePresentationState } from "../../client-sync/src/language-presentation.js";

export function applyLanguagePresentation(
  state: LanguagePresentationState,
  documentRef: Pick<Document, "documentElement"> = document,
): void {
  documentRef.documentElement.lang = state.languageTag;
  documentRef.documentElement.dir = state.direction;
}
