export {
  SCHEDULING_CONTRACT_ID,
  SCHEDULING_CONTRACT_VERSION,
  createSharedSchedulingCoreAdapter,
  validateSchedulingRequest,
  validateSchedulingResult,
} from "../../client-sync/src/scheduling-adapter.ts";

export type {
  ProjectContext as MobileProjectContext,
  CalendarReference as SchedulingCalendarReference,
  TimeQuantity as SchedulingDuration,
  CalculationContext,
  SchedulingActivity,
  SchedulingRelationship,
  SchedulingConstraint,
  SchedulingRequest as MobileSchedulingRequest,
  ScheduledActivity as MobileScheduledActivity,
  SchedulingResult as MobileSchedulingResult,
  SharedSchedulingCoreAdapter,
} from "../../client-sync/src/scheduling-adapter.ts";

/** @deprecated Use SCHEDULING_CONTRACT_VERSION from the canonical shared adapter. */
export const MOBILE_SCHEDULING_CONTRACT_VERSION = "1.0" as const;

export const validateMobileSchedulingResult = validateSchedulingResult;
