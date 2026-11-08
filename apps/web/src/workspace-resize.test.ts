import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import { createWorkspaceState, setP6Presentation } from "./workspace-model.js";

type Listener = (event: Event) => void;

type RenderContainer = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
  addEventListener: (type: string, listener: Listener) => void;
};

function resizeLayoutState() {
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "26",
    status: "active",
    fields: [
      { field_id: "code", subject_area: "activity", p6_field: "ActivityId", display_name: "Code", data_type: "string" as const, writable: false, computed: false, disposition: "supported" },
    ],
  };
  const layout = {
    schema_version: "p6-layout.v1" as const,
    scope: "project" as const,
    view_id: "activity-grid",
    revision: 2,
    columns: [
      { field_id: "code", visible: true, order: 0, width: 140, alignment: "start" as const, pinned: false, frozen: false },
    ],
  };
  return setP6Presentation(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    registry,
    layout,
  );
}

function fakeColumnDom(container: RenderContainer, rtl = false) {
  const attributes = new Map<string, string>();
  const handle = {
    dataset: { columnResize: "code" },
    listeners: new Map<string, Listener>(),
    setAttribute: (name: string, value: string) => attributes.set(name, value),
    addEventListener: (type: string, listener: Listener) => handle.listeners.set(type, listener),
    removeEventListener: (type: string) => handle.listeners.delete(type),
    setPointerCapture: () => {},
    closest: (selector: string): unknown => {
      if (selector === "[data-column-resize]") return handle;
      if (selector === "th") return header;
      return null;
    },
  };
  const header: {
    tagName: string;
    style: { width: string };
    dataset: { columnId: string };
    closest: (selector: string) => unknown;
    querySelector: (selector: string) => unknown;
    getBoundingClientRect: () => { width: number };
  } = {
    tagName: "TH",
    style: { width: "140px" },
    dataset: { columnId: "code" },
    closest: (selector: string) => (selector === "table" ? table : null),
    querySelector: (selector: string) => (selector === "[data-column-resize]" ? handle : null),
    getBoundingClientRect: () => ({ width: 140 }),
  };
  const cell = {
    tagName: "TD",
    dataset: { columnId: "code" },
    style: { width: "140px" },
    closest: () => null,
    querySelector: () => null,
  };
  const table = {
    style: { width: "720px" },
    getBoundingClientRect: () => ({ width: 720 }),
  };
  const grid = { querySelectorAll: () => [header, cell] };
  (container as unknown as { querySelector: (selector: string) => unknown }).querySelector = (selector: string) => {
    if (selector === "#cp-activity-grid") return grid;
    if (selector === "[dir]") return rtl ? { getAttribute: () => "rtl" } : null;
    return null;
  };
  return { handle, header, cell, table, attributes };
}

function captureContainer() {
  const listeners = new Map<string, Listener>();
  const container = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: Listener) => listeners.set(type, listener),
  };
  return { container, listeners };
}

test("keyboard column resize updates the header and cells, clamps, and persists through the P6 layout callback", () => {
  const { container, listeners } = captureContainer();
  const persisted: Array<[string, number]> = [];
  renderMainWorkspace(container as unknown as HTMLElement, resizeLayoutState(), {
    onP6FieldWidthChange: (fieldId, width) => persisted.push([fieldId, width]),
  });
  const dom = fakeColumnDom(container);
  const keydown = (key: string, shiftKey = false) => listeners.get("keydown")?.({
    key,
    shiftKey,
    target: dom.handle,
    preventDefault: () => {},
  } as unknown as KeyboardEvent);

  keydown("ArrowRight");
  assert.equal(dom.header.style.width, "150px");
  assert.equal(dom.cell.style.width, "150px");
  assert.equal(dom.attributes.get("aria-valuenow"), "150");
  assert.deepEqual(persisted, [["code", 150]]);

  keydown("ArrowLeft", true);
  assert.equal(dom.header.style.width, "110px");
  assert.deepEqual(persisted, [["code", 150], ["code", 110]]);

  dom.header.style.width = "50px";
  keydown("ArrowLeft");
  assert.equal(dom.header.style.width, "48px");

  dom.header.style.width = "636px";
  keydown("ArrowRight");
  assert.equal(dom.header.style.width, "640px");
});

