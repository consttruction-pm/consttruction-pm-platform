import type { AssignmentPeriod, AssignmentRecord } from "./workspace-assignments.js";
import { addDecimalText, compareDecimalText } from "./workspace-assignments.js";

/**
 * Resource usage is a read-only comparison of stored facts:
 *
 * - demand rate: each assignment's stored Units/Time with its stored time
 *   basis and hours-per-period;
 * - availability: the project service resolves the effective-dated Max Units
 *   for the period start, converted to that same basis and hours definition.
 *
 * Nothing here spreads activities, runs a scheduler or leveling pass, or
 * invents a capacity when a resource has no stored segment. Units/Time values
 * in different time bases are never combined.
 */

export const RESOURCE_RATE_BASES = ["hour", "day", "week", "month", "year"] as const;

export type ResourceRateBasis = (typeof RESOURCE_RATE_BASES)[number];

export type AssignmentRate = {
  assignmentId: string;
  unitsPerTime: string;
  basis: ResourceRateBasis;
  hoursPerTimePeriod: string;
};

export type CapacityResolution = {
  status: "resolved" | "not-registered" | "conflict" | "error";
  capacity: string | null;
  basis: string | null;
  identity: string | null;
  source: string | null;
  errorCode: string | null;
};

export type ResourceUsageGroup = {
  periodStart: string;
  assignmentIds: string[];
  demandUnits: string | null;
  demandCost: string | null;
};

export type ResourceUsageRateSummary =
  | { state: "comparable"; unitsPerTime: string; basis: ResourceRateBasis; hoursPerTimePeriod: string }
  | { state: "missing" }
  | { state: "partial" }
  | { state: "mixed" };

export type ResourceUsageStatus =
  | "overallocated"
  | "within"
  | "missing-rate"
  | "partial-rate"
  | "mixed-basis"
  | "missing-capacity"
  | "capacity-conflict"
  | "capacity-error";

export const RESOURCE_USAGE_TIMESCALES = ["day", "week", "month"] as const;

export type ResourceUsageTimescale = (typeof RESOURCE_USAGE_TIMESCALES)[number];

/**
 * A display bucket that sums stored period values whose start falls inside the
 * bucket. Buckets never spread an amount across days and never invent a width
 * the stored row does not have.
 */
export type ResourceUsageBucket = {
  bucketStart: string;
  bucketEnd: string;
  periodStarts: string[];
  assignmentIds: string[];
  demandUnits: string | null;
  demandCost: string | null;
  overallocatedPeriods: number;
};

export type ResourceUsageEntry = {
  periodStart: string;
  assignmentIds: string[];
  demandUnits: string | null;
  demandCost: string | null;
  unitsPerTime: string | null;
  basis: string | null;
  hoursPerTimePeriod: string | null;
  capacity: string | null;
  excess: string | null;
  capacityIdentity: string | null;
  capacitySource: string | null;
  status: ResourceUsageStatus;
  errorCode: string | null;
};

const DECIMAL = /^-?\d+(\.\d+)?$/;

/** Trim a stored decimal to a canonical form without changing its value. */
export function normalizeDecimalText(value: string): string {
  const trimmed = value.trim();
  const negative = trimmed.startsWith("-");
  const body = negative ? trimmed.slice(1) : trimmed;
  const [whole = "0", fraction = ""] = body.split(".");
  const normalizedWhole = whole.replace(/^0+(?=\d)/, "");
  const normalizedFraction = fraction.replace(/0+$/, "");
  const zero = normalizedWhole === "0" && normalizedFraction === "";
  return `${negative && !zero ? "-" : ""}${normalizedWhole}${normalizedFraction ? `.${normalizedFraction}` : ""}`;
}

/** Resolve cache key for one resource period and demand time definition. */
export function resourceUsageResolveKey(
  periodStart: string,
  basis: string,
  hoursPerTimePeriod: string,
): string {
  return `${periodStart}|${basis.toLowerCase()}|${normalizeDecimalText(hoursPerTimePeriod)}`;
}

