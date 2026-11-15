import { FetchSessionApi, type ProjectSummary } from "./session-api.js";
import { withCsrfHeader } from "./csrf.js";

export type EnterpriseTaskStatus = "open" | "in_progress" | "blocked" | "completed" | "cancelled";
export type EnterpriseTaskPriority = "low" | "normal" | "high" | "urgent";
export type EnterpriseTaskRecord = {
  contract_version: "cubi-enterprise-task.v1";
  task_id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  created_by_user_id: string;
  created_at: string;
  status: EnterpriseTaskStatus;
  priority: EnterpriseTaskPriority;
  assigned_user_id: string | null;
  assigned_team_id: string | null;
  project_id: string | null;
  due_at: string | null;
  dependency_ids: string[];
  revision: number;
  updated_at: string | null;
  completed_at: string | null;
  completed_by_user_id: string | null;
};
type TaskListResponse = { contract_version: string; tasks: EnterpriseTaskRecord[]; next_cursor: { before_updated_at: string | null; before_task_id: string } | null };
type TaskMutationResponse = { task: EnterpriseTaskRecord; revision: number };
type Locale = "en" | "fa";
type Filter = "all" | "active" | "blocked" | "due" | "completed" | "overdue";

const COPY = {
  en: {
    title: "Task Center", eyebrow: "CUBI ENTERPRISE", subtitle: "Coordinate work across your projects and personal workspace.",
    back: "Personal workbench", refresh: "Refresh", create: "New task", createTitle: "Create a task",
    taskTitle: "Task title", description: "Description", project: "Project scope", personal: "Personal tasks",
    due: "Due date", priority: "Priority", low: "Low", normal: "Normal", high: "High", urgent: "Urgent",
    save: "Create task", cancel: "Cancel", all: "All", active: "Active", blocked: "Blocked", completed: "Completed",
    dueFilter: "Due today", overdue: "Overdue", search: "Search tasks", empty: "No tasks in this view.", loading: "Loading tasks…",
    open: "Open", in_progress: "In progress", blockedStatus: "Blocked", completedStatus: "Completed", cancelled: "Cancelled",
    markProgress: "Start", markComplete: "Complete", reopen: "Reopen", status: "Status", task: "Task",
    dueLabel: "Due", scope: "Scope", priorityLabel: "Priority", error: "Something went wrong. Please try again.",
    session: "Your session has expired. Sign in to continue.", noProjects: "No projects are available to this account.",
    titleRequired: "Enter a task title.", createFailed: "The task could not be created.",
    updateFailed: "The task could not be updated.", created: "Task created.", updated: "Task updated.",
    allProjects: "All projects", personalShort: "Personal", noDue: "No due date",
    workspace: "Enterprise workspace", securityNote: "Access is checked by the server. Project tasks appear only when you have project permission.",
  },
  fa: {
    title: "مرکز وظایف", eyebrow: "کوبی سازمانی", subtitle: "هماهنگی کارها در پروژه‌ها و فضای کاری شخصی.",
    back: "میزکار شخصی", refresh: "تازه‌سازی", create: "وظیفه جدید", createTitle: "ایجاد وظیفه",
    taskTitle: "عنوان وظیفه", description: "شرح", project: "محدوده پروژه", personal: "وظایف شخصی",
    due: "سررسید", priority: "اولویت", low: "کم", normal: "عادی", high: "زیاد", urgent: "فوری",
    save: "ایجاد وظیفه", cancel: "انصراف", all: "همه", active: "فعال", blocked: "متوقف", completed: "تکمیل‌شده",
    dueFilter: "سررسید امروز", overdue: "سررسید گذشته", search: "جستجوی وظایف", empty: "وظیفه‌ای در این نما وجود ندارد.", loading: "در حال دریافت وظایف…",
    open: "باز", in_progress: "در حال انجام", blockedStatus: "متوقف", completedStatus: "تکمیل‌شده", cancelled: "لغوشده",
    markProgress: "شروع", markComplete: "تکمیل", reopen: "بازگشایی", status: "وضعیت", task: "وظیفه",
    dueLabel: "سررسید", scope: "محدوده", priorityLabel: "اولویت", error: "خطایی رخ داد. دوباره تلاش کنید.",
    session: "نشست شما پایان یافته است. برای ادامه وارد شوید.", noProjects: "پروژه‌ای برای این حساب در دسترس نیست.",
    titleRequired: "عنوان وظیفه را وارد کنید.", createFailed: "ایجاد وظیفه انجام نشد.",
    updateFailed: "به‌روزرسانی وظیفه انجام نشد.", created: "وظیفه ایجاد شد.", updated: "وظیفه به‌روزرسانی شد.",
    allProjects: "همه پروژه‌ها", personalShort: "شخصی", noDue: "بدون سررسید",
    workspace: "محیط سازمانی", securityNote: "دسترسی در سمت سرور کنترل می‌شود. وظایف پروژه فقط با مجوز معتبر نمایش داده می‌شوند.",
  },
} as const;