test("pointer column resizing applies RTL-aware deltas and persists only on release", () => {
  const { container, listeners } = captureContainer();
  const persisted: Array<[string, number]> = [];
  renderMainWorkspace(container as unknown as HTMLElement, resizeLayoutState(), {
    onP6FieldWidthChange: (fieldId, width) => persisted.push([fieldId, width]),
  });
  const dom = fakeColumnDom(container);
  const pointer = (type: string, clientX: number) => listeners.get(type)?.({
    clientX,
    pointerId: 1,
    target: dom.handle,
    preventDefault: () => {},
    stopPropagation: () => {},
  } as unknown as PointerEvent);

  pointer("pointerdown", 100);
  dom.handle.listeners.get("pointermove")?.({ clientX: 160 } as unknown as Event);
  assert.equal(dom.header.style.width, "200px");
  assert.deepEqual(persisted, [], "dragging must not persist intermediate widths");
  dom.handle.listeners.get("pointerup")?.({} as unknown as Event);
  assert.deepEqual(persisted, [["code", 200]]);

  const rtlListeners = new Map<string, Listener>();
  const rtlContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
    addEventListener: (type: string, listener: Listener) => rtlListeners.set(type, listener),
    closest: () => ({ getAttribute: () => "rtl" }),
  };
  renderMainWorkspace(rtlContainer as unknown as HTMLElement, resizeLayoutState());
  const rtlDom = fakeColumnDom(rtlContainer, true);
  rtlListeners.get("pointerdown")?.({
    clientX: 100,
    pointerId: 1,
    target: rtlDom.handle,
    preventDefault: () => {},
    stopPropagation: () => {},
  } as unknown as PointerEvent);
  rtlDom.handle.listeners.get("pointermove")?.({ clientX: 160 } as unknown as Event);
  assert.equal(rtlDom.header.style.width, "80px");
});

test("details splitter drags and keyboard adjustments update the 70/30 height split and clamp", () => {
  const { container, listeners } = captureContainer();
  renderMainWorkspace(container as unknown as HTMLElement, resizeLayoutState());
  const properties = new Map<string, string>([["--cp-split-primary", "70%"]]);
  const attributes = new Map<string, string>();
  const main = {
    style: {
      setProperty: (name: string, value: string) => properties.set(name, value),
      getPropertyValue: (name: string) => properties.get(name) ?? "",
    },
    getBoundingClientRect: () => ({ top: 0, height: 1000 }),
  };
  const splitter = {
    dataset: { splitKey: "cubi:workspace-details-split:v1:project-1:schedule" },
    listeners: new Map<string, Listener>(),
    setAttribute: (name: string, value: string) => attributes.set(name, value),
    addEventListener: (type: string, listener: Listener) => splitter.listeners.set(type, listener),
    removeEventListener: (type: string) => splitter.listeners.delete(type),
    setPointerCapture: () => {},
    closest: (selector: string): unknown => {
      if (selector === "[data-details-splitter]") return splitter;
      if (selector === ".cp-main") return main;
      return null;
    },
  };

  listeners.get("keydown")?.({
    key: "ArrowDown",
    target: splitter,
    preventDefault: () => {},
  } as unknown as KeyboardEvent);
  assert.equal(properties.get("--cp-split-primary"), "72%");
  assert.equal(attributes.get("aria-valuenow"), "72");

  listeners.get("keydown")?.({ key: "End", target: splitter, preventDefault: () => {} } as unknown as KeyboardEvent);
  assert.equal(properties.get("--cp-split-primary"), "80%");
  listeners.get("keydown")?.({
    key: "ArrowDown",
    target: splitter,
    preventDefault: () => {},
  } as unknown as KeyboardEvent);
  assert.equal(properties.get("--cp-split-primary"), "80%", "the split must clamp at the maximum");
  listeners.get("keydown")?.({ key: "Home", target: splitter, preventDefault: () => {} } as unknown as KeyboardEvent);
  assert.equal(properties.get("--cp-split-primary"), "70%");

  listeners.get("pointerdown")?.({
    clientY: 500,
    pointerId: 1,
    target: splitter,
    preventDefault: () => {},
  } as unknown as PointerEvent);
  splitter.listeners.get("pointermove")?.({ clientY: 600 } as unknown as Event);
  assert.equal(properties.get("--cp-split-primary"), "60.00%");
  splitter.listeners.get("pointerup")?.({} as unknown as Event);
  assert.equal(attributes.get("aria-valuenow"), "60");
});

