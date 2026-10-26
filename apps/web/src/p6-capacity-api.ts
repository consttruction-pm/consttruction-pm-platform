import type { ApiTransport, ProjectContext } from "./client.js";

export const P6_RESOURCE_CAPACITY_READ_API_VERSION =
  "p6-resource-capacity-read-api.v1";
export const P6_RESOURCE_CAPACITY_WRITE_API_VERSION =
  "p6-resource-capacity-write-api.v1";

export const CAPACITY_BASES = ["hour", "day", "week", "month", "year"] as const;
export type CapacityBasis = (typeof CAPACITY_BASES)[number];

export type CapacitySegment = {
  resource_id: string;
  identity: string;
  max_units: string;
  unit_basis: CapacityBasis;
  hours_per_time_period: string;
  units_per_hour: string;
  effective_from: string;
  effective_to: string | null;
  source: string;
};

export type CapacitySuperseded = {
  identity: string;
  replacement_identity: string;
  effective_to: string | null;
};

export type CapacityWriteResult = {
  contract_version: typeof P6_RESOURCE_CAPACITY_WRITE_API_VERSION;
  kind: "resource_capacity_write";
  scope: ProjectContext;
  capacity: CapacitySegment;
  superseded: CapacitySuperseded | null;
  status: "REGISTERED";
};

export type CapacityResolution = {
  contract_version: typeof P6_RESOURCE_CAPACITY_READ_API_VERSION;
  kind: "resource_capacity_value";
  scope: ProjectContext;
  resource_id: string;
  period: string;
  capacity: string;
  basis: CapacityBasis | null;
  source: string;
  identity: string;
  status: "RESOLVED";
};

export type CapacityWriteInput = {
  resource_id: string;
  max_units: string;
  unit_basis: CapacityBasis;
  hours_per_time_period: string;
  effective_from: string;
  effective_to: string | null;
  close_open_segment: boolean;
};

export type CapacityResolveInput = {
  resource_id: string;
  period: string;
  basis: CapacityBasis | null;
  hours_per_time_period: string | null;
};

export class CapacityClientError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "CapacityClientError";
  }
}

function invalid(code: string): never {
  throw new CapacityClientError(code);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireRecord(value: unknown, code: string): Record<string, unknown> {
  if (!isRecord(value)) invalid(code);
  return value;
}

function requireText(value: unknown, code: string): string {
  if (typeof value !== "string" || value.trim() === "") invalid(code);
  return value;
}

function requireDecimalText(value: unknown, code: string): string {
  if (typeof value === "string" && value.trim() !== "") return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return invalid(code);
}

function requireIsoDate(value: unknown, code: string): string {
  const text = requireText(value, code);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) invalid(code);
  return text;
}

function requireBasis(value: unknown, code: string): CapacityBasis {
  if (
    typeof value !== "string" ||
    !(CAPACITY_BASES as readonly string[]).includes(value)
  ) {
    invalid(code);
  }
  return value as CapacityBasis;
}

function requireScope(value: unknown, context: ProjectContext): void {
  const scope = requireRecord(value, "INVALID_CAPACITY_RESPONSE_SCOPE");
  if (
    scope.tenant_id !== context.tenant_id ||
    scope.project_id !== context.project_id ||
    Number(scope.project_revision) !== context.revision
  ) {
    invalid("CAPACITY_RESPONSE_SCOPE_MISMATCH");
  }
}

function projectSegment(value: unknown): CapacitySegment {
  const capacity = requireRecord(value, "INVALID_CAPACITY_SEGMENT");
  return {
    resource_id: requireText(capacity.resource_id, "INVALID_CAPACITY_RESOURCE_ID"),
    identity: requireText(capacity.identity, "INVALID_CAPACITY_IDENTITY"),
    max_units: requireDecimalText(capacity.max_units, "INVALID_CAPACITY_MAX_UNITS"),
    unit_basis: requireBasis(capacity.unit_basis, "INVALID_CAPACITY_BASIS"),
    hours_per_time_period: requireDecimalText(
      capacity.hours_per_time_period,
      "INVALID_CAPACITY_HOURS",
    ),
    units_per_hour: requireDecimalText(
      capacity.units_per_hour,
      "INVALID_CAPACITY_UNITS_PER_HOUR",
    ),
    effective_from: requireIsoDate(
      capacity.effective_from,
      "INVALID_CAPACITY_EFFECTIVE_FROM",
    ),
    effective_to:
      capacity.effective_to === null
        ? null
        : requireIsoDate(capacity.effective_to, "INVALID_CAPACITY_EFFECTIVE_TO"),
    source: requireText(capacity.source, "INVALID_CAPACITY_SOURCE"),
  };
}

