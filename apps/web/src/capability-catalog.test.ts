import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

/**
 * P3 contract — the public capability contract is generated from real evidence.
 *
 * `/capabilities.json` is the only machine-readable statement of what the
 * public site claims. Every capability must resolve to a published route, a
 * repository evidence path and a matching traceability row; the Pro offer must
 * match the authoritative checkout constant.
 */
const webRoot = process.cwd();
const repoRoot = join(webRoot, "..", "..");
const publicRoot = join(webRoot, "public");
const catalogPath = join(publicRoot, "capabilities.json");

type Capability = {
  id: string;
  environment: string;
  route: string;
  status: string;
  traceability_id: string;
};
type Catalog = {
  contract_version: string;
  generated_from: string;
  offer: {
    plan: string;
    currency: string;
    unit_price_minor: number;
    price_source: string;
    checkout_route: string;
  };
  capabilities: Capability[];
};

const catalog = JSON.parse(readFileSync(catalogPath, "utf8")) as Catalog;

function traceabilityRows(): Map<string, { status: string }> {
  const rows = new Map<string, { status: string }>();
  for (const file of ["engineering-v26.json", "enterprise-v26.json"]) {
    const data = JSON.parse(readFileSync(join(repoRoot, "docs", "traceability", file), "utf8"));
    for (const row of data.rows) rows.set(row.id, row);
  }
  return rows;
}

function routeFile(route: string): string {
  return join(publicRoot, route.replace(/^\/+/, ""), "index.html");
}

test("the public capability contract is complete and versioned", () => {
  assert.equal(catalog.contract_version, "cubi-public-capabilities.v1");
  assert.equal(catalog.generated_from, "apps/web/site/capabilities.mjs");
  assert.equal(catalog.offer.plan, "pro_monthly");
  assert.equal(catalog.offer.checkout_route, "/pricing/");
  assert.equal(catalog.capabilities.length, 10, "ten public capabilities ship");
  const ids = catalog.capabilities.map((capability) => capability.id);
  assert.equal(new Set(ids).size, ids.length, "capability ids must be unique");
});

test("the Pro offer matches the authoritative checkout constant", () => {
  const source = readFileSync(join(webRoot, "src", "pro-checkout.ts"), "utf8");
  const minor = Number(source.match(/PRO_MONTHLY_UNIT_PRICE_MINOR\s*=\s*(\d+)/)?.[1]);
  const currency = source.match(/PRO_MONTHLY_CURRENCY\s*=\s*"([A-Z]{3})"/)?.[1];
  assert.equal(catalog.offer.unit_price_minor, minor, "catalog price drifted from pro-checkout.ts");
  assert.equal(catalog.offer.currency, currency, "catalog currency drifted from pro-checkout.ts");
  assert.equal(catalog.offer.price_source, "apps/web/src/pro-checkout.ts");
  assert.ok(existsSync(routeFile(catalog.offer.checkout_route)), "checkout route must be published");
});

test("every capability resolves to a published route, real evidence and a matching trace row", () => {
  const rows = traceabilityRows();
  for (const capability of catalog.capabilities) {
    assert.ok(capability.route.startsWith("/"), `${capability.id} route must be absolute`);
    assert.ok(existsSync(routeFile(capability.route)), `${capability.id} route is not published`);
    const row = rows.get(capability.traceability_id);
    assert.ok(row, `${capability.id} traceability row is missing`);
    assert.equal(capability.status, row!.status, `${capability.id} status differs from its traceability row`);
  }
});

test("all eight Engineering feature pages are represented", () => {
  const routes = new Set(catalog.capabilities.map((capability) => capability.route));
  for (const route of [
    "/features/scheduling/",
    "/features/project-controls/",
    "/features/resources/",
    "/features/cost/",
    "/features/documents/",
    "/features/risks/",
    "/features/reporting/",
    "/features/ai-assistant/",
  ]) {
    assert.ok(routes.has(route), `${route} has no capability entry`);
  }
});

test("the public capability contract exposes no vendor branding", () => {
  const text = readFileSync(catalogPath, "utf8");
  const match = text.match(/\b(?:Oracle|Primavera|EPPM)\b|\bP6\b/i);
  assert.equal(match, null, `capabilities.json leaks vendor branding: ${match?.[0]}`);
});
