import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { WORKSPACE_NAVIGATION } from "./workspace-navigation.js";

const matrix = readFileSync(
  fileURLToPath(new URL("../../../docs/engineering/WEB_SURFACE_TRACEABILITY_MATRIX.md", import.meta.url)),
  "utf8",
);

const navigationKeys = new Set(WORKSPACE_NAVIGATION.map((item) => item.key));

const pageRows = matrix
  .split("\n")
  .filter((line) => {
    const cells = line.split("|").map((cell) => cell.trim());
    return cells.length >= 12 && navigationKeys.has(cells[1].replaceAll("`", ""));
  });

const submenuRows = matrix
  .split("\n")
  .filter((line) => /^\| [a-z]+ \| \d+ \| /.test(line));

function pageRow(key: string): string {
  const row = pageRows.find((line) => line.startsWith(`| \`${key}\` |`));
  assert.ok(row, `page ${key} is missing from the surface matrix`);
  return row;
}

test("surface matrix covers every navigation page with its declared status", () => {
  assert.equal(pageRows.length, WORKSPACE_NAVIGATION.length);
  for (const item of WORKSPACE_NAVIGATION) {
    const row = pageRow(item.key);
    const cells = row.split("|").map((cell) => cell.trim());
    assert.equal(cells[2], item.label.en, `${item.key} label drifted`);
    assert.equal(cells[3], item.status, `${item.key} nav status drifted from the code`);
  }
});

test("surface matrix lists every submenu in navigation order", () => {
  const expected = WORKSPACE_NAVIGATION.flatMap((item) =>
    item.submenus.map((submenu, index) => `${item.key}\u0000${index + 1}\u0000${submenu.en}`),
  );
  assert.equal(submenuRows.length, expected.length);
  for (const [position, entry] of expected.entries()) {
    const [key, index, label] = entry.split("\u0000");
    const row = submenuRows[position];
    assert.ok(
      row.startsWith(`| ${key} | ${index} | ${label} |`),
      `submenu ${key}#${index} (${label}) is missing or out of order: ${row}`,
    );
  }
});

test("surface status values are from the documented vocabulary", () => {
  const allowed = new Set(["WIRED", "WIRED-READ", "SHELL", "GAP-CORE"]);
  for (const row of pageRows) {
    const cells = row.split("|").map((cell) => cell.trim());
    const status = cells[9].replaceAll("`", "");
    assert.ok(allowed.has(status), `unknown surface status ${status} in ${cells[1]}`);
  }
  for (const row of submenuRows) {
    const cells = row.split("|").map((cell) => cell.trim());
    const status = cells[5].replaceAll("`", "");
    assert.ok(allowed.has(status), `unknown submenu status ${status} in ${cells[1]}#${cells[2]}`);
  }
});

test("every referenced gap is registered with an owner-friendly record", () => {
  const gapRows = matrix
    .split("\n")
    .filter((line) => /^\| GAP-[A-Z0-9-]+ \|/.test(line));
  const registered = new Set(gapRows.map((line) => line.split("|")[1].trim()));
  assert.ok(registered.size > 0);
  const referenced = new Set(
    matrix
      .split("\n")
      .flatMap((line) => line.match(/GAP-[A-Z0-9]+-[0-9]+/g) ?? []),
  );
  for (const gap of referenced) {
    assert.ok(registered.has(gap), `referenced gap ${gap} has no register row`);
  }
});

test("no surface claims completion without wired evidence", () => {
  for (const row of pageRows) {
    const cells = row.split("|").map((cell) => cell.trim());
    if (cells[9] === "WIRED") {
      assert.notEqual(cells[11], "None", `${cells[1]} is WIRED but lists no test evidence`);
    }
  }
});
