import assert from "node:assert/strict";
import test from "node:test";
import {
  WORKSPACE_ICON_NAMES,
  isWorkspaceIconName,
  workspaceIcon,
} from "./workspace-icons.js";

test("the icon registry is closed and unique", () => {
  assert.equal(new Set(WORKSPACE_ICON_NAMES).size, WORKSPACE_ICON_NAMES.length);
  assert.ok(WORKSPACE_ICON_NAMES.includes("milestone"));
  assert.ok(WORKSPACE_ICON_NAMES.includes("refresh"));
  assert.equal(isWorkspaceIconName("milestone"), true);
  assert.equal(isWorkspaceIconName("not-an-icon"), false);
});

test("unknown icons throw instead of falling back to another glyph", () => {
  assert.throws(
    () => workspaceIcon("not-an-icon" as never),
    /UNKNOWN_WORKSPACE_ICON:not-an-icon/,
  );
  const known = workspaceIcon("milestone");
  assert.match(known, /data-cp-icon="milestone"/);
  assert.match(known, /<path d="M8 2l6 6-6 6-6-6z">/);
  assert.match(known, /aria-hidden="true"/);
});
