import type { PageContext } from "../app.js";
import { ApiError, probe, type CapabilityProbe } from "../api.js";
import { badge, el, stateBlock } from "../ui.js";
import {
  detailList,
  emptyLine,
  note,
  pageActions,
  section,
  sectionBody,
  sourceStamp,
  sourceState,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 15 — Knowledge and PMBOK center.
 *
 * CUBI owns this surface, its handbooks and PMBOK material. The content itself
 * comes from the platform knowledge API (cards, coverage, search), and form
 * authoring is delegated to the shared Form Builder. No second form engine and
 * no local knowledge store are created here.
 */

type SearchState =
  | { status: "idle" }
  | { status: "loading"; query: string }
  | { status: "done"; query: string; payload: Record<string, unknown> }
  | { status: "error"; query: string; message: string };

let searchState: SearchState = { status: "idle" };

export type KnowledgeBadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

/**
 * The server owns publication state. The badge must repeat the state it was
 * given: a draft or rejected card is never painted as published guidance.
 */
export function publicationTone(status: string): KnowledgeBadgeTone {
  switch (status) {
    case "published": return "success";
    case "validated": return "info";
    case "draft": return "warning";
    case "rejected":
    case "retired": return "danger";
    default: return "neutral";
  }
}

/** Translation state is independent of source publication for every locale. */
export function translationTone(status: string): KnowledgeBadgeTone {
  switch (status) {
    case "published":
    case "approved": return "success";
    case "translated": return "info";
    case "draft":
    case "review_required": return "warning";
    case "missing":
    case "retired": return "neutral";
    default: return "neutral";
  }
}

export function renderKnowledge(ctx: PageContext, host: HTMLElement): void {
  const intro = section(
    "CUBI Knowledge & PMBOK",
    "CUBI-owned guidance, method material and PMBOK references. Content is read from the platform knowledge service; form authoring stays in the shared Form Builder.",
  );
  sectionBody(intro,
    note("No second form engine exists here. Forms are opened in the Engineering workspace, where the shared Form Builder is mounted.", "info"),
  );
  testId(intro, "knowledge-intro");
  host.append(intro);

  const capability = section("Knowledge service", "Exact answers from the knowledge API. An unregistered route is shown as unavailable.");
  const capabilityHost = el("div", {}, loadingLine(ctx));
  sectionBody(capability, capabilityHost);
  testId(capability, "knowledge-capability");
  host.append(capability);

  host.append(searchSection(ctx));

  const cards = section("Published guidance", "Validated cards with their official source. Each card keeps its source title, version and URL.");
  const cardsHost = el("div", {}, loadingLine(ctx));
  sectionBody(cards, cardsHost);
  testId(cards, "knowledge-cards");
  host.append(cards);

  const coverage = section("Coverage", "How much of each source is converted into published guidance. Gaps stay visible instead of being hidden.");
  const coverageHost = el("div", {}, loadingLine(ctx));
  sectionBody(coverage, coverageHost);
  testId(coverage, "knowledge-coverage");
  host.append(coverage);

  const forms = section("Shared Form Builder", "Reuse the existing organization form library. This page reads its overview and links to the real editor.");
  const formsHost = el("div", {}, loadingLine(ctx));
  sectionBody(forms, formsHost);
  testId(forms, "knowledge-forms");
  host.append(forms);

  void load(ctx, capabilityHost, cardsHost, coverageHost, formsHost);
}

async function load(
  ctx: PageContext,
  capabilityHost: HTMLElement,
  cardsHost: HTMLElement,
  coverageHost: HTMLElement,
  formsHost: HTMLElement,
): Promise<void> {
  const [cardsProbe, coverageProbe, formsProbe] = await Promise.all([
    probe("/api/knowledge/cards"),
    probe("/api/knowledge/coverage"),
    probe("/api/forms/organization/overview"),
  ]);

  capabilityHost.replaceChildren(connectionRows([
    ["Guidance cards", cardsProbe],
    ["Coverage report", coverageProbe],
    ["Shared Form Builder", formsProbe],
  ]));

  if (cardsProbe.state === "available") {
    try {
      const payload = await readJson<{ cards?: Record<string, unknown>[] }>("/api/knowledge/cards?limit=24");
      const rows = payload.cards ?? [];
      cardsHost.replaceChildren(rows.length ? cardsGrid(rows) : emptyLine("No published guidance card exists yet."));
    } catch (error) {
      cardsHost.replaceChildren(errorPanel(ctx, error, () => { void load(ctx, capabilityHost, cardsHost, coverageHost, formsHost); }));
    }
  } else {
    cardsHost.replaceChildren(sourceState(cardsProbe, ctx.t, { title: "Guidance cards", source: "Platform knowledge service" }));
  }

  if (coverageProbe.state === "available") {
    try {
      const payload = await readJson<Record<string, unknown>>("/api/knowledge/coverage");
      coverageHost.replaceChildren(coverageView(ctx, payload));
    } catch (error) {
      coverageHost.replaceChildren(errorPanel(ctx, error, () => { void load(ctx, capabilityHost, cardsHost, coverageHost, formsHost); }));
    }
  } else {
    coverageHost.replaceChildren(sourceState(coverageProbe, ctx.t, { title: "Coverage report", source: "Platform knowledge service" }));
  }

  if (formsProbe.state === "available") {
    try {
      const payload = await readJson<Record<string, unknown>>("/api/forms/organization/overview");
      formsHost.replaceChildren(formsView(ctx, payload));
    } catch (error) {
      formsHost.replaceChildren(errorPanel(ctx, error, () => { void load(ctx, capabilityHost, cardsHost, coverageHost, formsHost); }));
    }
  } else {
    formsHost.replaceChildren(sourceState(formsProbe, ctx.t, { title: "Shared Form Builder", source: "Existing form engine", detail: "The page links to the editor instead of embedding a second engine." }));
  }
}

function searchSection(ctx: PageContext): HTMLElement {
  const card = section("Search guidance", "Search the same knowledge service used by the assistant. Results cite the card and its official source.");
  const queryInput = testId(textInput({ placeholder: "e.g. baseline, critical path, earned value", name: "knowledge-query" }), "knowledge-search-input");
  const button = el("button", { class: "cubi-btn cubi-btn-primary", text: "Search", attrs: { type: "button" } });
  const results = el("div", { class: "cubi-knowledge-results" });
  const run = async (): Promise<void> => {
    const query = queryInput.value.trim();
    if (!query) {
      results.replaceChildren(note("Enter a search term first.", "warning"));
      return;
    }
    searchState = { status: "loading", query };
    results.replaceChildren(loadingLine(ctx));
    try {
      const payload = await readJson<Record<string, unknown>>(`/api/knowledge/search?q=${encodeURIComponent(query)}&limit=10&locale=${encodeURIComponent(ctx.locale)}`);
      searchState = { status: "done", query, payload };
      results.replaceChildren(searchResults(ctx, payload));
    } catch (error) {
      const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
      searchState = { status: "error", query, message: detail };
      results.replaceChildren(note(`The knowledge service did not answer: ${detail}. Nothing was substituted.`, "warning"));
    }
  };
  button.addEventListener("click", () => { void run(); });
  queryInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void run();
    }
  });
  const body: (Node | null)[] = [
    el("div", { class: "cubi-toolbar" }, queryInput, button),
  ];
  if (searchState.status === "done") results.replaceChildren(searchResults(ctx, searchState.payload));
  else if (searchState.status === "error") results.replaceChildren(note(`The knowledge service did not answer: ${searchState.message}. Nothing was substituted.`, "warning"));
  body.push(results);
  sectionBody(card, ...body);
  testId(card, "knowledge-search");
  return card;
}

