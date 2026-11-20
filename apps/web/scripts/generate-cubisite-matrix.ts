// Regenerates the C01–C35 capability/page/Help matrix and its JSON registry.
//
// Run with `npm run cubisite:matrix`. The output is deterministic: the test
// `src/capability-inheritance.test.ts` compares the committed files with a fresh
// render and fails on any drift.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { ROUTE_PATHS } from "../site/routes.mjs";
import { CAPABILITIES } from "../site/capabilities.mjs";
import { renderMarkdown, renderRegistryJson } from "../src/capability-inheritance.ts";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");

const routes = Object.entries(ROUTE_PATHS as Record<string, string>).map(([id, path]) => ({ id, path }));
const features = (CAPABILITIES as Array<{ id: string; route: string; status: string }>).map((feature) => ({
  id: feature.id,
  route: feature.route,
  status: feature.status,
}));

const markdownPath = join(repoRoot, "docs", "cubisite", "CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md");
const registryPath = join(repoRoot, "docs", "cubisite", "capability-page-help-registry.json");

writeFileSync(markdownPath, renderMarkdown(routes, features));
writeFileSync(registryPath, renderRegistryJson(routes, features));

const registry = JSON.parse(readFileSync(registryPath, "utf8"));
console.log(
  `Wrote ${registry.capabilities.length} capabilities and ${registry.pages.length} pages ` +
    `(${registry.pages.filter((page: { help: { topic: unknown } }) => page.help.topic).length} with an official topic).`,
);
