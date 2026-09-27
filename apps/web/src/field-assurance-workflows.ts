import type {
  InspectionStatus,
  QualityStatus,
  SafetyStatus,
  PunchStatus,
} from "./workspace-field-assurance.js";

export type FieldAssuranceResource = "inspection" | "quality_record" | "safety_observation" | "punch_item";

export type FieldAssuranceTransition =
  | { resource: "inspection"; from: InspectionStatus; to: InspectionStatus }
  | { resource: "quality_record"; from: QualityStatus; to: QualityStatus }
  | { resource: "safety_observation"; from: SafetyStatus; to: SafetyStatus }
  | { resource: "punch_item"; from: PunchStatus; to: PunchStatus };

const inspectionTransitions: Record<InspectionStatus, readonly InspectionStatus[]> = {
  draft: ["scheduled", "in_progress", "cancelled"],
  scheduled: ["in_progress", "cancelled"],
  in_progress: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

const qualityTransitions: Record<QualityStatus, readonly QualityStatus[]> = {
  open: ["in_progress", "cancelled"],
  in_progress: ["pending_verification", "rejected", "cancelled"],
  pending_verification: ["accepted", "rejected"],
  accepted: ["closed"],
  rejected: ["open", "in_progress", "cancelled"],
  closed: [],
  cancelled: [],
};

const safetyTransitions: Record<SafetyStatus, readonly SafetyStatus[]> = {
  open: ["in_progress", "resolved", "cancelled"],
  in_progress: ["resolved", "cancelled"],
  resolved: ["closed"],
  closed: [],
  cancelled: [],
};

const punchTransitions: Record<PunchStatus, readonly PunchStatus[]> = {
  open: ["in_progress", "cancelled"],
  in_progress: ["ready_for_verification", "cancelled"],
  ready_for_verification: ["closed", "rejected"],
  rejected: ["in_progress", "cancelled"],
  closed: [],
  cancelled: [],
};

export function canTransition(transition: FieldAssuranceTransition): boolean {
  return allowedTargets(transition.resource, transition.from).includes(transition.to);
}

export function assertTransition(transition: FieldAssuranceTransition): void {
  if (!canTransition(transition)) {
    throw new Error(
      `INVALID_${transition.resource.toUpperCase()}_TRANSITION:${transition.from}->${transition.to}`,
    );
  }
}

export function allowedTargets(
  resource: "inspection",
  status: InspectionStatus,
): readonly InspectionStatus[];
export function allowedTargets(
  resource: "quality_record",
  status: QualityStatus,
): readonly QualityStatus[];
export function allowedTargets(
  resource: "safety_observation",
  status: SafetyStatus,
): readonly SafetyStatus[];
export function allowedTargets(
  resource: "punch_item",
  status: PunchStatus,
): readonly PunchStatus[];
export function allowedTargets(
  resource: FieldAssuranceResource,
  status: InspectionStatus | QualityStatus | SafetyStatus | PunchStatus,
): readonly (InspectionStatus | QualityStatus | SafetyStatus | PunchStatus)[] {
  switch (resource) {
    case "inspection":
      return inspectionTransitions[status as InspectionStatus] ?? [];
    case "quality_record":
      return qualityTransitions[status as QualityStatus] ?? [];
    case "safety_observation":
      return safetyTransitions[status as SafetyStatus] ?? [];
    case "punch_item":
      return punchTransitions[status as PunchStatus] ?? [];
  }
}
