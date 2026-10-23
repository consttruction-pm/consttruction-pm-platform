import type { WorkspaceLocale } from "./workspace-model.js";
import { translateWorkspaceText } from "./workspace-localization.js";

export type WorkspaceShellLabels = {
  status: string;
  switchToEnglish: string;
  switchToPersian: string;
};

const labels: Partial<Record<WorkspaceLocale, WorkspaceShellLabels>> = {
  en: {
    status: "Web shell · Authenticated workspace",
    switchToEnglish: "Switch to English",
    switchToPersian: "Switch to Persian",
  },
  fa: {
    status: "پوسته وب · محیط کار احراز هویت‌شده",
    switchToEnglish: "تغییر به انگلیسی",
    switchToPersian: "تغییر به فارسی",
  },
};

export function getWorkspaceShellLabels(locale: WorkspaceLocale): WorkspaceShellLabels {
  const baseline = labels[locale] ?? labels.en!;
  return {
    status: translateWorkspaceText(locale, "shell.status", baseline.status),
    switchToEnglish: translateWorkspaceText(locale, "shell.switchToEnglish", baseline.switchToEnglish),
    switchToPersian: translateWorkspaceText(locale, "shell.switchToPersian", baseline.switchToPersian),
  };
}
