import assert from "node:assert/strict";
import test from "node:test";

import { getWorkspaceStartupCopy, renderWorkspaceStartupMarkup } from "./workspace-startup.js";

test("workspace startup has localized loading, slow and failed states", () => {
  for (const locale of ["en", "fa"] as const) {
    for (const mode of ["loading", "slow", "failed"] as const) {
      const copy = getWorkspaceStartupCopy(locale, mode);
      const markup = renderWorkspaceStartupMarkup(locale, mode);
      assert.ok(copy.title.length > 0);
      assert.ok(copy.message.length > 0);
      assert.match(markup, new RegExp(`data-workspace-startup="${mode}"`));
      assert.match(markup, new RegExp(`lang="${locale}"`));
      assert.match(markup, new RegExp(`dir="${locale === "fa" ? "rtl" : "ltr"}"`));
      assert.match(markup, /class="cp-startup-card"/);
    }
  }
});

test("slow and failed workspace startup states include a recovery action and stable diagnostic code", () => {
  for (const locale of ["en", "fa"] as const) {
    for (const mode of ["slow", "failed"] as const) {
      const markup = renderWorkspaceStartupMarkup(locale, mode);
      assert.match(markup, /data-workspace-startup-reload/);
      assert.match(markup, /data-startup-code=/);
    }
  }
  assert.equal(getWorkspaceStartupCopy("en", "failed").code, "WORKSPACE_ENTRY_LOAD_FAILED");
  assert.equal(getWorkspaceStartupCopy("fa", "failed").code, "WORKSPACE_ENTRY_LOAD_FAILED");
});

test("loading state exposes an accessible progress indicator without a false reload action", () => {
  const markup = renderWorkspaceStartupMarkup("en", "loading");
  assert.match(markup, /role="status"/);
  assert.match(markup, /role="progressbar"/);
  assert.doesNotMatch(markup, /data-workspace-startup-reload/);
});
