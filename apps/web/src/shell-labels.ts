import type { WorkspaceLocale } from "./workspace-model.js";

export type WorkspaceShellLabels = {
  status: string;
  switchToEnglish: string;
  switchToPersian: string;
};

const labels: Record<WorkspaceLocale, WorkspaceShellLabels> = {
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
  return labels[locale];
}
