import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  CapacityClientError,
  createP6CapacityClient,
  P6_RESOURCE_CAPACITY_READ_API_VERSION,
  P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
} from "./p6-capacity-api.js";

const CONTEXT: ProjectContext = {
  tenant_id: "t1",
  project_id: "preview-rps-01",
  revision: 7,
};

type GetCall = { path: string; context: ProjectContext };
type PostCall = { path: string; request: unknown; context: ProjectContext };

function transportWith(
  options: {
    getResult?: ApiResult<unknown>;
    postResult?: ApiResult<unknown>;
    gets?: GetCall[];
    posts?: PostCall[];
  } = {},
): ApiTransport {
  return {
    async get(path, context) {
      options.gets?.push({ path, context });
      return (options.getResult ?? { ok: false, error: {
        code: "GET_NOT_STUBBED",
        retryable: false,
        message_key: "error.test",
        available_actions: [],
      } }) as ApiResult<never>;
    },
    async post(path, request, context) {
      options.posts?.push({ path, request, context });
      return (options.postResult ?? { ok: false, error: {
        code: "POST_NOT_STUBBED",
        retryable: false,
        message_key: "error.test",
        available_actions: [],
      } }) as ApiResult<never>;
    },
  };
}

function scope() {
  return {
    tenant_id: "t1",
    project_id: "preview-rps-01",
    project_revision: 7,
  };
}

function segment(overrides: Record<string, unknown> = {}) {
  return {
    resource_id: "RPS-CIVIL-CREW",
    identity: "a".repeat(64),
    max_units: "12",
    unit_basis: "day",
    hours_per_time_period: "8",
    units_per_hour: "1.5",
    effective_from: "2026-10-15",
    effective_to: null,
    source: "manual-entry:preview-planner",
    ...overrides,
  };
}

function listEnvelope(items: unknown[] = [segment()]) {
  return {
    contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
    capacities: items.map((capacity) => ({
      contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
      kind: "resource_capacity_segment",
      scope: scope(),
      capacity,
    })),
  };
}

function writeEnvelope(capacity = segment()) {
  return {
    contract_version: P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
    kind: "resource_capacity_write",
    scope: scope(),
    capacity,
    superseded: {
      identity: "b".repeat(64),
      replacement_identity: "c".repeat(64),
      effective_to: "2026-10-14",
    },
    status: "REGISTERED",
  };
}

test("capacity client lists server segments and preserves exact values", async () => {
  const gets: GetCall[] = [];
  const client = createP6CapacityClient(
    transportWith({ getResult: { ok: true, data: listEnvelope() }, gets }),
    CONTEXT,
  );

  const segments = await client.listSegments();

  assert.deepEqual(gets, [
    {
      path: "/api/projects/preview-rps-01/p6/resource-capacities",
      context: CONTEXT,
    },
  ]);
  assert.deepEqual(segments, [
    {
      resource_id: "RPS-CIVIL-CREW",
      identity: "a".repeat(64),
      max_units: "12",
      unit_basis: "day",
      hours_per_time_period: "8",
      units_per_hour: "1.5",
      effective_from: "2026-10-15",
      effective_to: null,
      source: "manual-entry:preview-planner",
    },
  ]);
});

test("capacity client fails closed on contract, scope and segment validation", async () => {
  const cases: unknown[] = [
    { ...listEnvelope(), contract_version: "p6-resource-capacity-read-api.v2" },
    {
      ...listEnvelope(),
      capacities: [
        {
          contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
          kind: "resource_capacity_segment",
          scope: { ...scope(), tenant_id: "other" },
          capacity: segment(),
        },
      ],
    },
    {
      ...listEnvelope(),
      capacities: [
        {
          contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
          kind: "resource_capacity_segment",
          scope: scope(),
          capacity: segment({ max_units: "" }),
        },
      ],
    },
    {
      ...listEnvelope(),
      capacities: [
        {
          contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
          kind: "resource_capacity_segment",
          scope: scope(),
          capacity: segment({ effective_from: "15/10/2026" }),
        },
      ],
    },
  ];

  for (const data of cases) {
    const client = createP6CapacityClient(
      transportWith({ getResult: { ok: true, data } }),
      CONTEXT,
    );
    await assert.rejects(
      () => client.listSegments(),
      (error: unknown) => error instanceof CapacityClientError,
    );
  }
});

