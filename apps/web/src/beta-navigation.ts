import type { WorkspaceMenuKey } from "./workspace-model.js";

export type BetaFeatureStatus = "Implemented" | "Partial" | "Preview";

export type BetaSubmenu = {
  id: string;
  label: string;
  status: BetaFeatureStatus;
};

export type BetaMenuDefinition = {
  key: WorkspaceMenuKey;
  label: string;
  items: readonly BetaSubmenu[];
};

export const BETA_NAVIGATION: readonly BetaMenuDefinition[] = [
  { key: "project", label: "Project", items: [
    { id: "project.open", label: "Open Project", status: "Partial" },
    { id: "project.details", label: "Project Details", status: "Partial" },
    { id: "project.wbs", label: "WBS", status: "Partial" },
    { id: "project.eps", label: "EPS / Portfolio", status: "Preview" },
    { id: "project.codes", label: "Codes / UDF", status: "Partial" },
    { id: "project.baselines", label: "Baselines", status: "Partial" },
  ]},
  { key: "schedule", label: "Schedule", items: [
    { id: "schedule.activities", label: "Activities", status: "Partial" },
    { id: "schedule.relationships", label: "Relationships", status: "Partial" },
    { id: "schedule.calendars", label: "Calendars", status: "Partial" },
    { id: "schedule.options", label: "Schedule Options", status: "Partial" },
    { id: "schedule.recalculate", label: "Schedule / Recalculate", status: "Partial" },
    { id: "schedule.float", label: "Float / Critical Path", status: "Partial" },
    { id: "schedule.gantt", label: "Gantt", status: "Partial" },
  ]},
  { key: "progress", label: "Progress", items: [
    { id: "progress.update", label: "Update Progress", status: "Partial" },
    { id: "progress.steps", label: "Activity Steps", status: "Preview" },
    { id: "progress.ev", label: "Earned Value", status: "Partial" },
    { id: "progress.earnedSchedule", label: "Earned Schedule", status: "Partial" },
    { id: "progress.performance", label: "Schedule Performance", status: "Partial" },
  ]},
  { key: "resources", label: "Resources", items: [
    { id: "resources.dictionary", label: "Resource Dictionary", status: "Partial" },
    { id: "resources.assignments", label: "Resource Assignments", status: "Partial" },
    { id: "resources.roles", label: "Roles / Rates", status: "Partial" },
    { id: "resources.calendars", label: "Resource Calendars", status: "Partial" },
  ]},
  { key: "cost", label: "Cost", items: [
    { id: "cost.accounts", label: "Cost Accounts", status: "Preview" },
    { id: "cost.actuals", label: "Planned / Actual / Remaining", status: "Partial" },
    { id: "cost.forecast", label: "Forecast / Variance", status: "Partial" },
  ]},
  { key: "documents", label: "Documents", items: [
    { id: "documents.register", label: "Document Register", status: "Partial" },
    { id: "documents.drawings", label: "Drawings / Contracts", status: "Partial" },
    { id: "documents.rfi", label: "RFI / Submittal", status: "Preview" },
    { id: "documents.claims", label: "Claims / Evidence", status: "Partial" },
  ]},
  { key: "reports", label: "Reports", items: [
    { id: "reports.schedule", label: "Schedule Reports", status: "Partial" },
    { id: "reports.progress", label: "Progress / EVM Reports", status: "Partial" },
    { id: "reports.cost", label: "Cost Reports", status: "Partial" },
    { id: "reports.custom", label: "Custom Report / Columns", status: "Partial" },
  ]},
  { key: "control", label: "Control", items: [
    { id: "control.room", label: "Project Control Room", status: "Partial" },
    { id: "control.change", label: "Change / Claims", status: "Partial" },
    { id: "control.field", label: "Field Operations", status: "Preview" },
    { id: "control.quality", label: "Quality / Safety", status: "Preview" },
  ]},
  { key: "settings", label: "Settings", items: [
    { id: "settings.language", label: "Language", status: "Implemented" },
    { id: "settings.calendar", label: "Calendar Display", status: "Implemented" },
    { id: "settings.options", label: "Schedule Options", status: "Partial" },
    { id: "settings.units", label: "Units / Currency", status: "Partial" },
    { id: "settings.users", label: "Users / Roles / Permissions", status: "Partial" },
    { id: "settings.interchange", label: "Import / Export", status: "Partial" },
    { id: "settings.audit", label: "Audit / Revision", status: "Partial" },
  ]},
];

export function getBetaMenu(key: WorkspaceMenuKey): BetaMenuDefinition {
  return BETA_NAVIGATION.find((menu) => menu.key === key) ?? BETA_NAVIGATION[1];
}


const PERSIAN_SUBMENU_LABELS: Readonly<Record<string, string>> = {
  "project.open": "باز کردن پروژه",
  "project.details": "جزئیات پروژه",
  "project.wbs": "WBS",
  "project.eps": "EPS / پورتفولیو",
  "project.codes": "کدها / UDF",
  "project.baselines": "خطوط مبنا",
  "schedule.activities": "فعالیت‌ها",
  "schedule.relationships": "روابط",
  "schedule.calendars": "تقویم‌ها",
  "schedule.options": "گزینه‌های زمان‌بندی",
  "schedule.recalculate": "زمان‌بندی / محاسبه مجدد",
  "schedule.float": "شناوری / مسیر بحرانی",
  "schedule.gantt": "گانت",
  "progress.update": "به‌روزرسانی پیشرفت",
  "progress.steps": "گام‌های فعالیت",
  "progress.ev": "ارزش کسب‌شده",
  "progress.earnedSchedule": "زمان‌بندی کسب‌شده",
  "progress.performance": "عملکرد زمان‌بندی",
  "resources.dictionary": "فرهنگ منابع",
  "resources.assignments": "تخصیص منابع",
  "resources.roles": "نقش‌ها / نرخ‌ها",
  "resources.calendars": "تقویم منابع",
  "cost.accounts": "حساب‌های هزینه",
  "cost.actuals": "برنامه‌ریزی / واقعی / باقیمانده",
  "cost.forecast": "پیش‌بینی / واریانس",
  "documents.register": "ثبت اسناد",
  "documents.drawings": "نقشه‌ها / قراردادها",
  "documents.rfi": "RFI / Submittal",
  "documents.claims": "ادعاها / مستندات",
  "reports.schedule": "گزارش‌های زمان‌بندی",
  "reports.progress": "گزارش‌های پیشرفت / EVM",
  "reports.cost": "گزارش‌های هزینه",
  "reports.custom": "گزارش سفارشی / ستون‌ها",
  "control.room": "اتاق کنترل پروژه",
  "control.change": "تغییرات / ادعاها",
  "control.field": "عملیات کارگاه",
  "control.quality": "کیفیت / ایمنی",
  "settings.language": "زبان",
  "settings.calendar": "نمایش تقویم",
  "settings.options": "گزینه‌های زمان‌بندی",
  "settings.units": "واحدها / ارز",
  "settings.users": "کاربران / نقش‌ها / مجوزها",
  "settings.interchange": "ورود / خروج",
  "settings.audit": "ممیزی / نسخه",
};

export function getBetaSubmenuLabel(item: BetaSubmenu, locale: "fa" | "en"): string {
  return locale === "fa" ? PERSIAN_SUBMENU_LABELS[item.id] ?? item.label : item.label;
}