export function parseAssignmentRate(record: AssignmentRecord): AssignmentRate | null {
  const units = record.unitsPerTime?.trim() ?? "";
  const basis = record.unitsPerTimePeriod?.trim().toLowerCase() ?? "";
  const hours = record.hoursPerUnitsTimePeriod?.trim() ?? "";
  if (!units || !DECIMAL.test(units)) return null;
  if (!hours || !DECIMAL.test(hours) || compareDecimalText(hours, "0") <= 0) return null;
  if (!(RESOURCE_RATE_BASES as readonly string[]).includes(basis)) return null;
  return {
    assignmentId: record.assignmentId,
    unitsPerTime: units,
    basis: basis as ResourceRateBasis,
    hoursPerTimePeriod: hours,
  };
}

/** Group stored assignment-period values by their period start for one resource. */
export function groupResourceUsagePeriods(
  periods: readonly AssignmentPeriod[],
  resourceId: string,
): ResourceUsageGroup[] {
  const byPeriod = new Map<string, { units: string[]; costs: string[]; assignmentIds: Set<string> }>();
  for (const period of periods) {
    if (period.resourceId !== resourceId) continue;
    const existing = byPeriod.get(period.periodStart) ?? {
      units: [],
      costs: [],
      assignmentIds: new Set<string>(),
    };
    existing.units.push(period.units);
    existing.costs.push(period.cost);
    existing.assignmentIds.add(period.assignmentId);
    byPeriod.set(period.periodStart, existing);
  }
  return [...byPeriod.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([periodStart, value]) => ({
      periodStart,
      assignmentIds: [...value.assignmentIds].sort(),
      demandUnits: addDecimalText(value.units),
      demandCost: addDecimalText(value.costs),
    }));
}

/**
 * Summarize the stored Units/Time of the assignments that have a stored period
 * in this period row. Comparable only when every contributing assignment
 * stores Units/Time and all values share one time basis and hours definition.
 */
export function summarizeResourceUsageRates(
  group: ResourceUsageGroup,
  assignments: ReadonlyMap<string, AssignmentRecord>,
): ResourceUsageRateSummary {
  const rates: AssignmentRate[] = [];
  for (const assignmentId of group.assignmentIds) {
    const record = assignments.get(assignmentId);
    const rate = record ? parseAssignmentRate(record) : null;
    if (rate) rates.push(rate);
  }
  if (!rates.length) return { state: "missing" };
  if (rates.length !== group.assignmentIds.length) return { state: "partial" };
  const basis = rates[0].basis;
  const hours = rates[0].hoursPerTimePeriod;
  if (
    rates.some((rate) => rate.basis !== basis) ||
    rates.some((rate) => compareDecimalText(rate.hoursPerTimePeriod, hours) !== 0)
  ) {
    return { state: "mixed" };
  }
  const unitsPerTime = addDecimalText(rates.map((rate) => rate.unitsPerTime));
  if (unitsPerTime === null) return { state: "missing" };
  return { state: "comparable", unitsPerTime, basis, hoursPerTimePeriod: hours };
}

export function buildResourceUsage(
  groups: readonly ResourceUsageGroup[],
  assignments: ReadonlyMap<string, AssignmentRecord>,
  resolutions: ReadonlyMap<string, CapacityResolution>,
): ResourceUsageEntry[] {
  return groups.map((group) => {
    const summary = summarizeResourceUsageRates(group, assignments);
    const base = {
      periodStart: group.periodStart,
      assignmentIds: group.assignmentIds,
      demandUnits: group.demandUnits,
      demandCost: group.demandCost,
      unitsPerTime: null as string | null,
      basis: null as string | null,
      hoursPerTimePeriod: null as string | null,
      capacity: null as string | null,
      excess: null as string | null,
      capacityIdentity: null as string | null,
      capacitySource: null as string | null,
      errorCode: null as string | null,
    };
    if (summary.state === "missing") {
      return { ...base, status: "missing-rate" as const };
    }
    if (summary.state === "partial") {
      return { ...base, status: "partial-rate" as const };
    }
    if (summary.state === "mixed") {
      return { ...base, status: "mixed-basis" as const };
    }
    const key = resourceUsageResolveKey(group.periodStart, summary.basis, summary.hoursPerTimePeriod);
    const resolution = resolutions.get(key);
    const withRate = {
      ...base,
      unitsPerTime: summary.unitsPerTime,
      basis: summary.basis,
      hoursPerTimePeriod: summary.hoursPerTimePeriod,
    };
    if (!resolution || resolution.status === "error") {
      return {
        ...withRate,
        status: "capacity-error" as const,
        errorCode: resolution?.errorCode ?? "RESOURCE_CAPACITY_RESOLUTION_MISSING",
      };
    }
    if (resolution.status === "not-registered") {
      return { ...withRate, status: "missing-capacity" as const, errorCode: resolution.errorCode };
    }
    if (resolution.status === "conflict") {
      return { ...withRate, status: "capacity-conflict" as const, errorCode: resolution.errorCode };
    }
    const capacity = resolution.capacity;
    if (capacity === null) {
      return { ...withRate, status: "capacity-error" as const, errorCode: "RESOURCE_CAPACITY_RESOLUTION_EMPTY" };
    }
    const excess = addDecimalText([summary.unitsPerTime, `-${capacity}`]);
    const overallocated = compareDecimalText(excess, "0") > 0;
    return {
      ...withRate,
      capacity,
      excess: overallocated ? excess : null,
      capacityIdentity: resolution.identity,
      capacitySource: resolution.source,
      status: overallocated ? ("overallocated" as const) : ("within" as const),
      errorCode: null,
    };
  });
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

function isoDate(value: string): Date | null {
  const match = ISO_DATE.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null;
  }
  return parsed;
}

