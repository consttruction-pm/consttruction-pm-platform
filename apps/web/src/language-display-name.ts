export function displayLanguageName(
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