export function filterEnterpriseTasks(
  tasks: readonly EnterpriseTaskRecord[],
  filter: Filter,
  query = "",
  now = Date.now(),
): EnterpriseTaskRecord[] {
  const normalized = query.trim().toLocaleLowerCase();
  return tasks.filter((task) => {
    const matchesText = !normalized
      || task.title.toLocaleLowerCase().includes(normalized)
      || (task.description ?? "").toLocaleLowerCase().includes(normalized);
    if (!matchesText) return false;
    if (filter === "active") return task.status === "open" || task.status === "in_progress";
    if (filter === "blocked") return task.status === "blocked";
    if (filter === "due") return Boolean(task.due_at && new Date(task.due_at).toDateString() === new Date(now).toDateString() && task.status !== "completed" && task.status !== "cancelled");
    if (filter === "completed") return task.status === "completed" || task.status === "cancelled";
    if (filter === "overdue") return Boolean(task.due_at && Date.parse(task.due_at) < now && task.status !== "completed" && task.status !== "cancelled");
    return true;
  }).sort((a, b) => {
    const aDue = a.due_at ? Date.parse(a.due_at) : Number.POSITIVE_INFINITY;
    const bDue = b.due_at ? Date.parse(b.due_at) : Number.POSITIVE_INFINITY;
    return aDue - bDue || Date.parse(b.updated_at ?? b.created_at) - Date.parse(a.updated_at ?? a.created_at);
  });
}