function projectList(payload: unknown, context: ProjectContext): CapacitySegment[] {
  const envelope = requireRecord(payload, "INVALID_CAPACITY_LIST");
  if (envelope.contract_version !== P6_RESOURCE_CAPACITY_READ_API_VERSION) {
    invalid("UNSUPPORTED_CAPACITY_CONTRACT");
  }
  if (!Array.isArray(envelope.capacities)) invalid("INVALID_CAPACITY_LIST");
  return envelope.capacities.map((item) => {
    const record = requireRecord(item, "INVALID_CAPACITY_SEGMENT");
    if (
      record.contract_version !== P6_RESOURCE_CAPACITY_READ_API_VERSION ||
      record.kind !== "resource_capacity_segment"
    ) {
      invalid("UNSUPPORTED_CAPACITY_CONTRACT");
    }
    requireScope(record.scope, context);
    return projectSegment(record.capacity);
  });
}

function projectProfile(
  payload: unknown,
  resourceId: string,
  context: ProjectContext,
): CapacitySegment[] {
  const envelope = requireRecord(payload, "INVALID_CAPACITY_PROFILE");
  if (
    envelope.contract_version !== P6_RESOURCE_CAPACITY_READ_API_VERSION ||
    envelope.kind !== "resource_capacity_profile"
  ) {
    invalid("UNSUPPORTED_CAPACITY_CONTRACT");
  }
  if (envelope.status !== "REGISTERED") invalid("INVALID_CAPACITY_PROFILE_STATUS");
  requireScope(envelope.scope, context);
  if (envelope.resource_id !== resourceId) invalid("CAPACITY_RESOURCE_MISMATCH");
  if (!Array.isArray(envelope.segments)) invalid("INVALID_CAPACITY_PROFILE");
  return envelope.segments.map((segment) => projectSegment(segment));
}

function projectSuperseded(value: unknown): CapacitySuperseded | null {
  if (value === null) return null;
  const superseded = requireRecord(value, "INVALID_CAPACITY_SUPERSESSION");
  return {
    identity: requireText(
      superseded.identity,
      "INVALID_CAPACITY_SUPERSESSION",
    ),
    replacement_identity: requireText(
      superseded.replacement_identity,
      "INVALID_CAPACITY_SUPERSESSION",
    ),
    effective_to:
      superseded.effective_to === null
        ? null
        : requireIsoDate(
            superseded.effective_to,
            "INVALID_CAPACITY_SUPERSESSION",
          ),
  };
}

function projectWrite(
  payload: unknown,
  input: CapacityWriteInput,
  context: ProjectContext,
): CapacityWriteResult {
  const envelope = requireRecord(payload, "INVALID_CAPACITY_WRITE");
  if (
    envelope.contract_version !== P6_RESOURCE_CAPACITY_WRITE_API_VERSION ||
    envelope.kind !== "resource_capacity_write"
  ) {
    invalid("UNSUPPORTED_CAPACITY_CONTRACT");
  }
  if (envelope.status !== "REGISTERED") invalid("INVALID_CAPACITY_WRITE_STATUS");
  requireScope(envelope.scope, context);
  const capacity = projectSegment(envelope.capacity);
  if (capacity.resource_id !== input.resource_id) {
    invalid("CAPACITY_RESOURCE_MISMATCH");
  }
  return {
    contract_version: P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
    kind: "resource_capacity_write",
    scope: context,
    capacity,
    superseded: projectSuperseded(envelope.superseded),
    status: "REGISTERED",
  };
}

function projectResolution(
  payload: unknown,
  input: CapacityResolveInput,
  context: ProjectContext,
): CapacityResolution {
  const envelope = requireRecord(payload, "INVALID_CAPACITY_RESOLUTION");
  if (
    envelope.contract_version !== P6_RESOURCE_CAPACITY_READ_API_VERSION ||
    envelope.kind !== "resource_capacity_value"
  ) {
    invalid("UNSUPPORTED_CAPACITY_CONTRACT");
  }
  if (envelope.status !== "RESOLVED") invalid("INVALID_CAPACITY_RESOLUTION_STATUS");
  requireScope(envelope.scope, context);
  if (envelope.resource_id !== input.resource_id) {
    invalid("CAPACITY_RESOURCE_MISMATCH");
  }
  if (envelope.period !== input.period) invalid("CAPACITY_PERIOD_MISMATCH");
  const basis =
    envelope.basis === null
      ? null
      : requireBasis(envelope.basis, "INVALID_CAPACITY_BASIS");
  if (basis !== input.basis) invalid("CAPACITY_BASIS_MISMATCH");
  return {
    contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
    kind: "resource_capacity_value",
    scope: context,
    resource_id: input.resource_id,
    period: input.period,
    capacity: requireDecimalText(
      envelope.capacity,
      "INVALID_CAPACITY_VALUE",
    ),
    basis,
    source: requireText(envelope.source, "INVALID_CAPACITY_SOURCE"),
    identity: requireText(envelope.identity, "INVALID_CAPACITY_IDENTITY"),
    status: "RESOLVED",
  };
}

