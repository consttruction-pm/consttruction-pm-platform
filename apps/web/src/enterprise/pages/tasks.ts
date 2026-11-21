import type { PageContext } from "../app.js";
import { ApiError, api, probe, type EnterpriseTask } from "../api.js";
import { formatDate } from "../session.js";
import { badge, el, stateBlock } from "../ui.js";
import {
  emptyLine,
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

/**
 * Page 10 — Team and task center.
 *
 * Generic enterprise tasks, not Engineering activities and not timesheets. The list,
 * create form and revision-checked update are implemented against the
 * Enterprise Task API v1 contract. When the PostgreSQL-backed route is not
 * mounted, the page says so and shows no task rows.
 */

type TaskState = {
  projectId: string;
  status: string;
  priority: string;
  search: string;
  creating: boolean;
  available: boolean;
};

export function renderTasks(ctx: PageContext, host: HTMLElement): void {
  const state: TaskState = {
    projectId: ctx.query.get("project") ?? "",
    status: "all",
    priority: "all",
    search: "",
    creating: false,
    available: false,
  };
  const root = el("div");
  host.append(root);
  const paint = (): void => {
    root.replaceChildren(...build(ctx, state, paint));
  };
  paint();
}

function build(ctx: PageContext, state: TaskState, paint: () => void): HTMLElement[] {
  const nodes: HTMLElement[] = [];
  const intro = section("Enterprise tasks", "These are collaboration tasks. They are not Engineering activities, assignments, progress or timesheets, and they never change the schedule.");
  sectionBody(intro,
    note("Every mutation is revision-checked. A stale or duplicate submission is rejected by the server; the browser cannot force an update."),
  );
  testId(intro, "tasks-intro");
  nodes.push(intro);

  const capability = section("Task API status", "The row below is the real answer for GET /api/enterprise/tasks.");
  const capabilityHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(capability, capabilityHost);
  testId(capability, "tasks-capability");
  nodes.push(capability);

  const controls = section("Filters", "Project, status, priority and free-text search. Filtering is applied to records returned by the server.");
  const toolbar = el("div", { class: "cubi-toolbar" });
  const projectFilter = testId(selectControl(
    [{ value: "", label: "All accessible projects" }, ...ctx.projects.map((project) => ({ value: project.project_id, label: project.name }))],
    state.projectId,
    (value) => {
      state.projectId = value;
      paint();
    },
  ), "tasks-filter-project");
  const statusFilter = testId(selectControl([
    { value: "all", label: "All statuses" },
    { value: "open", label: "Open" },
    { value: "in_progress", label: "In progress" },
    { value: "blocked", label: "Blocked" },
    { value: "completed", label: "Completed" },
    { value: "cancelled", label: "Cancelled" },
  ], state.status, (value) => {
    state.status = value;
    paint();
  }), "tasks-filter-status");
  const priorityFilter = testId(selectControl([
    { value: "all", label: "All priorities" },
    { value: "low", label: "Low" },
    { value: "normal", label: "Normal" },
    { value: "high", label: "High" },
    { value: "urgent", label: "Urgent" },
  ], state.priority, (value) => {
    state.priority = value;
    paint();
  }), "tasks-filter-priority");
  const search = testId(textInput({ placeholder: "Search title", value: state.search }), "tasks-search");
  search.addEventListener("input", () => {
    state.search = search.value;
    paint();
  });
  const createToggle = testId(el("button", { class: "cubi-btn cubi-btn-primary", text: state.creating ? "Close form" : "New task", attrs: { type: "button" } }), "tasks-create-toggle");
  createToggle.disabled = !state.available;
  createToggle.addEventListener("click", () => {
    state.creating = !state.creating;
    paint();
  });
  const refresh = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.refresh"), attrs: { type: "button" } });
  refresh.addEventListener("click", () => paint());
  toolbar.append(projectFilter, statusFilter, priorityFilter, search, refresh, createToggle);
  sectionBody(controls, toolbar);
  testId(controls, "tasks-filters");
  nodes.push(controls);

  if (state.creating) nodes.push(createForm(ctx, state, paint));

  const list = section("Task register", "Assigned Team and Assigned User are shown exactly as the server returns them. Unassigned is stated, never inferred.");
  const listHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(list, listHost);
  testId(list, "tasks-register");
  nodes.push(list);

  const contract = section("Contract", "Registered endpoint and fields. The server enforces tenant, role and revision checks.");
  sectionBody(contract, el("div", { class: "cubi-conn" },
    contractRow("GET", "/api/enterprise/tasks?project_id=", "List tasks"),
    contractRow("POST", "/api/enterprise/tasks", "Create with Idempotency-Key"),
    contractRow("PATCH", "/api/enterprise/tasks/{task_id}", "Update with expected revision"),
  ));
  testId(contract, "tasks-contract");
  nodes.push(contract);

  void load(ctx, state, capabilityHost, listHost, paint);
  return nodes;
}

async function load(ctx: PageContext, state: TaskState, capabilityHost: HTMLElement, listHost: HTMLElement, paint: () => void): Promise<void> {
  const capability = await probe("/api/enterprise/tasks");
  const wasAvailable = state.available;
  state.available = capability.state === "available";
  capabilityHost.replaceChildren(
    el("div", { class: "cubi-conn-row" },
      el("span", {}, el("strong", { text: "Enterprise Task API v1" }), el("span", { class: "path", text: " /api/enterprise/tasks" })),
      el("span", {}, badge(`${capability.status || "—"}`, capability.state === "available" ? "success" : capability.state === "forbidden" ? "warning" : "neutral"), el("span", { text: " " }), badge(capability.state, capability.state === "available" ? "success" : capability.state === "forbidden" ? "warning" : "neutral")),
    ),
  );
  if (wasAvailable !== state.available) {
    // Re-render once so the create control reflects the real capability.
    paint();
    return;
  }
  if (capability.state !== "available") {
    listHost.replaceChildren(sourceState(capability, ctx.t, {
      title: "Task register is not connected",
      source: "Enterprise Task API v1 (tenant-scoped, revision-checked)",
      detail: "The task route did not answer for this session. Create and update stay disabled; no task row is simulated.",
      retry: () => paint(),
    }));
    return;
  }
  try {
    const payload = await api.listTasks(state.projectId || null);
    const rows = payload.tasks.filter((task) => {
      if (state.status !== "all" && task.status !== state.status) return false;
      if (state.priority !== "all" && task.priority !== state.priority) return false;
      if (state.search && !task.title.toLowerCase().includes(state.search.toLowerCase())) return false;
      return true;
    });
    listHost.replaceChildren(rows.length ? taskTable(ctx, rows, paint) : emptyLine("No task matches the current filters."));
  } catch (error) {
    const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
    listHost.replaceChildren(stateBlock("error", "The task register could not be read", `${detail}. Nothing was substituted.`, [retryButton(ctx, () => paint())]));
  }
}

function taskTable(ctx: PageContext, rows: EnterpriseTask[], paint: () => void): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  testId(wrap, "tasks-table");
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Task" }),
    el("th", { text: "Status" }),
    el("th", { text: "Priority" }),
    el("th", { text: "Assigned user" }),
    el("th", { text: "Assigned team" }),
    el("th", { text: "Project" }),
    el("th", { text: "Due" }),
    el("th", { text: "Revision" }),
    el("th", { text: "Update" }),
  )));
  const body = el("tbody");
  for (const task of rows) {
    const status = el("select", { class: "cubi-input", attrs: { "aria-label": `Status of ${task.title}` } });
    for (const value of ["open", "in_progress", "blocked", "completed", "cancelled"]) {
      const option = el("option", { text: value });
      option.value = value;
      option.selected = task.status === value;
      status.append(option);
    }
    const update = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Save", attrs: { type: "button" } });
    const message = el("span", { class: "cubi-field-hint" });
    update.addEventListener("click", () => {
      update.disabled = true;
      message.textContent = "";
      void api.updateTask(task.task_id, { expected_revision: task.revision, status: status.value })
        .then(() => {
          ctx.toast("Task updated on the server.", "info");
          paint();
        })
        .catch((error: unknown) => {
          update.disabled = false;
          if (error instanceof ApiError && error.status === 409) {
            message.textContent = "Rejected: the record changed. Refresh and review the new revision.";
          } else if (error instanceof ApiError) {
            message.textContent = `${error.code} (HTTP ${error.status})`;
          } else {
            message.textContent = String(error);
          }
        });
    });
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: task.title }), el("div", { class: "cubi-field-hint", text: task.task_id })),
      el("td", {}, badge(task.status, task.status === "completed" ? "success" : task.status === "blocked" ? "danger" : "info")),
      el("td", { text: task.priority }),
      el("td", { text: task.assigned_user_id || "Unassigned" }),
      el("td", { text: task.assigned_team_id || "Unassigned" }),
      el("td", { text: task.project_id || "—" }),
      el("td", { text: formatDate(task.due_at, ctx.locale) }),
      el("td", { text: String(task.revision) }),
      el("td", {}, el("div", { class: "cubi-row" }, status, update), message),
    ));
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function createForm(ctx: PageContext, state: TaskState, paint: () => void): HTMLElement {
  const card = section("New enterprise task", "Created with an Idempotency-Key so a retry cannot create a duplicate.");
  const form = el("form", { class: "cubi-form-grid" });
  const title = testId(textInput({ placeholder: "Task title", required: true }), "tasks-create-title");
  const description = textArea({ placeholder: "Description" });
  const priority = selectControl([
    { value: "low", label: "Low" },
    { value: "normal", label: "Normal" },
    { value: "high", label: "High" },
    { value: "urgent", label: "Urgent" },
  ], "normal", () => {});
  const assignedUser = textInput({ placeholder: "user id (optional)" });
  const assignedTeam = textInput({ placeholder: "team id (optional)" });
  const due = textInput({ type: "date" });
  const project = selectControl(
    [{ value: "", label: "No project" }, ...ctx.projects.map((item) => ({ value: item.project_id, label: item.name }))],
    state.projectId,
    () => {},
  );
  const error = el("p", { class: "cubi-alert cubi-alert-error", attrs: { role: "alert", hidden: "hidden" } });
  const submit = el("button", { class: "cubi-btn cubi-btn-primary", text: "Create task", attrs: { type: "submit" } });
  form.append(
    labelled("Title", title),
    labelled("Priority", priority),
    labelled("Project", project),
    labelled("Assigned user", assignedUser),
    labelled("Assigned team", assignedTeam),
    labelled("Due date", due),
    labelled("Description", description),
  );
  form.append(error, submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    error.hidden = true;
    if (!title.value.trim()) {
      error.textContent = "A title is required.";
      error.hidden = false;
      return;
    }
    submit.disabled = true;
    const key = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `task-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    void api.createTask({
      title: title.value.trim(),
      description: description.value || null,
      priority: priority.value,
      project_id: project.value || null,
      assigned_user_id: assignedUser.value.trim() || null,
      assigned_team_id: assignedTeam.value.trim() || null,
      due_at: due.value || null,
    }, key)
      .then(() => {
        ctx.toast("Task created on the server.", "info");
        paint();
      })
      .catch((cause: unknown) => {
        submit.disabled = false;
        const detail = cause instanceof ApiError ? `${cause.code} (HTTP ${cause.status})` : String(cause);
        error.textContent = `The task was not created: ${detail}.`;
        error.hidden = false;
      });
  });
  sectionBody(card, form);
  testId(card, "tasks-create-form");
  return card;
}

function contractRow(method: string, path: string, purpose: string): HTMLElement {
  return el("div", { class: "cubi-conn-row" },
    el("span", {}, badge(method, method === "GET" ? "info" : "warning"), el("span", { class: "path", text: ` ${path}` })),
    el("span", { class: "cubi-field-hint", text: purpose }),
  );
}

function retryButton(ctx: PageContext, onRetry: () => void): HTMLElement {
  const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.retry"), attrs: { type: "button" } });
  button.addEventListener("click", onRetry);
  return button;
}
