import assert from "node:assert/strict";
import test from "node:test";

import {
  getWorkspaceNavigation,
  getWorkspaceNavigationStatus,
  WORKSPACE_NAVIGATION,
} from "./workspace-navigation.js";
import { createWorkspaceState } from "./workspace-model.js";

test("workspace navigation exposes every V1 main menu surface", () => {
  assert.deepEqual(
    WORKSPACE_NAVIGATION.map((item) => item.key),
    ["project", "wbs", "schedule", "progress", "resources", "assignments", "roles", "calendars", "cost", "expenses", "documents", "reports", "tracking", "issues", "risks", "thresholds", "control", "settings"],
  );
});

test("schedule navigation exposes run controls and every reference section without overstating completion", () => {
  const item = getWorkspaceNavigation("schedule");

  assert.equal(item.status, "partial");
  assert.deepEqual(item.submenus.map((submenu) => submenu.en), [
    "Activity Grid",
    "Gantt Chart",
    "Relationships & lag",
    "Calendars & work time",
    "Schedule options & Data Date",
    "Resources & leveling",
    "Progress & baselines",
    "Run Schedule",
    "Formula editor",
    "Code Reference",
    "Option catalogue",
    "Formula contracts",
    "Documentation review",
  ]);
  assert.deepEqual(item.submenus.map((submenu) => submenu.fa), [
    "جدول فعالیت‌ها",
    "گانت",
    "روابط و وقفه",
    "تقویم‌ها و ساعات کاری",
    "تنظیمات زمان‌بندی و تاریخ داده",
    "منابع و تسطیح",
    "پیشرفت و مبناها",
    "اجرای زمان‌بندی",
    "ویرایشگر فرمول",
    "مرجع کد",
    "فهرست گزینه‌ها",
    "قراردادهای محاسباتی",
    "بازبینی مستندات",
  ]);
});

test("unsupported V1 surfaces are explicitly marked preview instead of being presented as implemented", () => {
  assert.equal(getWorkspaceNavigation("progress").status, "partial");
  assert.equal(getWorkspaceNavigation("resources").status, "partial");
  assert.equal(getWorkspaceNavigation("cost").status, "partial");
  assert.equal(getWorkspaceNavigation("reports").status, "preview");
});

test("Reports navigation exposes library, layout, batch, print and export surfaces", () => {
  assert.deepEqual(getWorkspaceNavigation("reports").submenus.map((item) => item.en), [
    "Report Library",
    "Report Layouts",
    "Batch Reports",
    "Print Preview",
    "Page Setup",
    "Export",
    "Custom Reports",
  ]);
});

test("Control navigation exposes quality, inspection, safety and closeout registers", () => {
  assert.deepEqual(getWorkspaceNavigation("control").submenus.map((item) => item.en), [
    "Control Summary",
    "Quality Records",
    "Inspections",
    "Safety Observations",
    "Field Issues",
    "Punch List",
    "Changes & Claims",
    "Forms & Workflows",
  ]);
});

test("Progress navigation exposes the live activity register and field evidence routes", () => {
  assert.deepEqual(getWorkspaceNavigation("progress").submenus.map((item) => item.en), [
    "Activity Progress",
    "Site Daily Logs",
    "Timecards",
    "Equipment Reports",
    "Field Issues",
    "Update Progress",
    "Period Performance",
  ]);
});

test("resource, cost and document windows expose their navigable register/detail surfaces", () => {
  assert.deepEqual(getWorkspaceNavigation("resources").submenus.map((item) => item.en), [
    "Resource Register",
    "Max units / time",
    "Assignments",
    "Resource Codes",
    "Roles",
  ]);
  assert.deepEqual(getWorkspaceNavigation("cost").submenus.map((item) => item.en), [
    "Cost Overview",
    "Cost Accounts",
    "Budget",
    "Cash Flow",
    "Earned Value",
    "Procurement",
    "Changes & Claims",
  ]);
  assert.deepEqual(getWorkspaceNavigation("documents").submenus.map((item) => item.en), [
    "Document Register",
    "Links",
    "Integrity",
    "Revisions",
    "Evidence",
  ]);
});

test("navigation status follows the workspace active menu", () => {
  const state = createWorkspaceState({
    tenant_id: "tenant-1",
    project_id: "project-1",
    revision: 0,
  });

  assert.equal(getWorkspaceNavigationStatus(state), "partial");
  assert.equal(
    getWorkspaceNavigationStatus({ ...state, activeMenu: "reports" }),
    "preview",
  );
});

test("navigation status labels follow the live status and ignore stale legacy translations", async () => {
  const { registerWorkspaceLocale } = await import("./workspace-localization.js");
  const { getWorkspaceNavigationStatusLabel } = await import("./workspace-navigation.js");
  registerWorkspaceLocale({
    locale: "fr",
    displayName: "Français",
    direction: "ltr",
    translations: {
      "navigation.schedule.status": "Implemented",
      "navigation.schedule.status.partial": "Partiel",
      "navigation.reports.status.preview": "Aperçu",
    },
  });
  assert.equal(getWorkspaceNavigationStatusLabel(getWorkspaceNavigation("schedule"), "fr"), "Partiel");
  assert.equal(getWorkspaceNavigationStatusLabel(getWorkspaceNavigation("reports"), "fr"), "Aperçu");
  assert.equal(getWorkspaceNavigationStatusLabel(getWorkspaceNavigation("schedule"), "fa"), "جزئی");
});
