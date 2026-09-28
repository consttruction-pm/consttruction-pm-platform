import type { UiTextDirection } from "./ui-interaction.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";

export type BetaFeatureStatus = "Implemented" | "Partial" | "Preview";

export type BetaSubmenu = {
  id: string;
  label: string;
  status: BetaFeatureStatus;
  textDirection: UiTextDirection;
};

export type BetaMenuDefinition = {
  key: WorkspaceMenuKey;
  label: string;
  items: readonly BetaSubmenu[];
  textDirection: UiTextDirection;
};

const item = (id: string, label: string, status: BetaFeatureStatus): BetaSubmenu => ({
  id, label, status, textDirection: "auto",
});

const menu = (key: WorkspaceMenuKey, label: string, items: readonly BetaSubmenu[]): BetaMenuDefinition => ({
  key, label, items, textDirection: "auto",
});

export const BETA_NAVIGATION: readonly BetaMenuDefinition[] = [
  menu("project", "Project", [
    item("project.open", "Open Project", "Partial"),
    item("project.details", "Project Details", "Partial"),
    item("project.wbs", "WBS", "Partial"),
    item("project.eps", "EPS / Portfolio", "Preview"),
    item("project.codes", "Codes / UDF", "Partial"),
    item("project.baselines", "Baselines", "Partial"),
  ]),
  menu("schedule", "Schedule", [
    item("schedule.activities", "Activities", "Partial"),
    item("schedule.relationships", "Relationships", "Partial"),
    item("schedule.calendars", "Calendars", "Partial"),
    item("schedule.options", "Schedule Options", "Partial"),
    item("schedule.recalculate", "Schedule / Recalculate", "Partial"),
    item("schedule.float", "Float / Critical Path", "Partial"),
    item("schedule.gantt", "Gantt", "Partial"),
  ]),
  menu("progress", "Progress", [
    item("progress.update", "Update Progress", "Partial"),
    item("progress.steps", "Activity Steps", "Preview"),
    item("progress.ev", "Earned Value", "Partial"),
    item("progress.earnedSchedule", "Earned Schedule", "Partial"),
    item("progress.performance", "Schedule Performance", "Partial"),
  ]),
  menu("resources", "Resources", [
    item("resources.dictionary", "Resource Dictionary", "Partial"),
    item("resources.assignments", "Resource Assignments", "Partial"),
    item("resources.roles", "Roles / Rates", "Partial"),
    item("resources.calendars", "Resource Calendars", "Partial"),
  ]),
  menu("cost", "Cost", [
    item("cost.accounts", "Cost Accounts", "Preview"),
    item("cost.actuals", "Planned / Actual / Remaining", "Partial"),
    item("cost.forecast", "Forecast / Variance", "Partial"),
  ]),
  menu("documents", "Documents", [
    item("documents.register", "Document Register", "Partial"),
    item("documents.drawings", "Drawings / Contracts", "Partial"),
    item("documents.rfi", "RFI / Submittal", "Preview"),
    item("documents.claims", "Claims / Evidence", "Partial"),
  ]),
  menu("reports", "Reports", [
    item("reports.schedule", "Schedule Reports", "Partial"),
    item("reports.progress", "Progress / EVM Reports", "Partial"),
    item("reports.cost", "Cost Reports", "Partial"),
    item("reports.custom", "Custom Report / Columns", "Partial"),
  ]),
  menu("control", "Control", [
    item("control.room", "Project Control Room", "Partial"),
    item("control.change", "Change / Claims", "Partial"),
    item("control.field", "Field Operations", "Preview"),
    item("control.quality", "Quality / Safety", "Preview"),
  ]),
  menu("settings", "Settings", [
    item("settings.language", "Language", "Implemented"),
    item("settings.calendar", "Calendar Display", "Implemented"),
    item("settings.options", "Schedule Options", "Partial"),
    item("settings.units", "Units / Currency", "Partial"),
    item("settings.users", "Users / Roles / Permissions", "Partial"),
    item("settings.interchange", "Import / Export", "Partial"),
    item("settings.audit", "Audit / Revision", "Partial"),
  ]),
];

const PERSIAN_SUBMENU_LABELS: Readonly<Record<string, string>> = {
  "project.open": "باز کردن پروژه", "project.details": "جزئیات پروژه", "project.wbs": "WBS", "project.eps": "EPS / پورتفولیو", "project.codes": "کدها / UDF", "project.baselines": "خطوط مبنا",
  "schedule.activities": "فعالیت‌ها", "schedule.relationships": "روابط", "schedule.calendars": "تقویم‌ها", "schedule.options": "گزینه‌های زمان‌بندی", "schedule.recalculate": "زمان‌بندی / محاسبه مجدد", "schedule.float": "شناوری / مسیر بحرانی", "schedule.gantt": "گانت",
  "progress.update": "به‌روزرسانی پیشرفت", "progress.steps": "گام‌های فعالیت", "progress.ev": "ارزش کسب‌شده", "progress.earnedSchedule": "زمان‌بندی کسب‌شده", "progress.performance": "عملکرد زمان‌بندی",
  "resources.dictionary": "فرهنگ منابع", "resources.assignments": "تخصیص منابع", "resources.roles": "نقش‌ها / نرخ‌ها", "resources.calendars": "تقویم منابع",
  "cost.accounts": "حساب‌های هزینه", "cost.actuals": "برنامه‌ریزی / واقعی / باقیمانده", "cost.forecast": "پیش‌بینی / واریانس",
  "documents.register": "ثبت اسناد", "documents.drawings": "نقشه‌ها / قراردادها", "documents.rfi": "RFI / Submittal", "documents.claims": "ادعاها / مستندات",
  "reports.schedule": "گزارش‌های زمان‌بندی", "reports.progress": "گزارش‌های پیشرفت / EVM", "reports.cost": "گزارش‌های هزینه", "reports.custom": "گزارش سفارشی / ستون‌ها",
  "control.room": "اتاق کنترل پروژه", "control.change": "تغییرات / ادعاها", "control.field": "عملیات کارگاه", "control.quality": "کیفیت / ایمنی",
  "settings.language": "زبان", "settings.calendar": "نمایش تقویم", "settings.options": "گزینه‌های زمان‌بندی", "settings.units": "واحدها / ارز", "settings.users": "کاربران / نقش‌ها / مجوزها", "settings.interchange": "ورود / خروج", "settings.audit": "ممیزی / نسخه",
};

export function getBetaMenu(key: WorkspaceMenuKey): BetaMenuDefinition {
  return BETA_NAVIGATION.find((candidate) => candidate.key === key) ?? BETA_NAVIGATION[1];
}

export function getBetaSubmenuLabel(item: BetaSubmenu, languageTag: string): string {
  const base = languageTag.trim().toLowerCase().split("-")[0];
  return base === "fa" ? PERSIAN_SUBMENU_LABELS[item.id] ?? item.label : item.label;
}
