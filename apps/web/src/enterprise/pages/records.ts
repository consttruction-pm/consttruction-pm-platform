/**
 * Config-driven record page.
 *
 * Eight register pages share this component, and every one of them uses the same
 * server contract: a tenant-scoped collection with revisions, soft delete,
 * restore and an audit trail. The page renders exactly the fields it is
 * configured with, sends them to the real API and reports what the server
 * answered. It never fabricates a row, a revision or a permission.
 */

import type { PageContext } from "../app.js";
import { api, probe, type EnterpriseRecord, type CapabilityProbe } from "../api.js";
import { badge, el } from "../ui.js";
import {
  connectionRow,
  detailList,
  labelled,
  note,
  projectFilterOptions,
  section,
  sectionBody,
  selectControl,
  sourceState,
  testId,
  textArea,
  textInput,
} from "./shared.js";

export type FieldKind = "text" | "number" | "date" | "select" | "textarea";

export type RecordField = {
  name: string;
  label: string;
  kind?: FieldKind;
  required?: boolean;
  placeholder?: string;
  hint?: string;
  options?: { value: string; label: string }[];
  min?: string;
  max?: string;
  step?: string;
};

export type RecordPageSpec = {
  kind: string;
  testId: string;
  description: string;
  note?: string;
  help: { topic: string; url: string };
  fields: RecordField[];
  columns: { key: string; label: string }[];
  statusOptions?: string[];
  /** Field names that carry JSON and must be parsed before the request. */
  jsonFields?: string[];
};

