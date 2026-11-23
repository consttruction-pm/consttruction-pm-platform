/**
 * Shared page building blocks.
 *
 * These helpers only compose local DOM. They never decide authority: a
 * capability badge reports what the server answered for a path, and a
 * "restricted" state is a fact about the server response, not a client gate.
 */

import type { CapabilityProbe } from "../api.js";
import type { EnterpriseLocale } from "../i18n.js";
import { badge, el, stateBlock, type Translator } from "../ui.js";

export type Tone = "neutral" | "success" | "warning" | "danger" | "info";

export function section(title: string, description?: string, actions: HTMLElement[] = []): HTMLElement {
  const node = el("section", { class: "cubi-card" });
  const head = el("header", { class: "cubi-card-head" });
  const titles = el("div", { class: "cubi-card-titles" });
  titles.append(el("h2", { class: "cubi-card-title", text: title }));
  if (description) titles.append(el("p", { class: "desc", text: description }));
  head.append(titles);
  if (actions.length) head.append(el("div", { class: "cubi-card-actions" }, ...actions));
  node.append(head);
  return node;
}

export function sectionBody(node: HTMLElement, ...children: (Node | string | null | undefined)[]): HTMLElement {
  const body = el("div", { class: "cubi-card-body" });
  for (const child of children) {
    if (child === null || child === undefined) continue;
    body.append(child);
  }
  node.append(body);
  return node;
}

export function pageActions(...items: (Node | null)[]): HTMLElement {
  return el("div", { class: "cubi-page-actions" }, ...items.filter((item): item is Node => Boolean(item)));
}

export function detailList(rows: [string, string | Node | null | undefined][]): HTMLElement {
  const list = el("dl", { class: "cubi-kv" });
  for (const [key, value] of rows) {
    list.append(el("dt", { text: key }));
    const dd = el("dd");
    if (value === null || value === undefined) dd.textContent = "—";
    else if (typeof value === "string") dd.textContent = value;
    else dd.append(value);
    list.append(dd);
  }
  return list;
}

export function sourceStamp(source: string, revision: number | string | null | undefined, updated: string | null | undefined, locale: EnterpriseLocale): HTMLElement {
  const parts = [`Source: ${source}`, `Revision: ${revision ?? "—"}`, `Updated: ${updated ? formatStamp(updated, locale) : "—"}`];
  return el("p", { class: "cubi-note", text: parts.join(" · ") });
}

export function formatStamp(iso: string, locale: EnterpriseLocale): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(parsed);
  } catch {
    return new Date(parsed).toISOString().slice(0, 16).replace("T", " ");
  }
}

export function capabilityLabel(probe: CapabilityProbe, t: Translator): string {
  if (probe.state === "available") return t("common.connected");
  if (probe.state === "forbidden") return t("common.forbidden");
  if (probe.state === "unauthenticated") return "Session required";
  if (probe.state === "unavailable" || probe.state === "source_unavailable") return t("common.notConnected");
  return t("common.error");
}

export function capabilityTone(probe: CapabilityProbe): Tone {
  if (probe.state === "available") return "success";
  if (probe.state === "forbidden") return "warning";
  if (probe.state === "unavailable" || probe.state === "source_unavailable") return "neutral";
  return "danger";
}

export function capabilityChip(probe: CapabilityProbe, t: Translator): HTMLElement {
  return badge(capabilityLabel(probe, t), capabilityTone(probe));
}

export function connectionRow(label: string, probe: CapabilityProbe, t: Translator): HTMLElement {
  return el(
    "div",
    { class: "cubi-conn-row" },
    el("span", {}, el("strong", { text: label }), el("span", { class: "path", text: " " + probe.path })),
    el("span", {}, badge(`${probe.status || "—"}`, probe.state === "available" ? "success" : probe.state === "forbidden" ? "warning" : probe.state === "unavailable" || probe.state === "source_unavailable" ? "neutral" : "danger"), el("span", { text: " " }), capabilityChip(probe, t)),
  );
}

export function connectionList(entries: { label: string; probe: CapabilityProbe }[], t: Translator): HTMLElement {
  return el("div", { class: "cubi-conn" }, ...entries.map((entry) => connectionRow(entry.label, entry.probe, t)));
}

/**
 * Explain why a source cannot be shown. This is the honest fallback for every
 * Enterprise capability whose server route is not installed in this build.
 */
