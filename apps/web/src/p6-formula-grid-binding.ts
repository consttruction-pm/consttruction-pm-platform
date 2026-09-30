import type {
  FieldRegistry,
  FormulaAuthoritativeResult,
  FormulaEditorModel,
  LayoutDefinition,
  P6Field,
} from "./p6-field-layout-foundation.js";
import type { P6FormulaEditorModel } from "./p6-formula-editor.js";
import { createP6FormulaEditor } from "./p6-formula-editor.js";

export type P6FormulaGridBindingState = {
  field: P6Field;
  presentation: LayoutDefinition["columns"][number];
  editor: ReturnType<P6FormulaEditorModel["getState"]>;
};

export type P6FormulaGridBinding = {
  getState(): P6FormulaGridBindingState;
  setExpression(expression: string): P6FormulaGridBindingState;
  validate(): Promise<P6FormulaGridBindingState>;
  applyAuthoritativeResult(result: FormulaAuthoritativeResult): P6FormulaGridBindingState;
};

function requireField(registry: FieldRegistry, fieldId: string): P6Field {
  const field = registry.fields.find((candidate) => candidate.field_id === fieldId);
  if (!field) throw new Error("UNKNOWN_FIELD");
  return field;
}

function requirePresentation(layout: LayoutDefinition, fieldId: string) {
  const presentation = layout.columns.find((column) => column.field_id === fieldId);
  if (!presentation) throw new Error("FIELD_NOT_IN_LAYOUT");
  return presentation;
}

export function createP6FormulaGridBinding(
  registry: FieldRegistry,
  layout: LayoutDefinition,
  fieldId: string,
  authority: Parameters<typeof createP6FormulaEditor>[1],
  expression = "",
): P6FormulaGridBinding {
  const field = requireField(registry, fieldId);
  requirePresentation(layout, fieldId);
  const editor = createP6FormulaEditor(fieldId, authority, expression);

  const state = (): P6FormulaGridBindingState => ({
    field,
    presentation: { ...requirePresentation(layout, fieldId) },
    editor: editor.getState(),
  });

  return {
    getState() {
      return state();
    },
    setExpression(nextExpression) {
      editor.setExpression(nextExpression);
      return state();
    },
    async validate() {
      await editor.validate();
      return state();
    },
    applyAuthoritativeResult(result) {
      editor.applyAuthoritativeResult(result);
      return state();
    },
  };
}
