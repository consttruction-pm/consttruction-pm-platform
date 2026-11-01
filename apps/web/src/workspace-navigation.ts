import type { WorkspaceLocale, WorkspaceMenuKey, WorkspaceState } from "./workspace-model.js";
import { translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";

export type WorkspaceSurfaceStatus = "implemented" | "partial" | "preview";

export type WorkspaceNavigationItem = {
  key: WorkspaceMenuKey;
  status: WorkspaceSurfaceStatus;
  label: { en: string; fa: string };
  statusLabel: { en: string; fa: string };
  submenus: { en: string; fa: string }[];
};

export const WORKSPACE_NAVIGATION: readonly WorkspaceNavigationItem[] = [
  { key: "project", status: "partial", label: { en: "Project", fa: "پروژه" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Project / WBS", fa: "پروژه / WBS" }, { en: "Details", fa: "جزئیات" }, { en: "Import / Export", fa: "ورود / خروجی" }] },
  { key: "schedule", status: "implemented", label: { en: "Schedule", fa: "زمان‌بندی" }, statusLabel: { en: "Implemented", fa: "پیاده‌سازی‌شده" }, submenus: [{ en: "Activity Grid", fa: "جدول فعالیت‌ها" }, { en: "Gantt Chart", fa: "گانت" }, { en: "Relationships & lag", fa: "روابط و وقفه" }, { en: "Calendars & work time", fa: "تقویم‌ها و ساعات کاری" }, { en: "Schedule options & Data Date", fa: "تنظیمات زمان‌بندی و تاریخ داده" }, { en: "Resources & leveling", fa: "منابع و تسطیح" }, { en: "Progress & baselines", fa: "پیشرفت و مبناها" }, { en: "Run Schedule", fa: "اجرای زمان‌بندی" }, { en: "Formula editor", fa: "ویرایشگر فرمول" }, { en: "Code Reference", fa: "مرجع کد" }, { en: "Option catalogue", fa: "فهرست گزینه‌ها" }, { en: "Formula contracts", fa: "قراردادهای محاسباتی" }, { en: "Documentation review", fa: "بازبینی مستندات" }] },
  { key: "progress", status: "preview", label: { en: "Progress", fa: "پیشرفت" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Progress Overview", fa: "نمای کلی پیشرفت" }, { en: "Progress Detail", fa: "جزئیات پیشرفت" }] },
  { key: "resources", status: "partial", label: { en: "Resources", fa: "منابع" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Max units / time", fa: "حداکثر واحد / زمان" }, { en: "Assignments", fa: "تخصیص‌ها" }] },
  { key: "cost", status: "preview", label: { en: "Cost", fa: "هزینه" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Cost Overview", fa: "نمای کلی هزینه" }, { en: "Cost Detail", fa: "جزئیات هزینه" }] },
  { key: "documents", status: "partial", label: { en: "Documents", fa: "اسناد" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Documents", fa: "اسناد" }, { en: "Evidence", fa: "مستندات" }] },
  { key: "reports", status: "preview", label: { en: "Reports", fa: "گزارش‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Reports", fa: "گزارش‌ها" }, { en: "Print", fa: "چاپ" }] },
  { key: "control", status: "partial", label: { en: "Control", fa: "کنترل" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Control Summary", fa: "خلاصه کنترل" }, { en: "Changes & Claims", fa: "تغییرات و ادعاها" }] },
  { key: "settings", status: "partial", label: { en: "Settings", fa: "تنظیمات" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Language", fa: "زبان" }, { en: "Workspace", fa: "محیط کار" }] },
];

export function getWorkspaceNavigation(activeMenu: WorkspaceMenuKey): WorkspaceNavigationItem {
  const item = WORKSPACE_NAVIGATION.find((entry) => entry.key === activeMenu);
  if (!item) throw new Error("WORKSPACE_MENU_NOT_FOUND");
  return item;
}

export function getWorkspaceNavigationLabel(item: WorkspaceNavigationItem, locale: WorkspaceLocale): string {
  return translateWorkspaceText(
    locale,
    `navigation.${item.key}`,
    translateWorkspaceUiText(locale, item.label.en, item.label.fa),
  );
}

export function getWorkspaceNavigationStatusLabel(item: WorkspaceNavigationItem, locale: WorkspaceLocale): string {
  return translateWorkspaceText(
    locale,
    `navigation.${item.key}.status`,
    translateWorkspaceUiText(locale, item.statusLabel.en, item.statusLabel.fa),
  );
}

export function getWorkspaceNavigationSubmenuLabel(item: WorkspaceNavigationItem, index: number, locale: WorkspaceLocale): string {
  const submenu = item.submenus[index];
  if (!submenu) throw new Error("WORKSPACE_SUBMENU_NOT_FOUND");
  return translateWorkspaceText(
    locale,
    `navigation.${item.key}.submenu.${index}`,
    translateWorkspaceUiText(locale, submenu.en, submenu.fa),
  );
}

export function getWorkspaceNavigationStatus(state: WorkspaceState): WorkspaceSurfaceStatus {
  return getWorkspaceNavigation(state.activeMenu).status;
}