function element<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function taskIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `enterprise-task-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function taskRequest<T>(path: string, method = "GET", body?: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 45_000);
  let response: Response;
  try {
    response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: withCsrfHeader(method, headers),
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    cache: "no-store",
    signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeout);
  }
  let payload: unknown;
  try { payload = await response.json(); } catch { payload = null; }
  if (response.status === 401) {
    window.location.assign(`/login?next=${encodeURIComponent("/enterprise")}`);
    throw new Error("SESSION_REQUIRED");
  }
  if (!response.ok) {
    const code = payload && typeof payload === "object" && "code" in payload
      ? String((payload as { code: unknown }).code) : `HTTP_${response.status}`;
    throw new Error(code);
  }
  return payload as T;
}

export async function mountEnterpriseTaskCenter(container: HTMLElement): Promise<void> {
  const locale: Locale = navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  const t = COPY[locale];
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  document.title = `CUBI Enterprise · ${t.title}`;
  container.replaceChildren();

  const shell = element("main", "ce-shell");
  shell.dir = locale === "fa" ? "rtl" : "ltr";
  const header = element("header", "ce-header");
  const brand = element("a", "ce-brand", "CUBI");
  brand.href = "/app";
  brand.setAttribute("aria-label", "CUBI workspace");
  const identity = element("div", "ce-header-title");
  identity.append(element("span", "ce-eyebrow", t.eyebrow), element("strong", "", t.workspace));
  const back = element("a", "ce-back", `← ${t.back}`);
  back.href = "/app";
  header.append(brand, identity, back);

  const hero = element("section", "ce-hero");
  const heroCopy = element("div");
  heroCopy.append(element("p", "ce-eyebrow", t.eyebrow), element("h1", "", t.title), element("p", "ce-subtitle", t.subtitle));
  const actions = element("div", "ce-hero-actions");
  const accessLink = element("a", "ce-button ce-button-secondary", locale === "fa" ? "دسترسی پروژه" : "Project Access");
  accessLink.href = "/enterprise/project-access";
  const refresh = element("button", "ce-button ce-button-secondary", t.refresh);
  const createButton = element("button", "ce-button ce-button-primary", `＋ ${t.create}`);
  actions.append(accessLink, refresh, createButton);
  hero.append(heroCopy, actions);

  const toolbar = element("section", "ce-toolbar");
  const scope = element("select", "ce-select") as HTMLSelectElement;
  scope.setAttribute("aria-label", t.project);
  const personalOption = element("option", "", t.personal) as HTMLOptionElement;
  personalOption.value = "";
  scope.append(personalOption);
  const search = element("input", "ce-search") as HTMLInputElement;
  search.type = "search";
  search.placeholder = t.search;
  search.setAttribute("aria-label", t.search);
  toolbar.append(scope, search);

  const filters = element("nav", "ce-filters");
  filters.setAttribute("aria-label", t.title);
  const filterDefs: Array<[Filter, string]> = [
    ["all", t.all], ["active", t.active], ["due", t.dueFilter], ["overdue", t.overdue], ["blocked", t.blocked], ["completed", t.completed],
  ];
  let activeFilter: Filter = "all";
  const filterButtons = new Map<Filter, HTMLButtonElement>();
  for (const [key, label] of filterDefs) {
    const button = element("button", "ce-filter", label) as HTMLButtonElement;
    button.type = "button";
    button.setAttribute("aria-pressed", key === activeFilter ? "true" : "false");
    button.addEventListener("click", () => {
      activeFilter = key;
      for (const [filter, item] of filterButtons) item.setAttribute("aria-pressed", filter === key ? "true" : "false");
      renderTasks();
    });
    filterButtons.set(key, button);
    filters.append(button);
  }

  const notice = element("p", "ce-notice");
  notice.setAttribute("role", "status");
  notice.hidden = true;
  const error = element("p", "ce-error");
  error.setAttribute("role", "alert");
  error.hidden = true;
  const listSection = element("section", "ce-list-section");
  const listHeader = element("div", "ce-list-header");
  listHeader.append(element("h2", "", t.task), element("span", "ce-count", "0"));
  const list = element("div", "ce-task-list");
  const loadMore = element("button", "ce-button ce-button-secondary ce-load-more", locale === "fa" ? "بارگذاری بیشتر" : "Load more") as HTMLButtonElement;
  loadMore.type = "button";
  loadMore.hidden = true;
  listSection.append(listHeader, list, loadMore);
  const security = element("p", "ce-security-note", t.securityNote);

  const form = element("form", "ce-create-form") as HTMLFormElement;
  form.hidden = true;
  const formTitle = element("h2", "", t.createTitle);
  const titleLabel = element("label", "ce-field");
  titleLabel.append(element("span", "", t.taskTitle));
  const titleInput = element("input") as HTMLInputElement;
  titleInput.required = true;
  titleInput.maxLength = 500;
  titleInput.name = "title";
  titleLabel.append(titleInput);
  const descriptionLabel = element("label", "ce-field");
  descriptionLabel.append(element("span", "", t.description));
  const descriptionInput = element("textarea") as HTMLTextAreaElement;
  descriptionInput.rows = 3;
  descriptionInput.maxLength = 10000;
  descriptionInput.name = "description";
  descriptionLabel.append(descriptionInput);
  const formGrid = element("div", "ce-form-grid");
  const dueLabel = element("label", "ce-field");
  dueLabel.append(element("span", "", t.due));
  const dueInput = element("input") as HTMLInputElement;
  dueInput.type = "date";
  dueInput.name = "due_at";
  dueLabel.append(dueInput);
  const priorityLabel = element("label", "ce-field");
  priorityLabel.append(element("span", "", t.priority));
  const prioritySelect = element("select") as HTMLSelectElement;
  prioritySelect.name = "priority";
  for (const [value, label] of [["low", t.low], ["normal", t.normal], ["high", t.high], ["urgent", t.urgent]] as const) {
    const option = element("option", "", label) as HTMLOptionElement;
    option.value = value;
    prioritySelect.append(option);
  }
  priorityLabel.append(prioritySelect);
  formGrid.append(dueLabel, priorityLabel);
  const formActions = element("div", "ce-form-actions");
  const cancel = element("button", "ce-button ce-button-secondary", t.cancel);
  cancel.type = "button";
  const submit = element("button", "ce-button ce-button-primary", t.save);
  submit.type = "submit";
  formActions.append(cancel, submit);
  form.append(formTitle, titleLabel, descriptionLabel, formGrid, formActions);

  shell.append(header, hero, toolbar, filters, notice, error, form, listSection, security);
  container.append(shell);

  let tasks: EnterpriseTaskRecord[] = [];
  let nextCursor: TaskListResponse["next_cursor"] = null;
  let busy = false;
  const showError = (message: string): void => { error.textContent = message; error.hidden = false; notice.hidden = true; };
  const showNotice = (message: string): void => { notice.textContent = message; notice.hidden = false; error.hidden = true; };

  const renderTasks = (): void => {
    const visible = filterEnterpriseTasks(tasks, activeFilter, search.value);
    list.replaceChildren();
    listHeader.querySelector(".ce-count")!.textContent = String(visible.length);
    if (!visible.length) {
      list.append(element("p", "ce-empty", t.empty));
    }
    for (const task of visible) {
      const card = element("article", "ce-task-card");
      const body = element("div", "ce-task-body");
      body.append(element("h3", "ce-task-title", task.title));
      if (task.description) body.append(element("p", "ce-task-description", task.description));
      const meta = element("div", "ce-task-meta");
      const statusLabel = task.status === "in_progress" ? t.in_progress
        : task.status === "blocked" ? t.blockedStatus
          : task.status === "completed" ? t.completedStatus
            : task.status === "cancelled" ? t.cancelled : t.open;
      const status = element("span", `ce-badge ce-status-${task.status}`, statusLabel);
      const priority = element("span", `ce-badge ce-priority-${task.priority}`, t[task.priority]);
      const due = element("span", "ce-task-due", task.due_at ? `${t.dueLabel}: ${new Date(task.due_at).toLocaleDateString(locale)}` : t.noDue);
      meta.append(status, priority, due);
      body.append(meta);
      const controls = element("div", "ce-task-actions");
      if (task.status === "open" || task.status === "blocked") {
        const start = element("button", "ce-button ce-button-small ce-button-secondary", t.markProgress);
        start.type = "button";
        start.addEventListener("click", () => { void updateTask(task, "in_progress"); });
        controls.append(start);
      } else if (task.status === "in_progress") {
        const complete = element("button", "ce-button ce-button-small ce-button-primary", t.markComplete);
        complete.type = "button";
        complete.addEventListener("click", () => { void updateTask(task, "completed"); });
        controls.append(complete);
      } else if (task.status === "completed") {
        const reopen = element("button", "ce-button ce-button-small ce-button-secondary", t.reopen);
        reopen.type = "button";
        reopen.addEventListener("click", () => { void updateTask(task, "in_progress"); });
        controls.append(reopen);
      }
      card.append(body, controls);
      list.append(card);
    }
  };

  const loadTasks = async (append = false): Promise<void> => {
    if (busy) return;
    busy = true;
    if (!append) {
      tasks = [];
      nextCursor = null;
      list.replaceChildren(element("p", "ce-empty", t.loading));
    }
    loadMore.disabled = true;
    error.hidden = true;
    try {
      const parameters = new URLSearchParams({ limit: "100" });
      if (scope.value) parameters.set("project_id", scope.value);
      if (append && nextCursor) {
        parameters.set("before_task_id", nextCursor.before_task_id);
        if (nextCursor.before_updated_at) parameters.set("before_updated_at", nextCursor.before_updated_at);
      }
      const result = await taskRequest<TaskListResponse>(`/api/enterprise/tasks?${parameters.toString()}`);
      const page = Array.isArray(result.tasks) ? result.tasks : [];
      tasks = append ? [...tasks, ...page] : page;
      nextCursor = result.next_cursor ?? null;
      renderTasks();
      loadMore.hidden = !nextCursor;
    } catch (reason) {
      showError(reason instanceof Error && reason.message === "SESSION_REQUIRED" ? t.session : t.error);
      list.replaceChildren(element("p", "ce-empty", t.empty));
      loadMore.hidden = true;
    } finally {
      busy = false;
      loadMore.disabled = false;
    }
  };

  const updateTask = async (task: EnterpriseTaskRecord, status: EnterpriseTaskStatus): Promise<void> => {
    const buttons = list.querySelectorAll("button");
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const result = await taskRequest<TaskMutationResponse>(
        `/api/enterprise/tasks/${encodeURIComponent(task.task_id)}`,
        "PATCH",
        { contract_version: "cubi-enterprise-task.v1", expected_revision: task.revision, status },
      );
      tasks = tasks.map((item) => item.task_id === task.task_id ? result.task : item);
      showNotice(t.updated);
      renderTasks();
    } catch (reason) {
      showError(t.updateFailed);
      buttons.forEach((button) => { button.disabled = false; });
    }
  };

  const openForm = (open: boolean): void => {
    form.hidden = !open;
    if (open) titleInput.focus();
    else form.reset();
  };
  createButton.addEventListener("click", () => openForm(form.hidden));
  cancel.addEventListener("click", () => openForm(false));
  refresh.addEventListener("click", () => { void loadTasks(); });
  loadMore.addEventListener("click", () => { void loadTasks(true); });
  search.addEventListener("input", renderTasks);
  scope.addEventListener("change", () => { notice.hidden = true; void loadTasks(); });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = titleInput.value.trim();
    if (!title) { titleInput.setCustomValidity(t.titleRequired); titleInput.reportValidity(); return; }
    titleInput.setCustomValidity("");
    submit.disabled = true;
    try {
      const dueAt = dueInput.value ? new Date(`${dueInput.value}T23:59:00`).toISOString() : null;
      const result = await taskRequest<TaskMutationResponse>(
        "/api/enterprise/tasks", "POST",
        {
          contract_version: "cubi-enterprise-task.v1",
          title,
          description: descriptionInput.value.trim() || null,
          priority: prioritySelect.value,
          project_id: scope.value || null,
          due_at: dueAt,
        },
        taskIdempotencyKey(),
      );
      tasks = [result.task, ...tasks.filter((item) => item.task_id !== result.task.task_id)];
      openForm(false);
      showNotice(t.created);
      renderTasks();
    } catch (reason) {
      showError(t.createFailed);
    } finally {
      submit.disabled = false;
    }
  });

  try {
    const sessionApi = new FetchSessionApi(window.location.origin);
    const session = await sessionApi.getSession();
    if (!session.ok) {
      window.location.assign(`/login?next=${encodeURIComponent("/enterprise")}`);
      return;
    }
    const projects = await sessionApi.listProjects();
    if (projects.ok) {
      for (const project of projects.data.projects) {
        const option = element("option", "", project.name) as HTMLOptionElement;
        option.value = project.project_id;
        scope.append(option);
      }
    }
    await loadTasks();
  } catch {
    showError(t.error);
  }
}