function searchResults(ctx: PageContext, payload: Record<string, unknown>): HTMLElement {
  const hits = (payload.hits as Record<string, unknown>[] | undefined) ?? [];
  const wrap = el("div");
  if (payload.insufficient_knowledge === true) {
    wrap.append(note("The service reports insufficient knowledge for this query. No answer was invented.", "warning"));
  }
  if (!hits.length) {
    wrap.append(emptyLine("No guidance card matched this query."));
    return wrap;
  }
  for (const hit of hits) {
    const sourceUrl = typeof hit.source_url === "string" ? hit.source_url : "";
    const title = String(hit.title ?? "Untitled");
    const titleNode = sourceUrl
      ? el("a", { class: "cubi-link", text: title, attrs: { href: sourceUrl, target: "_blank", rel: "noopener noreferrer" } })
      : el("strong", { text: title });
    wrap.append(el("div", { class: "cubi-knowledge-hit" },
      el("div", { class: "cubi-knowledge-hit-head" }, titleNode,
        badge(String(hit.card_type ?? hit.entity_kind ?? "card"), "info"),
        hit.translation_status ? badge(String(hit.translation_status), translationTone(String(hit.translation_status))) : null,
      ),
      el("p", { class: "desc", text: String(hit.snippet ?? "") }),
      el("div", { class: "cubi-field-hint", text: `Score ${Number(hit.score ?? 0).toFixed(2)} · ${String(hit.scope ?? "central")}${hit.fallback_used ? " · fallback language" : ""}` }),
    ));
  }
  wrap.append(sourceStamp("Platform knowledge search", String(payload.query_locale ?? "—"), null, ctx.locale));
  return wrap;
}

