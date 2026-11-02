import assert from "node:assert/strict";
import test from "node:test";

import { renderWorkspaceCommandShell } from "./workspace-command-shell.js";

test("visual command shell exposes all global menu families and toolbar groups", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const label of ["Workspace", "Edit", "View", "Project", "Organization", "Tools", "Administration", "Help"]) {
    assert.ok(html.includes(`<summary>${label}</summary>`), `missing ${label} menu`);
  }
  for (const group of ["Standard", "Project", "Layout", "Schedule", "CUBI Tools"]) {
    assert.ok(html.includes(`<strong>${group}</strong>`), `missing ${group} toolbar group`);
  }
  assert.match(html, /Show on Top/);
  assert.match(html, /Show on Bottom/);
  assert.match(html, /Group and Sort By/);
  assert.match(html, /Activity Network/);
  assert.match(html, /disabled/);
  assert.match(html, /button\[aria-disabled=true\]\{opacity:\.48;cursor:not-allowed\}/);
  assert.match(html, /:focus-visible\{outline:2px solid #1c6bb7/);
  assert.match(html, /data-shell-command="Timescale" title="Open the corresponding options for the current view"/);
  assert.match(html, /data-shell-command="Columns" title="Open the corresponding options for the current view"/);
  assert.doesNotMatch(html, /data-shell-command="Timescale"[^>]*disabled/);
  assert.doesNotMatch(html, /data-shell-command="Columns"[^>]*disabled/);
  assert.match(html, /data-shell-command="Save"[^>]*disabled/);
});

test("view commands are enabled only for a window that implements the corresponding controls", () => {
  const projectHtml = renderWorkspaceCommandShell("en", "project");
  assert.match(projectHtml, /data-shell-command="Timescale"[^>]*disabled/);
  assert.match(projectHtml, /data-shell-command="Columns"[^>]*disabled/);
  const activityHtml = renderWorkspaceCommandShell("en", "schedule");
  assert.doesNotMatch(activityHtml, /data-shell-command="Timescale"[^>]*disabled/);
  assert.doesNotMatch(activityHtml, /data-shell-command="Columns"[^>]*disabled/);
});

test("CUBI Form Builder is additive and exposes both governed libraries", () => {
  const html = renderWorkspaceCommandShell("en");
  assert.match(html, /Form Builder/);
  assert.match(html, /Organization Form Library/);
  assert.match(html, /Project Form Library/);
  assert.match(html, /Form Templates/);
  assert.match(html, /Form Versions/);
});

test("Persian command shell localizes menus, common commands and toolbar groups in RTL", () => {
  const html = renderWorkspaceCommandShell("fa");
  assert.match(html, /dir="rtl"/);
  assert.match(html, /<summary>محیط کار<\/summary>/);
  assert.match(html, /<summary>ویرایش<\/summary>/);
  assert.match(html, /<summary>نمایش<\/summary>/);
  assert.match(html, /ذخیره/);
  assert.match(html, /افزودن/);
  assert.match(html, /فرم‌ساز/);
  assert.match(html, /نوار ابزار اصلی/);
});


test("visual command shell uses activated language-pack command translations", async () => {
  const { registerWorkspaceLocale } = await import("./workspace-localization.js");
  registerWorkspaceLocale({
    locale: "ja",
    displayName: "日本語",
    direction: "ltr",
    translations: {
      "command.Workspace": "ワークスペース",
      "command.New Project": "新しいプロジェクト",
    },
  });
  const html = renderWorkspaceCommandShell("ja");
  assert.match(html, /ワークスペース/);
  assert.match(html, /新しいプロジェクト/);
});


test("Arabic command shell applies RTL layout direction", async () => {
  const { registerWorkspaceLocale } = await import("./workspace-localization.js");
  registerWorkspaceLocale({
    locale: "ar",
    displayName: "العربية",
    direction: "rtl",
    translations: {
      "command.Workspace": "مساحة العمل",
      "command.New Project": "مشروع جديد",
    },
  });
  const html = renderWorkspaceCommandShell("ar");
  assert.match(html, /class="cubi-command-shell" dir="rtl"/);
  assert.match(html, /مساحة العمل/);
  assert.match(html, /مشروع جديد/);
});

test("View menu includes the complete Version 26 display toolbar commands in CUBI wording", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const command of ["Hint Help", "Launch", "Reset All Toolbars", "Lock All Toolbars", "Tab Groups", "Collapse To", "Activity Critical Path", "Check Schedule", "Attachments", "Line Numbers"]) {
    assert.ok(html.includes(command), `missing View menu command: ${command}`);
  }
  const fa = renderWorkspaceCommandShell("fa");
  for (const command of ["راهنمای زمینه‌ای", "بازنشانی همه نوارهای ابزار", "قفل همه نوارهای ابزار"]) {
    assert.ok(fa.includes(command), `missing Persian View menu command: ${command}`);
  }
});

