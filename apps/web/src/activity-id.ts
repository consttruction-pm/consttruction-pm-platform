/**
 * Activity ID auto-numbering from the V26 Project Details Defaults tab.
 *
 * The stored project defaults own the prefix, suffix and increment. This module
 * only proposes the next identifier for the create form; the server validates
 * and stores whatever the user confirms, so it is never schedule math.
 */
export type ActivityIdDefaults = {
  prefix: string;
  suffix: string;
  increment: number;
  incrementActivityId: boolean;
};

export const DEFAULT_ACTIVITY_ID_INCREMENT = 10;

function normalizeIncrement(value: number): number {
  if (!Number.isInteger(value) || value < 1 || value > 10000) {
    return DEFAULT_ACTIVITY_ID_INCREMENT;
  }
  return value;
}

export function stripActivityIdAffixes(
  activityId: string,
  prefix: string,
  suffix: string,
): string {
  let core = activityId.trim();
  if (prefix && core.startsWith(prefix)) core = core.slice(prefix.length);
  if (suffix && core.endsWith(suffix)) core = core.slice(0, core.length - suffix.length);
  return core;
}

type NumericTail = { head: string; value: number; width: number } | null;

function splitNumericTail(core: string): NumericTail {
  const match = /^(.*?)(\d+)$/.exec(core);
  if (!match) return null;
  return { head: match[1], value: Number(match[2]), width: match[2].length };
}

function incrementCore(core: string, increment: number): string {
  const tail = splitNumericTail(core);
  if (tail === null) {
    return `${core}${increment}`;
  }
  const next = tail.value + increment;
  const digits = String(next).padStart(tail.width, "0");
  return `${tail.head}${digits}`;
}

/**
 * Propose the next Activity ID.
 *
 * With "Increment Activity ID based on selected activity" enabled, the
 * selected row is the base; otherwise the highest existing numeric tail is the
 * base. A project with no matching activity starts from the increment itself.
 */
export function computeNextActivityId(
  activityIds: readonly string[],
  defaults: ActivityIdDefaults,
  selectedActivityId?: string | null,
): string {
  const prefix = defaults.prefix ?? "";
  const suffix = defaults.suffix ?? "";
  const increment = normalizeIncrement(defaults.increment);
  const cores = activityIds.map((id) => stripActivityIdAffixes(id, prefix, suffix));

  let baseCore: string | null = null;
  if (defaults.incrementActivityId && selectedActivityId) {
    const selectedCore = stripActivityIdAffixes(selectedActivityId, prefix, suffix);
    if (selectedCore) baseCore = selectedCore;
  }
  if (baseCore === null) {
    let highest: { core: string; value: number } | null = null;
    for (const core of cores) {
      const tail = splitNumericTail(core);
      if (tail === null) continue;
      if (highest === null || tail.value > highest.value) {
        highest = { core, value: tail.value };
      }
    }
    baseCore = highest?.core ?? "";
  }

  return `${prefix}${incrementCore(baseCore, increment)}${suffix}`;
}
