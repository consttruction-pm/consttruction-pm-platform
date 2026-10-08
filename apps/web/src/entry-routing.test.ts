import assert from "node:assert/strict";
import test from "node:test";
import { resolveEntryRoute } from "./entry-routing.js";

test("custom-domain root paths resolve to the CUBI landing page", () => {
  for (const pathname of ["/", "", "/index.html", "/index.html/"]) {
    assert.equal(resolveEntryRoute(pathname), "landing", pathname);
  }
});

test("GitHub Pages project-base paths resolve to the CUBI landing page", () => {
  for (const pathname of [
    "/consttruction-pm-platform",
    "/consttruction-pm-platform/",
    "/consttruction-pm-platform/index.html",
  ]) {
    assert.equal(resolveEntryRoute(pathname), "landing", pathname);
  }
});

test("app paths resolve to the application under custom domain and project base", () => {
  for (const pathname of [
    "/app",
    "/app/",
    "/app/index.html",
    "/consttruction-pm-platform/app",
    "/consttruction-pm-platform/app/",
    "/consttruction-pm-platform/app/index.html",
  ]) {
    assert.equal(resolveEntryRoute(pathname), "app", pathname);
  }
});
