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
  { key: "wbs", status: "partial", label: { en: "WBS", fa: "ساختار شکست" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "WBS Register", fa: "فهرست ساختار شکست" }, { en: "WBS Details", fa: "جزئیات ساختار شکست" }, { en: "WBS Chart", fa: "نمودار ساختار شکست" }] },
  { key: "schedule", status: "partial", label: { en: "Schedule", fa: "زمان‌بندی" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Activity Grid", fa: "جدول فعالیت‌ها" }, { en: "Gantt Chart", fa: "گانت" }, { en: "Relationships & lag", fa: "روابط و وقفه" }, { en: "Calendars & work time", fa: "تقویم‌ها و ساعات کاری" }, { en: "Schedule options & Data Date", fa: "تنظیمات زمان‌بندی و تاریخ داده" }, { en: "Resources & leveling", fa: "منابع و تسطیح" }, { en: "Progress & baselines", fa: "پیشرفت و مبناها" }, { en: "Run Schedule", fa: "اجرای زمان‌بندی" }, { en: "Formula editor", fa: "ویرایشگر فرمول" }, { en: "Code Reference", fa: "مرجع کد" }, { en: "Option catalogue", fa: "فهرست گزینه‌ها" }, { en: "Formula contracts", fa: "قراردادهای محاسباتی" }, { en: "Documentation review", fa: "بازبینی مستندات" }] },
  { key: "progress", status: "preview", label: { en: "Progress", fa: "پیشرفت" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Progress Overview", fa: "نمای کلی پیشرفت" }, { en: "Progress Detail", fa: "جزئیات پیشرفت" }] },
  { key: "resources", status: "partial", label: { en: "Resources", fa: "منابع" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Resource Register", fa: "فهرست منابع" }, { en: "Max units / time", fa: "حداکثر واحد / زمان" }, { en: "Assignments", fa: "تخصیص‌ها" }, { en: "Resource Codes", fa: "کدهای منابع" }, { en: "Roles", fa: "نقش‌ها" }] },
  { key: "assignments", status: "preview", label: { en: "Resource Assignments", fa: "تخصیص منابع" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Assignment Register", fa: "فهرست تخصیص‌ها" }, { en: "Resource Usage", fa: "مصرف منابع" }, { en: "Assignment Details", fa: "جزئیات تخصیص" }] },
  { key: "roles", status: "preview", label: { en: "Roles", fa: "نقش‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Role Register", fa: "فهرست نقش‌ها" }, { en: "Rates & Limits", fa: "نرخ‌ها و محدودیت‌ها" }, { en: "Assignments", fa: "تخصیص‌ها" }] },
  { key: "calendars", status: "partial", label: { en: "Calendars", fa: "تقویم‌ها" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Calendar Register", fa: "فهرست تقویم‌ها" }, { en: "Workweek & Shifts", fa: "هفته کاری و شیفت‌ها" }, { en: "Exceptions & Holidays", fa: "استثناها و تعطیلات" }, { en: "Assignments", fa: "تخصیص‌ها" }] },
  { key: "cost", status: "preview", label: { en: "Cost", fa: "هزینه" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Cost Overview", fa: "نمای کلی هزینه" }, { en: "Cost Detail", fa: "جزئیات هزینه" }] },
  { key: "expenses", status: "preview", label: { en: "Expenses", fa: "هزینه‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Expense Register", fa: "فهرست هزینه‌ها" }, { en: "Cost Accounts", fa: "حساب‌های هزینه" }, { en: "Expense Details", fa: "جزئیات هزینه" }] },
  { key: "documents", status: "partial", label: { en: "Documents", fa: "اسناد" }, statusLabel: { en: "Partial", fa: "جزئی" }, submenus: [{ en: "Document Register", fa: "فهرست اسناد" }, { en: "Links", fa: "پیوندها" }, { en: "Integrity", fa: "یکپارچگی" }, { en: "Revisions", fa: "بازنگری‌ها" }, { en: "Evidence", fa: "مدارک" }] },
  { key: "reports", status: "preview", label: { en: "Reports", fa: "گزارش‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Reports", fa: "گزارش‌ها" }, { en: "Print", fa: "چاپ" }] },
  { key: "tracking", status: "preview", label: { en: "Tracking", fa: "رهگیری" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Project Table", fa: "جدول پروژه" }, { en: "Project Bar Chart", fa: "نمودار میله‌ای پروژه" }, { en: "Project Gantt / Profile", fa: "گانت / منحنی پروژه" }, { en: "Resource Analysis", fa: "تحلیل منابع" }] },
  { key: "issues", status: "preview", label: { en: "Issues", fa: "مسائل" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Issue Register", fa: "فهرست مسائل" }, { en: "Issue Details", fa: "جزئیات مسئله" }] },
  { key: "risks", status: "preview", label: { en: "Risks", fa: "ریسک‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Risk Register", fa: "فهرست ریسک‌ها" }, { en: "Risk Analysis", fa: "تحلیل ریسک" }, { en: "Risk Details", fa: "جزئیات ریسک" }] },
  { key: "thresholds", status: "preview", label: { en: "Thresholds", fa: "آستانه‌ها" }, statusLabel: { en: "Preview", fa: "پیش‌نمایش" }, submenus: [{ en: "Threshold Register", fa: "فهرست آستانه‌ها" }, { en: "Monitoring Rules", fa: "قواعد پایش" }, { en: "Threshold Details", fa: "جزئیات آستانه" }] },
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
  const labels: Record<WorkspaceSurfaceStatus, { en: string; fa: string }> = {
    implemented: { en: "Implemented", fa: "پیاده‌سازی‌شده" },
    partial: { en: "Partial", fa: "جزئی" },
    preview: { en: "Preview", fa: "پیش‌نمایش" },
  };
  const label = labels[item.status];
  // The legacy status key omitted the status value and could preserve a stale
  // "Implemented" translation after a surface was downgraded to Partial.
  return translateWorkspaceText(
    locale,
    `navigation.${item.key}.status.${item.status}`,
    translateWorkspaceUiText(locale, label.en, label.fa),
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
