import assert from "node:assert/strict";
import test from "node:test";
import { resolveRequestFile } from "./preview-server.mjs";

test("preview resolver serves the main HTML entry", () => {
  const resolved = resolveRequestFile("/");
  assert.ok(resolved?.endsWith("apps/web/index.html"));
});

test("preview resolver strips query strings", () => {
  assert.equal(
    resolveRequestFile("/styles.css?v=42"),
    resolveRequestFile("/styles.css"),
  );
});

test("preview resolver maps built web output under /dist", () => {
  const resolved = resolveRequestFile("/dist/main.js?cache=1");
  assert.ok(resolved?.endsWith("apps/web/dist/web/src/main.js"));
});

test("preview resolver maps built client-sync output explicitly", () => {
  const resolved = resolveRequestFile("/client-sync/src/scheduling-adapter.js");
  assert.ok(resolved?.endsWith("apps/web/dist/client-sync/src/scheduling-adapter.js"));
});

test("preview resolver rejects path traversal outside the preview roots", () => {
  assert.equal(resolveRequestFile("/../package.json"), null);
  assert.equal(resolveRequestFile("/%2e%2e/package.json"), null);
});
