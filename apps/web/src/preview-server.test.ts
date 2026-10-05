import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { dirname, join } from "node:path";

import { resolveRequestFile } from "../preview-server.mjs";

const webRoot = dirname(fileURLToPath(new URL("../index.html", import.meta.url)));

test("preview resolver maps the root document", () => {
  assert.equal(resolveRequestFile("/"), join(webRoot, "index.html"));
});

test("preview resolver maps the compiled web entry", () => {
  assert.equal(resolveRequestFile("/dist/main.js"), join(webRoot, "dist", "web", "src", "main.js"));
});

test("preview resolver preserves query-string independence", () => {
  assert.equal(
    resolveRequestFile("/dist/main.js?cacheBust=1"),
    join(webRoot, "dist", "web", "src", "main.js"),
  );
});

test("preview resolver maps client-sync output", () => {
  assert.equal(
    resolveRequestFile("/client-sync/src/revision-transport.js"),
    join(webRoot, "dist", "client-sync", "src", "revision-transport.js"),
  );
});

test("preview resolver rejects traversal outside the web root", () => {
  assert.equal(resolveRequestFile("/dist/../../../../package.json"), null);
});

test("preview resolver rejects encoded traversal outside the web root", () => {
  assert.equal(resolveRequestFile("/dist/%2e%2e/%2e%2e/%2e%2e/%2e%2e/package.json"), null);
});