test("Version 26 menu inventory is represented in CUBI menus without exposing source-product branding", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const command of [
    "Enterprise Project Structure", "Tracking", "Resource Codes", "Role Codes", "Stored Images",
    "Schedule Visualization", "Project Comparison &amp; Variance", "Admin Categories",
    "Financial Period Calendars", "Expand", "Bottom Layout Options", "Activity Details", "Table", "Gantt Chart", "Share Feedback",
    "Exchange Data", "Select Project Portfolio", "Commit Changes", "Refresh Data",
    "Progress Spotlight", "Activity Critical Path", "Check Schedule", "Tab Groups",
    "Store Period Performance", "Issue Navigator", "Report Preferences",
  ]) {
    assert.ok(html.includes(command), `missing Version 26 menu item: ${command}`);
  }
  assert.doesNotMatch(html, /Oracle|Primavera|P6 Professional/i);
  const activityHtml = renderWorkspaceCommandShell("en", "schedule");
  assert.doesNotMatch(activityHtml, /data-shell-command="Bottom Layout Options"[^>]*disabled/);
  assert.doesNotMatch(activityHtml, /data-shell-command="Activity Details"[^>]*disabled/);
  assert.doesNotMatch(activityHtml, /data-shell-command="Table"[^>]*disabled/);
  assert.doesNotMatch(activityHtml, /data-shell-command="Gantt Chart"[^>]*disabled/);
  for (const command of ["Add Activity", "Add WBS", "Add Relationship", "Link Activities", "Find"]) {
    assert.doesNotMatch(activityHtml, new RegExp(`data-shell-command="${command}"[^>]*disabled`));
  }
  const projectHtml = renderWorkspaceCommandShell("en", "project");
  assert.doesNotMatch(projectHtml, /data-shell-command="Add WBS"[^>]*disabled/);
  assert.match(projectHtml, /data-shell-command="Add Activity"[^>]*disabled/);
  assert.match(projectHtml, /data-shell-command="Bottom Layout Options"[^>]*disabled/);
});

test("global menus include the remaining documented file, edit, organization, tools and help commands", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const command of ["Commit Changes", "Refresh Data", "Print Setup", "Send Project", "Check In", "Check Out", "Select Project Portfolio", "Replace", "Spell Check", "Organizational Breakdown Structure", "Activity Step Templates", "External Applications", "Disable Auto-Reorganization", "Job Services", "Report Wizard", "Publish", "Local Help", "Online Help"]) {
    assert.ok(html.includes(command), `missing menu command: ${command}`);
  }
  assert.match(html, /Ctrl\+W/);
  assert.match(html, /F10/);
  assert.match(html, /Ctrl\+R/);
  assert.match(html, /F7/);
  const fa = renderWorkspaceCommandShell("fa");
  assert.match(fa, /ثبت تغییرات/);
  assert.match(fa, /به‌روزرسانی داده‌ها/);
  assert.match(fa, /راهنمای محلی/);
});

test("Version 26 tools submenu inventory includes summarize scopes, approvals and publish layouts", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const command of ["Summarize", "Open Projects", "All Projects", "Disable Auto-Reorganization", "Job Services", "Job Status", "Approvals", "Timesheets", "Report Preferences", "Project Website", "Activity Layouts", "Tracking Layouts", "Share Feedback", "Resources by Role", "Exchange Data", "CUBI Project Package"]) {
    assert.ok(html.includes(command), `missing documented submenu command: ${command}`);
  }
  assert.match(html, /cubi-command-parent/);
  const fa = renderWorkspaceCommandShell("fa");
  assert.match(fa, /تبادل داده/);
  assert.match(fa, /برگه‌های زمانی/);
  assert.match(fa, /ارسال بازخورد/);
});

test("View menu exposes the full toolbar catalogue and tab-group actions as nested menus", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const command of ["Expand", "Action Toolbar", "Administrator Toolbar", "Assign Toolbar", "Bottom Layout Toolbar", "Dictionaries Toolbar", "Display Toolbar", "Edit Toolbar", "Enterprise Toolbar", "Find Toolbar", "Layout Toolbar", "Move Toolbar", "Print Toolbar", "Project Toolbar", "Publish Toolbar", "Reports Toolbar", "Standard Toolbar", "Tools Toolbar", "Top Layout Toolbar", "Merge Windows", "Create New Tab Group"]) {
    assert.ok(html.includes(command), `missing toolbar/tab-group command: ${command}`);
  }
  const fa = renderWorkspaceCommandShell("fa");
  assert.match(fa, /نوار ابزار چیدمان بالا/);
  assert.match(fa, /ایجاد گروه زبانه جدید/);
});
