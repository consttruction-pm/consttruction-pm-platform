import type { WorkspaceLocale } from "./workspace-model.js";
import { readStoredValue, writeStoredValue, type PreferenceStorage } from "./workspace-preferences.js";

/**
 * Named toolbar families. Visibility is a browser-local preference per user;
 * hiding a family never removes its commands from the menus, so no capability
 * becomes unreachable.
 */
export const WORKSPACE_TOOLBAR_GROUPS = [
  "workspace",
  "edit",
  "layout",
  "view",
  "project",
  "activities",
  "wbs",
  "gantt",
  "resources",
  "reports",
  "tools",
] as const;

export type WorkspaceToolbarGroup = typeof WORKSPACE_TOOLBAR_GROUPS[number];

export const WORKSPACE_TOOLBAR_STORAGE_KEY = "cubi:workspace-toolbars";

export const WORKSPACE_TOOLBAR_LABELS: Readonly<Record<WorkspaceLocale, Readonly<Record<WorkspaceToolbarGroup, string>>>> = {
  en: { workspace: "Workspace", edit: "Edit", layout: "Layout", view: "View", project: "Project", activities: "Activities", wbs: "WBS", gantt: "Gantt / Charts", resources: "Resources", reports: "Reports", tools: "Tools" },
  fa: { workspace: "محیط کار", edit: "ویرایش", layout: "چیدمان", view: "نما", project: "پروژه", activities: "فعالیت‌ها", wbs: "ساختار شکست", gantt: "گانت / نمودارها", resources: "منابع", reports: "گزارش‌ها", tools: "ابزارها" },
  de: { workspace: "Arbeitsbereich", edit: "Bearbeiten", layout: "Layout", view: "Ansicht", project: "Projekt", activities: "Vorgänge", wbs: "PSP", gantt: "Gantt / Diagramme", resources: "Ressourcen", reports: "Berichte", tools: "Werkzeuge" },
  zh: { workspace: "工作区", edit: "编辑", layout: "布局", view: "视图", project: "项目", activities: "活动", wbs: "WBS", gantt: "甘特图 / 图表", resources: "资源", reports: "报表", tools: "工具" },
  fr: { workspace: "Espace de travail", edit: "Édition", layout: "Disposition", view: "Affichage", project: "Projet", activities: "Activités", wbs: "WBS", gantt: "Gantt / graphiques", resources: "Ressources", reports: "Rapports", tools: "Outils" },
  ja: { workspace: "ワークスペース", edit: "編集", layout: "レイアウト", view: "表示", project: "プロジェクト", activities: "アクティビティ", wbs: "WBS", gantt: "ガント / グラフ", resources: "リソース", reports: "レポート", tools: "ツール" },
  ko: { workspace: "작업 공간", edit: "편집", layout: "레이아웃", view: "보기", project: "프로젝트", activities: "활동", wbs: "WBS", gantt: "간트 / 차트", resources: "자원", reports: "보고서", tools: "도구" },
  ar: { workspace: "مساحة العمل", edit: "تحرير", layout: "التخطيط", view: "عرض", project: "المشروع", activities: "الأنشطة", wbs: "هيكل العمل", gantt: "جانت / المخططات", resources: "الموارد", reports: "التقارير", tools: "الأدوات" },
  ru: { workspace: "Рабочая область", edit: "Правка", layout: "Макет", view: "Вид", project: "Проект", activities: "Работы", wbs: "СДР", gantt: "Гантт / диаграммы", resources: "Ресурсы", reports: "Отчёты", tools: "Инструменты" },
};

export function isWorkspaceToolbarGroup(value: string): value is WorkspaceToolbarGroup {
  return (WORKSPACE_TOOLBAR_GROUPS as readonly string[]).includes(value);
}

export function toolbarVisibilityStorageKey(userId: string): string {
  return `${WORKSPACE_TOOLBAR_STORAGE_KEY}:${encodeURIComponent(userId.trim())}`;
}

/** Hidden families only; every family is visible until the user hides it. */
export function readHiddenToolbarGroups(
  userId: string,
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceToolbarGroup[] {
  if (!userId.trim()) return [];
  const raw = readStoredValue(toolbarVisibilityStorageKey(userId), storage);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    const wanted = new Set(parsed.filter((value): value is string => typeof value === "string"));
    return WORKSPACE_TOOLBAR_GROUPS.filter((group) => wanted.has(group));
  } catch {
    return [];
  }
}

export function rememberHiddenToolbarGroups(
  userId: string,
  hidden: readonly WorkspaceToolbarGroup[],
  storage: PreferenceStorage | null = browserStorage(),
): void {
  if (!userId.trim()) return;
  const normalized = WORKSPACE_TOOLBAR_GROUPS.filter((group) => hidden.includes(group));
  writeStoredValue(toolbarVisibilityStorageKey(userId), JSON.stringify(normalized), storage);
}

export function toggleToolbarGroup(
  hidden: readonly WorkspaceToolbarGroup[],
  group: WorkspaceToolbarGroup,
): WorkspaceToolbarGroup[] {
  return hidden.includes(group)
    ? hidden.filter((item) => item !== group)
    : WORKSPACE_TOOLBAR_GROUPS.filter((item) => item === group || hidden.includes(item));
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
