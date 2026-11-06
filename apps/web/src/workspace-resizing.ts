import type { WorkspaceState } from "./workspace-model.js";
import type { WorkspaceRendererOptions } from "./workspace-view.js";

type ResizeKind = "table-gantt" | "details" | "column";

type ResizeRuntime = {
  state: WorkspaceState;
  options: WorkspaceRendererOptions;
};

type ActiveDrag = {
  pointerId: number;
  kind: ResizeKind;
  handle: HTMLElement;
  startX: number;
  startValue: number;
  startWidth?: number;
  apply(value: number): void;
};

const runtimes = new WeakMap<HTMLElement, ResizeRuntime>();
const bound = new WeakSet<HTMLElement>();
const MIN_COLUMN_WIDTH = 40;
const MAX_COLUMN_WIDTH = 720;
const DEFAULT_TABLE_RATIO = 45;
const DEFAULT_DETAILS_RATIO = 70;

export function clampResizePercent(value: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

export function resizedColumnWidth(
  startWidth: number,
  startX: number,
  currentX: number,
  direction: "ltr" | "rtl",
): number {
  const directionFactor = direction === "rtl" ? -1 : 1;
  return clampResizePercent(
    startWidth + (currentX - startX) * directionFactor,
    MIN_COLUMN_WIDTH,
    MAX_COLUMN_WIDTH,
    startWidth,
  );
}

function storageKey(state: WorkspaceState, kind: "table-gantt" | "details"): string {
  return [
    "cubi:workspace:split",
    encodeURIComponent(state.context.tenant_id),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
    kind,
  ].join(":");
}

function readPercent(key: string, min: number, max: number, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === null) return fallback;
    return clampResizePercent(Number(raw), min, max, fallback);
  } catch {
    return fallback;
  }
}

function writePercent(key: string, value: number): void {
  try {
    window.localStorage.setItem(key, value.toFixed(2));
  } catch {
    // A blocked or full browser storage must not block resizing in this session.
  }
}

function isRtl(runtime: ResizeRuntime, container: HTMLElement): boolean {
  return runtime.state.direction === "rtl" ||
    container.querySelector<HTMLElement>(".cp-p6-workspace")?.dir === "rtl";
}

function updateColumnPreview(container: HTMLElement, columnId: string, width: number): void {
  const cells = Array.from(container.querySelectorAll<HTMLElement>("[data-column-id]"))
    .filter((element) => element.dataset.columnId === columnId);
  for (const cell of cells) cell.style.width = `${width.toFixed(0)}px`;

  const table = container.querySelector<HTMLTableElement>("#cp-activity-grid table");
  if (table) {
    const headers = Array.from(table.querySelectorAll<HTMLElement>("thead th.cp-p6-column"));
    const total = headers.reduce((sum, header) => sum + (Number.parseFloat(header.style.width) || 0), 0);
    table.style.width = `${total + 92}px`;

    let stickyOffset = 0;
    for (const header of headers) {
      const widthValue = Number.parseFloat(header.style.width) || 0;
      const pinned = header.dataset.columnPinned === "true" || header.dataset.columnFrozen === "true";
      if (pinned) {
        const id = header.dataset.columnId;
        if (id) {
          for (const cell of Array.from(table.querySelectorAll<HTMLElement>("[data-column-id]"))) {
            if (cell.dataset.columnId === id) {
              cell.style.setProperty("--cp-p6-sticky-offset", `${stickyOffset}px`);
            }
          }
        }
        stickyOffset += widthValue;
      }
    }
  }
}

