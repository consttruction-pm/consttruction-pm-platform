export const SCHEDULING_CONTRACT_ID =
  "constructionpm://contracts/time-scheduling/v1" as const;
export const SCHEDULING_CONTRACT_VERSION = "1.0" as const;

export type SchedulingProjectContext = Readonly<{
  tenant_id: string;
  project_id: string;
  revision: number;
}>;

export type CalendarReference = Readonly<{
  calendar_id: string;
  calendar_version: string;
  kind: "working-day" | "working-time";
}>;

export type TimeQuantity = Readonly<{
  value: string;
  unit: "working-hour" | "working-day";
}>;

export type CalculationContext = Readonly<{
  schedule_mode: "EARLIEST" | "ALAP";
  project_start: string;
  project_finish?: string | null;
  data_date?: string | null;
  critical_float_threshold_hours?: string | null;
  time_precision?: "minute" | "second" | "millisecond" | "microsecond";
  rounding_policy?: "exact" | "calendar-boundary";
  project_calendar?: CalendarReference;
  default_activity_calendar?: CalendarReference;
  default_relationship_lag_calendar?: CalendarReference;
  schedule_options?: Readonly<Record<string, boolean | number | string>>;
}>;

export type SchedulingActivity = Readonly<{
  activity_id: string;
  duration_value: string;
  duration_unit: "working-hour" | "working-day";
  calendar: CalendarReference;
  constraint_ids?: readonly string[];
}>;

export type SchedulingRelationship = Readonly<{
  predecessor_id: string;
  successor_id: string;
  type: "FS" | "SS" | "FF" | "SF";
  lag_value: string;
  lag_unit: "working-hour" | "working-day";
  lag_calendar?: CalendarReference;
}>;

export type SchedulingConstraint = Readonly<{
  activity_id: string;
  type:
    | "START_NO_EARLIER_THAN"
    | "START_NO_LATER_THAN"
    | "FINISH_NO_EARLIER_THAN"
    | "FINISH_NO_LATER_THAN"
    | "MANDATORY_START"
    | "MANDATORY_FINISH";
  target: string;
}>;

export type SchedulingRequest = Readonly<{
  contract_version: typeof SCHEDULING_CONTRACT_VERSION;
  project_context: SchedulingProjectContext;
  calculation_context: CalculationContext;
  activities: readonly SchedulingActivity[];
  relationships: readonly SchedulingRelationship[];
  constraints: readonly SchedulingConstraint[];
}>;

export type ScheduledActivity = Readonly<{
  activity_id: string;
  start: string;
  finish: string;
  duration: TimeQuantity;
  total_float?: TimeQuantity | null;
  free_float?: TimeQuantity | null;
  critical: boolean;
}>;

export type SchedulingResult = Readonly<{
  contract_version: typeof SCHEDULING_CONTRACT_VERSION;
  project_context: SchedulingProjectContext;
  calculation_fingerprint: string;
  project_finish: string;
  activities: readonly ScheduledActivity[];
}>;

const DECIMAL = /^[+-]?\\d+(?:\\.\\d+)?$/;

function requireNonEmpty(value: string, code: string): void {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
}

function validateContext(context: SchedulingProjectContext): void {
  requireNonEmpty(context.tenant_id, "INVALID_SCHEDULING_TENANT");
  requireNonEmpty(context.project_id, "INVALID_SCHEDULING_PROJECT");
  if (!Number.isInteger(context.revision) || context.revision < 0) {
    throw new Error("INVALID_SCHEDULING_REVISION");
  }
}

function validateCalendar(calendar: CalendarReference): void {
  requireNonEmpty(calendar.calendar_id, "INVALID_SCHEDULING_CALENDAR_ID");
  requireNonEmpty(calendar.calendar_version, "INVALID_SCHEDULING_CALENDAR_VERSION");
}

function validateQuantity(value: string, code: string): void {
  if (!DECIMAL.test(value)) throw new Error(code);
}

