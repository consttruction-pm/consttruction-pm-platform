import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";

import { HELP_REGISTRY, resolveContextualHelp } from "./help-registry.js";
import {
  CAPABILITY_INHERITANCE,
  SITE_WIDE_CAPABILITIES,
  capabilityIdsForRoute,
  renderMarkdown,
  renderRegistryJson,
} from "./capability-inheritance.js";
import { CAPABILITIES } from "../site/capabilities.mjs";
import { ROUTE_PATHS } from "../site/routes.mjs";

const matrixPath = new URL("../../../docs/cubisite/CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md", import.meta.url);
const registryPath = new URL("../../../docs/cubisite/capability-page-help-registry.json", import.meta.url);

const routes = Object.entries(ROUTE_PATHS as Record<string, string>).map(([id, path]) => ({ id, path }));
const features = CAPABILITIES.map((feature) => ({
  id: feature.id,
  route: feature.route,
  status: feature.status,
}));

const traceability = ["engineering", "enterprise"].flatMap((environment) => {
  const raw = JSON.parse(
    readFileSync(new URL(`../../../docs/traceability/${environment}-v26.json`, import.meta.url), "utf8"),
  );
  return (Array.isArray(raw) ? raw : raw.rows) as Array<{ id: string; help: unknown }>;
});
const traceabilityIds = new Set(traceability.map((row) => row.id));
const helpIds = new Set(HELP_REGISTRY.map((entry) => entry.id));

test("the committed matrix and registry match a fresh render", () => {
  assert.ok(existsSync(matrixPath), "the matrix must be committed");
  assert.ok(existsSync(registryPath), "the registry must be committed");
  assert.equal(readFileSync(matrixPath, "utf8"), renderMarkdown(routes, features));
  assert.equal(readFileSync(registryPath, "utf8"), renderRegistryJson(routes, features));
});

test("the matrix carries C01 through C35 exactly once, in order", () => {
  const ids = CAPABILITY_INHERITANCE.map((capability) => capability.id);
  assert.equal(ids.length, 35);
  assert.deepEqual(
    ids,
    Array.from({ length: 35 }, (_, index) => `C${String(index + 1).padStart(2, "0")}`),
  );
});

test("every capability cites only existing routes, rows, entries and features", () => {
  const routePaths = new Set(routes.map((route) => route.path));
  const featureIds = new Set(features.map((feature) => feature.id));
  for (const capability of CAPABILITY_INHERITANCE) {
    for (const route of capability.publicRoutes) {
      assert.ok(routePaths.has(route), `${capability.id} cites unknown route /${route}`);
    }
    for (const row of capability.workspaceRows) {
      assert.ok(traceabilityIds.has(row), `${capability.id} cites unknown traceability row ${row}`);
    }
    if (capability.helpEntryId) {
      assert.ok(helpIds.has(capability.helpEntryId), `${capability.id} cites unknown help entry`);
      const entry = HELP_REGISTRY.find((candidate) => candidate.id === capability.helpEntryId);
      assert.ok(entry?.help, `${capability.id} cites an entry without an official topic`);
    }
    if (capability.featureId) {
      assert.ok(featureIds.has(capability.featureId), `${capability.id} cites unknown feature`);
    }
  }
});

test("C05 stays an evidence gap instead of an invented capability", () => {
  const c05 = CAPABILITY_INHERITANCE.find((capability) => capability.id === "C05");
  assert.ok(c05);
  assert.equal(c05.status, "MISSING_EVIDENCE");
  assert.deepEqual([...c05.publicRoutes], []);
  assert.deepEqual([...c05.workspaceRows], []);
  assert.equal(c05.helpEntryId, null);
  assert.equal(c05.featureId, null);
});

test("every published route appears with the capability set it advertises", () => {
  const registry = JSON.parse(readFileSync(registryPath, "utf8"));
  assert.equal(registry.pages.length, routes.length);
  for (const route of routes) {
    const page = registry.pages.find((candidate: { route: string }) => candidate.route === route.path);
    assert.ok(page, `matrix is missing /${route.path}`);
    assert.deepEqual(page.capabilityIds, capabilityIdsForRoute(route.path));
    for (const siteWide of SITE_WIDE_CAPABILITIES) {
      assert.ok(page.capabilityIds.includes(siteWide), `/${route.path} must inherit ${siteWide}`);
    }
  }
});

test("page help is exactly what the assistant resolves", () => {
  const registry = JSON.parse(readFileSync(registryPath, "utf8"));
  for (const page of registry.pages) {
    const resolved = resolveContextualHelp(`/${page.route}`);
    assert.equal(page.help.level, resolved.level, `/${page.route} level drifted`);
    assert.equal(page.help.entryId, resolved.entryId, `/${page.route} entry drifted`);
    assert.deepEqual(page.help.topic, resolved.topic, `/${page.route} topic drifted`);
  }
});

test("the reconciliation counts match the traceability sources", () => {
  const engineering = traceability.filter((row) => (row as { help?: { pdfPage?: number } }).help?.pdfPage);
  const topics = traceability.filter((row) => (row as { help?: unknown }).help);
  const registry = JSON.parse(readFileSync(registryPath, "utf8"));
  assert.equal(registry.reconciliation.engineeringPdfPages, engineering.length);
  assert.equal(registry.reconciliation.engineeringPdfPagesMatched, engineering.length);
  assert.equal(registry.reconciliation.officialTopics, topics.length);
  assert.equal(registry.reconciliation.officialTopicsReachable, topics.length);
});

test("every official topic in the matrix exists in the Help registry", () => {
  const markdown = readFileSync(matrixPath, "utf8");
  const titles = new Set(
    HELP_REGISTRY.flatMap((entry) => (entry.help ? [entry.help.title] : [])),
  );
  for (const page of JSON.parse(readFileSync(registryPath, "utf8")).pages) {
    if (!page.help.topic) continue;
    assert.ok(titles.has(page.help.topic.title), `invented topic title: ${page.help.topic.title}`);
    assert.ok(markdown.includes(page.help.topic.title), `matrix omits ${page.help.topic.title}`);
  }
});
