import assert from "node:assert/strict";
import test from "node:test";

import { toUiState } from "../../client-sync/src/language-manager-ui-contract.js";

test("Web UI contract preserves RTL and capability metadata", () => {
  const state = toUiState({
    selectedLanguage: "fa",
    items: [
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        installedPackageId: "construction-pm.language.fa",
        installedVersion: "1.0.0",
        verified: true,
        offlineReady: true,
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
    downloading: null,
    progress: null,
    error: null,
  });

  assert.equal(state.rows[0]?.direction, "rtl");
  assert.equal(state.rows[0]?.offlineAi, true);
  assert.equal(state.rows[0]?.selected, true);
});