function cardsGrid(rows: Record<string, unknown>[]): HTMLElement {
  const grid = el("div", { class: "cubi-knowledge-grid" });
  for (const card of rows) {
    const sourceUrl = typeof card.source_url === "string" ? card.source_url : "";
    const title = String(card.title ?? "Untitled guidance");
    const publication = String(card.publication_status ?? "unknown");
    const validation = String(card.validation_status ?? "");
    const translation = String(card.translation_status ?? "");
    const head = el("div", { class: "cubi-knowledge-card-head" },
      sourceUrl
        ? el("a", { class: "cubi-link", text: title, attrs: { href: sourceUrl, target: "_blank", rel: "noopener noreferrer" } })
        : el("strong", { text: title }),
      badge(String(card.card_type ?? "card"), "info"),
    );
    const tone = publicationTone(publication);
    const node = el("article", { class: "cubi-knowledge-card" },
      el("header", {}, head,
        el("p", { class: "desc", text: String(card.purpose ?? card.category ?? "") }),
      ),
      el("div", { class: "cubi-knowledge-card-body" },
        el("div", { class: "cubi-field-hint", text: `Source: ${String(card.source_title ?? "—")} · v${String(card.source_version ?? "—")}` }),
        badge(publication, tone),
        validation && validation !== publication
          ? badge(`validation: ${validation}`, publicationTone(validation))
          : null,
        translation ? badge(translation, translationTone(translation)) : null,
        el("span", { class: "cubi-field-hint", text: `Revision ${String(card.revision ?? "—")}` }),
      ),
    );
    testId(node, `knowledge-card-${publication}`);
    grid.append(node);
  }
  return grid;
}

function coverageView(ctx: PageContext, payload: Record<string, unknown>): HTMLElement {
  const wrap = el("div");
  const counts = (payload.card_counts as Record<string, unknown> | undefined) ?? {};
  const stats = el("div", { class: "cubi-stat-grid" });
  for (const [key, value] of Object.entries(counts)) {
    stats.append(el("div", { class: "cubi-stat" },
      el("span", { class: "cubi-stat-label", text: key }),
      el("strong", { class: "cubi-stat-value", text: String(value) }),
    ));
  }
  wrap.append(stats);

  const sources = (payload.sources as Record<string, unknown>[] | undefined) ?? [];
  if (!sources.length) {
    wrap.append(emptyLine("No ingestable source is registered."));
  } else {
    const table = el("div", { class: "cubi-table-wrap" });
    const node = el("table", { class: "cubi-table" });
    node.append(el("thead", {}, el("tr", {},
      el("th", { text: "Source" }),
      el("th", { text: "Status" }),
      el("th", { text: "Mandatory areas" }),
      el("th", { text: "Unconverted topics" }),
      el("th", { text: "Failures" }),
    )));
    const body = el("tbody");
    for (const source of sources) {
      const areas = (source.mandatory_areas as unknown[] | undefined) ?? [];
      const pending = (source.unconverted_topics as unknown[] | undefined) ?? [];
      const failures = (source.failures as unknown[] | undefined) ?? [];
      body.append(el("tr", {},
        el("td", {}, el("strong", { text: String(source.title ?? source.source_id ?? "—") }), el("div", { class: "cubi-field-hint", text: String(source.source_id ?? "") })),
        el("td", {}, badge(String(source.status ?? "not ingested"), source.status === "complete" ? "success" : source.status ? "warning" : "neutral")),
        el("td", {}, el("div", { class: "cubi-chip-row" }, ...areas.slice(0, 6).map((area) => badge(String(area), "neutral"))), areas.length > 6 ? el("div", { class: "cubi-field-hint", text: `+${areas.length - 6} more` }) : null),
        el("td", { text: String(pending.length) }),
        el("td", { text: String(failures.length) }),
      ));
    }
    node.append(body);
    table.append(node);
    wrap.append(table);
  }
  wrap.append(sourceStamp("Platform knowledge coverage report", String(payload.contract_version ?? "cubi-knowledge-coverage.v1"), null, ctx.locale));
  return wrap;
}

