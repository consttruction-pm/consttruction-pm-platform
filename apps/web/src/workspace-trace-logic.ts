/**
 * Trace Logic bottom view. The chain is derived only from the persisted
 * activity relationships already loaded in the workspace; nothing is estimated.
 * Cycles are cut with an explicit notice instead of being drawn as if the logic
 * were finite.
 */
import type { WorkspaceActivityRow, WorkspaceRelationshipRow } from "./workspace-model.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

/** Legacy single-depth key, still read so an existing preference survives. */
export const TRACE_LOGIC_STORAGE_KEY = "cubi:workspace:trace-logic-depth";
export const TRACE_LOGIC_PREDECESSOR_STORAGE_KEY = "cubi:workspace:trace-logic-predecessor-depth";
export const TRACE_LOGIC_SUCCESSOR_STORAGE_KEY = "cubi:workspace:trace-logic-successor-depth";
export const TRACE_LOGIC_MIN_DEPTH = 1;
export const TRACE_LOGIC_MAX_DEPTH = 5;
export const TRACE_LOGIC_DEFAULT_DEPTH = 2;

/** Help: Bottom Layout Options specifies the predecessor levels and the
 * successor levels separately. */
export type TraceLogicDepths = {
  predecessors: number;
  successors: number;
};

export const TRACE_LOGIC_DEFAULT_DEPTHS: TraceLogicDepths = {
  predecessors: TRACE_LOGIC_DEFAULT_DEPTH,
  successors: TRACE_LOGIC_DEFAULT_DEPTH,
};

export type TraceLogicRow = {
  activity: WorkspaceActivityRow;
  /** 1 = direct neighbour, 2 = neighbour of a neighbour, ... */
  level: number;
  /** Relationship that reaches this activity from the previous level. */
  relationshipId: string;
  edgeLabel: string;
  critical: boolean;
};

export type TraceLogicModel = {
  selectedId: string | null;
  predecessors: TraceLogicRow[];
  successors: TraceLogicRow[];
  depths: TraceLogicDepths;
  /** A visited activity reappeared, so the walk stopped on that branch. */
  cycleDetected: boolean;
  /** Relationship endpoints that are not loaded as activities. */
  missingReferences: number;
};

export function normalizeTraceDepth(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return TRACE_LOGIC_DEFAULT_DEPTH;
  return Math.min(TRACE_LOGIC_MAX_DEPTH, Math.max(TRACE_LOGIC_MIN_DEPTH, Math.trunc(parsed)));
}

export function normalizeTraceLogicDepths(
  input: number | Partial<TraceLogicDepths> | null | undefined,
): TraceLogicDepths {
  if (typeof input === "number" || input === null || input === undefined) {
    const depth = normalizeTraceDepth(input);
    return { predecessors: depth, successors: depth };
  }
  return {
    predecessors: normalizeTraceDepth(input.predecessors),
    successors: normalizeTraceDepth(input.successors),
  };
}

function edgeLabel(type: string, lagValue: string, lagUnit: string, locale: string): string {
  const lag = Number(lagValue);
  const suffix = Number.isFinite(lag) && lag !== 0
    ? `${lag > 0 ? "+" : ""}${lagValue}${lagUnit === "working-hour" ? translateWorkspaceUiText(locale, "h", "س") : translateWorkspaceUiText(locale, "d", "ر")}`
    : "";
  return `${type}${suffix}`;
}

/**
 * Walks predecessors and successors level by level. A relationship pointing at
 * an activity that is not loaded is counted but never turned into a row.
 */
