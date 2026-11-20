/**
 * Small, dependency-free Enterprise UI kit.
 *
 * All content is inserted with textContent (never innerHTML) so server strings
 * cannot become markup. Every page uses the same state vocabulary:
 * loading, empty, error, forbidden and unavailable.
 */

import type { CapabilityProbe } from "./api.js";
import type { EnterpriseLocale } from "./i18n.js";

export type Translator = (key: string, vars?: Record<string, string | number>) => string;

type Props = {
  class?: string;
  text?: string;
  title?: string;
  attrs?: Record<string, string>;
  dataset?: Record<string, string>;
};

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props?: Props,
  ...children: (Node | string | null | undefined)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (props?.class) node.className = props.class;
  if (props?.text !== undefined) node.textContent = props.text;
  if (props?.title) node.title = props.title;
  if (props?.attrs) {
    for (const [name, value] of Object.entries(props.attrs)) node.setAttribute(name, value);
  }
  if (props?.dataset) {
    for (const [name, value] of Object.entries(props.dataset)) node.dataset[name] = value;
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

export function clear(node: HTMLElement): void {
  node.replaceChildren();
}

export function link(href: string, text: string, className = "cubi-link"): HTMLAnchorElement {
  const anchor = el("a", { class: className, text });
  anchor.href = href;
  return anchor;
}

export function icon(name: "dashboard" | "portfolio" | "projects" | "access" | "tasks" | "workflow" | "approval" | "resource" | "report" | "knowledge" | "home" | "logout" | "plus" | "refresh" | "arrow" | "chevron" | "search" | "lock" | "check" | "info" | "warning"): HTMLSpanElement {
  const span = el("span", { class: `cubi-icon cubi-icon-${name}`, attrs: { "aria-hidden": "true" } });
  span.textContent = "";
  return span;
}

export function badge(text: string, tone: "neutral" | "success" | "warning" | "danger" | "info" = "neutral"): HTMLSpanElement {
  return el("span", { class: `cubi-badge cubi-badge-${tone}`, text });
}

export function button(
  label: string,
  onClick: () => void,
  options: { variant?: "primary" | "secondary" | "ghost" | "danger"; disabled?: boolean; type?: "button" | "submit"; testId?: string } = {},
): HTMLButtonElement {
  const node = el("button", {
    class: `cubi-btn cubi-btn-${options.variant ?? "secondary"}`,
    text: label,
    attrs: { type: options.type ?? "button" },
  });
  if (options.disabled) node.disabled = true;
  if (options.testId) node.dataset.testid = options.testId;
  node.addEventListener("click", onClick);
  return node;
}

export function stateBlock(
  kind: "loading" | "empty" | "error" | "forbidden" | "unavailable",
  title: string,
  message: string,
  actions: HTMLElement[] = [],
): HTMLDivElement {
  const block = el("div", { class: `cubi-state cubi-state-${kind}`, attrs: { role: kind === "error" ? "alert" : "status" } });
  block.append(
    el("div", { class: "cubi-state-mark", text: kind === "loading" ? "" : kind === "empty" ? "–" : kind === "forbidden" ? "!" : kind === "unavailable" ? "∅" : "!" }),
    el("div", { class: "cubi-state-body" },
      el("strong", { text: title }),
      el("p", { text: message }),
      actions.length ? el("div", { class: "cubi-state-actions" }, ...actions) : null,
    ),
  );
  if (kind === "loading") block.querySelector(".cubi-state-mark")?.classList.add("cubi-spinner");
  return block;
}

export function spinner(): HTMLDivElement {
  return el("div", { class: "cubi-loading", attrs: { role: "status", "aria-live": "polite" } },
    el("div", { class: "cubi-spinner" }),
    el("span", { text: "" }),
  );
}

export function card(
  title: string | null,
  body: Node | null,
  options: { eyebrow?: string; actions?: HTMLElement[]; className?: string; testId?: string } = {},
): HTMLElement {
  const node = el("section", { class: `cubi-card ${options.className ?? ""}`.trim() });
  if (options.testId) node.dataset.testid = options.testId;
  if (title || options.actions?.length) {
    const head = el("header", { class: "cubi-card-head" });
    const titles = el("div", { class: "cubi-card-titles" });
    if (options.eyebrow) titles.append(el("span", { class: "cubi-eyebrow", text: options.eyebrow }));
    if (title) titles.append(el("h2", { class: "cubi-card-title", text: title }));
    head.append(titles);
    if (options.actions?.length) head.append(el("div", { class: "cubi-card-actions" }, ...options.actions));
    node.append(head);
  }
  if (body) node.append(el("div", { class: "cubi-card-body" }, body));
  return node;
}

export function statCard(label: string, value: string, meta?: string, tone?: "neutral" | "success" | "warning" | "danger"): HTMLElement {
  const node = el("div", { class: `cubi-stat ${tone ? `cubi-stat-${tone}` : ""}`.trim() });
  node.append(
    el("span", { class: "cubi-stat-label", text: label }),
    el("strong", { class: "cubi-stat-value", text: value }),
  );
  if (meta) node.append(el("span", { class: "cubi-stat-meta", text: meta }));
  return node;
}

export function field(
  label: string,
  control: HTMLElement,
  options: { hint?: string; required?: boolean; testId?: string; id?: string } = {},
): HTMLElement {
  const wrapper = el("label", { class: "cubi-field" });
  if (options.testId) wrapper.dataset.testid = options.testId;
  const id = options.id ?? `cubi-field-${Math.random().toString(36).slice(2, 9)}`;
  control.id = control.id || id;
  wrapper.append(
    el("span", { class: "cubi-field-label" }, label, options.required ? el("em", { text: " *", attrs: { "aria-hidden": "true" } }) : null),
    control,
  );
  if (options.hint) wrapper.append(el("span", { class: "cubi-field-hint", text: options.hint }));
  return wrapper;
}

export function input(
  type: string,
  name: string,
  options: { value?: string; placeholder?: string; autocomplete?: string; required?: boolean; maxLength?: number } = {},
): HTMLInputElement {
  const node = el("input", { class: "cubi-input" });
  node.type = type;
  node.name = name;
  if (options.value !== undefined) node.value = options.value;
  if (options.placeholder) node.placeholder = options.placeholder;
  if (options.autocomplete) node.setAttribute("autocomplete", options.autocomplete);
  if (options.required) node.required = true;
  if (options.maxLength) node.maxLength = options.maxLength;
  return node;
}

export function select(
  name: string,
  options: { value: string; label: string; disabled?: boolean }[],
  selected?: string,
): HTMLSelectElement {
  const node = el("select", { class: "cubi-input" });
  node.name = name;
  for (const option of options) {
    const item = el("option", { text: option.label });
    item.value = option.value;
    if (option.disabled) item.disabled = true;
    if (selected !== undefined && option.value === selected) item.selected = true;
    node.append(item);
  }
  return node;
}

export function textarea(name: string, options: { rows?: number; placeholder?: string; value?: string } = {}): HTMLTextAreaElement {
  const node = el("textarea", { class: "cubi-input cubi-textarea" });
  node.name = name;
  node.rows = options.rows ?? 3;
  if (options.placeholder) node.placeholder = options.placeholder;
  if (options.value !== undefined) node.value = options.value;
  return node;
}

export type TableColumn<T> = {
  key: string;
  label: string;
  render?: (row: T) => Node | string;
  width?: string;
};

export function dataTable<T>(
  columns: TableColumn<T>[],
  rows: readonly T[],
  options: { caption?: string; empty?: string; getKey?: (row: T, index: number) => string; onRow?: (row: T) => void; testId?: string } = {},
): HTMLElement {
  const wrapper = el("div", { class: "cubi-table-wrap" });
  if (options.testId) wrapper.dataset.testid = options.testId;
  const table = el("table", { class: "cubi-table" });
  if (options.caption) table.append(el("caption", { class: "cubi-visually-hidden", text: options.caption }));
  const headRow = el("tr");
  for (const column of columns) {
    const th = el("th", { text: column.label, attrs: { scope: "col" } });
    if (column.width) th.style.width = column.width;
    headRow.append(th);
  }
  table.append(el("thead", {}, headRow));
  const tbody = el("tbody");
  if (!rows.length) {
    tbody.append(el("tr", {}, el("td", { class: "cubi-table-empty", text: options.empty ?? "—", attrs: { colspan: String(columns.length) } })));
  }
  rows.forEach((row, index) => {
    const tr = el("tr");
    if (options.getKey) tr.dataset.key = options.getKey(row, index);
    for (const column of columns) {
      const td = el("td");
      const value = column.render ? column.render(row) : String((row as Record<string, unknown>)[column.key] ?? "");
      td.append(typeof value === "string" ? document.createTextNode(value) : value);
      tr.append(td);
    }
    if (options.onRow) {
      tr.tabIndex = 0;
      tr.classList.add("cubi-row-action");
      tr.addEventListener("click", () => options.onRow?.(row));
      tr.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          options.onRow?.(row);
        }
      });
    }
    tbody.append(tr);
  });
  table.append(tbody);
  wrapper.append(table);
  return wrapper;
}

