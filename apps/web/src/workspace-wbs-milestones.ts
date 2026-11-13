import type {
  WorkspaceWbsMilestone,
  WorkspaceWbsPercentCompleteTechnique,
  WorkspaceWbsStatus,
} from "./workspace-model.js";

/**
 * Weighted roll-up used by P6 WBS Milestones: completed weight over total
 * weight. The server computes the persisted value; this mirror is used only to
 * preview the same arithmetic while weights or completion change in the editor.
 */
export function weightedPercentComplete(
  milestones: readonly WorkspaceWbsMilestone[],
): number {
  const total = milestones.reduce((sum, item) => sum + item.weight, 0);
  if (!(total > 0)) return 0;
  const done = milestones.reduce(
    (sum, item) => (item.completed ? sum + item.weight : sum),
    0,
  );
  return Math.round((done / total) * 10000) / 100;
}

export function wbsStatusLabel(locale: string, status: WorkspaceWbsStatus | undefined): string {
  if (!status) return "—";
  const labels: Record<WorkspaceWbsStatus, [string, string]> = {
    planned: ["Planned", "برنامه‌ریزی‌شده"],
    active: ["Active", "فعال"],
    inactive: ["Inactive", "غیرفعال"],
    what_if: ["What-If", "فرضی"],
  };
  const [en, fa] = labels[status];
  return locale === "fa" ? fa : en;
}

export function wbsTechniqueLabel(
  locale: string,
  technique: WorkspaceWbsPercentCompleteTechnique | undefined,
): string {
  if (!technique) return "—";
  if (technique === "milestones") {
    return locale === "fa" ? "نقاط عطف وزنی" : "WBS Milestones";
  }
  return locale === "fa" ? "فعالیت‌ها" : "Activities";
}
