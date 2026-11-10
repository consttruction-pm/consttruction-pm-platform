import type { WorkspaceLocale } from "./workspace-model.js";
import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/** Presentation-only skins over one CUBI workspace renderer. */
export const WORKSPACE_THEME_IDS = ["classic", "modern", "graphite", "arctic", "copper", "midnight"] as const;
export type WorkspaceTheme = typeof WORKSPACE_THEME_IDS[number];
export type WorkspaceThemeLabels = Readonly<Record<WorkspaceTheme, string>>;

export const WORKSPACE_THEME_STORAGE_KEY = "cubi:workspace-theme";
export const DEFAULT_WORKSPACE_THEME: WorkspaceTheme = "classic";

export function isWorkspaceTheme(value: unknown): value is WorkspaceTheme {
  return typeof value === "string" && (WORKSPACE_THEME_IDS as readonly string[]).includes(value);
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

/** Apply the selected palette and its shared surface/color-scheme mode. */
export function applyWorkspaceTheme(
  theme: WorkspaceTheme,
  root: HTMLElement | null = defaultRoot(),
): void {
  if (!root) return;
  root.setAttribute("data-cubi-theme", theme);
  if (theme === "classic") root.removeAttribute("data-cubi-theme-surface");
  else root.setAttribute("data-cubi-theme-surface", "layered");
  root.setAttribute("data-cubi-color-scheme",
    theme === "graphite" || theme === "midnight" ? "dark" : "light");
}

export const WORKSPACE_THEME_LABELS: Readonly<Record<WorkspaceLocale, WorkspaceThemeLabels>> = {
  en: { classic: "CUBI Classic — Version 26 Reference", modern: "CUBI Modern 3D", graphite: "CUBI Graphite — Dark", arctic: "CUBI Arctic — Light", copper: "CUBI Copper — Warm", midnight: "CUBI Midnight — Deep" },
  fa: { classic: "کوبی کلاسیک — مرجع نسخه ۲۶", modern: "کوبی مدرن سه‌بعدی", graphite: "کوبی گرافیت — تیره", arctic: "کوبی قطبی — روشن", copper: "کوبی مس — گرم", midnight: "کوبی نیمه‌شب — عمیق" },
  de: { classic: "CUBI Classic — Referenz Version 26", modern: "CUBI Modern 3D", graphite: "CUBI Graphite — Dunkel", arctic: "CUBI Arctic — Hell", copper: "CUBI Copper — Warm", midnight: "CUBI Midnight — Tiefblau" },
  zh: { classic: "CUBI 经典 — 版本 26 参考", modern: "CUBI 现代 3D", graphite: "CUBI 石墨 — 深色", arctic: "CUBI 极地 — 浅色", copper: "CUBI 铜色 — 暖色", midnight: "CUBI 午夜 — 深蓝" },
  fr: { classic: "CUBI Classique — référence version 26", modern: "CUBI Moderne 3D", graphite: "CUBI Graphite — sombre", arctic: "CUBI Arctique — clair", copper: "CUBI Cuivre — chaleureux", midnight: "CUBI Minuit — bleu profond" },
  ja: { classic: "CUBI クラシック — バージョン 26 リファレンス", modern: "CUBI モダン 3D", graphite: "CUBI グラファイト — ダーク", arctic: "CUBI アークティック — ライト", copper: "CUBI カッパー — ウォーム", midnight: "CUBI ミッドナイト — ディープ" },
  ko: { classic: "CUBI 클래식 — 버전 26 참조", modern: "CUBI 모던 3D", graphite: "CUBI 그래파이트 — 다크", arctic: "CUBI 아크틱 — 라이트", copper: "CUBI 코퍼 — 웜", midnight: "CUBI 미드나이트 — 딥" },
  ar: { classic: "CUBI الكلاسيكي — مرجع الإصدار 26", modern: "CUBI الحديث ثلاثي الأبعاد", graphite: "CUBI جرافيت — داكن", arctic: "CUBI قطبي — فاتح", copper: "CUBI نحاسي — دافئ", midnight: "CUBI منتصف الليل — أزرق عميق" },
  ru: { classic: "CUBI Классический — эталон версии 26", modern: "CUBI Современный 3D", graphite: "CUBI Графит — тёмный", arctic: "CUBI Арктика — светлый", copper: "CUBI Медь — тёплый", midnight: "CUBI Полночь — глубокий синий" },
};

export function workspaceThemeLabels(locale: WorkspaceLocale): WorkspaceThemeLabels {
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
