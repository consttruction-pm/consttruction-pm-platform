import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import {
  FEATURE_REGISTRY,
  HELP_REGISTRY,
  normalizeHelpRoute,
  resolveContextualHelp,
} from "./help-registry.js";
import { getAssistantHelpCopy } from "./assistant-help-copy.js";
import { resolveAssistantGuide } from "./assistant-guide.js";

const root = process.cwd();

type TraceabilityRow = {
  id: string;
  page: string;
  surface: string;
  help: { source: string; title: string; url: string; pdfPage: number | null } | null;
  helpRationale: string | null;
  status: string;
};

function readRows(file: string): TraceabilityRow[] {
  const document = JSON.parse(
    readFileSync(join(root, "../../docs/traceability", file), "utf8"),
  );
  return document.rows as TraceabilityRow[];
}

test("the compiled Help registry matches the traceability sources", () => {
  const rows = [...readRows("engineering-v26.json"), ...readRows("enterprise-v26.json")];
  assert.equal(HELP_REGISTRY.length, rows.length);
  for (const [index, row] of rows.entries()) {
    const entry = HELP_REGISTRY[index];
    assert.equal(entry.id, row.id);
    assert.equal(entry.page, row.page ?? "");
    assert.equal(entry.surface, row.surface);
    assert.equal(entry.rationale, row.helpRationale ?? null);
    assert.equal(entry.status, row.status);
    if (row.help) {
      assert.deepEqual(entry.help, {
        source: row.help.source,
        title: row.help.title,
        url: row.help.url,
        pdfPage: row.help.pdfPage ?? null,
      });
    } else {
      assert.equal(entry.help, null, `${entry.id} must stay without a topic`);
    }
  }
});

test("the compiled feature registry matches the published capability contract", () => {
  const catalog = JSON.parse(readFileSync(join(root, "public/capabilities.json"), "utf8"));
  assert.equal(FEATURE_REGISTRY.length, catalog.capabilities.length);
  for (const [index, capability] of catalog.capabilities.entries()) {
    const feature = FEATURE_REGISTRY[index];
    assert.equal(feature.id, capability.id);
    assert.equal(feature.route, capability.route);
    assert.equal(feature.status, capability.status);
    assert.equal(feature.traceabilityId, capability.traceability_id);
  }
});

test("route normalisation strips the base path, index file and locale prefix", () => {
  assert.equal(normalizeHelpRoute("/features/cost/index.html"), "/features/cost/");
  assert.equal(normalizeHelpRoute("/tr/features/cost/"), "/features/cost/");
  assert.equal(normalizeHelpRoute("/ar/"), "/");
  assert.equal(normalizeHelpRoute("/repo/de/faq/index.html", "/repo/"), "/faq/");
  assert.equal(normalizeHelpRoute(""), "/");
});

test("direct, localized and feature resolution cite the recorded topic", () => {
  const direct = resolveContextualHelp("/features/cost/");
  assert.equal(direct.level, "direct");
  assert.equal(direct.topic?.title, "Expenses");
  assert.equal(direct.topic?.pdfPage, 250);
  assert.equal(direct.feature?.id, "cost");
  assert.equal(direct.feature?.status, "PARTIAL");

  const localized = resolveContextualHelp("/tr/features/scheduling/");
  assert.equal(localized.level, "direct");
  assert.equal(localized.topic?.title, "Scheduling Projects");
  assert.equal(localized.feature?.id, "scheduling");
});

test("a deeper path inherits the nearest documented parent", () => {
  const parent = resolveContextualHelp("/features/cost/sub-screen/");
  assert.equal(parent.level, "parent");
  assert.equal(parent.entryId, "ENG-PUB-FEATURES-COST");
  assert.equal(parent.topic?.title, "Expenses");
});

test("workspace menus resolve their documented surface", () => {
  const wbs = resolveContextualHelp("/app/", { menu: "wbs" });
  assert.equal(wbs.level, "direct");
  assert.equal(wbs.entryId, "ENG-WS-WBS");
  assert.equal(wbs.topic?.title, "Defining the WBS");

  const unmapped = resolveContextualHelp("/app/", { menu: "backup" });
  assert.equal(unmapped.level, "direct");
  assert.equal(unmapped.entryId, "ENG-WS-SHELL");
});

test("a workspace path without its own row inherits the shell topic", () => {
  const inherited = resolveContextualHelp("/app/unmapped/");
  assert.equal(inherited.level, "inherited");
  assert.equal(inherited.entryId, "ENG-WS-SHELL");
  assert.equal(inherited.topic?.title, "Using main windows");
});

test("an enterprise path without its own row uses the nearest documented parent", () => {
  const parent = resolveContextualHelp("/enterprise/unmapped/");
  assert.equal(parent.level, "parent");
  assert.equal(parent.entryId, "ENT-DASHBOARDS");
});

test("pages without an official topic fall back to internal documentation", () => {
  const platform = resolveContextualHelp("/platform/");
  assert.equal(platform.level, "internal-docs");
  assert.equal(platform.topic, null);
  assert.match(platform.reason ?? "", /no P6 Professional Help topic/i);

  const privacy = resolveContextualHelp("/de/privacy/");
  assert.equal(privacy.level, "internal-docs");
  assert.equal(privacy.topic, null);
});

test("the AI Workbench document is registered without borrowing a vendor topic", () => {
  const workbench = resolveContextualHelp("/ai-workbench/");
  assert.equal(workbench.level, "internal-docs");
  assert.equal(workbench.entryId, "ENG-WS-AI-WORKBENCH");
  assert.equal(workbench.topic, null);
  assert.match(workbench.reason ?? "", /CUBI-owned/i);
});

test("an unknown public path never borrows another page's topic", () => {
  const unknown = resolveContextualHelp("/not-a-page/");
  assert.equal(unknown.level, "internal-docs");
  assert.equal(unknown.entryId, null);
  assert.equal(unknown.topic, null);
  assert.equal(unknown.reason, null);
});

test("the guide carries the same resolved help as the registry", () => {
  const cost = resolveAssistantGuide({
    page: "platform",
    state: "visitor",
    locale: "en",
    pathname: "/platform/",
  });
  assert.equal(cost.help.level, "internal-docs");
  assert.equal(cost.help.topic, null);
  assert.match(cost.help.reason ?? "", /CUBI-owned public content/);

  const workspace = resolveAssistantGuide({
    page: "workspace",
    state: "ready",
    menu: "calendars",
    locale: "de",
    pathname: "/app/",
  });
  assert.equal(workspace.help.level, "direct");
  assert.equal(workspace.help.topic?.title, "Defining Calendars");
});

test("the Help labels are localized for all ten locales", () => {
  for (const locale of ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"]) {
    const copy = getAssistantHelpCopy(locale);
    assert.ok(copy.heading.trim().length > 2, `${locale} heading`);
    assert.ok(copy.noTopic.trim().length > 10, `${locale} noTopic`);
    assert.ok(copy.level.direct.trim().length >= 2, `${locale} direct label`);
    assert.ok(copy.level["internal-docs"].trim().length >= 2, `${locale} internal label`);
  }
  assert.match(getAssistantHelpCopy("ar").heading, /[\u0600-\u06FF]/);
  assert.match(getAssistantHelpCopy("ja").heading, /[\u3040-\u30FF]/);
  assert.notEqual(getAssistantHelpCopy("fa").heading, getAssistantHelpCopy("en").heading);
});
