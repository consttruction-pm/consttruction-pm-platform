export const MOBILE_SCHEDULING_CONTRACT_VERSION = "time-scheduling-portability.v1" as const;

export type SchedulingDuration = Readonly<{
  value: string;
  unit: "WORKING_DAY" | "WORKING_HOUR";
}>;

export type SchedulingCalendarReference = Readonly<{
  calendar_id: string;
  calendar_version: number;
  kind: "working-day" | "working-time";
}>;

export type MobileSchedulingRequest = Readonly<{
  contract_version: typeof MOBILE_SCHEDULING_CONTRACT_VERSION;
  project_schema_version: number;
  tenant_id: string;
  project_id: string;
  project_revision: number;
  calculation_schema_version: string;
  calendar_assignments: Readonly<Record<string, SchedulingCalendarReference>>;
  scheduling_settings: Readonly<Record<string, string | number | boolean | null>>;
  project_start: string | null;
  project_finish: string | null;
  data_date: string | null;
  activities: readonly Readonly<{
    id: string;
    duration: SchedulingDuration;
  }>[];
  relationships: readonly Readonly<{
    predecessor_id: string;
    successor_id: string;
    type: "FS" | "SS" | "FF" | "SF";
    lag: SchedulingDuration;
  }>[];
  constraints: readonly Readonly<{
    activity_id: string;
    type:
      | "START_NO_EARLIER_THAN"
      | "START_NO_LATER_THAN"
      | "FINISH_NO_EARLIER_THAN"
      | "FINISH_NO_LATER_THAN"
      | "MANDATORY_START"
      | "MANDATORY_FINISH";
    target: string;
  }>[];
}>;

export type MobileScheduledActivity = Readonly<{
  activity_id: string;
  start: string;
  finish: string;
  duration: SchedulingDuration;
  total_float: SchedulingDuration | null;
  free_float: SchedulingDuration | null;
  critical: boolean;
}>;

export type MobileSchedulingResult = Readonly<{
  contract_version: typeof MOBILE_SCHEDULING_CONTRACT_VERSION;
  calculation_fingerprint: string;
  project_finish: string;
  activities: readonly MobileScheduledActivity[];
}>;

/**
 * Injection boundary for the authoritative Shared Scheduling Core.
 *
 * This interface deliberately contains no scheduling formulas. Mobile only
 * supplies the portable calculation context and consumes authoritative results.
 */
export interface SharedSchedulingCoreAdapter {
  schedule(input: MobileSchedulingRequest): Promise<MobileSchedulingResult>;
}

export function createSharedSchedulingCoreAdapter(
  core: SharedSchedulingCoreAdapter,
): SharedSchedulingCoreAdapter {
  return Object.freeze(core);
}

export function validateMobileSchedulingResult(
  result: MobileSchedulingResult,
): MobileSchedulingResult {
  if (result.contract_version !== MOBILE_SCHEDULING_CONTRACT_VERSION) {
    throw new Error("INVALID_SCHEDULING_CONTRACT_VERSION");
  }
  if (!result.calculation_fingerprint.trim()) {
    throw new Error("MISSING_SCHEDULING_FINGERPRINT");
  }
  if (!result.project_finish.trim()) {
    throw new Error("MISSING_SCHEDULING_PROJECT_FINISH");
  }
  for (const activity of result.activities) {
    if (!activity.activity_id.trim() || !activity.start.trim() || !activity.finish.trim()) {
      throw new Error("INVALID_SCHEDULING_ACTIVITY_RESULT");
    }
    if (!activity.duration.value.trim()) {
      throw new Error("INVALID_SCHEDULING_ACTIVITY_DURATION");
    }
    if (activity.total_float && !activity.total_float.value.trim()) {
      throw new Error("INVALID_SCHEDULING_TOTAL_FLOAT");
    }
    if (activity.free_float && !activity.free_float.value.trim()) {
      throw new Error("INVALID_SCHEDULING_FREE_FLOAT");
    }
  }
  return result;
}
