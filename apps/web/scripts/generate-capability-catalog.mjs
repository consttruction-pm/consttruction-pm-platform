#!/usr/bin/env node
// Generates the public capability contract served as `/capabilities.json`.
//
// The catalog is only accepted when every entry resolves to a published route,
// real repository evidence and a matching traceability row. The Pro offer price
// is read from the authoritative checkout constant so the public page and the
// payment flow cannot drift.
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { CAPABILITIES, CONTRACT_VERSION, PUBLIC_OFFER } from "../site/capabilities.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..", "..");
const webRoot = join(repoRoot, "apps", "web");
const publicRoot = join(webRoot, "public");

function fail(message) {
  throw new Error(`CAPABILITY_CATALOG_INVALID: ${message}`);
}

function readJson(relative) {
  return JSON.parse(readFileSync(join(repoRoot, relative), "utf8"));
}

const traceability = new Map();
for (const file of ["engineering-v26.json", "enterprise-v26.json"]) {
  for (const row of readJson(`docs/traceability/${file}`).rows) {
    traceability.set(row.id, row);
  }
}

function routeFile(route) {
  return route === "" ? join(webRoot, "index.html") : join(publicRoot, route, "index.html");
}

function readAuthoritativePrice() {
  const source = readFileSync(join(repoRoot, PUBLIC_OFFER.priceSource), "utf8");
  const minor = source.match(/PRO_MONTHLY_UNIT_PRICE_MINOR\s*=\s*(\d+)/);
  const currency = source.match(/PRO_MONTHLY_CURRENCY\s*=\s*"([A-Z]{3})"/);
  if (!minor || !currency) fail(`cannot read the Pro price from ${PUBLIC_OFFER.priceSource}`);
  return { unitPriceMinor: Number(minor[1]), currency: currency[1] };
}

const price = readAuthoritativePrice();
if (price.unitPriceMinor !== PUBLIC_OFFER.unitPriceMinor) {
  fail(
    `PUBLIC_OFFER price ${PUBLIC_OFFER.unitPriceMinor} drifted from ${PUBLIC_OFFER.priceSource} (${price.unitPriceMinor})`,
  );
}
if (price.currency !== PUBLIC_OFFER.currency) {
  fail(`PUBLIC_OFFER currency ${PUBLIC_OFFER.currency} drifted from ${PUBLIC_OFFER.priceSource} (${price.currency})`);
}
if (!existsSync(routeFile(PUBLIC_OFFER.checkoutRoute))) {
  fail(`checkout route ${PUBLIC_OFFER.checkoutRoute} is not published`);
}

const seen = new Set();
const capabilities = CAPABILITIES.map((capability) => {
  if (seen.has(capability.id)) fail(`duplicate capability id ${capability.id}`);
  seen.add(capability.id);
  if (!existsSync(routeFile(capability.route))) fail(`route ${capability.route} is not published`);
  for (const evidence of capability.evidence) {
    if (!existsSync(join(repoRoot, evidence))) fail(`evidence ${evidence} is missing for ${capability.id}`);
  }
  const row = traceability.get(capability.traceabilityId);
  if (!row) fail(`traceability row ${capability.traceabilityId} is missing for ${capability.id}`);
  if (row.status !== capability.status) {
    fail(
      `capability ${capability.id} says ${capability.status} but ${capability.traceabilityId} says ${row.status}`,
    );
  }
  return {
    id: capability.id,
    environment: capability.environment,
    route: `/${capability.route}`,
    status: capability.status,
    traceability_id: capability.traceabilityId,
    ...(capability.routeNote ? { route_note: capability.routeNote } : {}),
  };
});

const payload = {
  contract_version: CONTRACT_VERSION,
  generated_from: "apps/web/site/capabilities.mjs",
  offer: {
    plan: PUBLIC_OFFER.plan,
    currency: price.currency,
    unit_price_minor: price.unitPriceMinor,
    price_source: PUBLIC_OFFER.priceSource,
    checkout_route: `/${PUBLIC_OFFER.checkoutRoute}`,
  },
  capabilities,
};

writeFileSync(join(publicRoot, "capabilities.json"), `${JSON.stringify(payload, null, 2)}\n`);
console.log(`wrote public/capabilities.json (${capabilities.length} capabilities)`);