export function sourceState(
  probe: CapabilityProbe,
  t: Translator,
  options: { title: string; source: string; detail?: string; retry?: () => void },
): HTMLElement {
  const endpoint = `GET ${probe.path} · ${probe.code || "—"}`;
  if (probe.state === "available") {
    return stateBlock("empty", options.title, options.detail ?? "The source responded, but returned no records for this view.");
  }
  if (probe.state === "forbidden") {
    return stateBlock(
      "forbidden",
      options.title,
      `${t("common.forbidden")} The server denied ${probe.path}. ${options.detail ?? ""}`.trim(),
    );
  }
  if (probe.state === "unauthenticated") {
    return stateBlock("forbidden", options.title, `The server requires a valid session for ${probe.path}.`);
  }
  if (probe.state === "source_unavailable") {
    return stateBlock(
      "unavailable",
      options.title,
      `${t("common.notConnected")} — ${options.source} is mounted but the Engineering source it reports from is not connected (${endpoint}). No value is derived or substituted. ${options.detail ?? ""}`.trim(),
      options.retry ? [retryButton(options.retry, t)] : [],
    );
  }
  if (probe.state === "unavailable") {
    return stateBlock(
      "unavailable",
      options.title,
      `${t("common.notConnected")} — ${options.source} has no registered route on this server (${endpoint}). The page will show real data as soon as the contract is mounted; nothing is fabricated here. ${options.detail ?? ""}`.trim(),
      options.retry ? [retryButton(options.retry, t)] : [],
    );
  }
  return stateBlock(
    "error",
    options.title,
    `The request to ${probe.path} failed (${endpoint}). ${options.detail ?? ""}`.trim(),
    options.retry ? [retryButton(options.retry, t)] : [],
  );
}

export function retryButton(retry: () => void, t: Translator): HTMLElement {
  const node = el("button", { class: "cubi-btn cubi-btn-secondary", text: t("common.retry"), attrs: { type: "button" } });
  node.addEventListener("click", retry);
  return node;
}

export function note(text: string, tone: "info" | "warning" | "neutral" = "neutral"): HTMLElement {
  return el("div", { class: `cubi-alert ${tone === "warning" ? "cubi-alert-error" : "cubi-alert-info"}`, attrs: { role: "note" } }, el("span", { text }));
}

export function mono(text: string): HTMLElement {
  return el("span", { class: "cubi-mono", text });
}

export function emptyLine(text: string): HTMLElement {
  return el("p", { class: "cubi-empty-line", text });
}

export function testId<T extends HTMLElement>(node: T, id: string): T {
  node.dataset.testid = id;
  return node;
}

export function labelled(label: string, control: HTMLElement, hint?: string): HTMLElement {
  const wrapper = el("label", { class: "cubi-field" });
  wrapper.append(el("span", { class: "cubi-field-label", text: label }), control);
  if (hint) wrapper.append(el("span", { class: "cubi-field-hint", text: hint }));
  return wrapper;
}

export function selectControl(options: { value: string; label: string; disabled?: boolean; group?: string }[], selected: string, onChange: (value: string) => void): HTMLSelectElement {
  const control = el("select", { class: "cubi-input" });
  let activeGroup: string | null = null;
  let target: HTMLElement = control;
  for (const option of options) {
    if ((option.group ?? null) !== activeGroup) {
      activeGroup = option.group ?? null;
      if (activeGroup) {
        const group = document.createElement("optgroup");
        group.label = activeGroup;
        control.append(group);
        target = group;
      } else {
        target = control;
      }
    }
    const item = el("option", { text: option.label });
    item.value = option.value;
    if (option.disabled) item.disabled = true;
    if (option.value === selected) item.selected = true;
    target.append(item);
  }
  control.addEventListener("change", () => onChange(control.value));
  return control;
}

export function projectFilterOptions(
  personalProjects: { project_id: string; name: string }[],
  sharedProjects: { project_id: string; name: string }[],
  emptyLabel: string,
): { value: string; label: string; group?: string }[] {
  return [
    { value: "", label: emptyLabel },
    ...personalProjects.map((project) => ({
      value: project.project_id, label: project.name, group: "User projects",
    })),
    ...sharedProjects.map((project) => ({
      value: project.project_id, label: project.name, group: "Shared build workspace",
    })),
  ];
}

export function textInput(options: { type?: string; placeholder?: string; value?: string; name?: string; required?: boolean; maxLength?: number; autocomplete?: string } = {}): HTMLInputElement {
  const input = el("input", { class: "cubi-input" });
  input.type = options.type ?? "text";
  if (options.placeholder) input.placeholder = options.placeholder;
  if (options.value !== undefined) input.value = options.value;
  if (options.name) input.name = options.name;
  if (options.required) input.required = true;
  if (options.maxLength) input.maxLength = options.maxLength;
  if (options.autocomplete) input.setAttribute("autocomplete", options.autocomplete);
  return input;
}

export function textArea(options: { placeholder?: string; rows?: number; value?: string } = {}): HTMLTextAreaElement {
  const input = el("textarea", { class: "cubi-input cubi-textarea" });
  input.rows = options.rows ?? 3;
  if (options.placeholder) input.placeholder = options.placeholder;
  if (options.value !== undefined) input.value = options.value;
  return input;
}

export function renderProjectOptions(projects: { project_id: string; name: string }[], selected: string): { value: string; label: string }[] {
  return [{ value: "", label: "All accessible projects" }, ...projects.map((project) => ({ value: project.project_id, label: project.name }))].map((option) => ({ ...option, disabled: false, ...(option.value === selected ? {} : {}) }));
}

/** Device-local preference helper; every caller must label the value as local-only. */
export function readLocalJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function writeLocalJson(key: string, value: unknown): boolean {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
