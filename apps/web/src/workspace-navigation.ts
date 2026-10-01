import type { WorkspaceLocale, WorkspaceMenuKey, WorkspaceState } from "./workspace-model.js";

export type WorkspaceSurfaceStatus = "implemented" | "partial" | "preview";

export type WorkspaceNavigationItem = {
  key: WorkspaceMenuKey;
  status: WorkspaceSurfaceStatus;
  label: { en: string; fa: string };
  submenus: { en: string; fa: string }[];
};

export const WORKSPACE_NAVIGATION: readonly WorkspaceNavigationItem[] = [
  { key: "project", status: "partial", label: { en: "Project", fa: "پروژه" }, submenus: [{ en: "Project / WBS", fa: "پروژه / WBS" }, { en: "Details", fa: "جزئیات" }] },
  { key: "schedule", status: "implemented", label: { en: "Schedule", fa: "زمان‌بندی" }, submenus: [{ en: "Activity Grid", fa: "جدول فعالیت‌ها" }, { en: "Gantt Chart", fa: "گانت" }] },
  { key: "progress", status: "preview", label: { en: "Progress", fa: "پیشرفت" }, submenus: [{ en: "Progress Overview", fa: "نمای کلی پیشرفت" }, { en: "Progress Detail", fa: "جزئیات پیشرفت" }] },
  { key: "resources", status: "preview", label: { en: "Resources", fa: "منابع" }, submenus: [{ en: "Resources", fa: "منابع" }, { en: "Assignments", fa: "تخصیص‌ها" }] },
  { key: "cost", status: "preview", label: { en: "Cost", fa: "هزینه" }, submenus: [{ en: "Cost Overview", fa: "نمای کلی هزینه" }, { en: "Cost Detail", fa: "جزئیات هزینه" }] },
  { key: "documents", status: "partial", label: { en: "Documents", fa: "اسناد" }, submenus: [{ en: "Documents", fa: "اسناد" }, { en: "Evidence", fa: "مستندات" }] },
  { key: "reports", status: "preview", label: { en: "Reports", fa: "گزارش‌ها" }, submenus: [{ en: "Reports", fa: "گزارش‌ها" }, { en: "Print", fa: "چاپ" }] },
  { key: "control", status: "partial", label: { en: "Control", fa: "کنترل" }, submenus: [{ en: "Control Summary", fa: "خلاصه کنترل" }, { en: "Changes & Claims", fa: "تغییرات و ادعاها" }] },
  { key: "settings", status: "partial", label: { en: "Settings", fa: "تنظیمات" }, submenus: [{ en: "Language", fa: "زبان" }, { en: "Workspace", fa: "محیط کار" }] },
];

export function getWorkspaceNavigation(activeMenu: WorkspaceMenuKey): WorkspaceNavigationItem {
  const item = WORKSPACE_NAVIGATION.find((entry) => entry.key === activeMenu);
  if (!item) throw new Error("WORKSPACE_MENU_NOT_FOUND");
  return item;
}

export function getWorkspaceNavigationLabel(item: WorkspaceNavigationItem, locale: WorkspaceLocale): string {
  return item.label[locale];
}

export function getWorkspaceNavigationStatus(state: WorkspaceState): WorkspaceSurfaceStatus {
  return getWorkspaceNavigation(state.activeMenu).status;
}
