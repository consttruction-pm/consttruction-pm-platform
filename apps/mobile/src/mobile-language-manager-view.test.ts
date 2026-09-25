import assert from "node:assert/strict";
import test from "node:test";

import {
  buildMobileLanguageManagerSurface,
  type MobileLanguageManagerCopy,
} from "./mobile-language-manager-view.js";

const copy: MobileLanguageManagerCopy = {
  title: "Language",
  ready: "Ready",
  downloading: (language) => `Downloading ${language}`,
  language: "Language",
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
  rtl: "RTL",
  ltr: "LTR",
  downloadProgress: "Language pack download progress",
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
  ],
} as const;

test("mobile language manager surface is compact, registry-driven and RTL aware", () => {
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

  const surface = buildMobileLanguageManagerSurface(
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
  assert.equal(surface.rows[1]?.voiceInput, true);
  assert.equal(surface.rows[1]?.removeAction, null);
});

test("mobile language manager exposes inactive-pack removal", () => {
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

  const surface = buildMobileLanguageManagerSurface(
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
