import assert from "node:assert/strict";
import test from "node:test";

import { renderWorkspaceCommandShell } from "./workspace-command-shell.js";

test("visual command shell exposes one global menu bar and no duplicate grouped toolbar", () => {
  const html = renderWorkspaceCommandShell("en");
  for (const label of ["Workspace", "Edit", "View", "Project", "Organization", "Tools", "Administration", "Help"]) {
    assert.match(html, new RegExp(`<summary>${label}<span class="cubi-submenu-caret">›</span></summary>`), `missing ${label} menu`);
  }
  assert.match(html, /class="cubi-command-menubar" role="menubar"/);
  assert.doesNotMatch(html, /class="cubi-toolbar"/, "the grouped command toolbar must not duplicate the primary icon toolbar");
  assert.match(html, /Show on Top/);
  assert.match(html, /Show on Bottom/);
  assert.match(html, /Group and Sort By/);
  assert.match(html, /Activity Network/);
  assert.match(html, /disabled/);
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

test("Persian command shell localizes the single menu bar in RTL", () => {
  const html = renderWorkspaceCommandShell("fa");
  assert.match(html, /dir="rtl"/);
  assert.match(html, /<summary>محیط کار<span class="cubi-submenu-caret">›<\/span><\/summary>/);
  assert.match(html, /<summary>ویرایش<span class="cubi-submenu-caret">›<\/span><\/summary>/);
  assert.match(html, /<summary>نمایش<span class="cubi-submenu-caret">›<\/span><\/summary>/);
  assert.match(html, /ذخیره/);
  assert.match(html, /افزودن/);
  assert.match(html, /فرم‌ساز/);
  assert.match(html, /منوی اصلی/);
  assert.doesNotMatch(html, /نوار ابزار اصلی/);
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