function cellValue(record: EnterpriseRecord, key: string): string {
  const value = record[key];
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return `${value.length} item${value.length === 1 ? "" : "s"}`;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function fieldControl(field: RecordField, value: string): HTMLElement {
  if (field.kind === "textarea") return textArea({ placeholder: field.placeholder, value, rows: 3 });
  if (field.kind === "select") {
    const control = selectControl(field.options ?? [], value, () => {});
    return control;
  }
  const input = textInput({
    type: field.kind ?? "text",
    placeholder: field.placeholder,
    value,
    name: field.name,
    required: field.required,
  });
  if (field.min !== undefined) input.min = field.min;
  if (field.max !== undefined) input.max = field.max;
  if (field.step !== undefined) input.step = field.step;
  return input;
}

export function renderRecordPage(ctx: PageContext, host: HTMLElement, spec: RecordPageSpec): void {
  const basePath = `/api/enterprise/${spec.kind}`;
  let probeState: CapabilityProbe | null = null;

  const intro = section(spec.description);
  const help = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open the Help topic", attrs: { target: "_blank", rel: "noopener noreferrer" } });
  help.href = spec.help.url;
  sectionBody(intro,
    el("p", { class: "cubi-field-hint", text: `Help topic: ${spec.help.topic}` }),
    spec.note ? note(spec.note, "warning") : null,
    el("div", { class: "cubi-row" }, help),
  );
  testId(intro, `${spec.testId}-intro`);
  host.append(intro);

  const formSection = section("Record", "Every write carries a revision guard; the server rejects stale edits and records the actor.");
  const form = el("form", { class: "cubi-form-grid" });
  const inputs = new Map<string, HTMLElement>();
  for (const field of spec.fields) {
    const control = fieldControl(field, field.options?.[0]?.value ?? "");
    inputs.set(field.name, control);
    form.append(labelled(field.label, control, field.hint));
  }
  if (spec.statusOptions) {
    const status = selectControl(spec.statusOptions.map((value) => ({ value, label: value })), spec.statusOptions[0], () => {});
    inputs.set("status", status);
    form.append(labelled("Status", status, "Saved with the record."));
  }
  const submit = testId(el("button", { class: "cubi-btn cubi-btn-primary", text: "Create record", attrs: { type: "submit" } }), `${spec.testId}-submit`);
  const cancel = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Cancel edit", attrs: { type: "button", hidden: "hidden" } });
  const result = testId(el("p", { class: "cubi-alert cubi-alert-info", attrs: { role: "status", hidden: "hidden" } }), `${spec.testId}-result`);
  form.append(result, el("div", { class: "cubi-row" }, submit, cancel));
  sectionBody(formSection, form);
  testId(formSection, `${spec.testId}-form`);
  host.append(formSection);

  let editing: EnterpriseRecord | null = null;
  const values = (): Record<string, unknown> => {
    const body: Record<string, unknown> = {};
    for (const field of spec.fields) {
      const control = inputs.get(field.name) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | undefined;
      if (!control) continue;
      const raw = control.value;
      if (field.kind === "number") {
        if (raw.trim() === "") continue;
        body[field.name] = Number(raw);
      } else {
        body[field.name] = raw.trim();
      }
    }
    if (spec.statusOptions) {
      const status = inputs.get("status") as HTMLSelectElement | undefined;
      if (status) body.status = status.value;
    }
    for (const name of spec.jsonFields ?? []) {
      const raw = String(body[name] ?? "").trim();
      if (!raw) continue;
      body[name] = JSON.parse(raw);
    }
    return body;
  };
  const fill = (record: EnterpriseRecord | null): void => {
    editing = record;
    for (const field of spec.fields) {
      const control = inputs.get(field.name) as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | undefined;
      if (!control) continue;
      const value = record ? record[field.name] : undefined;
      control.value = value === null || value === undefined
        ? ""
        : (spec.jsonFields ?? []).includes(field.name)
          ? JSON.stringify(value, null, 1)
          : String(value);
    }
    if (spec.statusOptions) {
      const status = inputs.get("status") as HTMLSelectElement | undefined;
      if (status) status.value = String(record?.status ?? spec.statusOptions[0]);
    }
    submit.textContent = record ? "Save changes" : "Create record";
    cancel.hidden = !record;
    formSection.scrollIntoView({ block: "nearest" });
  };
  cancel.addEventListener("click", () => {
    fill(null);
    result.hidden = true;
  });

  const showResult = (message: string, error: boolean): void => {
    result.textContent = message;
    result.className = `cubi-alert ${error ? "cubi-alert-error" : "cubi-alert-info"}`;
    result.hidden = false;
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    let body: Record<string, unknown>;
    try {
      body = values();
    } catch (error) {
      showResult(`The form contains invalid JSON: ${error instanceof Error ? error.message : String(error)}`, true);
      return;
    }
    for (const field of spec.fields) {
      if (!field.required) continue;
      const value = body[field.name];
      if (value === undefined || value === "" || (typeof value === "number" && Number.isNaN(value))) {
        showResult(`${field.label} is required.`, true);
        return;
      }
    }
    const target = editing;
    submit.disabled = true;
    const run = target
      ? api.enterpriseUpdate(spec.kind, target.record_id, { ...body, expected_revision: target.revision })
      : api.enterpriseCreate(spec.kind, body, newKey());
    run
      .then((payload) => {
        submit.disabled = false;
        showResult(target ? `Saved as revision ${payload.record.revision}.` : `Created ${payload.record.record_id}.`, false);
        ctx.toast(target ? "Record saved on the server." : "Record created on the server.", "info");
        fill(null);
        void reload();
      })
      .catch((error: unknown) => {
        submit.disabled = false;
        showResult(describe(error), true);
      });
  });

  const listSection = section(
    "Stored records",
    "Rows are read back from the server after every write. Filters are applied by the server; sorting, selection and export apply to the loaded page.",
  );
  const listHost = el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") }));
  const countLabel = el("span", { class: "cubi-field-hint", attrs: { "aria-live": "polite" } });

  const searchInput = textInput({ type: "search", placeholder: "Search records" });
  searchInput.setAttribute("aria-label", "Search records");
  const statusOptions = (spec.statusOptions ?? []).map((value) => ({ value, label: value }));
  const statusFilter = selectControl([{ value: "", label: "All statuses" }, ...statusOptions], "", () => { void reload(); });
  statusFilter.setAttribute("aria-label", "Filter by status");
  const projectFilter = selectControl(
    projectFilterOptions(ctx.projects, ctx.sharedProjects ?? [], "All projects"),
    "",
    () => { void reload(); },
  );
  projectFilter.setAttribute("aria-label", "Filter by project");
  const includeDeleted = el("input");
  includeDeleted.type = "checkbox";
  const toggleLabel = el("label", { class: "cubi-inline-check" }, includeDeleted, el("span", { text: "Include deleted" }));
  includeDeleted.addEventListener("change", () => { void reload(); });

  const refresh = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.refresh"), attrs: { type: "button" } });
  refresh.addEventListener("click", () => { void reload(); });
  const exportButton = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Export CSV", attrs: { type: "button" } });
  exportButton.disabled = true;
  const printButton = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Print", attrs: { type: "button" } });
  printButton.addEventListener("click", () => window.print());

  const toolbar = el("div", { class: "cubi-toolbar" },
    searchInput,
    statusFilter,
    projectFilter,
    toggleLabel,
    el("div", { class: "cubi-toolbar-group" }, refresh, exportButton, printButton),
  );
  const detailHost = el("div", { class: "cubi-detail-panel", attrs: { hidden: "hidden" } });
  sectionBody(listSection, toolbar, countLabel, listHost, detailHost);
  testId(listSection, `${spec.testId}-list`);
  host.append(listSection);

  let loaded: EnterpriseRecord[] = [];
  let sortKey: string | null = null;
  let sortDirection: 1 | -1 = 1;
  let selectedId: string | null = null;
  const selected = new Set<string>();
  let menu: HTMLElement | null = null;
  let lastFocusedRow: HTMLElement | null = null;

  const sorted = (): EnterpriseRecord[] => sortRecords(loaded, sortKey, sortDirection, ctx.locale);

  const closeMenu = (restoreFocus = true): void => {
    if (!menu) return;
    menu.remove();
    menu = null;
    if (restoreFocus) lastFocusedRow?.focus();
  };

  const openMenu = (record: EnterpriseRecord, x: number, y: number): void => {
    closeMenu(false);
    const deleted = Boolean(record.deleted_at);
    menu = el("div", { class: "cubi-context-menu", attrs: { role: "menu", "aria-label": "Record actions" } });
    const item = (label: string, run: () => void): void => {
      const entry = el("button", { class: "cubi-context-item", text: label, attrs: { type: "button", role: "menuitem" } });
      entry.addEventListener("click", () => { closeMenu(); run(); });
      menu?.append(entry);
    };
    item("Open details", () => selectRecord(record.record_id));
    if (deleted) {
      item("Restore record", () => restoreRecord(record));
    } else {
      item("Edit record", () => fill(record));
      item("Delete record", () => deleteRecord(record));
    }
    item("Refresh", () => { void reload(); });
    menu.style.position = "fixed";
    menu.style.left = `${Math.min(x, window.innerWidth - 220)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - 180)}px`;
    menu.dataset.recordId = record.record_id;
    document.body.append(menu);
    (menu.querySelector("button") as HTMLButtonElement | null)?.focus();
  };

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu) {
      event.preventDefault();
      closeMenu();
      return;
    }
    if (event.key === "Escape" && !detailHost.hidden) {
      detailHost.hidden = true;
      selectedId = null;
      lastFocusedRow?.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (menu && !menu.contains(event.target as Node)) closeMenu(false);
  });
  window.addEventListener("scroll", () => closeMenu(false), { passive: true });

  const selectRecord = (id: string): void => {
    selectedId = id;
    renderDetail();
  };

  const renderDetail = (): void => {
    const record = loaded.find((item) => item.record_id === selectedId) ?? null;
    if (!record) {
      detailHost.hidden = true;
      detailHost.replaceChildren();
      return;
    }
    const deleted = Boolean(record.deleted_at);
    const rows: [string, string][] = [
      ["Record", record.record_id],
      ["Kind", record.kind],
      ["Status", String(record.status ?? "—")],
      ["Revision", String(record.revision)],
      ["Created", String(record.created_at ?? "—")],
      ["Updated", String(record.updated_at ?? "—")],
      ["Deleted", deleted ? String(record.deleted_at) : "No"],
    ];
    for (const field of spec.fields) {
      const value = record[field.name];
      rows.push([field.label, value === null || value === undefined ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value)]);
    }
    const actions = el("div", { class: "cubi-row" });
    if (!deleted) {
      actions.append(
        el("button", { class: "cubi-btn cubi-btn-primary", text: "Edit", attrs: { type: "button" }, }) as HTMLButtonElement,
      );
    }
    const close = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Close details", attrs: { type: "button" } });
    close.addEventListener("click", () => { detailHost.hidden = true; selectedId = null; lastFocusedRow?.focus(); });
    if (!deleted) {
      (actions.firstElementChild as HTMLButtonElement).addEventListener("click", () => fill(record));
    }
    actions.append(close);
    detailHost.replaceChildren(
      el("div", { class: "cubi-spread" }, el("h3", { text: "Record details" }), badge(deleted ? "deleted" : String(record.status ?? "active"), deleted ? "danger" : "info")),
      detailList(rows),
      actions,
    );
    detailHost.hidden = false;
  };

  const deleteRecord = (record: EnterpriseRecord): void => {
    api.enterpriseDelete(spec.kind, record.record_id, record.revision)
      .then(() => { ctx.toast("Record soft-deleted on the server; it stays recoverable.", "info"); void reload(); })
      .catch((error: unknown) => showResult(describe(error), true));
  };

  const restoreRecord = (record: EnterpriseRecord): void => {
    api.enterpriseRestore(spec.kind, record.record_id, record.revision)
      .then(() => { ctx.toast("Record restored on the server.", "info"); void reload(); })
      .catch((error: unknown) => showResult(describe(error), true));
  };

  const exportCsv = (): void => {
    const rows = selected.size ? sorted().filter((item) => selected.has(item.record_id)) : sorted();
    if (!rows.length) return;
    const columns: [string, (item: EnterpriseRecord) => string][] = [
      ["record_id", (item) => item.record_id],
      ...spec.columns.map((column): [string, (item: EnterpriseRecord) => string] => [
        column.label,
        (item) => cellValue(item, column.key),
      ]),
      ["status", (item) => String(item.status ?? "")],
      ["revision", (item) => String(item.revision)],
      ["created_at", (item) => String(item.created_at ?? "")],
      ["updated_at", (item) => String(item.updated_at ?? "")],
    ];
    const blob = new Blob([recordsToCsv(rows, columns)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${spec.kind}-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  exportButton.addEventListener("click", exportCsv);

  const recordTable = (items: EnterpriseRecord[]): HTMLElement => {
    const wrap = el("div", { class: "cubi-table-wrap" });
    testId(wrap, `${spec.testId}-table`);
    const table = el("table", { class: "cubi-table", attrs: { role: "grid", "aria-label": `${spec.kind} records` } });
    const headerCell = (key: string, label: string): HTMLElement => {
      const active = sortKey === key;
      const th = el("th", {
        attrs: {
          scope: "col",
          tabindex: "0",
          "aria-sort": active ? (sortDirection === 1 ? "ascending" : "descending") : "none",
        },
      }, el("span", { text: label }), el("span", { class: "cubi-sort", text: active ? (sortDirection === 1 ? " ▲" : " ▼") : " ↕" }));
      const toggle = (): void => {
        if (sortKey !== key) { sortKey = key; sortDirection = 1; }
        else if (sortDirection === 1) sortDirection = -1;
        else { sortKey = null; sortDirection = 1; }
        renderRows();
      };
      th.addEventListener("click", toggle);
      th.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); }
      });
      return th;
    };
    const checkAll = el("input");
    checkAll.type = "checkbox";
    checkAll.setAttribute("aria-label", "Select all records on this page");
    checkAll.addEventListener("change", () => {
      selected.clear();
      if (checkAll.checked) for (const item of sorted()) selected.add(item.record_id);
      renderRows();
    });
    const head = el("tr", {},
      el("th", { class: "cubi-select-col", attrs: { scope: "col" } }, checkAll),
      ...spec.columns.map((column) => headerCell(column.key, column.label)),
      el("th", { text: ctx.t("common.status"), attrs: { scope: "col" } }),
      el("th", { text: ctx.t("common.revision"), attrs: { scope: "col" } }),
      el("th", { text: ctx.t("common.actions"), attrs: { scope: "col" } }),
    );
    const body = el("tbody");
    table.append(el("thead", {}, head), body);
    wrap.append(table);

    function renderRows(): void {
      body.replaceChildren();
      const rows = sorted();
      for (const item of rows) {
        const deleted = Boolean(item.deleted_at);
        const isSelected = item.record_id === selectedId;
        const check = el("input");
        check.type = "checkbox";
        check.checked = selected.has(item.record_id);
        check.setAttribute("aria-label", `Select ${String(item.record_id)}`);
        check.addEventListener("change", () => {
          if (check.checked) selected.add(item.record_id); else selected.delete(item.record_id);
          exportButton.disabled = !loaded.length;
        });
        const edit = el("button", { class: "cubi-btn cubi-btn-secondary", text: deleted ? "Restore" : "Edit", attrs: { type: "button" } });
        edit.addEventListener("click", () => { deleted ? restoreRecord(item) : fill(item); });
        const remove = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Delete", attrs: { type: "button" } });
        remove.disabled = deleted;
        remove.addEventListener("click", () => deleteRecord(item));
        const row = el("tr", {
          class: [deleted ? "is-deleted" : "", isSelected ? "is-selected" : ""].filter(Boolean).join(" ") || undefined,
          attrs: { tabindex: "0", "aria-selected": isSelected ? "true" : "false" },
        },
          el("td", { class: "cubi-select-col" }, check),
          ...spec.columns.map((column) => el("td", { text: cellValue(item, column.key) })),
          el("td", {}, badge(deleted ? "deleted" : String(item.status ?? "—"), deleted ? "danger" : item.status === "active" ? "success" : "neutral")),
          el("td", { text: String(item.revision) }),
          el("td", {}, el("div", { class: "cubi-row" }, edit, remove)),
        );
        row.addEventListener("click", (event) => {
          if ((event.target as HTMLElement).closest("button,input")) return;
          lastFocusedRow = row;
          selectRecord(item.record_id);
        });
        row.addEventListener("contextmenu", (event) => {
          event.preventDefault();
          lastFocusedRow = row;
          selectRecord(item.record_id);
          openMenu(item, event.clientX, event.clientY);
        });
        row.addEventListener("keydown", (event) => {
          if (event.key === "Enter") { event.preventDefault(); selectRecord(item.record_id); }
          else if (event.key === "Shift+F10" || event.key === "ContextMenu") {
            event.preventDefault();
            lastFocusedRow = row;
            const box = row.getBoundingClientRect();
            openMenu(item, box.left + 24, box.top + 18);
          } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            const next = event.key === "ArrowDown" ? row.nextElementSibling : row.previousElementSibling;
            (next as HTMLElement | null)?.focus();
          } else if (event.key === " ") {
            event.preventDefault();
            check.checked = !check.checked;
            check.dispatchEvent(new Event("change"));
          }
        });
        body.append(row);
      }
      if (!rows.length) {
        body.append(el("tr", {}, el("td", { attrs: { colspan: String(spec.columns.length + 4) } },
          el("div", { class: "cubi-empty-inline", text: "No records match the current filters." }))));
      }
      countLabel.textContent = `${rows.length} of ${loaded.length} record${loaded.length === 1 ? "" : "s"} shown`;
      exportButton.disabled = !loaded.length;
      checkAll.checked = rows.length > 0 && rows.every((item) => selected.has(item.record_id));
      if (selectedId && !loaded.some((item) => item.record_id === selectedId)) selectedId = null;
      renderDetail();
    }

    renderRows();
    return wrap;
  };
  let tableHost: HTMLElement | null = null;

  const reload = async (): Promise<void> => {
    probeState = await probe(basePath);
    if (probeState.state !== "available") {
      listHost.replaceChildren(
        sourceState(probeState, ctx.t, {
          title: "This register is not connected",
          source: `Enterprise ${spec.kind} API`,
          retry: () => { void reload(); },
        }),
      );
      submit.disabled = true;
      return;
    }
    submit.disabled = false;
    try {
      const query: Record<string, string> = {};
      if (searchInput.value.trim()) query.q = searchInput.value.trim();
      if (statusFilter.value) query.status = statusFilter.value;
      if (projectFilter.value) query.project_id = projectFilter.value;
      if (includeDeleted.checked) query.include_deleted = "1";
      loaded = (await api.enterpriseList(spec.kind, query)).items;
      selectedId = null;
      const nextTable = recordTable(loaded);
      if (tableHost) tableHost.replaceWith(nextTable);
      else listHost.replaceChildren(nextTable);
      tableHost = nextTable;
      countLabel.textContent = `${loaded.length} record${loaded.length === 1 ? "" : "s"} returned by the server`;
      exportButton.disabled = !loaded.length;
    } catch (error) {
      submit.disabled = true;
      listHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: describe(error) }));
    }
  };

  let searchTimer: number | undefined;
  searchInput.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => { void reload(); }, 250);
  });

  const capability = section("Connection", "This row reports the server answer for the register route, not a client guess.");
  const capabilityHost = el("div");
  sectionBody(capability, capabilityHost);
  testId(capability, `${spec.testId}-capability`);
  host.append(capability);

  void reload().then(() => {
    if (probeState) capabilityHost.replaceChildren(connectionRow(spec.kind, probeState, ctx.t));
  });
}

