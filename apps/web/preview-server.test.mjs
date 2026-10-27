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

test("preview resolver maps built web output under /dist", () => {
  const resolved = resolveRequestFile("/dist/main.js?cache=1");
  assert.ok(portable(resolved)?.endsWith("apps/web/dist/web/src/main.js"));
});

test("preview resolver maps built client-sync output explicitly", () => {
  const resolved = resolveRequestFile("/client-sync/src/scheduling-adapter.js");
  assert.ok(portable(resolved)?.endsWith("apps/web/dist/client-sync/src/scheduling-adapter.js"));
});

test("preview resolver rejects path traversal outside the preview roots", () => {
  assert.equal(resolveRequestFile("/../package.json"), null);
  assert.equal(resolveRequestFile("/%2e%2e/package.json"), null);
});

test("preview resolver serves public marketing pages with and without trailing slash", () => {
  for (const route of ["/platform/", "/platform", "/solutions/", "/resources/", "/contact/"]) {
    const resolved = portable(resolveRequestFile(route));
    assert.ok(resolved?.endsWith("/index.html"), "Expected " + route + " to resolve to index.html");
    assert.ok(resolved?.includes("/public/"), "Expected " + route + " to resolve from public assets");
  }
});

test("preview resolver serves the canonical assistant avatar from the public asset root", () => {
  const resolved = portable(resolveRequestFile("/cubi-assistant-avatar.svg"));
  assert.ok(resolved?.endsWith("/apps/web/public/cubi-assistant-avatar.svg"));
  assert.ok(resolved && existsSync(resolved), "assistant avatar asset must exist at the resolved path");
});


test("preview resolver serves the Persian language routes as real documents", () => {
  for (const route of ["/fa/", "/fa", "/fa/index.html", "/fa/platform/", "/fa/solutions/", "/fa/resources/", "/fa/contact/"]) {
    const resolved = portable(resolveRequestFile(route));
    assert.ok(resolved?.endsWith("/index.html"), "Expected " + route + " to resolve to index.html");
    assert.ok(resolved?.includes("/public/fa/"), "Expected " + route + " to resolve from the Persian documents");
    assert.ok(resolved && existsSync(resolved), "Expected a shipped document for " + route);
  }
});

test("the language twins describe themselves and link to each other", () => {
  const pairs = [
    ["/platform/", "/fa/platform/"],
    ["/solutions/", "/fa/solutions/"],
    ["/resources/", "/fa/resources/"],
    ["/contact/", "/fa/contact/"],
  ];
  const switchHref = (html) => html.match(/<a class="cubi-public-language"[^>]*?href="([^"]+)"/)?.[1];
  for (const [english, persian] of pairs) {
    const englishHtml = readFileSync(resolveRequestFile(english), "utf8");
    const persianHtml = readFileSync(resolveRequestFile(persian), "utf8");
    assert.match(englishHtml, /<html lang="en" dir="ltr">/);
    assert.match(persianHtml, /<html lang="fa" dir="rtl">/);
    const forward = switchHref(englishHtml);
    const backward = switchHref(persianHtml);
    assert.ok(forward, `${english} has no language switch link`);
    assert.ok(backward, `${persian} has no language switch link`);
    // Directory URLs make a wrong "./" prefix resolve to a dead route, so the
    // switch is verified as a real URL rather than as a string.
    assert.equal(new URL(forward, "https://preview.test" + english).pathname, persian);
    assert.equal(new URL(backward, "https://preview.test" + persian).pathname, english);
  }
});

test("every public page and the workspace shell load the shared floating assistant", () => {
  for (const route of [
    "/", "/platform/", "/solutions/", "/resources/", "/contact/",
    "/fa/", "/fa/platform/", "/fa/solutions/", "/fa/resources/", "/fa/contact/",
    "/app",
  ]) {
    const resolved = resolveRequestFile(route);
    assert.ok(resolved && existsSync(resolved), "Expected a page for " + route);
    assert.match(readFileSync(resolved, "utf8"), /global-assistant-launcher\.js/, "Missing assistant launcher script on " + route);
  }
});

test("preview resolver maps the floating assistant module to the compiled Web output", () => {
  const resolved = portable(resolveRequestFile("/dist/global-assistant-launcher.js"));
  assert.ok(resolved?.endsWith("/apps/web/dist/web/src/global-assistant-launcher.js"));
});