export function buildTraceLogic(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  selectedId: string | null,
  locale: string,
  depths: number | Partial<TraceLogicDepths> = TRACE_LOGIC_DEFAULT_DEPTHS,
): TraceLogicModel {
  const byId = new Map(activities.map((row) => [row.id, row]));
  const normalized = normalizeTraceLogicDepths(depths);
  const model: TraceLogicModel = {
    selectedId: selectedId && byId.has(selectedId) ? selectedId : null,
    predecessors: [],
    successors: [],
    depths: normalized,
    cycleDetected: false,
    missingReferences: 0,
  };
  if (!model.selectedId) return model;

  const walk = (direction: "predecessor" | "successor"): TraceLogicRow[] => {
    const rows: TraceLogicRow[] = [];
    const selectedId = model.selectedId as string;
    const limit = direction === "predecessor" ? normalized.predecessors : normalized.successors;
    // Each frontier entry keeps the path that reached it so a repeated activity
    // is only a cycle when it is an ancestor of the branch. Two paths that meet
    // again (a diamond) are a convergence and must not be reported as circular.
    let frontier = new Map<string, ReadonlySet<string>>([[selectedId, new Set([selectedId])]]);
    const visited = new Set([selectedId]);
    for (let level = 1; level <= limit && frontier.size; level += 1) {
      const next = new Map<string, Set<string>>();
      for (const relationship of relationships) {
        const from = direction === "predecessor" ? relationship.successorId : relationship.predecessorId;
        const to = direction === "predecessor" ? relationship.predecessorId : relationship.successorId;
        const path = frontier.get(from);
        if (!path) continue;
        const activity = byId.get(to);
        if (!activity) {
          model.missingReferences += 1;
          continue;
        }
        if (path.has(to)) {
          model.cycleDetected = true;
          continue;
        }
        if (visited.has(to)) continue;
        visited.add(to);
        next.set(to, new Set(path).add(to));
        rows.push({
          activity,
          level,
          relationshipId: relationship.id,
          edgeLabel: edgeLabel(relationship.type, relationship.lagValue, relationship.lagUnit, locale),
          critical: activity.gantt?.critical === true,
        });
      }
      frontier = next;
    }
    return rows;
  };

  model.predecessors = walk("predecessor");
  model.successors = walk("successor");
  return model;
}