function setSplitRatio(
  container: HTMLElement,
  kind: "table-gantt" | "details",
  value: number,
): void {
  if (kind === "table-gantt") {
    const split = container.querySelector<HTMLElement>("[data-panel-split]");
    if (!split) return;
    split.style.setProperty("--cp-split-table", `${value.toFixed(2)}%`);
    const handle = split.querySelector<HTMLElement>('[data-resize-handle="table-gantt"]');
    handle?.setAttribute("aria-valuenow", value.toFixed(0));
    return;
  }
  const main = container.querySelector<HTMLElement>(".cp-main");
  if (!main) return;
  main.style.setProperty("--cp-split-details", `${value.toFixed(2)}%`);
  const handle = main.querySelector<HTMLElement>('[data-resize-handle="details"]');
  handle?.setAttribute("aria-valuenow", value.toFixed(0));
}

function persistedDefaultWidth(runtime: ResizeRuntime, columnId: string): number {
  const current = runtime.state.columns.find((column) => column.id === columnId)?.width;
  return current ?? 120;
}

/**
 * Adds pointer/keyboard resizing to the existing live workspace.
 * Split ratios are browser-local presentation preferences; column widths go
 * through the existing revision-checked P6 layout API callback.
 */
export function bindWorkspaceResizeInteractions(
  container: HTMLElement,
  state: WorkspaceState,
  options: WorkspaceRendererOptions,
): void {
  // The renderer is also exercised by server-side and DOM-light unit fixtures.
  // Only install browser interactions when this is a real mounted browser node.
  if (
    typeof container?.querySelector !== "function" ||
    typeof container.addEventListener !== "function" ||
    typeof window === "undefined" ||
    typeof document === "undefined"
  ) return;
  const runtime: ResizeRuntime = { state, options };
  runtimes.set(container, runtime);

  const tableKey = storageKey(state, "table-gantt");
  const detailsKey = storageKey(state, "details");
  const tableRatio = readPercent(tableKey, 30, 70, DEFAULT_TABLE_RATIO);
  const detailsRatio = readPercent(detailsKey, 55, 85, DEFAULT_DETAILS_RATIO);
  setSplitRatio(container, "table-gantt", tableRatio);
  setSplitRatio(container, "details", detailsRatio);

  const tableHandle = container.querySelector<HTMLElement>('[data-resize-handle="table-gantt"]');
  if (tableHandle) tableHandle.setAttribute("aria-valuenow", tableRatio.toFixed(0));
  const detailsHandle = container.querySelector<HTMLElement>('[data-resize-handle="details"]');
  if (detailsHandle) detailsHandle.setAttribute("aria-valuenow", detailsRatio.toFixed(0));

  if (bound.has(container) || typeof container.addEventListener !== "function") return;
  bound.add(container);

  let active: ActiveDrag | null = null;
  const endDrag = (commit: boolean): void => {
    if (!active) return;
    const drag = active;
    active = null;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
    window.removeEventListener("pointercancel", onPointerCancel);
    const shell = container.closest<HTMLElement>(".cp-app-shell") ?? container;
    shell.classList.remove("is-resizing", `is-resizing-${drag.kind}`);
    document.documentElement.classList.remove("cubi-is-resizing");
    if (!commit) {
      drag.apply(drag.startValue);
    } else if (drag.kind === "table-gantt" || drag.kind === "details") {
      const latest = runtimes.get(container);
      const finalValue = drag.kind === "table-gantt"
        ? Number.parseFloat(container.querySelector<HTMLElement>("[data-panel-split]")?.style.getPropertyValue("--cp-split-table") ?? "")
        : Number.parseFloat(container.querySelector<HTMLElement>(".cp-main")?.style.getPropertyValue("--cp-split-details") ?? "");
      if (Number.isFinite(finalValue) && latest) writePercent(storageKey(latest.state, drag.kind), finalValue);
    } else if (drag.kind === "column" && drag.startWidth !== undefined) {
      const id = drag.handle.dataset.columnResize;
      const header = drag.handle.closest<HTMLElement>("th[data-column-id]");
      const width = Number.parseFloat(header?.style.width ?? "");
      const latest = runtimes.get(container);
      if (id && Number.isFinite(width) && latest?.options.onP6FieldWidthChange) {
        latest.options.onP6FieldWidthChange(id, clampResizePercent(width, MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH, drag.startWidth));
      }
    }
    try {
      if (drag.handle.hasPointerCapture(drag.pointerId)) drag.handle.releasePointerCapture(drag.pointerId);
    } catch {
      // Pointer capture may already have been released by the browser.
    }
  };

  function onPointerMove(event: PointerEvent): void {
    if (!active || event.pointerId !== active.pointerId) return;
    const drag = active;
    if (drag.kind === "table-gantt") {
      const split = drag.handle.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      const rect = split.getBoundingClientRect();
      if (rect.width <= 0) return;
      const rtl = isRtl(runtimes.get(container)!, container);
      const percent = rtl
        ? ((rect.right - event.clientX) / rect.width) * 100
        : ((event.clientX - rect.left) / rect.width) * 100;
      drag.apply(clampResizePercent(percent, 30, 70, DEFAULT_TABLE_RATIO));
    } else if (drag.kind === "details") {
      const main = drag.handle.closest<HTMLElement>(".cp-main");
      if (!main) return;
      const rect = main.getBoundingClientRect();
      if (rect.height <= 0) return;
      const percent = ((event.clientY - rect.top) / rect.height) * 100;
      drag.apply(clampResizePercent(percent, 55, 85, DEFAULT_DETAILS_RATIO));
    } else if (drag.startWidth !== undefined) {
      const runtime = runtimes.get(container);
      const header = drag.handle.closest<HTMLElement>("th[data-column-id]");
      if (!runtime || !header) return;
      const direction = isRtl(runtime, container) ? "rtl" : "ltr";
      const width = resizedColumnWidth(drag.startWidth, drag.startX, event.clientX, direction);
      drag.apply(width);
    }
  }

  function onPointerUp(event: PointerEvent): void {
    if (active && event.pointerId === active.pointerId) endDrag(true);
  }

  function onPointerCancel(event: PointerEvent): void {
    if (active && event.pointerId === active.pointerId) endDrag(false);
  }

  container.addEventListener("pointerdown", (event) => {
    const target = event.target instanceof Element
      ? event.target.closest<HTMLElement>("[data-resize-handle]")
      : null;
    if (!target || (event as PointerEvent).button !== 0 || (event as PointerEvent).isPrimary === false) return;
    const runtime = runtimes.get(container);
    if (!runtime) return;
    const kind = target.dataset.resizeHandle as ResizeKind | undefined;
    if (kind !== "table-gantt" && kind !== "details" && kind !== "column") return;

    const pointerEvent = event as PointerEvent;
    let startValue = 0;
    let startWidth: number | undefined;
    if (kind === "table-gantt") {
      const split = target.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      startValue = Number.parseFloat(split.style.getPropertyValue("--cp-split-table")) || DEFAULT_TABLE_RATIO;
    } else if (kind === "details") {
      const main = target.closest<HTMLElement>(".cp-main");
      if (!main || !runtime.state.visiblePanels.details) return;
      startValue = Number.parseFloat(main.style.getPropertyValue("--cp-split-details")) || DEFAULT_DETAILS_RATIO;
    } else {
      const header = target.closest<HTMLElement>("th[data-column-id]");
      const columnId = target.dataset.columnResize;
      if (!header || !columnId) return;
      startWidth = Number.parseFloat(header.style.width) || persistedDefaultWidth(runtime, columnId);
      startValue = startWidth;
    }

    pointerEvent.preventDefault();
    try {
      target.setPointerCapture(pointerEvent.pointerId);
    } catch {
      // Window-level pointer listeners below also work without pointer capture.
    }

    const drag: ActiveDrag = {
      pointerId: pointerEvent.pointerId,
      kind,
      handle: target,
      startX: pointerEvent.clientX,
      startValue,
      startWidth,
      apply(value: number) {
        if (kind === "column") {
          const id = target.dataset.columnResize;
          if (id) updateColumnPreview(container, id, clampResizePercent(value, MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH, startValue));
          target.setAttribute("aria-valuenow", String(Math.round(value)));
          return;
        }
        setSplitRatio(container, kind, value);
      },
    };
    active = drag;
    const shell = container.closest<HTMLElement>(".cp-app-shell") ?? container;
    shell.classList.add("is-resizing", `is-resizing-${kind}`);
    document.documentElement.classList.add("cubi-is-resizing");
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerCancel);
  });

  container.addEventListener("dblclick", (event) => {
    const target = event.target instanceof Element
      ? event.target.closest<HTMLElement>('[data-resize-handle="table-gantt"], [data-resize-handle="details"]')
      : null;
    if (!target) return;
    event.preventDefault();
    const kind = target.dataset.resizeHandle as "table-gantt" | "details";
    const latest = runtimes.get(container);
    if (!latest) return;
    const value = kind === "table-gantt" ? DEFAULT_TABLE_RATIO : DEFAULT_DETAILS_RATIO;
    setSplitRatio(container, kind, value);
    writePercent(storageKey(latest.state, kind), value);
  });

  container.addEventListener("keydown", (event) => {
    const target = event.target instanceof Element
      ? event.target.closest<HTMLElement>("[data-resize-handle]")
      : null;
    if (!target) return;
    const kind = target.dataset.resizeHandle as ResizeKind | undefined;
    if (kind !== "table-gantt" && kind !== "details" && kind !== "column") return;
    const runtime = runtimes.get(container);
    if (!runtime) return;

    const horizontal = kind !== "details";
    const arrows = horizontal ? ["ArrowLeft", "ArrowRight"] : ["ArrowUp", "ArrowDown"];
    if (!arrows.includes(event.key) && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();

    if (kind === "column") {
      const id = target.dataset.columnResize;
      const header = target.closest<HTMLElement>("th[data-column-id]");
      if (!id || !header) return;
      const current = Number.parseFloat(header.style.width) || persistedDefaultWidth(runtime, id);
      const rtl = isRtl(runtime, container);
      const direction = event.key === "Home" ? -1 : event.key === "End" ? 1
        : event.key === "ArrowRight" ? (rtl ? -1 : 1) : (rtl ? 1 : -1);
      const next = event.key === "Home" ? MIN_COLUMN_WIDTH
        : event.key === "End" ? MAX_COLUMN_WIDTH
          : clampResizePercent(current + direction * 8, MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH, current);
      updateColumnPreview(container, id, next);
      target.setAttribute("aria-valuenow", String(Math.round(next)));
      runtime.options.onP6FieldWidthChange?.(id, next);
      return;
    }

    const current = kind === "table-gantt"
      ? Number.parseFloat(target.closest<HTMLElement>("[data-panel-split]")?.style.getPropertyValue("--cp-split-table") ?? "") || DEFAULT_TABLE_RATIO
      : Number.parseFloat(target.closest<HTMLElement>(".cp-main")?.style.getPropertyValue("--cp-split-details") ?? "") || DEFAULT_DETAILS_RATIO;
    const increasing = event.key === "End" || (event.key === "ArrowRight" && kind === "table-gantt" && !isRtl(runtime, container)) ||
      (event.key === "ArrowLeft" && kind === "table-gantt" && isRtl(runtime, container)) ||
      (event.key === "ArrowDown" && kind === "details");
    const decreasing = event.key === "Home" || (event.key === "ArrowLeft" && kind === "table-gantt" && !isRtl(runtime, container)) ||
      (event.key === "ArrowRight" && kind === "table-gantt" && isRtl(runtime, container)) ||
      (event.key === "ArrowUp" && kind === "details");
    const min = kind === "table-gantt" ? 30 : 55;
    const max = kind === "table-gantt" ? 70 : 85;
    const next = event.key === "Home" ? min : event.key === "End" ? max
      : clampResizePercent(current + (increasing ? 2 : decreasing ? -2 : 0), min, max, current);
    setSplitRatio(container, kind, next);
    writePercent(storageKey(runtime.state, kind), next);
  });
}
