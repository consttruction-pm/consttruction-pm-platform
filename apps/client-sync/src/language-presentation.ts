import type { LanguageDirection, LanguageTypography, ResolvedLanguage } from "./language.ts";

export type LanguagePresentationState = {
  languageTag: string;
  locale: string;
  direction: LanguageDirection;
  offline: boolean;
  packVersion: string | null;
  typography: LanguageTypography;
};

export function toPresentationState(resolved: ResolvedLanguage): LanguagePresentationState {
  return {
    ...resolved,
    typography: {
      ...resolved.typography,
      fallbackFamilies: [...resolved.typography.fallbackFamilies],
    },
  };
}
