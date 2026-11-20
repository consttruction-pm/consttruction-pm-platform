import type { PageContext } from "../app.js";
import { probe } from "../api.js";
import { badge, el } from "../ui.js";
import {
  emptyLine,
  labelled,
  note,
  pageActions,
  readLocalJson,
  section,
  sectionBody,
  selectControl,
  sourceState,
  testId,
  textInput,
  writeLocalJson,
} from "./shared.js";

/**
 * Page 11 — Workflow studio.
 *
 * Versioned, visual workflow design. Drafts are edited and validated locally so
 * the designer is usable before the workflow service is mounted; publishing is
 * server-only and stays disabled with an explicit reason. Validation is pure and
 * deterministic, and the same checks run before a publish request would be sent.
 */

type Step = { id: string; name: string; terminal: boolean };
type Transition = { from: string; to: string; label: string };
export type Draft = {
  id: string;
  name: string;
  revision: number;
  updated_at: string;
  steps: Step[];
  transitions: Transition[];
};

const STORAGE_KEY = "cubi.enterprise.workflow.draft.v1";

function seedDraft(): Draft {
  return {
    id: "draft",
    name: "Project change request",
    revision: 1,
    updated_at: new Date().toISOString(),
    steps: [
      { id: "draft", name: "Draft", terminal: false },
      { id: "review", name: "Review", terminal: false },
      { id: "approved", name: "Approved", terminal: true },
      { id: "rejected", name: "Rejected", terminal: true },
    ],
    transitions: [
      { from: "draft", to: "review", label: "Submit" },
      { from: "review", to: "approved", label: "Approve" },
      { from: "review", to: "rejected", label: "Reject" },
    ],
  };
}

type State = { draft: Draft; error: string | null; savedAt: string | null };

export function renderWorkflows(ctx: PageContext, host: HTMLElement): void {
  const stored = readLocalJson<Draft | null>(STORAGE_KEY, null);
  const state: State = { draft: normalize(stored) ?? seedDraft(), error: null, savedAt: null };
  const root = el("div");
  host.append(root);
  const paint = (): void => {
    root.replaceChildren(...build(ctx, state, paint));
  };
  paint();
}

