import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, setCalendarMode, setLocale, withActivities } from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDirection,
  getWorkspaceLocaleDisplayName,
  registerWorkspaceLocale,
  translateWorkspaceText,
} from "./workspace-localization.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 2 };

test("registered third language renders workspace strings without source edits", () => {
  registerWorkspaceLocale({
    locale: "de",
    displayName: "Deutsch",
    direction: "ltr",
    translations: {
      "workspace.project": "Projekt",
      "workspace.details": "Einzelheiten",
      "navigation.schedule": "Zeitplan",
      "navigation.schedule.status": "Implementiert",
      "navigation.schedule.submenu.0": "Aktivitätenraster",
      "navigation.schedule.submenu.1": "Balkenplan",
      "column.activity_name": "Aktivitätsname",
    },
  });

  let state = createWorkspaceState(context, "de");
  state = withActivities(state, [{ id: "A-1", wbsId: "W-1", code: "01", name: "Test activity" }]);
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);

  assert.match(container.innerHTML, /Projekt/);
  assert.match(container.innerHTML, /Zeitplan/);
  assert.match(container.innerHTML, /Aktivitätenraster/);
  assert.match(container.innerHTML, /Balkenplan/);
  assert.equal(state.columns.find((column) => column.id === "activity_name")?.label, "Aktivitätsname");
});

test("locale registration controls direction and is available to the language switcher", () => {
  registerWorkspaceLocale({
    locale: "ar",
    displayName: "العربية",
    direction: "rtl",
    translations: { "workspace.project": "المشروع" },
  });
  assert.equal(getWorkspaceLocaleDirection("ar"), "rtl");
  assert.equal(getWorkspaceLocaleDisplayName("ar"), "العربية");
  assert.ok(getAvailableWorkspaceLocales().includes("ar"));
  assert.equal(translateWorkspaceText("ar", "workspace.project", "Project"), "المشروع");
});

test("switching locale preserves project and calendar state", () => {
  registerWorkspaceLocale({ locale: "de", displayName: "Deutsch", direction: "ltr", translations: {} });
  let state = createWorkspaceState(context, "fa", "jalali");
  state = setLocale(state, "de");
  state = setCalendarMode(state, "jalali");
  assert.deepEqual(state.context, context);
  assert.equal(state.calendarMode, "jalali");
  assert.equal(state.locale, "de");
  assert.equal(state.direction, "ltr");
});

test("invalid locale resource is rejected instead of silently accepted", () => {
  assert.throws(() => registerWorkspaceLocale({
    locale: "not a locale",
    displayName: "Invalid",
    direction: "ltr",
    translations: {},
  }), /INVALID_WORKSPACE_LOCALE/);
  assert.throws(() => registerWorkspaceLocale({
    locale: "de",
    displayName: "Deutsch",
    direction: "ltr",
    translations: { "workspace.project": " " },
  }), /INVALID_WORKSPACE_TRANSLATION/);
});
