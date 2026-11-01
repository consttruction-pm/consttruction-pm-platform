import type { WorkspaceLocale } from "./workspace-model.js";
import { translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";

export type WorkspaceShellLabels = {
  status: string;
  switchToEnglish: string;
  switchToPersian: string;
  switchToJalali: string;
  switchToGregorian: string;
};

const labels: Partial<Record<WorkspaceLocale, WorkspaceShellLabels>> = {
  en: {
    status: "Web shell · Authenticated workspace",
    switchToEnglish: "Switch to English",
    switchToPersian: "Switch to Persian",
    switchToJalali: "Show dates in the Jalali calendar",
    switchToGregorian: "Show dates in the Gregorian calendar",
  },
  fa: {
    status: "پوسته وب · محیط کار احراز هویت‌شده",
    switchToEnglish: "تغییر به انگلیسی",
    switchToPersian: "تغییر به فارسی",
    switchToJalali: "نمایش تاریخ‌ها در تقویم هجری شمسی",
    switchToGregorian: "نمایش تاریخ‌ها در تقویم میلادی",
  },
};

export function getWorkspaceShellLabels(locale: WorkspaceLocale): WorkspaceShellLabels {
  const english = labels.en!;
  const persian = labels.fa!;
  const translate = (key: keyof WorkspaceShellLabels): string => {
    const packed = translateWorkspaceText(locale, `shell.${key}`, "");
    if (packed) return packed;
    return translateWorkspaceUiText(locale, english[key], persian[key]);
  };
  return {
    status: translate("status"),
    switchToEnglish: translate("switchToEnglish"),
    switchToPersian: translate("switchToPersian"),
    switchToJalali: translate("switchToJalali"),
    switchToGregorian: translate("switchToGregorian"),
  };
}