export function toolbar(...items: (Node | null)[]): HTMLElement {
  return el("div", { class: "cubi-toolbar" }, ...items);
}

export function tabs<T extends string>(
  items: { id: T; label: string }[],
  selected: T,
  onChange: (id: T) => void,
): HTMLElement {
  const bar = el("div", { class: "cubi-tabs", attrs: { role: "tablist" } });
  for (const item of items) {
    const tab = el("button", {
      class: `cubi-tab ${item.id === selected ? "is-selected" : ""}`.trim(),
      text: item.label,
      attrs: { role: "tab", type: "button", "aria-selected": item.id === selected ? "true" : "false" },
    });
    tab.addEventListener("click", () => onChange(item.id));
    bar.append(tab);
  }
  return bar;
}

export function emptyPanel(title: string, message: string): HTMLElement {
  return stateBlock("empty", title, message);
}

export function capabilityTone(probe: CapabilityProbe): "success" | "warning" | "danger" | "neutral" {
  if (probe.state === "available") return "success";
  if (probe.state === "forbidden") return "warning";
  if (probe.state === "unavailable") return "neutral";
  return "danger";
}

export function localeName(locale: EnterpriseLocale): string {
  return locale;
}

export function relTime(iso: string | null | undefined, locale: EnterpriseLocale): string {
  if (!iso) return "—";
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  const diff = Date.now() - parsed;
  const minutes = Math.round(diff / 60_000);
  if (Math.abs(minutes) < 1) return locale === "fa" ? "همین حالا" : "just now";
  try {
    const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
    if (Math.abs(minutes) < 60) return formatter.format(-minutes, "minute");
    const hours = Math.round(minutes / 60);
    if (Math.abs(hours) < 24) return formatter.format(-hours, "hour");
    return formatter.format(-Math.round(hours / 24), "day");
  } catch {
    return new Date(parsed).toISOString().slice(0, 16).replace("T", " ");
  }
}
