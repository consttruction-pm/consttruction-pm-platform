import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  RESOURCE_DICTIONARY_API_VERSION,
  buildResourceChoices,
  loadResourceDictionary,
  type ResourceDictionaryEntry,
} from "./resource-dictionary.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

function envelope(resource: Record<string, unknown>) {
  return {
    contract_version: RESOURCE_DICTIONARY_API_VERSION,
    kind: "p6_resource",
    scope: { tenant_id: "t1", project_id: "project-1" },
    resource,
  };
}

function transportWith(result: ApiResult<unknown>, calls: { gets: string[] } = { gets: [] }): ApiTransport {
  return {
    async get(path) {
      calls.gets.push(path);
      return result as ApiResult<never>;
    },
    async post() {
      throw new Error("resource dictionary is read-only");
    },
  };
}

const CREW = envelope({
  resource_id: "R-CREW",
  name: "Civil Crew",
  resource_type: "labor",
  is_active: true,
  record_revision: 2,
});

test("resource dictionary reads the project-scoped master list and keeps stored fields", async () => {
  const calls = { gets: [] as string[] };
  const result = await loadResourceDictionary(
    transportWith({
      ok: true,
      data: {
        contract_version: RESOURCE_DICTIONARY_API_VERSION,
        resources: [CREW, envelope({ resource_id: "R-MAT", name: "Concrete", resource_type: "material", is_active: false, record_revision: 1 })],
      },
    }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [
    { resourceId: "R-CREW", name: "Civil Crew", resourceType: "labor", isActive: true },
    { resourceId: "R-MAT", name: "Concrete", resourceType: "material", isActive: false },
  ]);
  assert.deepEqual(calls.gets, ["/api/projects/project-1/p6/resources"]);
});

test("resource dictionary fails closed on a foreign contract or malformed master", async () => {
  const foreign = await loadResourceDictionary(
    transportWith({ ok: true, data: { contract_version: "other", resources: [CREW] } }),
    CONTEXT,
  );
  assert.equal(foreign.ok, false);
  if (!foreign.ok) assert.equal(foreign.error.code, "INVALID_RESOURCE_LIST");

  const badType = await loadResourceDictionary(
    transportWith({
      ok: true,
      data: {
        contract_version: RESOURCE_DICTIONARY_API_VERSION,
        resources: [envelope({ resource_id: "R1", name: "Bad", resource_type: "machine", is_active: true })],
      },
    }),
    CONTEXT,
  );
  assert.equal(badType.ok, false);
  if (!badType.ok) assert.equal(badType.error.code, "INVALID_RESOURCE_RECORD");

  const missingName = await loadResourceDictionary(
    transportWith({
      ok: true,
      data: {
        contract_version: RESOURCE_DICTIONARY_API_VERSION,
        resources: [envelope({ resource_id: "R1", name: "  ", resource_type: "labor", is_active: true })],
      },
    }),
    CONTEXT,
  );
  assert.equal(missingName.ok, false);
  if (!missingName.ok) assert.equal(missingName.error.code, "INVALID_RESOURCE_RECORD");
});

test("resource choices offer only active records but preserve the current reference", () => {
  const entries: ResourceDictionaryEntry[] = [
    { resourceId: "R-CREW", name: "Civil Crew", resourceType: "labor", isActive: true },
    { resourceId: "R-ELEC", name: "Electrical Crew", resourceType: "labor", isActive: true },
    { resourceId: "R-MAT", name: "Concrete", resourceType: "material", isActive: false },
  ];
  // Inactive entries are hidden when they are not the current reference.
  assert.deepEqual(
    buildResourceChoices(entries, "").map((choice) => choice.resourceId),
    ["R-CREW", "R-ELEC"],
  );
  // The current inactive reference stays visible so revise does not drop it.
  const withInactive = buildResourceChoices(entries, "R-MAT");
  assert.deepEqual(withInactive.map((choice) => [choice.resourceId, choice.isActive]), [
    ["R-CREW", true],
    ["R-MAT", false],
    ["R-ELEC", true],
  ]);
  // A reference that is absent from the dictionary is still preserved once.
  assert.deepEqual(
    buildResourceChoices(entries, "R-LEGACY").map((choice) => [choice.resourceId, choice.isActive]),
    [["R-CREW", true], ["R-ELEC", true], ["R-LEGACY", false]],
  );
});