function resolveStorage(storage?: Storage): Storage | null {
  if (storage) return storage;
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function readStoredDepth(key: string, storage?: Storage): number | null {
  try {
    const raw = resolveStorage(storage)?.getItem(key);
    if (raw === null || raw === undefined || raw.trim() === "") return null;
    const parsed = Number.parseInt(raw, 10);
    return Number.isFinite(parsed) ? normalizeTraceDepth(parsed) : null;
  } catch {
    return null;
  }
}

export function readTraceLogicDepths(storage?: Storage): TraceLogicDepths {
  // A project saved with the first single-depth control keeps that value for
  // both sides until either side is changed through Bottom Layout Options.
  const legacy = readStoredDepth(TRACE_LOGIC_STORAGE_KEY, storage);
  return {
    predecessors: readStoredDepth(TRACE_LOGIC_PREDECESSOR_STORAGE_KEY, storage)
      ?? legacy
      ?? TRACE_LOGIC_DEFAULT_DEPTH,
    successors: readStoredDepth(TRACE_LOGIC_SUCCESSOR_STORAGE_KEY, storage)
      ?? legacy
      ?? TRACE_LOGIC_DEFAULT_DEPTH,
  };
}

export function storeTraceLogicDepths(
  depths: number | Partial<TraceLogicDepths>,
  storage?: Storage,
): TraceLogicDepths {
  const normalized = normalizeTraceLogicDepths(depths);
  try {
    const target = resolveStorage(storage);
    target?.setItem(TRACE_LOGIC_PREDECESSOR_STORAGE_KEY, String(normalized.predecessors));
    target?.setItem(TRACE_LOGIC_SUCCESSOR_STORAGE_KEY, String(normalized.successors));
  } catch {
    // Preference storage is optional; the chosen depth still applies to this render.
  }
  return normalized;
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function traceRow(row: TraceLogicRow, locale: string, selectedId: string | null): string {
  const t = (en: string, fa: string): string => translateWorkspaceUiText(locale, en, fa);
  const selected = row.activity.id === selectedId;
  const progress = row.activity.gantt?.progressPercent;
  const criticalLabel = t("Critical activity", "فعالیت بحرانی");
  return `<li class="cp-trace-row${row.critical ? " is-critical" : ""}${selected ? " is-selected" : ""}" data-trace-activity-id="${esc(row.activity.id)}"${row.critical ? ` title="${esc(criticalLabel)}"` : ""}>
    <span class="cp-trace-level" aria-label="${esc(t(`Level ${row.level}`, `سطح ${row.level}`))}">${row.level}</span>
    <button type="button" class="cp-trace-goto" data-trace-goto="${esc(row.activity.id)}">
      <strong>${esc(row.activity.id)}</strong> — ${esc(row.activity.name)}
    </button>
    <span class="cp-trace-edge" translate="no">${esc(row.edgeLabel)}</span>
    <span class="cp-trace-progress">${progress === undefined ? "—" : `${Math.round(progress)}%`}</span>
  </li>`;
}

export function renderTraceLogic(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  locale: string,
  selectedId: string | null,
  depths: number | Partial<TraceLogicDepths> = TRACE_LOGIC_DEFAULT_DEPTHS,
): string {
  const t = (en: string, fa: string): string => translateWorkspaceUiText(locale, en, fa);
  const model = buildTraceLogic(activities, relationships, selectedId, locale, depths);
  const selected = model.selectedId ? activities.find((row) => row.id === model.selectedId) ?? null : null;

  const depthOptions = (selectedValue: number): string => Array.from(
    { length: TRACE_LOGIC_MAX_DEPTH - TRACE_LOGIC_MIN_DEPTH + 1 },
    (_, index) => TRACE_LOGIC_MIN_DEPTH + index,
  ).map((value) => `<option value="${value}"${value === selectedValue ? " selected" : ""}>${value}</option>`).join("");
  const depthField = (direction: "predecessors" | "successors", label: string, value: number): string =>
    `<label class="cp-trace-depth">${esc(label)}
      <select data-trace-depth="${direction}">${depthOptions(value)}</select>
    </label>`;
  const depthsMarkup = `${depthField("predecessors", t("Predecessors", "پیش‌نیازها"), model.depths.predecessors)}
    ${depthField("successors", t("Successors", "پس‌نیازها"), model.depths.successors)}`;
  const dataset = `data-trace-logic data-trace-predecessor-depth="${model.depths.predecessors}" data-trace-successor-depth="${model.depths.successors}"`;

  if (!selected) {
    return `<section class="cp-trace-logic" ${dataset}>
      <header class="cp-trace-head"><h2 id="cp-trace-heading">${esc(t("Trace Logic", "ردیابی منطق"))}</h2>${depthsMarkup}</header>
      <div class="cp-empty">${esc(t(
        "Select an activity to trace its predecessor and successor chains.",
        "برای ردیابی زنجیرهٔ پیش‌نیازها و پس‌نیازها یک فعالیت انتخاب کنید.",
      ))}</div>
    </section>`;
  }

  const notices: string[] = [];
  if (model.cycleDetected) {
    notices.push(t(
      "A circular dependency was found in the persisted relationships; the chain stops at the repeated activity.",
      "در روابط ذخیره‌شده وابستگی چرخه‌ای یافت شد؛ زنجیره در فعالیت تکراری متوقف می‌شود.",
    ));
  }
  if (model.missingReferences) {
    notices.push(t(
      "Some relationship endpoints are not loaded activities and were left out of the chain.",
      "برخی سر دیگر روابط، فعالیت بارگذاری‌شده نیستند و از زنجیره حذف شدند.",
    ));
  }
  if (!model.predecessors.length && !model.successors.length) {
    notices.push(t(
      "No persisted relationship reaches this activity within the chosen depth.",
      "در عمق انتخاب‌شده، هیچ رابطهٔ ذخیره‌شده‌ای به این فعالیت نمی‌رسد.",
    ));
  }

  const group = (title: string, rows: readonly TraceLogicRow[]): string => `<section class="cp-trace-group">
    <h3>${esc(title)} <small>${rows.length}</small></h3>
    ${rows.length
      ? `<ol class="cp-trace-list">${rows.map((row) => traceRow(row, locale, model.selectedId)).join("")}</ol>`
      : `<p class="cp-trace-empty">${esc(t("None within depth.", "در این عمق وجود ندارد."))}</p>`}
  </section>`;

  return `<section class="cp-trace-logic" ${dataset}>
    <header class="cp-trace-head">
      <div><h2 id="cp-trace-heading">${esc(t("Trace Logic", "ردیابی منطق"))}</h2>
        <span class="cp-trace-selected" data-trace-selected="${esc(selected.id)}">${esc(selected.id)} — ${esc(selected.name)}</span></div>
      <div class="cp-trace-depths">${depthsMarkup}</div>
    </header>
    ${notices.map((notice) => `<p class="cp-register-notice">${esc(notice)}</p>`).join("")}
    <div class="cp-trace-groups">
      ${group(t("Predecessors", "پیش‌نیازها"), model.predecessors)}
      ${group(t("Successors", "پس‌نیازها"), model.successors)}
    </div>
    <p class="cp-trace-note">${esc(t(
      "Chains are read from the persisted plan logic. Dates are not recalculated in this view.",
      "زنجیره‌ها از منطق برنامهٔ ذخیره‌شده خوانده می‌شوند. تاریخ‌ها در این نما بازمحاسبه نمی‌شوند.",
    ))}</p>
  </section>`;
}
