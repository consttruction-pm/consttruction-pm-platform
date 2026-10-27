import type { WorkspaceLocale } from "./workspace-model.js";
import { translateWorkspaceText } from "./workspace-localization.js";

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
  const baseline = labels[locale] ?? labels.en!;
  return {
    status: translateWorkspaceText(locale, "shell.status", baseline.status),
    switchToEnglish: translateWorkspaceText(locale, "shell.switchToEnglish", baseline.switchToEnglish),
    switchToPersian: translateWorkspaceText(locale, "shell.switchToPersian", baseline.switchToPersian),
    switchToJalali: translateWorkspaceText(locale, "shell.switchToJalali", baseline.switchToJalali),
    switchToGregorian: translateWorkspaceText(locale, "shell.switchToGregorian", baseline.switchToGregorian),
  };
}