function formsView(ctx: PageContext, payload: Record<string, unknown>): HTMLElement {
  const wrap = el("div");
  const counts = (payload.counts as Record<string, unknown> | undefined) ?? {};
  const libraries = (payload.libraries as Record<string, Record<string, unknown>> | undefined) ?? {};
  const organization = (libraries.organization?.templates as Record<string, unknown>[] | undefined) ?? [];

  wrap.append(detailList([
    ["Contract", String(payload.contract_version ?? "—")],
    ["Engine", String(payload.engine_version ?? "—")],
    ["Organization templates", String(counts.organization_templates ?? organization.length)],
    ["Project templates", String(counts.project_templates ?? "—")],
    ["Published templates", String(counts.published_project_templates ?? "—")],
    ["Pending approvals", String(counts.pending_approvals ?? "—")],
  ]));

  if (organization.length) {
    const table = el("div", { class: "cubi-table-wrap" });
    const node = el("table", { class: "cubi-table" });
    node.append(el("thead", {}, el("tr", {},
      el("th", { text: "Organization template" }),
      el("th", { text: "Status" }),
      el("th", { text: "Revision" }),
    )));
    const body = el("tbody");
    for (const template of organization.slice(0, 20)) {
      body.append(el("tr", {},
        el("td", {}, el("strong", { text: String(template.name ?? template.template_id ?? "—") }), el("div", { class: "cubi-field-hint", text: String(template.template_id ?? "") })),
        el("td", { text: String(template.status ?? template.published_version ?? "—") }),
        el("td", { text: String(template.revision ?? "—") }),
      ));
    }
    node.append(body);
    table.append(node);
    wrap.append(table);
  } else {
    wrap.append(emptyLine("The organization library has no template yet. Create one in the shared Form Builder."));
  }

  wrap.append(
    note("Form authoring, bindings, submissions and approvals stay in the shared Form Builder. This center only reads the library overview.", "info"),
    pageActions(linkButton("Open the shared Form Builder in Engineering", "/app/")),
    sourceStamp("Shared Form Builder organization library", String(payload.contract_version ?? "—"), null, ctx.locale),
  );
  return wrap;
}

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" }, cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, `HTTP_${response.status}`, `HTTP ${response.status}`);
  return (await response.json()) as T;
}

function connectionRows(entries: [string, CapabilityProbe][]): HTMLElement {
  const wrap = el("div", { class: "cubi-conn" });
  for (const [label, capability] of entries) {
    wrap.append(el("div", { class: "cubi-conn-row" },
      el("span", {}, el("strong", { text: label }), el("span", { class: "path", text: ` ${capability.path}` })),
      el("span", {}, badge(`${capability.status || "—"}`, capability.state === "available" ? "success" : capability.state === "forbidden" ? "warning" : capability.state === "unavailable" ? "neutral" : "danger"), el("span", { text: " " }), badge(capability.state, capability.state === "available" ? "success" : capability.state === "unavailable" ? "neutral" : "warning")),
    ));
  }
  return wrap;
}

function loadingLine(ctx: PageContext): HTMLElement {
  return el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") }));
}

function errorPanel(ctx: PageContext, error: unknown, retry: () => void): HTMLElement {
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.retry"), attrs: { type: "button" } });
  button.addEventListener("click", retry);
  return stateBlock("error", "The knowledge source could not be read", `${detail}. Nothing was substituted.`, [button]);
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}
