/**
 * Activity clipboard for Cut / Copy / Paste.
 *
 * The clipboard keeps authoritative source IDs, never a stale copy of project
 * fields. Paste re-reads each source and creates a new Activity Master record
 * through the server; a Cut succeeds only when every source was removed.
 */
export type ActivityClipboardMode = "copy" | "cut";

export type ActivityClipboard = {
  projectId: string;
  ids: readonly string[];
  mode: ActivityClipboardMode;
};

export function makeActivityClipboard(projectId: string, ids: readonly string[], mode: ActivityClipboardMode): ActivityClipboard | null {
  const unique = [...new Set(ids.filter((id) => Boolean(id)))];
  return unique.length ? { projectId, ids: unique, mode } : null;
}

/** P6 renumbers pasted activities; CUBI derives a collision-free suffix. */
export function nextPastedActivityId(sourceId: string, taken: ReadonlySet<string>): string {
  const base = `${sourceId}-C`;
  for (let index = 1; index < 1000; index += 1) {
    const candidate = `${base}${index}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${base}${Date.now()}`;
}

type RawActivity = Record<string, unknown>;

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

/**
 * Build the create payload from the authoritative GET DTO. Only fields the
 * create contract accepts are forwarded; status/progress dates are not copied
 * so a pasted activity starts as planned work, and the server applies project
 * defaults for anything the source did not carry.
 */
export function buildPastedActivityPayload(
  raw: unknown,
  newId: string,
  wbsId: string | null,
): Record<string, unknown> | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const envelope = raw as RawActivity;
  const activity = (envelope.activity && typeof envelope.activity === "object" && !Array.isArray(envelope.activity))
    ? envelope.activity as RawActivity
    : envelope;
  const duration = activity.duration_value;
  if (!newId.trim()) return null;
  return {
    contract_version: "p6-activity-master-api.v1",
    activity_id: newId,
    name: text(activity.name, newId),
    duration_value: typeof duration === "number" || typeof duration === "string" ? duration : 1,
    duration_unit: text(activity.duration_unit, "working-day"),
    wbs_id: wbsId,
    activity_type: text(activity.activity_type, "Task Dependent"),
    status: "Not Started",
    status_code: "Planned",
    percent_complete_type: text(activity.percent_complete_type, "DURATION"),
    duration_type: text(activity.duration_type, "Fixed Duration & Units"),
    cost_account_id: typeof activity.cost_account_id === "string" ? activity.cost_account_id : null,
    leveling_priority: text(activity.leveling_priority, "Normal"),
  };
}
