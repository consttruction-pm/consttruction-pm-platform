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
  labelled,
  note,
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

  const listSection = section("Stored records", "Rows are read back from the server after every write. Deleted rows stay recoverable.");
  const listHost = el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") }));
  const deletedToggle = el("input");
  deletedToggle.type = "checkbox";
  const toggleLabel = el("label", { class: "cubi-inline-check" }, deletedToggle, el("span", { text: "Include deleted records" }));
  deletedToggle.addEventListener("change", () => { void load(); });
  const refresh = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.refresh"), attrs: { type: "button" } });
  refresh.addEventListener("click", () => { void load(); });
  sectionBody(listSection, el("div", { class: "cubi-row" }, toggleLabel, refresh), listHost);
  testId(listSection, `${spec.testId}-list`);
  host.append(listSection);

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
        void load();
      })
      .catch((error: unknown) => {
        submit.disabled = false;
        showResult(describe(error), true);
      });
  });

  const load = async (): Promise<void> => {
    probeState = await probe(basePath);
    if (probeState.state !== "available") {
      listHost.replaceChildren(
        sourceState(probeState, ctx.t, {
          title: "This register is not connected",
          source: `Enterprise ${spec.kind} API`,
          retry: () => { void load(); },
        }),
      );
      submit.disabled = true;
      return;
    }
    submit.disabled = false;
    try {
      const items = (await api.enterpriseList(spec.kind, deletedToggle.checked ? { include_deleted: "1" } : {})).items;
      listHost.replaceChildren(items.length ? recordTable(items) : el("p", { class: "cubi-field-hint", text: "The server answered with zero records for this tenant." }));
    } catch (error) {
      submit.disabled = true;
      listHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: describe(error) }));
    }
  };

  const recordTable = (items: EnterpriseRecord[]): HTMLElement => {
    const wrap = el("div", { class: "cubi-table-wrap" });
    testId(wrap, `${spec.testId}-table`);
    const table = el("table", { class: "cubi-table" });
    const head = el("tr", {},
      ...spec.columns.map((column) => el("th", { text: column.label })),
      el("th", { text: ctx.t("common.status") }),
      el("th", { text: ctx.t("common.revision") }),
      el("th", { text: ctx.t("common.actions") }),
    );
    const body = el("tbody");
    for (const item of items) {
      const deleted = Boolean(item.deleted_at);
      const edit = el("button", { class: "cubi-btn cubi-btn-secondary", text: deleted ? "Restore" : "Edit", attrs: { type: "button" } });
      edit.addEventListener("click", () => {
        if (deleted) {
          api.enterpriseRestore(spec.kind, item.record_id, item.revision)
            .then(() => { ctx.toast("Record restored on the server.", "info"); void load(); })
            .catch((error: unknown) => showResult(describe(error), true));
          return;
        }
        fill(item);
      });
      const remove = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Delete", attrs: { type: "button" } });
      remove.disabled = deleted;
      remove.addEventListener("click", () => {
        api.enterpriseDelete(spec.kind, item.record_id, item.revision)
          .then(() => { ctx.toast("Record soft-deleted on the server; it stays recoverable.", "info"); void load(); })
          .catch((error: unknown) => showResult(describe(error), true));
      });
      body.append(el("tr", { class: deleted ? "is-deleted" : undefined },
        ...spec.columns.map((column) => el("td", { text: cellValue(item, column.key) })),
        el("td", {}, badge(deleted ? "deleted" : String(item.status ?? "—"), deleted ? "danger" : item.status === "active" ? "success" : "neutral")),
        el("td", { text: String(item.revision) }),
        el("td", {}, el("div", { class: "cubi-row" }, edit, remove)),
      ));
    }
    table.append(el("thead", {}, head), body);
    wrap.append(table);
    return wrap;
  };

  const capability = section("Connection", "This row reports the server answer for the register route, not a client guess.");
  const capabilityHost = el("div");
  sectionBody(capability, capabilityHost);
  testId(capability, `${spec.testId}-capability`);
  host.append(capability);

  void load().then(() => {
    if (probeState) capabilityHost.replaceChildren(connectionRow(spec.kind, probeState, ctx.t));
  });
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
