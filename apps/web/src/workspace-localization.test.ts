import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, setCalendarMode, setLocale, withActivities } from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDirection,
  getWorkspaceLocaleDisplayName,
  registerWorkspaceLocale,
  readWorkspaceLocaleDefinitionFromPack,
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
      "workspace.details": "<img src=x onerror=alert(1)>",
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
  assert.match(container.innerHTML, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(container.innerHTML, /<img src=x onerror/);
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


test("language-pack UI translations require the versioned schema before activation", () => {
  const manifest = {
    package_id: "cubi-lang-de",
    language_tag: "de-DE",
    version: "1.0.0",
    app_compatibility: { min_version: "1.0.0", max_version: null },
    artifact: { format: "zip", compressed_size_bytes: 1, download_uri: "https://example.invalid/de.zip", delta_from: null },
    resources: { translation: "translations/ui.json", glossary: "glossary.json", help: "help.json", reports: "reports.json", voice_input: null, voice_output: null, offline_ai_model: null },
    integrity: { checksum: `sha256:${"a".repeat(64)}`, signature: "signature", signing_key_id: null },
    capabilities: { ui: true, help: true, ai_text: true, voice_input: false, voice_output: false, offline_ai: false },
  } as const;
  const bytes = new TextEncoder().encode(JSON.stringify({
    schema_version: "cubi-ui-translations.v1",
    display_name: "Deutsch",
    direction: "ltr",
    translations: { "workspace.project": "Projekt" },
  }));
  const definition = readWorkspaceLocaleDefinitionFromPack(
    manifest as never,
    [{ path: "translations/ui.json", bytes }],
  );
  assert.equal(definition?.locale, "de-DE");
  assert.equal(definition?.displayName, "Deutsch");
  assert.equal(definition?.translations["workspace.project"], "Projekt");

  assert.throws(() => readWorkspaceLocaleDefinitionFromPack(
    manifest as never,
    [{ path: "translations/ui.json", bytes: new TextEncoder().encode("{}") }],
  ), /UNSUPPORTED_WORKSPACE_LOCALE_TRANSLATION_SCHEMA/);
});


test("Arabic, French, Japanese, Korean and Russian are registered as selectable workspace locales", () => {
  const expected = [
    ["ar", "العربية", "rtl"],
    ["fr", "Français", "ltr"],
    ["ja", "日本語", "ltr"],
    ["ko", "한국어", "ltr"],
    ["ru", "Русский", "ltr"],
  ] as const;
  for (const [locale, displayName, direction] of expected) {
    assert.ok(getAvailableWorkspaceLocales().includes(locale));
    assert.equal(getWorkspaceLocaleDisplayName(locale), displayName);
    assert.equal(getWorkspaceLocaleDirection(locale), direction);
    const state = setLocale(createWorkspaceState(context, "en"), locale);
    assert.equal(state.locale, locale);
    assert.equal(state.direction, direction);
  }
});


test("baseline catalogs translate the command surface for Arabic, French, Japanese, Korean and Russian", async () => {
  const { hasWorkspaceUiTranslations, translateWorkspaceUiText } = await import("./workspace-localization.js");
  const { catalogSize } = await import("./workspace-locale-catalogs.js");
  const { translateColumnLabel } = await import("./workspace-ui-translations.js");
  const chrome = [
    "File", "Edit", "View", "Project", "Enterprise", "Tools", "Window", "Help",
    "Show Details", "Hide Details", "Workspace theme", "Language", "Panels", "Details",
    "CUBI Classic — Version 26 Reference", "CUBI Modern 3D",
    "OK", "Cancel", "Close", "Activity Details", "Project Details",
  ];
  const columns = ["Activity ID", "Activity Name", "Start", "Finish", "Duration", "Status"];
  for (const locale of ["ar", "fr", "ja", "ko", "ru"]) {
    assert.equal(hasWorkspaceUiTranslations(locale), true, `${locale} must advertise translations`);
    assert.ok(catalogSize(locale) >= 150, `${locale} catalog covers fewer than 150 strings`);
    for (const english of chrome) {
      const translated = translateWorkspaceUiText(locale, english, "persian-fallback");
      assert.notEqual(translated, "persian-fallback", `${locale} fell back to Persian for "${english}"`);
      assert.ok(translated.trim().length > 0);
      // "OK" is legitimately identical in French and English; every other key must change.
      if (english !== "OK") {
        assert.notEqual(translated, english, `${locale} is missing a translation for "${english}"`);
      }
    }
    for (const label of columns) {
      assert.notEqual(translateColumnLabel(locale, label), label, `${locale} column ${label} is untranslated`);
    }
  }
  assert.equal(getWorkspaceLocaleDirection("ar"), "rtl");
  assert.equal(getWorkspaceLocaleDirection("ru"), "ltr");
});


test("verified locale resources can translate the visual command menu and shared UI labels", async () => {
  registerWorkspaceLocale({
    locale: "fr",
    displayName: "Français",
    direction: "ltr",
    translations: {
      "command.Workspace": "Espace de travail",
      "command.New Project": "Nouveau projet",
      "ui.Project": "Projet",
      "column.label.Activity Name": "Nom de l’activité",
    },
  });
  const { renderWorkspaceCommandShell } = await import("./workspace-command-shell.js");
  const shell = renderWorkspaceCommandShell("fr");
  assert.match(shell, /Espace de travail/);
  assert.match(shell, /Nouveau projet/);
  assert.equal(translateWorkspaceText("fr", "ui.Project", "Project"), "Projet");
});