function validateWriteInput(input: CapacityWriteInput): CapacityWriteInput {
  if (!input.resource_id.trim()) invalid("INVALID_RESOURCE_ID");
  if (!input.max_units.trim()) invalid("INVALID_MAX_UNITS");
  if (!input.hours_per_time_period.trim()) {
    invalid("INVALID_HOURS_PER_TIME_PERIOD");
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.effective_from)) {
    invalid("INVALID_EFFECTIVE_FROM");
  }
  if (
    input.effective_to !== null &&
    !/^\d{4}-\d{2}-\d{2}$/.test(input.effective_to)
  ) {
    invalid("INVALID_EFFECTIVE_TO");
  }
  if (
    input.effective_to !== null &&
    input.effective_to < input.effective_from
  ) {
    invalid("INVALID_EFFECTIVE_INTERVAL");
  }
  if (!(CAPACITY_BASES as readonly string[]).includes(input.unit_basis)) {
    invalid("INVALID_CAPACITY_BASIS");
  }
  return input;
}

function validateResolveInput(input: CapacityResolveInput): CapacityResolveInput {
  if (!input.resource_id.trim()) invalid("INVALID_RESOURCE_ID");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.period)) invalid("INVALID_PERIOD");
  if ((input.basis === null) !== (input.hours_per_time_period === null)) {
    invalid("CAPACITY_CONVERSION_INCOMPLETE");
  }
  if (input.basis !== null) {
    requireBasis(input.basis, "INVALID_CAPACITY_BASIS");
    requireDecimalText(
      input.hours_per_time_period,
      "INVALID_HOURS_PER_TIME_PERIOD",
    );
  }
  return input;
}

export type P6CapacityClient = {
  listSegments(): Promise<readonly CapacitySegment[]>;
  getProfile(resourceId: string): Promise<readonly CapacitySegment[]>;
  saveEffectiveChange(input: CapacityWriteInput): Promise<CapacityWriteResult>;
  resolveCapacity(input: CapacityResolveInput): Promise<CapacityResolution>;
};

export function createP6CapacityClient(
  transport: ApiTransport,
  context: ProjectContext,
): P6CapacityClient {
  const path = `/api/projects/${encodeURIComponent(
    context.project_id,
  )}/p6/resource-capacities`;

  return {
    async listSegments() {
      const response = await transport.get<unknown>(path, context);
      if (!response.ok) {
        invalid(response.error.code || "CAPACITY_LIST_FAILED");
      }
      return projectList(response.data, context);
    },

    async getProfile(resourceId) {
      if (!resourceId.trim()) invalid("INVALID_RESOURCE_ID");
      const response = await transport.get<unknown>(
        `${path}/${encodeURIComponent(resourceId)}`,
        context,
      );
      if (!response.ok) {
        invalid(response.error.code || "CAPACITY_PROFILE_FAILED");
      }
      return projectProfile(response.data, resourceId, context);
    },

    async saveEffectiveChange(input) {
      const validated = validateWriteInput(input);
      const request = {
        contract_version: P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
        expected_revision: context.revision,
        resource_id: validated.resource_id,
        max_units: validated.max_units,
        unit_basis: validated.unit_basis,
        hours_per_time_period: validated.hours_per_time_period,
        effective_from: validated.effective_from,
        effective_to: validated.effective_to,
        close_open_segment: validated.close_open_segment,
      };
      const response = await transport.post<
        typeof request,
        unknown
      >(path, request, context);
      if (!response.ok) {
        invalid(response.error.code || "CAPACITY_WRITE_FAILED");
      }
      return projectWrite(response.data, validated, context);
    },

    async resolveCapacity(input) {
      const validated = validateResolveInput(input);
      const request = {
        contract_version: P6_RESOURCE_CAPACITY_READ_API_VERSION,
        period: validated.period,
        basis: validated.basis,
        hours_per_time_period: validated.hours_per_time_period,
      };
      const response = await transport.post<
        typeof request,
        unknown
      >(
        `${path}/${encodeURIComponent(validated.resource_id)}/resolve`,
        request,
        context,
      );
      if (!response.ok) {
        invalid(response.error.code || "CAPACITY_RESOLVE_FAILED");
      }
      return projectResolution(response.data, validated, context);
    },
  };
}