test("capacity write posts the revision lock and never supplies identity or source", async () => {
  const posts: PostCall[] = [];
  const client = createP6CapacityClient(
    transportWith({ postResult: { ok: true, data: writeEnvelope() }, posts }),
    CONTEXT,
  );

  const result = await client.saveEffectiveChange({
    resource_id: "RPS-CIVIL-CREW",
    max_units: "10",
    unit_basis: "day",
    hours_per_time_period: "8",
    effective_from: "2026-11-01",
    effective_to: null,
    close_open_segment: true,
  });

  assert.equal(posts.length, 1);
  assert.equal(
    posts[0].path,
    "/api/projects/preview-rps-01/p6/resource-capacities",
  );
  assert.deepEqual(posts[0].request, {
    contract_version: P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
    expected_revision: 7,
    resource_id: "RPS-CIVIL-CREW",
    max_units: "10",
    unit_basis: "day",
    hours_per_time_period: "8",
    effective_from: "2026-11-01",
    effective_to: null,
    close_open_segment: true,
  });
  const request = posts[0].request as Record<string, unknown>;
  assert.equal("identity" in request, false);
  assert.equal("source" in request, false);
  assert.equal(result.capacity.identity, "a".repeat(64));
  assert.equal(result.superseded?.effective_to, "2026-10-14");
  assert.equal(result.status, "REGISTERED");
});

test("capacity resolution sends the basis request and uses the server value", async () => {
  const posts: PostCall[] = [];
  const client = createP6CapacityClient(
    transportWith({
      postResult: {
        ok: true,
        data: {
          contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
          kind: "resource_capacity_value",
          scope: scope(),
          resource_id: "RPS-CIVIL-CREW",
          period: "2026-11-02",
          capacity: "50",
          basis: "week",
          source: "manual-entry:preview-planner",
          identity: "a".repeat(64),
          status: "RESOLVED",
        },
      },
      posts,
    }),
    CONTEXT,
  );

  const result = await client.resolveCapacity({
    resource_id: "RPS-CIVIL-CREW",
    period: "2026-11-02",
    basis: "week",
    hours_per_time_period: "40",
  });

  assert.equal(
    posts[0].path,
    "/api/projects/preview-rps-01/p6/resource-capacities/RPS-CIVIL-CREW/resolve",
  );
  assert.deepEqual(posts[0].request, {
    contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
    period: "2026-11-02",
    basis: "week",
    hours_per_time_period: "40",
  });
  assert.equal(result.capacity, "50");
  assert.equal(result.basis, "week");
});

test("capacity client rejects incomplete conversion and mismatched responses", async () => {
  const client = createP6CapacityClient(
    transportWith(),
    CONTEXT,
  );
  await assert.rejects(
    () =>
      client.resolveCapacity({
        resource_id: "RPS-CIVIL-CREW",
        period: "2026-11-02",
        basis: "week",
        hours_per_time_period: null,
      }),
    (error: unknown) =>
      error instanceof CapacityClientError &&
      error.message === "CAPACITY_CONVERSION_INCOMPLETE",
  );

  const mismatched = createP6CapacityClient(
    transportWith({
      postResult: {
        ok: true,
        data: {
          contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
          kind: "resource_capacity_value",
          scope: scope(),
          resource_id: "OTHER",
          period: "2026-11-02",
          capacity: "50",
          basis: "week",
          source: "manual-entry:preview-planner",
          identity: "a".repeat(64),
          status: "RESOLVED",
        },
      },
    }),
    CONTEXT,
  );
  await assert.rejects(
    () =>
      mismatched.resolveCapacity({
        resource_id: "RPS-CIVIL-CREW",
        period: "2026-11-02",
        basis: "week",
        hours_per_time_period: "40",
      }),
    (error: unknown) =>
      error instanceof CapacityClientError &&
      error.message === "CAPACITY_RESOURCE_MISMATCH",
  );
});

test("capacity client surfaces the server authorization code unchanged", async () => {
  const client = createP6CapacityClient(
    transportWith({
      postResult: {
        ok: false,
        error: {
          code: "authorization denied for permission=project.write",
          retryable: false,
          message_key: "error.authorization.denied",
          available_actions: [],
        },
      },
    }),
    CONTEXT,
  );

  await assert.rejects(
    () =>
      client.saveEffectiveChange({
        resource_id: "RPS-CIVIL-CREW",
        max_units: "10",
        unit_basis: "day",
        hours_per_time_period: "8",
        effective_from: "2026-11-01",
        effective_to: null,
        close_open_segment: true,
      }),
    (error: unknown) =>
      error instanceof CapacityClientError &&
      error.message.includes("project.write"),
  );
});
