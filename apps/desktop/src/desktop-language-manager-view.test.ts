import assert from "node:assert/strict";
import test from "node:test";

import {
  buildDesktopLanguageManagerSurface,
  type DesktopLanguageManagerCopy,
} from "./desktop-language-manager-view.js";

const copy: DesktopLanguageManagerCopy = {
  title: "Language",
  ready: "Ready",
  downloading: (language) => `Downloading ${language}`,
  supportedLanguages: "Supported languages",
  language: "Language",
  locale: "Locale",
  direction: "Direction",
  installed: "Installed",
  offline: "Offline",
  ai: "AI",
  voiceIn: "Voice In",
  voiceOut: "Voice Out",
  offlineAi: "Offline AI",
  selected: "Selected",
  use: "Use",
  download: "Download",
  update: "Update",
  unavailable: "Unavailable",
  remove: "Remove",
  yes: "Yes",
  no: "No",
  missing: "—",
  action: "Action",
  downloadProgress: "Language pack download progress",
  rtl: "RTL",
  ltr: "LTR",
};

const catalog = {
  schemaVersion: "1.0",
  generatedAt: "2026-09-25T00:00:00Z",
  defaultLanguage: "en",
  items: [
    {
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.1.0",
      minAppVersion: "0.1.0",
      maxAppVersion: null,
      compressedSizeBytes: 128,
      downloadUri: "https://example.invalid/fa.zip",
      checksum: "abc",
      signature: "sig",
      capabilities: {
        ui: true,
        help: true,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: true,
      },
      resourcePaths: {
        translation: "translation.json",
        glossary: "glossary.json",
        help: "help.json",
        reports: "reports.json",
      },
    },
    {
      packageId: "construction-pm.language.en",
      languageTag: "en",
      version: "1.0.0",
      minAppVersion: "0.1.0",
      maxAppVersion: null,
      compressedSizeBytes: 128,
      downloadUri: "https://example.invalid/en.zip",
      checksum: "def",
      signature: "sig",
      capabilities: {
        ui: true,
        help: true,
        aiText: true,
        voiceInput: false,
        voiceOutput: false,
        offlineAi: true,
      },
      resourcePaths: {
        translation: "translation.json",
        glossary: "glossary.json",
        help: "help.json",
        reports: "reports.json",
      },
    },
  ],
} as const;

test("desktop language manager surface is registry/capability driven", () => {
  const state = {
    selectedLanguage: "en",
    status: "ready" as const,
    activeDownloadLanguage: null,
    progressPercent: null,
    errorKey: null,
    rows: [
      {
        languageTag: "en",
        locale: "en-US",
        direction: "ltr" as const,
        installedPackageId: "construction-pm.language.en",
        installedVersion: "1.0.0",
        verified: true,
        offlineReady: true,
        aiText: true,
        voiceInput: false,
        voiceOutput: false,
        offlineAi: true,
        selected: true,
      },
      {
        languageTag: "fa",
        locale: "fa-IR",
        direction: "rtl" as const,
        installedPackageId: null,
        installedVersion: null,
        verified: false,
        offlineReady: false,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: true,
        selected: false,
      },
    ],
  };

  const surface = buildDesktopLanguageManagerSurface(
    state,
    catalog,
    "0.1.0",
    copy,
  );

  assert.equal(surface.uiLanguage, "en");
  assert.equal(surface.direction, "ltr");
  assert.equal(surface.rows[0]?.action.kind, "none");
  assert.equal(surface.rows[1]?.action.kind, "download");
  assert.equal(surface.rows[1]?.action.version, "1.1.0");
  assert.equal(surface.rows[1]?.direction, "rtl");
  assert.equal(surface.rows[1]?.removeAvailable, false);
  assert.equal(surface.rows[0]?.removeAction, null);
});

test("desktop language manager renders translated errors without mutating language data", () => {
  const state = {
    selectedLanguage: "fa",
    status: "error" as const,
    activeDownloadLanguage: null,
    progressPercent: null,
    errorKey: "LANGUAGE_ACTIVATION_NOT_CONFIGURED",
    rows: [
      {
        languageTag: "fa",
        locale: "fa-IR",
        direction: "rtl" as const,
        installedPackageId: "construction-pm.language.fa",
        installedVersion: "1.0.0",
        verified: true,
        offlineReady: true,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: true,
        selected: true,
      },
    ],
  };

  const surface = buildDesktopLanguageManagerSurface(
    state,
    catalog,
    "0.1.0",
    copy,
    (key) => `translated:${key}`,
  );

  assert.equal(surface.uiLanguage, "fa");
  assert.equal(surface.direction, "rtl");
  assert.equal(surface.statusText, "translated:LANGUAGE_ACTIVATION_NOT_CONFIGURED");
  assert.equal(surface.rows[0]?.languageTag, "fa");
  assert.equal(surface.rows[0]?.installedVersion, "1.0.0");
});


test("desktop language manager exposes a safe remove command for inactive verified packs", () => {
  const state = {
    selectedLanguage: "en",
    status: "ready" as const,
    activeDownloadLanguage: null,
    progressPercent: null,
    errorKey: null,
    rows: [
      {
        languageTag: "en",
        locale: "en-US",
        direction: "ltr" as const,
        installedPackageId: "construction-pm.language.en",
        installedVersion: "1.0.0",
        verified: true,
        offlineReady: true,
        aiText: true,
        voiceInput: false,
        voiceOutput: false,
        offlineAi: true,
        selected: true,
      },
      {
        languageTag: "fa",
        locale: "fa-IR",
        direction: "rtl" as const,
        installedPackageId: "construction-pm.language.fa",
        installedVersion: "1.0.0",
        verified: true,
        offlineReady: true,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: true,
        selected: false,
      },
    ],
  };

  const surface = buildDesktopLanguageManagerSurface(
    state,
    catalog,
    "0.1.0",
    copy,
  );

  assert.deepEqual(surface.rows[1]?.removeAction, {
    kind: "remove-installed",
    packageId: "construction-pm.language.fa",
    version: "1.0.0",
  });
});
