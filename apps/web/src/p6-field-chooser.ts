import type {
  FieldRegistry,
  LayoutDefinition,
  P6Field,
} from "./p6-field-layout-foundation.js";
import {
  addField,
  createColumnPresentation,
  removeField,
  reorderFields,
  updateFieldPresentation,
} from "./p6-field-layout-foundation.js";

export type P6FieldChooserState = {
  search: string;
  subject_area: string | null;
  selected_field_ids: readonly string[];
};

export type P6FieldChooserModel = {
  getAvailableFields(): readonly P6Field[];
  getSelectedFields(): readonly P6Field[];
  setSearch(search: string): P6FieldChooserState;
  setSubjectArea(subjectArea: string | null): P6FieldChooserState;
  add(fieldId: string): LayoutDefinition;
  remove(fieldId: string): LayoutDefinition;
  reorder(fieldIds: readonly string[]): LayoutDefinition;
  updatePresentation(fieldId: string, presentation: Parameters<typeof updateFieldPresentation>[2]): LayoutDefinition;
};

function matchesField(field: P6Field, state: P6FieldChooserState): boolean {
  const query = state.search.trim().toLocaleLowerCase();
  const matchesSubject = state.subject_area === null || field.subject_area === state.subject_area;
  if (!matchesSubject) return false;
  if (!query) return true;
  return [field.field_id, field.p6_field, field.display_name]
    .some((value) => value.toLocaleLowerCase().includes(query));
}

function requireField(registry: FieldRegistry, fieldId: string): P6Field {
  const field = registry.fields.find((candidate) => candidate.field_id === fieldId);
  if (!field) throw new Error("UNKNOWN_FIELD");
  return field;
}

function selectedIds(layout: LayoutDefinition): readonly string[] {
  return layout.columns.map((column) => column.field_id);
}

export function createP6FieldChooser(
  registry: FieldRegistry,
  initialLayout: LayoutDefinition,
): P6FieldChooserModel {
  const state: P6FieldChooserState = {
    search: "",
    subject_area: null,
    selected_field_ids: selectedIds(initialLayout),
  };

  const syncState = (layout: LayoutDefinition): void => {
    state.selected_field_ids = selectedIds(layout);
  };

  return {
    getAvailableFields() {
      return registry.fields.filter((field) => matchesField(field, state));
    },
    getSelectedFields() {
      return state.selected_field_ids.map((fieldId) => requireField(registry, fieldId));
    },
    setSearch(search) {
      state.search = search;
      return { ...state, selected_field_ids: [...state.selected_field_ids] };
    },
    setSubjectArea(subjectArea) {
      state.subject_area = subjectArea;
      return { ...state, selected_field_ids: [...state.selected_field_ids] };
    },
    add(fieldId) {
      const field = requireField(registry, fieldId);
      const layout = addField(initialLayout, field, {});
      syncState(layout);
      initialLayout = layout;
      return layout;
    },
    remove(fieldId) {
      const layout = removeField(initialLayout, fieldId);
      syncState(layout);
      initialLayout = layout;
      return layout;
    },
    reorder(fieldIds) {
      const fields = fieldIds.map((fieldId) => requireField(registry, fieldId));
      const layout = reorderFields(initialLayout, fields);
      syncState(layout);
      initialLayout = layout;
      return layout;
    },
    updatePresentation(fieldId, presentation) {
      requireField(registry, fieldId);
      const layout = updateFieldPresentation(initialLayout, fieldId, presentation);
      syncState(layout);
      initialLayout = layout;
      return layout;
    },
  };
}