/** Sort the loaded page by one column; ties keep the server order. */
export function sortRecords<T extends Record<string, unknown>>(
  items: readonly T[],
  key: string | null,
  direction: 1 | -1,
  locale: string,
): T[] {
  if (!key) return [...items];
  return [...items].sort((left, right) => {
    const a = left[key];
    const b = right[key];
    return String(a ?? "").localeCompare(String(b ?? ""), locale) * direction;
  });
}

/**
 * Serialise the current rows to CSV with a BOM for Excel. Every value is
 * quoted, so commas, quotes and newlines in tenant data stay intact.
 */
export function recordsToCsv(
  rows: readonly Record<string, unknown>[],
  columns: readonly [string, (item: never) => string][],
): string {
  const quote = (value: string): string => `"${value.replace(/"/g, '""')}"`;
  const lines = [columns.map(([label]) => quote(label)).join(",")];
  for (const row of rows) {
    lines.push(columns.map(([, read]) => quote(read(row as never))).join(","));
  }
  return "\uFEFF" + lines.join("\r\n");
}

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `rec-${Date.now()}`;
}

function describe(error: unknown): string {
  const record = error as { status?: number; code?: string; message?: string };
  if (typeof record?.status === "number") {
    if (record.status === 403) return `The server denied this write (${record.code}). Your session does not hold the required Enterprise role.`;
    if (record.status === 409) return `The server rejected the write as stale (${record.code}). Re-read the record and try again.`;
    if (record.status === 400) return `The server rejected the payload (${record.code}).`;
    return `The server answered ${record.status} (${record.code}).`;
  }
  return error instanceof Error ? error.message : String(error);
}
