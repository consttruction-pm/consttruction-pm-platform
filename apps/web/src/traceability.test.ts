import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

/**
 * P1 contract — environment ↔ official Help traceability.
 *
 * Every CUBI public route and workspace window is mapped to the official Help
 * baseline of its environment (Engineering: P6 Professional V26 HTML Help plus
 * the 815-page Help PDF; Enterprise: P6 EPPM V26 HTML Help). The matrices are
 * internal evidence and must never leak vendor branding into the customer UI.
 */
const root = process.cwd();
const repoRoot = join(root, "..", "..");
const traceDir = join(repoRoot, "docs", "traceability");

type Help = { source: string; title: string; url: string; pdfPage: number | null };
type Row = {
  id: string;
  environment: "engineering" | "enterprise";
  kind: "public_page" | "workspace_page";
  page: string;
  surface: string;
  module: string | null;
  help: Help | null;
  helpRationale: string | null;
  cubiBehavior: string;
  evidence: string;
  status: string;
};

function loadMatrix(file: string): { baseline: string; rows: Row[] } {
  return JSON.parse(readFileSync(join(traceDir, file), "utf8"));
}

const engineering = loadMatrix("engineering-v26.json");
const enterprise = loadMatrix("enterprise-v26.json");
const allRows = [...engineering.rows, ...enterprise.rows];

const ENG_URL = "https://docs.oracle.com/cd/G48902_01/client_help/en_US/";
const EPPM_URL = "https://docs.oracle.com/cd/G48897_01/p6help/en/";
const STATUSES = new Set(["PUBLISHED", "IMPLEMENTED", "PARTIAL", "PLANNED", "CUBI_OWNED", "LEGAL"]);
const ENTERPRISE_MODULES = new Set([
  "team-task",
  "feedback-approval",
  "operations-job",
  "workflow",
  "organization-access",
  "project-portal",
  "integration-hub",
  "portfolio-executive",
]);

function routesFromInventory(): string[] {
  const source = readFileSync(join(root, "site", "routes.mjs"), "utf8");
  const block = source.match(/export const ROUTE_PATHS = \{([\s\S]*?)\};/);
  assert.ok(block, "ROUTE_PATHS block must exist");
  return [...block![1].matchAll(/(?:"[^"]+"|[A-Za-z0-9_-]+):\s*"([^"]*)"/g)].map((match) => match[1]);
}

test("every English public route is mapped exactly once", () => {
  const routes = routesFromInventory();
  assert.equal(routes.length, 25, "the canonical inventory is 25 routes");
  const mapped = engineering.rows.filter((row) => row.kind === "public_page").map((row) => row.page);
  assert.equal(new Set(mapped).size, mapped.length, "public pages must not repeat");
  for (const route of routes) {
    const page = `/${route}`;
    assert.ok(mapped.includes(page), `route ${page} is missing from the Engineering matrix`);
  }
});

test("matrix rows are unique, complete and carry real evidence", () => {
  const ids = allRows.map((row) => row.id);
  assert.equal(new Set(ids).size, ids.length, "row ids must be unique");
  for (const row of allRows) {
    assert.ok(row.id && row.page && row.surface && row.cubiBehavior, `row ${row.id} is incomplete`);
    assert.ok(STATUSES.has(row.status), `row ${row.id} has an unknown status ${row.status}`);
    assert.ok(existsSync(join(repoRoot, row.evidence)), `row ${row.id} evidence is missing: ${row.evidence}`);
    if (row.help === null) {
      assert.ok(
        row.status === "CUBI_OWNED" || row.status === "LEGAL",
        `row ${row.id} may omit Help only when CUBI-owned or legal`,
      );
      assert.ok(row.helpRationale, `row ${row.id} must explain why no Help topic applies`);
    }
  }
});

test("Engineering rows cite the V26 HTML Help and a page of the 815-page PDF", () => {
  for (const row of engineering.rows) {
    if (!row.help) continue;
    assert.equal(row.help.source, "P6 Professional V26 HTML Help", `row ${row.id} source`);
    assert.ok(row.help.url.startsWith(ENG_URL), `row ${row.id} must cite P6 Professional V26 HTML Help`);
    assert.ok(Number.isInteger(row.help.pdfPage), `row ${row.id} needs a PDF page`);
    assert.ok(row.help.pdfPage! >= 1 && row.help.pdfPage! <= 815, `row ${row.id} PDF page outside 1..815`);
  }
});

test("Enterprise rows cite the P6 EPPM V26 HTML Help and cover all eight modules", () => {
  const modules = new Set<string>();
  for (const row of enterprise.rows) {
    if (row.help) {
      assert.equal(row.help.source, "P6 EPPM V26 HTML Help", `row ${row.id} source`);
      assert.ok(row.help.url.startsWith(EPPM_URL), `row ${row.id} must cite P6 EPPM V26 HTML Help`);
      assert.equal(row.help.pdfPage, null, `row ${row.id} must not claim an EPPM PDF page`);
    }
    if (row.module) modules.add(row.module);
  }
  for (const module of ENTERPRISE_MODULES) {
    assert.ok(modules.has(module), `Enterprise module ${module} is not represented`);
  }
});

test("generated Markdown stays in sync with the JSON source", () => {
  for (const [file, matrix] of [
    ["CUBI_ENGINEERING_V26_TRACEABILITY.md", engineering],
    ["CUBI_ENTERPRISE_V26_TRACEABILITY.md", enterprise],
  ] as const) {
    const markdown = readFileSync(join(traceDir, file), "utf8");
    assert.ok(markdown.includes(`**Rows:** ${matrix.rows.length}`), `${file} row count is stale`);
    for (const row of matrix.rows) {
      assert.ok(markdown.includes(`| ${row.id} |`), `${file} is missing row ${row.id}`);
    }
  }
});

test("customer-facing surfaces never expose the vendor baseline", () => {
  const banned = /\b(?:Oracle|Primavera|EPPM)\b|\bP6\b/i;
  const files: string[] = [join(root, "index.html")];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".html")) files.push(path);
    }
  };
  walk(join(root, "public"));
  for (const entry of readdirSync(join(root, "site", "locales"))) {
    if (entry.endsWith(".mjs")) files.push(join(root, "site", "locales", entry));
  }
  for (const entry of readdirSync(join(root, "src"))) {
    if (/^landing.*\.ts$/.test(entry)) files.push(join(root, "src", entry));
  }
  for (const file of files) {
    const match = readFileSync(file, "utf8").match(banned);
    assert.equal(match, null, `${file} exposes vendor branding: ${match?.[0]}`);
  }
});