test("table and Gantt splitter drags adjust the width split, clamp, and persist on release", () => {
  const { container, listeners } = captureContainer();
  renderMainWorkspace(container as unknown as HTMLElement, resizeLayoutState());
  const properties = new Map<string, string>([["--cp-split-table", "45%"]]);
  const attributes = new Map<string, string>();
  const split = {
    dataset: { splitKey: "cubi:workspace-split:v1:project-1:schedule" },
    style: {
      setProperty: (name: string, value: string) => properties.set(name, value),
      getPropertyValue: (name: string) => properties.get(name) ?? "",
    },
    getBoundingClientRect: () => ({ left: 0, right: 1000, width: 1000 }),
    closest: () => null,
  };
  const splitter = {
    listeners: new Map<string, Listener>(),
    setAttribute: (name: string, value: string) => attributes.set(name, value),
    addEventListener: (type: string, listener: Listener) => splitter.listeners.set(type, listener),
    removeEventListener: (type: string) => splitter.listeners.delete(type),
    setPointerCapture: () => {},
    closest: (selector: string): unknown => {
      if (selector === "[data-panel-splitter]") return splitter;
      if (selector === "[data-panel-split]") return split;
      return null;
    },
  };

  listeners.get("pointerdown")?.({
    clientX: 450,
    pointerId: 1,
    target: splitter,
    preventDefault: () => {},
  } as unknown as PointerEvent);
  splitter.listeners.get("pointermove")?.({ clientX: 600 } as unknown as Event);
  assert.equal(properties.get("--cp-split-table"), "60.00%");
  assert.equal(attributes.get("aria-valuenow"), "60");
  splitter.listeners.get("pointermove")?.({ clientX: 950 } as unknown as Event);
  assert.equal(properties.get("--cp-split-table"), "75.00%", "the split must clamp at the maximum");
  splitter.listeners.get("pointerup")?.({} as unknown as Event);
  assert.equal(attributes.get("aria-valuenow"), "75");
});

test("reset commands restore the default 70/30 and 50/50 splits and the default column widths", () => {
  const { container, listeners } = captureContainer();
  const resets: Array<Readonly<Record<string, number>>> = [];
  renderMainWorkspace(container as unknown as HTMLElement, resizeLayoutState(), {
    onP6ColumnWidthsReset: (widths) => resets.push(widths),
  });
  const properties = new Map<string, string>([["--cp-split-primary", "50%"], ["--cp-split-table", "60%"]]);
  const attributes = new Map<string, string>();
  const split = {
    dataset: { splitKey: "cubi:workspace-split:v1:project-1:schedule" },
    style: {
      setProperty: (name: string, value: string) => properties.set(name, value),
      getPropertyValue: (name: string) => properties.get(name) ?? "",
    },
    querySelector: () => splitter,
  };
  const splitter = {
    dataset: { splitKey: "cubi:workspace-details-split:v1:project-1:schedule" },
    setAttribute: (name: string, value: string) => attributes.set(name, value),
  };
  const main = { style: split.style };
  (container as unknown as { querySelector: (selector: string) => unknown }).querySelector = (selector: string) => {
    if (selector === "[data-panel-split]") return split;
    if (selector === ".cp-main") return main;
    if (selector === "[data-details-splitter]") return splitter;
    return null;
  };
  const click = (dataset: Record<string, string>) => {
    const target = { dataset, closest: (selector: string) => (selector.startsWith("[data-project-settings]") ? target : null) };
    listeners.get("click")?.({ target } as unknown as Event);
  };

  click({ resetDetailsSplit: "" });
  assert.equal(properties.get("--cp-split-primary"), "70%");
  assert.equal(attributes.get("aria-valuenow"), "70");

  click({ resetTableSplit: "" });
  assert.equal(properties.get("--cp-split-table"), "50%");
  assert.equal(attributes.get("aria-valuenow"), "50");

  click({ resetColumnWidths: "" });
  assert.deepEqual(resets, [{ code: 48 }]);
});