function isoText(value: Date): string {
  return value.toISOString().slice(0, 10);
}

/** Inclusive first/last day of the bucket that contains a stored period start. */
export function resourceUsageBucketBounds(
  periodStart: string,
  timescale: ResourceUsageTimescale,
): { start: string; end: string } | null {
  const date = isoDate(periodStart);
  if (!date) return null;
  if (timescale === "day") return { start: periodStart, end: periodStart };
  if (timescale === "week") {
    const start = new Date(date);
    start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
    const end = new Date(start);
    end.setUTCDate(end.getUTCDate() + 6);
    return { start: isoText(start), end: isoText(end) };
  }
  const start = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
  const end = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0));
  return { start: isoText(start), end: isoText(end) };
}

/**
 * Sum already-grouped stored periods into display buckets.
 *
 * A period with an unparseable start stays in its own bucket so it is never
 * silently moved into a bucket whose range would be wrong.
 */
export function groupResourceUsageBuckets(
  groups: readonly ResourceUsageGroup[],
  timescale: ResourceUsageTimescale,
  overallocatedStarts: ReadonlySet<string> = new Set(),
): ResourceUsageBucket[] {
  const byBucket = new Map<string, {
    bucketStart: string;
    bucketEnd: string;
    periodStarts: string[];
    assignmentIds: Set<string>;
    units: string[];
    costs: string[];
    overallocated: number;
  }>();
  for (const group of groups) {
    const bounds = resourceUsageBucketBounds(group.periodStart, timescale);
    const bucketStart = bounds?.start ?? group.periodStart;
    const bucketEnd = bounds?.end ?? group.periodStart;
    const key = `${bucketStart}|${bucketEnd}`;
    const existing = byBucket.get(key) ?? {
      bucketStart,
      bucketEnd,
      periodStarts: [],
      assignmentIds: new Set<string>(),
      units: [],
      costs: [],
      overallocated: 0,
    };
    existing.periodStarts.push(group.periodStart);
    for (const assignmentId of group.assignmentIds) existing.assignmentIds.add(assignmentId);
    if (group.demandUnits !== null) existing.units.push(group.demandUnits);
    if (group.demandCost !== null) existing.costs.push(group.demandCost);
    if (overallocatedStarts.has(group.periodStart)) existing.overallocated += 1;
    byBucket.set(key, existing);
  }
  return [...byBucket.values()]
    .sort((left, right) => left.bucketStart.localeCompare(right.bucketStart))
    .map((bucket) => ({
      bucketStart: bucket.bucketStart,
      bucketEnd: bucket.bucketEnd,
      periodStarts: bucket.periodStarts.sort((left, right) => left.localeCompare(right)),
      assignmentIds: [...bucket.assignmentIds].sort(),
      demandUnits: bucket.units.length ? addDecimalText(bucket.units) : null,
      demandCost: bucket.costs.length ? addDecimalText(bucket.costs) : null,
      overallocatedPeriods: bucket.overallocated,
    }));
}
