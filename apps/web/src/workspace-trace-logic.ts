/**
 * Trace Logic bottom view. The chain is derived only from the persisted
 * activity relationships already loaded in the workspace; nothing is estimated.
 * Cycles are cut with an explicit notice instead of being drawn as if the logic
 * were finite.
 */
import type { WorkspaceActivityRow, WorkspaceRelationshipRow } from "./workspace-model.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export const TRACE_LOGIC_STORAGE_KEY = "cubi:workspace:trace-logic-depth";
export const TRACE_LOGIC_MIN_DEPTH = 1;
export const TRACE_LOGIC_MAX_DEPTH = 5;
export const TRACE_LOGIC_DEFAULT_DEPTH = 2;

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
  depth: number;
  /** A visited activity reappeared, so the walk stopped on that branch. */
  cycleDetected: boolean;
  /** Relationship endpoints that are not loaded as activities. */
  missingReferences: number;
};

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
  depth: number = TRACE_LOGIC_DEFAULT_DEPTH,
): TraceLogicModel {
  const byId = new Map(activities.map((row) => [row.id, row]));
  const clamped = Math.min(TRACE_LOGIC_MAX_DEPTH, Math.max(TRACE_LOGIC_MIN_DEPTH, Math.trunc(depth) || TRACE_LOGIC_DEFAULT_DEPTH));
  const model: TraceLogicModel = {
    selectedId: selectedId && byId.has(selectedId) ? selectedId : null,
    predecessors: [],
    successors: [],
    depth: clamped,
    cycleDetected: false,
    missingReferences: 0,
  };
  if (!model.selectedId) return model;

  const walk = (direction: "predecessor" | "successor"): TraceLogicRow[] => {
    const rows: TraceLogicRow[] = [];
    const selectedId = model.selectedId as string;
    // Each frontier entry keeps the path that reached it so a repeated activity
    // is only a cycle when it is an ancestor of the branch. Two paths that meet
    // again (a diamond) are a convergence and must not be reported as circular.
    let frontier = new Map<string, ReadonlySet<string>>([[selectedId, new Set([selectedId])]]);
    const visited = new Set([selectedId]);
    for (let level = 1; level <= clamped && frontier.size; level += 1) {
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

export function readTraceLogicDepth(storage?: Storage): number {
  try {
    const raw = (storage ?? (typeof window === "undefined" ? null : window.localStorage))?.getItem(TRACE_LOGIC_STORAGE_KEY);
    const parsed = raw === null || raw === undefined ? Number.NaN : Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed)) return TRACE_LOGIC_DEFAULT_DEPTH;
    return Math.min(TRACE_LOGIC_MAX_DEPTH, Math.max(TRACE_LOGIC_MIN_DEPTH, parsed));
  } catch {
    return TRACE_LOGIC_DEFAULT_DEPTH;
  }
}

export function storeTraceLogicDepth(value: number, storage?: Storage): void {
  const clamped = Math.min(TRACE_LOGIC_MAX_DEPTH, Math.max(TRACE_LOGIC_MIN_DEPTH, Math.trunc(value) || TRACE_LOGIC_DEFAULT_DEPTH));
  try {
    (storage ?? (typeof window === "undefined" ? null : window.localStorage))?.setItem(TRACE_LOGIC_STORAGE_KEY, String(clamped));
  } catch {
    // Preference storage is optional; the chosen depth still applies to this render.
  }
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
  return `<li class="cp-trace-row${row.critical ? " is-critical" : ""}${selected ? " is-selected" : ""}" data-trace-activity-id="${esc(row.activity.id)}">
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
  depth: number,
): string {
  const t = (en: string, fa: string): string => translateWorkspaceUiText(locale, en, fa);
  const model = buildTraceLogic(activities, relationships, selectedId, locale, depth);
  const selected = model.selectedId ? activities.find((row) => row.id === model.selectedId) ?? null : null;

  const depthOptions = Array.from({ length: TRACE_LOGIC_MAX_DEPTH - TRACE_LOGIC_MIN_DEPTH + 1 }, (_, index) => TRACE_LOGIC_MIN_DEPTH + index)
    .map((value) => `<option value="${value}"${value === model.depth ? " selected" : ""}>${value}</option>`)
    .join("");

  if (!selected) {
    return `<section class="cp-trace-logic" data-trace-logic data-trace-depth-value="${model.depth}">
      <header class="cp-trace-head"><h2 id="cp-trace-heading">${esc(t("Trace Logic", "ردیابی منطق"))}</h2></header>
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

  return `<section class="cp-trace-logic" data-trace-logic data-trace-depth-value="${model.depth}">
    <header class="cp-trace-head">
      <div><h2 id="cp-trace-heading">${esc(t("Trace Logic", "ردیابی منطق"))}</h2>
        <span class="cp-trace-selected" data-trace-selected="${esc(selected.id)}">${esc(selected.id)} — ${esc(selected.name)}</span></div>
      <label class="cp-trace-depth">${esc(t("Depth", "عمق"))}
        <select data-trace-depth>${depthOptions}</select>
      </label>
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
