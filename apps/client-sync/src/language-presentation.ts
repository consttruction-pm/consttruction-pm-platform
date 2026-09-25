import type { LanguageDirection, ResolvedLanguage } from "./language.ts";

export type LanguagePresentationState = {
  languageTag: string;
  locale: string;
  direction: LanguageDirection;
  offline: boolean;
  packVersion: string | null;
};

export function toPresentationState(
  resolved: ResolvedLanguage,
): LanguagePresentationState {
  return {
    languageTag: resolved.languageTag,
    locale: resolved.locale,
    direction: resolved.direction,
    offline: resolved.offline,
    packVersion: resolved.packVersion,
  };
}
