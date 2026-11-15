import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";
import { resolveRequestFile } from "./preview-server.mjs";

// The resolver returns platform-native paths. Normalizing separators keeps the
// contract assertions meaningful on Windows, Linux and macOS.
function portable(value) {
  return value === null ? null : value.replaceAll("\\", "/");
}

test("preview resolver serves the main HTML entry", () => {
  const resolved = resolveRequestFile("/");
  assert.ok(portable(resolved)?.endsWith("apps/web/index.html"));
});

test("preview resolver serves the temporary role picker and personal workbench", () => {
  assert.ok(portable(resolveRequestFile("/login"))?.endsWith("apps/web/login.html"));
  assert.ok(portable(resolveRequestFile("/workbench"))?.endsWith("apps/web/workbench.html"));
});

test("preview resolver serves the application shell at /app", () => {
  for (const route of ["/app", "/app/", "/app/index.html", "/app?view=activity"]) {
    const resolved = resolveRequestFile(route);
    assert.ok(portable(resolved)?.endsWith("apps/web/app.html"), "Expected " + route + " to resolve to app.html");
  }
});

test("preview resolver strips query strings", () => {
  assert.equal(
    resolveRequestFile("/styles.css?v=42"),
    resolveRequestFile("/styles.css"),
  );
});

test("preview resolver maps the checkout module into the built web output", () => {
  const resolved = portable(resolveRequestFile("/dist/pro-ch¶»§q«^