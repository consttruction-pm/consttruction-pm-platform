import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDirection,
  getWorkspaceLocaleDisplayName,
} from "./workspace-localization.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export type WorkspaceLanguageOption = Readonly<{
  value: string;
  label: string;
  direction: "ltr" | "rtl";
}>;

/** The language selector is driven by the single registered CUBI locale list. */
export function getWorkspaceLanguageOptions(): readonly WorkspaceLanguageOption[] {
  return getAvailableWorkspaceLocales().map((locale) => ({
    value: locale,
    label: getWorkspaceLocaleDisplayName(locale),
    direction: getWorkspaceLocaleDirection(locale),
  }));
}

/** A compact selector embedded in the authenticated Visual Workspace chrome. */
export function createWorkspaceLanguageSelect(
  locale: string,
  onSelect: (locale: string) => void,
): HTMLSelectElement {
  const select = document.createElement("select");
  select.className = "cp-workspace-language";
  select.dataset.workspaceLanguage = locale;
  select.setAttribute("aria-label", translateWorkspaceUiText(locale, "Language", "زبان"));
  select.title = translateWorkspaceUiText(locale, "Language", "زبان");
  for (const optionData of getWorkspaceLanguageOptions()) {
    const option = document.createElement("option");
    option.value = optionData.value;
    option.lang = optionData.value;
    option.dir = optionData.direction;
    option.textContent = optionData.label;
    option.selected = optionData.value === locale;
    select.append(option);
  }
  select.addEventListener("change", () => onSelect(select.value));
  return select;
}
