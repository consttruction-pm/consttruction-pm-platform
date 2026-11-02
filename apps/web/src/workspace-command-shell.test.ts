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