function build(ctx: PageContext, state: State, paint: () => void): HTMLElement[] {
  const nodes: HTMLElement[] = [];
  const intro = section("Versioned workflow design", "A workflow is a named, versioned graph of steps and transitions. Drafts are device-local; publishing is server-only.");
  sectionBody(intro, note("Draft edits are stored on this device only. The workflow service route is probed below; nothing is presented as published."));
  testId(intro, "workflows-intro");
  nodes.push(intro);

  const capability = section("Workflow service status", "GET /api/enterprise/workflows is the published workflow register.");
  const capabilityHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(capability, capabilityHost);
  testId(capability, "workflows-capability");
  nodes.push(capability);

  const validation = validate(state.draft);
  const split = el("div", { class: "cubi-workflow" });

  const editor = section(`Draft · ${state.draft.name}`, `Revision ${state.draft.revision} · last saved ${state.savedAt ?? formatTime(state.draft.updated_at)} (device-local)`);
  const nameInput = testId(textInput({ value: state.draft.name, maxLength: 120 }), "workflows-name");
  nameInput.addEventListener("input", () => { state.draft.name = nameInput.value; });
  const stepName = testId(textInput({ placeholder: "New step name" }), "workflows-step-name");
  const stepForm = el("form", { class: "cubi-row" });
  const addStep = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Add step", attrs: { type: "submit" } });
  stepForm.append(stepName, addStep);
  stepForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = stepName.value.trim();
    if (!value) return;
    const base = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "step";
    let id = base;
    let counter = 2;
    while (state.draft.steps.some((step) => step.id === id)) id = `${base}-${counter++}`;
    state.draft.steps.push({ id, name: value, terminal: false });
    state.draft.revision += 1;
    state.draft.updated_at = new Date().toISOString();
    persist(ctx, state);
    paint();
  });

  const stepsTable = el("div", { class: "cubi-table-wrap" });
  const stepsNode = el("table", { class: "cubi-table" });
  stepsNode.append(el("thead", {}, el("tr", {}, el("th", { text: "Step" }), el("th", { text: "ID" }), el("th", { text: "Terminal" }), el("th", { text: "" }))));
  const stepsBody = el("tbody");
  state.draft.steps.forEach((step) => {
    const terminal = el("input");
    terminal.type = "checkbox";
    terminal.checked = step.terminal;
    terminal.addEventListener("change", () => {
      step.terminal = terminal.checked;
      state.draft.revision += 1;
      state.draft.updated_at = new Date().toISOString();
      persist(ctx, state);
      paint();
    });
    const remove = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Remove", attrs: { type: "button" } });
    remove.addEventListener("click", () => {
      state.draft.steps = state.draft.steps.filter((item) => item.id !== step.id);
      state.draft.transitions = state.draft.transitions.filter((item) => item.from !== step.id && item.to !== step.id);
      state.draft.revision += 1;
      state.draft.updated_at = new Date().toISOString();
      persist(ctx, state);
      paint();
    });
    stepsBody.append(el("tr", {},
      el("td", {}, el("strong", { text: step.name })),
      el("td", {}, el("code", { class: "cubi-mono", text: step.id })),
      el("td", {}, terminal),
      el("td", {}, remove),
    ));
  });
  stepsNode.append(stepsBody);
  stepsTable.append(stepsNode);

  const from = state.draft.steps[0]?.id ?? "";
  const to = state.draft.steps[1]?.id ?? state.draft.steps[0]?.id ?? "";
  const transitionFrom = selectControl(state.draft.steps.map((step) => ({ value: step.id, label: step.name })), from, () => {});
  const transitionTo = selectControl(state.draft.steps.map((step) => ({ value: step.id, label: step.name })), to, () => {});
  const transitionLabel = textInput({ placeholder: "Transition label" });
  const addTransition = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Add transition", attrs: { type: "button" } });
  addTransition.addEventListener("click", () => {
    const candidate = { from: transitionFrom.value, to: transitionTo.value, label: transitionLabel.value.trim() || "Transition" };
    const duplicate = state.draft.transitions.some((item) => item.from === candidate.from && item.to === candidate.to);
    if (!candidate.from || !candidate.to) {
      state.error = "Both a source and a target step are required.";
      paint();
      return;
    }
    if (duplicate) {
      state.error = "That transition already exists.";
      paint();
      return;
    }
    state.error = null;
    state.draft.transitions.push(candidate);
    state.draft.revision += 1;
    state.draft.updated_at = new Date().toISOString();
    persist(ctx, state);
    paint();
  });

  const transitionsTable = el("div", { class: "cubi-table-wrap" });
  const transitionsNode = el("table", { class: "cubi-table" });
  transitionsNode.append(el("thead", {}, el("tr", {}, el("th", { text: "From" }), el("th", { text: "To" }), el("th", { text: "Label" }), el("th", { text: "" }))));
  const transitionsBody = el("tbody");
  state.draft.transitions.forEach((transition, index) => {
    const remove = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Remove", attrs: { type: "button" } });
    remove.addEventListener("click", () => {
      state.draft.transitions.splice(index, 1);
      state.draft.revision += 1;
      state.draft.updated_at = new Date().toISOString();
      persist(ctx, state);
      paint();
    });
    transitionsBody.append(el("tr", {},
      el("td", { text: stepNameById(state.draft, transition.from) }),
      el("td", { text: stepNameById(state.draft, transition.to) }),
      el("td", { text: transition.label }),
      el("td", {}, remove),
    ));
  });
  transitionsNode.append(transitionsBody);
  transitionsTable.append(transitionsNode);

  sectionBody(editor,
    labelled("Workflow name", nameInput),
    el("h3", { text: "Steps" }),
    stepsTable,
    stepForm,
    el("h3", { text: "Transitions" }),
    transitionsTable,
    el("div", { class: "cubi-row" }, transitionFrom, transitionTo, transitionLabel, addTransition),
    state.error ? el("p", { class: "cubi-alert cubi-alert-error", text: state.error }) : null,
  );
  testId(editor, "workflows-editor");
  split.append(editor);

  const canvasCard = section("Visual designer", "The compiled graph. Validation must pass before a publish request can be made.");
  const canvas = el("div", { class: "cubi-flow-canvas" });
  testId(canvas, "workflows-canvas");
  if (state.draft.steps.length === 0) canvas.append(el("p", { class: "cubi-flow-empty", text: "Add a step to start the workflow." }));
  for (const step of state.draft.steps) {
    const node = el("div", { class: `cubi-flow-node ${step.terminal ? "terminal" : ""}`.trim() });
    node.append(el("strong", { text: step.name }), el("span", { text: step.terminal ? "terminal" : "step" }));
    canvas.append(node);
    const outgoing = state.draft.transitions.filter((transition) => transition.from === step.id);
    for (const transition of outgoing) {
      canvas.append(el("div", { class: "cubi-flow-edge", attrs: { title: transition.label } }));
      canvas.append(el("div", { class: "cubi-flow-node" }, el("strong", { text: stepNameById(state.draft, transition.to) }), el("span", { text: transition.label })));
    }
  }
  const validationList = el("div", { class: "cubi-list" });
  if (validation.length === 0) {
    validationList.append(el("div", { class: "cubi-list-item" }, el("strong", { text: "Validation passed" }), badge("valid", "success")));
  } else {
    for (const message of validation) {
      validationList.append(el("div", { class: "cubi-list-item" }, el("span", { text: message }), badge("blocked", "danger")));
    }
  }
  sectionBody(canvasCard, canvas, validationList);
  testId(canvasCard, "workflows-validation");
  split.append(canvasCard);
  nodes.push(split);

  const publish = el("button", { class: "cubi-btn cubi-btn-primary", text: "Publish version", attrs: { type: "button" } });
  publish.disabled = true;
  publish.title = "Publishing requires the server workflow route.";
  nodes.push(pageActions(
    actionButton("Save draft", () => {
      state.draft.revision += 1;
      state.draft.updated_at = new Date().toISOString();
      persist(ctx, state);
      state.savedAt = formatTime(state.draft.updated_at);
      ctx.toast("Draft saved on this device.", "info");
      paint();
    }),
    actionButton("Validate", () => {
      ctx.toast(validation.length === 0 ? "Validation passed." : `${validation.length} validation issue(s) found.`, validation.length === 0 ? "info" : "error");
      paint();
    }),
    publish,
    actionButton("Reset draft", () => {
      state.draft = seedDraft();
      state.error = null;
      state.savedAt = null;
      writeLocalJson(STORAGE_KEY, state.draft);
      paint();
    }),
  ));
  nodes.push(note("Validation checks: at least two steps, at least one terminal step, no duplicate transitions, every transition references a step, and every step is reachable from the first step.", "warning"));

  void loadService(ctx, capabilityHost);
  return nodes;
}

