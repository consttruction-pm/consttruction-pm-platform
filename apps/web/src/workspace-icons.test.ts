import assert from "node:assert/strict";
import test from "node:test";
import {
  WORKSPACE_ICON_NAMES,
  isWorkspaceIconName,
  workspaceIcon,
} from "./workspace-icons.js";
import { WORKSPACE_WINDOW_ICONS } from "./workspace-command-icons.js";

test("the icon registry is closed and unique", () => {
  assert.equal(new Set(WORKSPACE_ICON_NAMES).size, WORKSPACE_ICON_NAMES.length);
  assert.ok(WORKSPACE_ICON_NAMES.includes("milestone"));
  assert.ok(WORKSPACE_ICON_NAMES.includes("refresh"));
  assert.equal(isWorkspaceIconName("milestone"), true);
  assert.equal(isWorkspaceIconName("not-an-icon"), false);
});

test("every registry icon paints a distinct path", () => {
  const paths = WORKSPACE_ICON_NAMES.map((name) => {
    const markup = workspaceIcon(name);
    const path = /<path d="([^"]+)"/.exec(markup)?.[1];
    assert.ok(path, `icon ${name} must render a path`);
    return path;
  });
  const byPath = new Map<string, string[]>();
  WORKSPACE_ICON_NAMES.forEach((name, index) => {
    const owners = byPath.get(paths[index]) ?? [];
    owners.push(name);
    byPath.set(paths[index], owners);
  });
  const duplicates = [...byPath.values()].filter((owners) => owners.length > 1);
  assert.deepEqual(duplicates, [], `independent icons must not share one glyph: ${JSON.stringify(duplicates)}`);
});

test("independent workspace windows never share one glyph", () => {
  const entries = Object.entries(WORKSPACE_WINDOW_ICONS);
  const byIcon = new Map<string, string[]>();
  for (const [windowKey, icon] of entries) {
    const owners = byIcon.get(icon) ?? [];
    owners.push(windowKey);
    byIcon.set(icon, owners);
  }
  const duplicates = [...byIcon.entries()].filter(([, owners]) => owners.length > 1);
  assert.deepEqual(duplicates, [], `windows must map to distinct icon names: ${JSON.stringify(duplicates)}`);
  // The problem glyphs from the owner review must stay separate.
  const glyphs = (name: (typeof WORKSPACE_WINDOW_ICONS)[keyof typeof WORKSPACE_WINDOW_ICONS]) =>
    /<path d="([^"]+)"/.exec(workspaceIcon(name))?.[1];
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.issues), glyphs(WORKSPACE_WINDOW_ICONS.risks));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.issues), glyphs("warning"));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.resources), glyphs(WORKSPACE_WINDOW_ICONS.roles));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.cost), glyphs(WORKSPACE_WINDOW_ICONS.expenses));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.progress), glyphs(WORKSPACE_WINDOW_ICONS.tracking));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.thresholds), glyphs(WORKSPACE_WINDOW_ICONS.control));
  assert.notEqual(glyphs(WORKSPACE_WINDOW_ICONS.documents), glyphs(WORKSPACE_WINDOW_ICONS.backup));
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
