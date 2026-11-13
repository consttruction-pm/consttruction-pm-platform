import { describe, it } from "node:test";
import assert from "node:assert/strict";
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import {
  LAYOUT_EXCHANGE_FORMAT,
  LAYOUT_SELECTION_STORAGE_PREFIX,
  layoutCatalogEntries,
  layoutDisplayName,
  layoutHasUnsavedChanges,
  layoutScopeLabel,
  loadLayoutCatalog,
  parseLayoutDocument,
  parseLayoutSelections,
  readLayoutSelection,
  renderLayoutSelectorMarkup,
  serializeLayoutDocument,
  writeLayoutSelection,
} from "./workspace-layout-selector.js";

const context: ProjectContext = { tenant_id: "tenant-a", project_id: "project-a" } as ProjectContext;

function layout(scope: LayoutDefinition["scope"], revision: number, name?: string): LayoutDefinition {
  return {
    schema_version: "p6-layout.v1",
    scope,
    view_id: "activity",
    revision,
    columns: [
      { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
    ],
    ...(name ? { metadata: { layoutName: name } } : {}),
  };
}

function transportReturning(values: Record<string, LayoutDefinition | null | "error">): ApiTransport {
  return {
    async get<T>(path: string): Promise<ApiResult<T>> {
      const scope = path.includes("/layouts/user/") ? "user" : "project";
      const value = values[scope];
      if (value === "error") {
        return { ok: false, error: { code: "P6_LAYOUT_READ_FAILED", message: "boom" } } as unknown as ApiResult<T>;
      }
      if (value == null) {
        return { ok: false, error: { code: "P6_LAYOUT_NOT_FOUND", message: "missing" } } as unknown as ApiResult<T>;
      }
      return { ok: true, data: value as unknown as T };
    },
    async post(): Promise<ApiResult<never>> {
      throw new Error("read-only test transport");
    },
  };
}

describe("layout display naming", () => {
  it("uses the stored layout name and never invents one", () => {
    assert.equal(layoutDisplayName(layout("project", 3, "Classic Schedule Layout"), "en"), "Classic Schedule Layout");
    assert.equal(layoutDisplayName(layout("project", 3, "   "), "en"), layoutScopeLabel("project", "en"));
    assert.equal(layoutDisplayName(layout("user", 1), "en"), "User layout");
    assert.equal(layoutDisplayName(null, "fa"), "بدون چیدمان");
  });

  it("labels scopes in both interface languages", () => {
    assert.equal(layoutScopeLabel("project", "en"), "Project layout");
    assert.equal(layoutScopeLabel("user", "fa"), "چیدمان کاربر");
  });
});

describe("layout catalogue", () => {
  it("lists only stored scopes in project then user order", () => {
    const entries = layoutCatalogEntries(
      { project: layout("project", 4, "Classic Schedule Layout"), user: layout("user", 2, "My columns") },
      "en",
    );
    assert.deepEqual(
      entries.map((entry) => [entry.scope, entry.name, entry.revision]),
      [
        ["project", "Classic Schedule Layout", 4],
        ["user", "My columns", 2],
      ],
    );
  });

  it("omits a scope that has no stored layout instead of faking one", () => {
    const entries = layoutCatalogEntries({ project: null, user: layout("user", 1) }, "en");
    assert.equal(entries.length, 1);
    assert.equal(entries[0].scope, "user");
  });

  it("drops a stored layout whose scope does not match its slot", () => {
    const entries = layoutCatalogEntries({ project: layout("user", 1), user: null }, "en");
    assert.deepEqual(entries, []);
  });

  it("loads both scopes from the layout contract and maps not-found to null", async () => {
    const catalog = await loadLayoutCatalog(
      transportReturning({ project: layout("project", 5, "Classic Schedule Layout"), user: null }),
      context,
      "activity",
    );
    assert.equal(catalog.project?.revision, 5);
    assert.equal(catalog.user, null);
  });

  it("surfaces a read failure instead of pretending the catalogue is empty", async () => {
    await assert.rejects(
      () => loadLayoutCatalog(transportReturning({ project: "error", user: null }), context, "activity"),
      /P6_LAYOUT_READ_FAILED/,
    );
  });
});

describe("layout selection storage", () => {
  it("keeps one selection per tenant and project", () => {
    const empty = parseLayoutSelections(null);
    const first = writeLayoutSelection(empty, "tenant-a", "project-a", {
      scope: "user",
      viewId: "activity",
      revision: 2,
    });
    const second = writeLayoutSelection(parseLayoutSelections(first), "tenant-a", "project-b", {
      scope: "project",
      viewId: "activity",
      revision: 7,
    });
    const store = parseLayoutSelections(second);
    assert.deepEqual(readLayoutSelection(store, "tenant-a", "project-a"), {
      scope: "user",
      viewId: "activity",
      revision: 2,
    });
    assert.deepEqual(readLayoutSelection(store, "tenant-a", "project-b"), {
      scope: "project",
      viewId: "activity",
      revision: 7,
    });
    assert.equal(readLayoutSelection(store, "tenant-a", "project-c"), null);
  });

  it("ignores malformed or out-of-contract entries", () => {
    assert.deepEqual(parseLayoutSelections("not json"), {});
    assert.deepEqual(parseLayoutSelections("[]"), {});
    const store = parseLayoutSelections(
      JSON.stringify({
        "t:p": { scope: "global", viewId: "activity", revision: 1 },
        "t:q": { scope: "project", viewId: "", revision: 1 },
        "t:r": { scope: "project", viewId: "activity", revision: -2 },
        "t:s": { scope: "project", viewId: "activity", revision: 3 },
      }),
    );
    assert.deepEqual(Object.keys(store), ["t:s"]);
  });

  it("is namespaced so unrelated workspace state cannot collide", () => {
    assert.equal(LAYOUT_SELECTION_STORAGE_PREFIX, "cubi:workspace-layout-selection");
  });
});

describe("layout selector markup", () => {
  const base = {
    locale: "en",
    current: layout("project", 4, "Classic Schedule Layout"),
    previewScope: null,
    canSave: true,
    entries: [
      {
        scope: "project" as const,
        layout: layout("project", 4, "Classic Schedule Layout"),
        name: "Classic Schedule Layout",
        revision: 4,
      },
    ],
    loaded: true,
    error: null,
  };

  it("shows the stored layout name and revision in the trigger", () => {
    const markup = renderLayoutSelectorMarkup(base);
    assert.match(markup, /data-layout-trigger/);
    assert.match(markup, /Classic Schedule Layout/);
    assert.match(markup, /Project layout · r4/);
  });

  it("offers only the stored entries as menu options", () => {
    const markup = renderLayoutSelectorMarkup(base);
    assert.equal((markup.match(/data-layout-option=/g) ?? []).length, 1);
    assert.match(markup, /role="menuitemradio"/);
    assert.doesNotMatch(markup, /No stored layout is available/);
  });

  it("states the loading and empty states honestly", () => {
    const loading = renderLayoutSelectorMarkup({ ...base, entries: [], loaded: false });
    assert.match(loading, /Reading stored layouts/);
    assert.equal((loading.match(/data-layout-option=/g) ?? []).length, 0);
    const empty = renderLayoutSelectorMarkup({ ...base, entries: [], loaded: true });
    assert.match(empty, /No stored layout is available for this project/);
  });

  it("disables Apply and Cancel until a preview exists", () => {
    const markup = renderLayoutSelectorMarkup(base);
    assert.match(markup, /data-layout-action="apply" disabled/);
    assert.match(markup, /data-layout-action="cancel" disabled/);
    const previewing = renderLayoutSelectorMarkup({ ...base, previewScope: "user" });
    assert.match(previewing, /data-layout-action="apply"\s+title=/);
    assert.match(previewing, /data-layout-action="cancel"\s+title=/);
    assert.match(previewing, /Preview — not saved/);
  });

  it("disables saving with a stated reason when the role cannot write", () => {
    const markup = renderLayoutSelectorMarkup({ ...base, canSave: false });
    assert.match(markup, /data-layout-action="save" disabled/);
    assert.match(markup, /Your role cannot save layouts/);
  });

  it("never claims a layout switch mutates schedule data", () => {
    const markup = renderLayoutSelectorMarkup(base);
    assert.match(markup, /Switching never changes activities, relationships, WBS or dates/);
    assert.doesNotMatch(markup, /Oracle|Primavera|P6/);
  });
});

describe("layout exchange", () => {
  it("exports presentation only under a versioned format", () => {
    const text = serializeLayoutDocument(layout("project", 4, "Classic Schedule Layout"), "Classic Schedule Layout");
    const parsed = JSON.parse(text);
    assert.equal(parsed.format, LAYOUT_EXCHANGE_FORMAT);
    assert.equal(parsed.name, "Classic Schedule Layout");
    assert.equal(parsed.layout.view_id, "activity");
    assert.equal(parsed.layout.columns.length, 1);
    assert.equal("scope" in parsed.layout, false);
    assert.equal("revision" in parsed.layout, false);
    assert.doesNotMatch(text, /project-a|tenant-a/);
  });

  it("imports into a user-scope draft at revision zero", () => {
    const text = serializeLayoutDocument(layout("project", 9, "Road"), "Road");
    const imported = parseLayoutDocument(text);
    assert.equal(imported.name, "Road");
    assert.equal(imported.layout.scope, "user");
    assert.equal(imported.layout.revision, 0);
    assert.equal(imported.layout.columns[0].field_id, "activity_id");
  });

  it("rejects malformed, foreign and unnamed documents", () => {
    assert.throws(() => parseLayoutDocument("{"), /INVALID_LAYOUT_DOCUMENT/);
    assert.throws(() => parseLayoutDocument(JSON.stringify({ format: "other" })), /INVALID_LAYOUT_DOCUMENT/);
    const unnamed = JSON.parse(serializeLayoutDocument(layout("project", 1), "x"));
    unnamed.name = " ";
    assert.throws(() => parseLayoutDocument(JSON.stringify(unnamed)), /INVALID_LAYOUT_DOCUMENT_NAME/);
  });

  it("rejects columns the current registry does not define", () => {
    const registry = {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26.0",
      status: "authoritative",
      fields: [
        {
          field_id: "activity_id",
          subject_area: "Activity",
          p6_field: "id",
          display_name: "Activity ID",
          data_type: "string",
          writable: false,
          computed: false,
          disposition: "native",
        },
      ],
    } as const;
    const imported = parseLayoutDocument(
      serializeLayoutDocument(layout("project", 2, "Known"), "Known"),
      registry as never,
    );
    assert.equal(imported.layout.columns[0].field_id, "activity_id");
    const foreign = JSON.parse(serializeLayoutDocument(layout("project", 2, "Unknown"), "Unknown"));
    foreign.layout.columns[0].field_id = "not_in_registry";
    assert.throws(() => parseLayoutDocument(JSON.stringify(foreign), registry as never), /P6_COLUMN_FIELD_NOT_IN_REGISTRY/);
  });
});

describe("layout selector exchange actions", () => {
  const markupOptions = {
    locale: "en" as const,
    current: layout("project", 4, "Classic Schedule Layout"),
    previewScope: null,
    canSave: true,
    entries: [
      {
        scope: "project" as const,
        layout: layout("project", 4, "Classic Schedule Layout"),
        name: "Classic Schedule Layout",
        revision: 4,
      },
    ],
    loaded: true,
    error: null,
  };

  it("offers rename, export and import with honest disabled states", () => {
    const markup = renderLayoutSelectorMarkup({ ...markupOptions, canSave: false });
    assert.match(markup, /data-layout-action="rename" disabled/);
    assert.match(markup, /data-layout-action="import" disabled/);
    assert.match(markup, /data-layout-import/);
    const writable = renderLayoutSelectorMarkup(markupOptions);
    assert.match(writable, /data-layout-action="rename"\s+title=/);
    assert.match(writable, /data-layout-action="export"\s+title=/);
    assert.match(writable, /data-layout-action="import"\s+title=/);
  });

  it("offers New and Reset to Default, and states that Delete is not available", () => {
    const markup = renderLayoutSelectorMarkup(markupOptions);
    assert.match(markup, /data-layout-action="new"/);
    assert.match(markup, /data-layout-action="reset-default"/);
    assert.match(markup, /data-layout-action="delete" disabled/);
    assert.match(markup, /does not support deleting a stored layout/);
    const viewer = renderLayoutSelectorMarkup({ ...markupOptions, canSave: false });
    assert.match(viewer, /data-layout-action="new" disabled/);
    assert.match(viewer, /data-layout-action="reset-default" disabled/);
  });

  it("shows an unsaved-changes state only when the window is dirty", () => {
    assert.doesNotMatch(renderLayoutSelectorMarkup(markupOptions), /data-layout-state="dirty"/);
    const dirty = renderLayoutSelectorMarkup({ ...markupOptions, dirty: true });
    assert.match(dirty, /data-layout-state="dirty"/);
    assert.match(dirty, /Unsaved changes/);
    const preview = renderLayoutSelectorMarkup({ ...markupOptions, dirty: true, previewScope: "project" });
    assert.doesNotMatch(preview, /data-layout-state="dirty"/);
    assert.match(preview, /data-layout-state="preview"/);
  });
});

describe("layout dirty state", () => {
  const defaults = {
    groupBy: "wbs" as const,
    sortLevels: [{ columnId: "wbs", direction: "asc" as const }],
    presentation: undefined,
  };

  it("treats a layout without a stored plan as the Activities defaults", () => {
    assert.equal(layoutHasUnsavedChanges({ layout: layout("project", 1), ...defaults }), false);
    assert.equal(
      layoutHasUnsavedChanges({ layout: layout("project", 1), ...defaults, groupBy: "none", sortLevels: [] }),
      true,
    );
  });

  it("compares the group mode and every sort level with the stored plan", () => {
    const stored = layout("project", 5, "Stored");
    stored.metadata = {
      groupSort: { groupBy: "none", sortLevels: [{ columnId: "activity.name", direction: "desc" }] },
    };
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "none",
        sortLevels: [{ columnId: "activity.name", direction: "desc" }],
        presentation: undefined,
      }),
      false,
    );
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "wbs",
        sortLevels: [{ columnId: "activity.name", direction: "desc" }],
        presentation: undefined,
      }),
      true,
    );
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "none",
        sortLevels: [{ columnId: "activity.name", direction: "asc" }],
        presentation: undefined,
      }),
      true,
    );
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "none",
        sortLevels: [],
        presentation: undefined,
      }),
      true,
    );
  });

  it("compares presentation only when the stored revision carries it", () => {
    const stored = layout("project", 3, "Stored");
    stored.metadata = { presentation: { table: { fontSize: 12 } } };
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "wbs",
        sortLevels: [{ columnId: "wbs", direction: "asc" }],
        presentation: { table: { fontSize: 12 } },
      }),
      false,
    );
    assert.equal(
      layoutHasUnsavedChanges({
        layout: stored,
        groupBy: "wbs",
        sortLevels: [{ columnId: "wbs", direction: "asc" }],
        presentation: { table: { fontSize: 15 } },
      }),
      true,
    );
    assert.equal(
      layoutHasUnsavedChanges({ layout: null, groupBy: "none", sortLevels: [], presentation: null }),
      false,
    );
  });
});
