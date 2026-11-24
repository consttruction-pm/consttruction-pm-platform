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
    ["project", "wbs", "schedule", "progress", "resources", "assignments", "roles", "calendars", "cost", "expenses", "documents", "reports", "tracking", "issues", "risks", "thresholds", "control", "settings", "administration", "exchange", "backup"],
  );
});

test("schedule navigation exposes run controls and every reference section", () => {
  const item = getWorkspaceNavigation("schedule");

  assert.equal(item.status, "implemented");
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

test("no mounted window is marked preview: status reflects the tested data path", () => {
  assert.equal(getWorkspaceNavigation("progress").status, "partial");
  assert.equal(getWorkspaceNavigation("resources").status, "partial");
  assert.equal(getWorkspaceNavigation("cost").status, "partial");
  assert.equal(getWorkspaceNavigation("issues").status, "partial");
  // These windows mount a real module whose create/edit/delete paths are
  // covered by tests against the project API, so calling them a preview would
  // understate working behaviour.
  for (const key of ["reports", "tracking", "risks", "thresholds", "administration", "exchange", "backup"] as const) {
    assert.notEqual(getWorkspaceNavigation(key).status, "preview", `${key} has a mounted, tested data path`);
    assert.equal(getWorkspaceNavigation(key).status, "partial");
  }
});

test("navigation status follows the workspace active menu", () => {
  const state = createWorkspaceState({
    tenant_id: "tenant-1",
    project_id: "project-1",
    revision: 0,
  });

  assert.equal(getWorkspaceNavigationStatus(state), "implemented");
  assert.equal(
    getWorkspaceNavigationStatus({ ...state, activeMenu: "reports" }),
    "partial",
  );
});