function loadService(ctx: PageContext, host: HTMLElement): void {
  void probe("/api/enterprise/workflows").then((state) => {
    if (state.state === "available") {
      host.replaceChildren(el("div", { class: "cubi-conn-row" }, el("strong", { text: "Published workflow register" }), badge(`${state.status}`, "success")));
    } else {
      host.replaceChildren(sourceState(state, ctx.t, { title: "Published workflows", source: "Enterprise workflow service", detail: "Local drafts remain fully editable and validated; only publishing is unavailable." }));
    }
  });
}

export function validate(draft: Draft): string[] {
  const errors: string[] = [];
  if (!draft.name.trim()) errors.push("The workflow needs a name.");
  if (draft.steps.length < 2) errors.push("A workflow needs at least two steps.");
  const ids = new Set<string>();
  for (const step of draft.steps) {
    if (!step.id.trim()) errors.push("Every step needs an ID.");
    if (!step.name.trim()) errors.push("Every step needs a name.");
    if (ids.has(step.id)) errors.push(`Duplicate step ID: ${step.id}.`);
    ids.add(step.id);
  }
  if (!draft.steps.some((step) => step.terminal)) errors.push("At least one step must be terminal.");
  const seen = new Set<string>();
  for (const transition of draft.transitions) {
    if (!ids.has(transition.from) || !ids.has(transition.to)) errors.push("A transition references a missing step.");
    if (transition.from === transition.to) errors.push("A step cannot transition to itself.");
    const key = `${transition.from}->${transition.to}`;
    if (seen.has(key)) errors.push(`Duplicate transition: ${key}.`);
    seen.add(key);
  }
  if (draft.steps.length) {
    const start = draft.steps[0].id;
    const reachable = new Set<string>([start]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const transition of draft.transitions) {
        if (reachable.has(transition.from) && !reachable.has(transition.to)) {
          reachable.add(transition.to);
          changed = true;
        }
      }
    }
    for (const step of draft.steps) {
      if (!reachable.has(step.id)) errors.push(`Step "${step.name}" is unreachable from the first step.`);
    }
  }
  return Array.from(new Set(errors));
}

function normalize(draft: Draft | null): Draft | null {
  if (!draft || !Array.isArray(draft.steps) || !Array.isArray(draft.transitions)) return null;
  return draft;
}

function persist(ctx: PageContext, state: State): void {
  if (!writeLocalJson(STORAGE_KEY, state.draft)) ctx.toast("This browser refused local storage; the draft will not persist.", "error");
}

function stepNameById(draft: Draft, id: string): string {
  return draft.steps.find((step) => step.id === id)?.name ?? id;
}

function actionButton(text: string, onClick: () => void): HTMLElement {
  const node = el("button", { class: "cubi-btn cubi-btn-secondary", text, attrs: { type: "button" } });
  node.addEventListener("click", onClick);
  return node;
}

function formatTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  return new Date(parsed).toISOString().slice(0, 16).replace("T", " ");
}