export function validateSchedulingRequest(
  request: SchedulingRequest,
): SchedulingRequest {
  if (request.contract_version !== SCHEDULING_CONTRACT_VERSION) {
    throw new Error("INVALID_SCHEDULING_CONTRACT_VERSION");
  }
  validateContext(request.project_context);
  requireNonEmpty(request.calculation_context.schedule_mode, "INVALID_SCHEDULING_MODE");
  requireNonEmpty(request.calculation_context.project_start, "INVALID_SCHEDULING_PROJECT_START");

  for (const calendar of [
    request.calculation_context.project_calendar,
    request.calculation_context.default_activity_calendar,
    request.calculation_context.default_relationship_lag_calendar,
  ]) {
    if (calendar) validateCalendar(calendar);
  }
  if (request.calculation_context.critical_float_threshold_hours != null) {
    validateQuantity(
      request.calculation_context.critical_float_threshold_hours,
      "INVALID_SCHEDULING_CRITICAL_FLOAT_THRESHOLD",
    );
  }

  for (const activity of request.activities) {
    requireNonEmpty(activity.activity_id, "INVALID_SCHEDULING_ACTIVITY_ID");
    validateQuantity(activity.duration_value, "INVALID_SCHEDULING_DURATION");
    validateCalendar(activity.calendar);
  }

  for (const relationship of request.relationships) {
    requireNonEmpty(relationship.predecessor_id, "INVALID_SCHEDULING_PREDECESSOR");
    requireNonEmpty(relationship.successor_id, "INVALID_SCHEDULING_SUCCESSOR");
    validateQuantity(relationship.lag_value, "INVALID_SCHEDULING_LAG");
    if (relationship.lag_calendar) validateCalendar(relationship.lag_calendar);
  }

  for (const constraint of request.constraints) {
    requireNonEmpty(constraint.activity_id, "INVALID_SCHEDULING_CONSTRAINT_ACTIVITY");
    requireNonEmpty(constraint.target, "INVALID_SCHEDULING_CONSTRAINT_TARGET");
  }
  return request;
}

export function validateSchedulingResult(
  result: SchedulingResult,
  expectedContext?: SchedulingProjectContext,
): SchedulingResult {
  if (result.contract_version !== SCHEDULING_CONTRACT_VERSION) {
    throw new Error("INVALID_SCHEDULING_CONTRACT_VERSION");
  }
  validateContext(result.project_context);
  if (expectedContext && (
    result.project_context.tenant_id !== expectedContext.tenant_id ||
    result.project_context.project_id !== expectedContext.project_id ||
    result.project_context.revision !== expectedContext.revision
  )) {
    throw new Error("SCHEDULING_PROJECT_CONTEXT_MISMATCH");
  }
  requireNonEmpty(result.calculation_fingerprint, "MISSING_SCHEDULING_FINGERPRINT");
  requireNonEmpty(result.project_finish, "MISSING_SCHEDULING_PROJECT_FINISH");
  for (const activity of result.activities) {
    requireNonEmpty(activity.activity_id, "INVALID_SCHEDULING_ACTIVITY_RESULT");
    requireNonEmpty(activity.start, "INVALID_SCHEDULING_ACTIVITY_START");
    requireNonEmpty(activity.finish, "INVALID_SCHEDULING_ACTIVITY_FINISH");
    validateQuantity(activity.duration.value, "INVALID_SCHEDULING_ACTIVITY_DURATION");
    if (activity.total_float) {
      validateQuantity(activity.total_float.value, "INVALID_SCHEDULING_TOTAL_FLOAT");
    }
    if (activity.free_float) {
      validateQuantity(activity.free_float.value, "INVALID_SCHEDULING_FREE_FLOAT");
    }
  }
  return result;
}

/** Thin injection boundary: scheduling semantics stay in Shared Core. */
export interface SharedSchedulingCoreAdapter {
  schedule(input: SchedulingRequest): Promise<SchedulingResult>;
}

export function createSharedSchedulingCoreAdapter(
  core: SharedSchedulingCoreAdapter,
): SharedSchedulingCoreAdapter {
  return Object.freeze(core);
}
