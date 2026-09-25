import assert from "node:assert/strict";
import test from "node:test";

import { toUiState } from "./language-manager-ui-contract.ts";

test("maps language manager state into framework-neutral UI state", () => {
  const state = toUiState({
    selectedLanguage: "fa",
    downloading: "fa",
    progress: {
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.0.0",
      phase: "downloading",
      bytesReceived: 25,
      totalBytes: 100,
    },
    error: null,
    items: [
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        installedPackageId: null,
        installedVersion: null,
        verified: false,
        offlineReady: false,
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: true,
          voiceOutput: true,
          offlineAi: true,
        },
      },
    ],
  });

  assert.equal(state.selectedLanguage, "fa");
  assert.equal(state.rows[0]?.selected, true);
  assert.equal(state.rows[0]?.offlineAi, true);
  assert.equal(state.progressPercent, 25);
  assert.equal(state.status, "downloading");
});

test("reports UI error state", () => {
  const state = toUiState({
    selectedLanguage: "en",
    downloading: null,
    progress: null,
    error: "LANGUAGE_PACK_VERIFICATION_FAILED",
    items: [],
  });

  assert.equal(state.status, "error");
  assert.equal(state.errorMessage, "LANGUAGE_PACK_VERIFICATION_FAILED");
});


test("exposes errors as translation keys", () => {
  const state = toUiState({
    selectedLanguage: "en",
    items: [],
    downloading: null,
    progress: null,
    error: "LANGUAGE_PACK_VERIFICATION_FAILED",
  });

  assert.equal(state.status, "error");
  assert.equal(state.errorKey, "LANGUAGE_PACK_VERIFICATION_FAILED");
});
