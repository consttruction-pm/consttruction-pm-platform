import type { WorkspaceLocale } from "./workspace-model.js";
import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/**
 * Two authorized presentation skins over one workspace implementation.
 * Classic reproduces the documented workstation appearance; Modern 3D uses the
 * CUBI palette with layered Windows 11 inspired surfaces. The skin is a token
 * set only: it never changes commands, layouts, data or calculations.
 */
export type WorkspaceTheme = "classic" | "modern";

export const WORKSPACE_THEME_STORAGE_KEY = "cubi:workspace-theme";
export const DEFAULT_WORKSPACE_THEME: WorkspaceTheme = "classic";

export function isWorkspaceTheme(value: unknown): value is WorkspaceTheme {
  return value === "classic" || value === "modern";
}

export function readWorkspaceTheme(
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceTheme {
  const raw = readStoredValue(WORKSPACE_THEME_STORAGE_KEY, storage);
  return isWorkspaceTheme(raw) ? raw : DEFAULT_WORKSPACE_THEME;
}

export function rememberWorkspaceTheme(
  theme: WorkspaceTheme,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  writeStoredValue(WORKSPACE_THEME_STORAGE_KEY, theme, storage);
}

/** The token set is selected on the document root so every surface follows it. */
export function applyWorkspaceTheme(
  theme: WorkspaceTheme,
  root: HTMLElement | null = defaultRoot(),
): void {
  root?.setAttribute("data-cubi-theme", theme);
}

export const WORKSPACE_THEME_LABELS: Readonly<Record<WorkspaceLocale, { classic: string; modern: string }>> = {
  en: { classic: "CUBI Classic — Version 26 Reference", modern: "CUBI Modern 3D" },
  fa: { classic: "CUBI کلاسیک — مرجع نسخه ۲۶", modern: "CUBI مدرن سه‌بعدی" },
  de: { classic: "CUBI Classic — Referenz Version 26", modern: "CUBI Modern 3D" },
  zh: { classic: "CUBI 经典 — 版本 26 参考", modern: "CUBI 现代 3D" },
  fr: { classic: "CUBI Classique — référence version 26", modern: "CUBI Moderne 3D" },
  ja: { classic: "CUBI クラシック — バージョン 26 リファレンス", modern: "CUBI モダン 3D" },
  ko: { classic: "CUBI 클래식 — 버전 26 참조", modern: "CUBI 모던 3D" },
  ar: { classic: "CUBI الكلاسيكي — مرجع الإصدار 26", modern: "CUBI الحديث ثلاثي الأبعاد" },
  ru: { classic: "CUBI Классический — эталон версии 26", modern: "CUBI Современный 3D" },
};

export function workspaceThemeLabels(
  locale: WorkspaceLocale,
): { classic: string; modern: string } {
  return WORKSPACE_THEME_LABELS[locale] ?? WORKSPACE_THEME_LABELS.en;
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function defaultRoot(): HTMLElement | null {
  return typeof document === "undefined" ? null : document.documentElement;
}
