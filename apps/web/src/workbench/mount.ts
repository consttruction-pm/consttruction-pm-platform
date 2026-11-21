/**
 * Boot and interaction for the CUBI AI Workbench.
 *
 * The shell is rendered once so typing in the command box never loses focus;
 * panels are replaced when server data arrives. Every control either calls an
 * authoritative endpoint or opens a documented state. No control pretends to
 * work.
 */
import {
  WorkbenchApi,
  newCorrelationId,
  type RiskRecord,
  type WorkbenchCommandPlan,
  type WorkbenchContext,
  type WorkspaceReadSnapshot,
} from "./api.js";
import { direction, isWritable, planAction, escapeHtml, t } from "./model.js";
import {
  renderAnalysisStudio,
  renderBlockedStudio,
  renderCommandPlan,
  renderFallbackNotice,
  renderHeader,
  renderInspector,
  renderProjectChooser,
  renderRiskForm,
  renderRiskStudio,
  renderStatusBar,
  renderStudioTabs,
  type ShellState,
} from "./render.js";

const STORAGE_KEY = "cubi.workbench.locale";
const SUPPORTED = ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"];

type ProjectsPayload = {
  projects: { project_id: string; name: string; revision: number }[];
};

function resolveLocale(requested: string | null): string {
  const candidates = [
    requested,
    typeof window === "undefined" ? null : window.localStorage.getItem(STORAGE_KEY),
    typeof window === "undefined" ? null : window.localStorage.getItem("cubi.login.locale"),
    typeof navigator === "undefined" ? null : navigator.language,
  ];
  for (const candidate of candidates) {
    if (!candidate) continue;
    const base = candidate.split("-")[0].toLowerCase();
    if (SUPPORTED.includes(base)) return base;
  }
  return "en";
}

function initialState(locale: string, projectId: string | null): ShellState {
  return {
    locale,
    projectId,
    context: null,
    plan: null,
    activeStudio: "risk-analysis",
    risks: [],
    selectedRisk: null,
    editingRisk: null,
    riskHistory: [],
    historyRisk: null,
    riskNotice: null,
    workspace: null,
    riskError: null,
    analysisError: null,
    baselines: [],
    baselineError: null,
    evm: null,
    evmError: null,
    evmBaselineId: "",
    evmCurrency: "",
    evmDataDate: "",
    loading: null,
    lastUpdated: null,
    connected: typeof navigator === "undefined" ? true : navigator.onLine,
    fallbackNotice: locale.split("-")[0] !== "en",
  };
}

function shellMarkup(locale: string): string {
  return `
    <div class="aiw-shell" dir="${direction(locale)}">
      <div id="aiw-header"></div>
      <div class="aiw-body">
        <aside class="aiw-command" id="aiw-command" aria-label="${escapeHtml(t(locale, "Command panel", "پنل فرمان"))}">
          <header class="aiw-command-header">
            <h2>${escapeHtml(t(locale, "Command", "فرمان"))}</h2>
            <button type="button" data-workbench="toggle-command" aria-label="${escapeHtml(t(locale, "Hide command panel", "پنهان‌کردن پنل فرمان"))}">⟨</button>
          </header>
          <div class="aiw-command-body">
            <div id="aiw-context-chips" class="aiw-context-chips"></div>
            <div id="aiw-plan-region" class="aiw-plan-region"></div>
            <form id="aiw-command-form" class="aiw-command-form" novalidate>
              <label for="aiw-command-input" class="aiw-visually-hidden">${escapeHtml(t(locale, "Command", "فرمان"))}</label>
              <textarea id="aiw-command-input" name="command" rows="3" maxlength="2000" placeholder="${escapeHtml(t(locale, "Describe the engineering task. The assistant opens the right studio; it does not guess data.", "کار مهندسی را بنویسید. دستیار کارگاه مناسب را باز می‌کند و داده‌ای حدس نمی‌زند."))}"></textarea>
              <button type="submit" id="aiw-command-submit">${escapeHtml(t(locale, "Send command", "ارسال فرمان"))}</button>
              <p class="aiw-form-error" id="aiw-command-error" role="alert" hidden></p>
            </form>
            <div id="aiw-history" class="aiw-history" aria-live="polite"></div>
          </div>
        </aside>
        <button type="button" class="aiw-command-restore" data-workbench="toggle-command" hidden aria-label="${escapeHtml(t(locale, "Show command panel", "نمایش پنل فرمان"))}">⟩</button>
        <main class="aiw-main">
          <div id="aiw-tabs"></div>
          <div id="aiw-studio" class="aiw-studio" aria-live="polite"></div>
        </main>
        <aside class="aiw-inspector" id="aiw-inspector" aria-label="${escapeHtml(t(locale, "Inspector", "بازرس"))}">
          <header class="aiw-inspector-header">
            <button type="button" data-workbench="toggle-inspector" aria-label="${escapeHtml(t(locale, "Hide inspector", "پنهان‌کردن بازرس"))}">⟩</button>
            <button type="button" data-workbench="help" aria-label="${escapeHtml(t(locale, "Help", "راهنما"))}">?</button>
          </header>
          <div id="aiw-inspector-body"></div>
        </aside>
      </div>
      <footer class="aiw-status-bar" id="aiw-status" aria-live="polite"></footer>
      <p class="aiw-fallback" id="aiw-fallback" hidden></p>
    </div>`;
}

export type MountOptions = {
  api?: WorkbenchApi;
  root?: HTMLElement;
};

export async function mountWorkbench(options: MountOptions = {}): Promise<void> {
  const found = options.root ?? document.getElementById("aiw-root");
  if (!found) throw new Error("WORKBENCH_ROOT_NOT_FOUND");
  const root: HTMLElement = found;
  const api = options.api ?? new WorkbenchApi();
  const params = new URLSearchParams(window.location.search);
  const locale = resolveLocale(params.get("lang"));
  const projectId = params.get("project");
  document.documentElement.lang = locale;
  document.documentElement.dir = direction(locale);
  root.innerHTML = shellMarkup(locale);

  const state = initialState(locale, projectId);
  const history: WorkbenchCommandPlan[] = [];
  let riskFormOpen = false;
  let helpOpen = false;
  let sessionTenant = "";
  let risksLoaded = false;
  let analysisLoaded = false;
  let riskByIdempotency = new Map<string, string>();
  let projectRevision = 0;

  const el = <T extends HTMLElement>(id: string): T =>
    root.querySelector(`#${id}`) as T;

  function setError(id: string, message: string | null): void {
    const node = root.querySelector<HTMLElement>(`#${id}`);
    if (!node) return;
    node.textContent = message ?? "";
    node.hidden = !message;
  }

  function renderAll(): void {
    el("aiw-header").innerHTML = renderHeader(state);
    el("aiw-tabs").innerHTML = projectId ? renderStudioTabs(state) : "";
    const studio = state.context?.studios.find((item) => item.id === state.activeStudio);
    if (!projectId) {
      // The chooser is rendered separately once projects are loaded.
    } else if (!studio || !studio.can_open) {
      el("aiw-studio").innerHTML = renderBlockedStudio(state.locale, studio ?? null);
    } else if (state.activeStudio === "risk-analysis") {
      el("aiw-studio").innerHTML = renderRiskStudio(state);
    } else if (state.activeStudio === "project-analysis") {
      el("aiw-studio").innerHTML = renderAnalysisStudio(state);
    } else {
      el("aiw-studio").innerHTML = renderPartialStudio(studio);
    }
    el("aiw-inspector-body").innerHTML = helpOpen
      ? renderHelpPanel()
      : riskFormOpen
        ? renderRiskForm(state.locale)
        : renderInspector(state);
    el("aiw-status").innerHTML = renderStatusBar(state);
    const fallback = el("aiw-fallback");
    fallback.innerHTML = state.fallbackNotice ? renderFallbackNotice(state.locale) : "";
    fallback.hidden = !state.fallbackNotice;
    renderPlanRegion();
    renderContextChips();
  }

  function renderPartialStudio(studio: WorkbenchContext["studios"][number]): string {
    return `<section class="aiw-panel aiw-partial" data-partial-studio="${escapeHtml(studio.id)}">
      <h2>${escapeHtml(t(state.locale, studio.id === "decision-approval" ? "Decision & Approval Workspace" : "Staged studio", studio.id === "decision-approval" ? "فضای تصمیم و تأیید" : "کارگاه مرحله‌ای"))}</h2>
      <p class="aiw-status-line"><span class="aiw-status is-partial">${escapeHtml(studio.status)}</span></p>
      <p>${escapeHtml(t(state.locale, "This studio is registered as partial. Only the parts backed by an authoritative service are offered; no proposal or write control is shown until the contract exists.", "این کارگاه به‌صورت جزئی ثبت شده است. فقط بخش‌هایی که سرویس معتبر دارند ارائه می‌شوند؛ تا ایجاد قرارداد، هیچ کنترل پیشنهاد یا نوشتن نمایش داده نمی‌شود."))}</p>
      <dl class="aiw-facts">
        <dt>${escapeHtml(t(state.locale, "Service", "سرویس"))}</dt><dd>${escapeHtml(studio.service)}</dd>
        <dt>${escapeHtml(t(state.locale, "Reason", "علت"))}</dt><dd>${escapeHtml(studio.blocked_reason || "—")}</dd>
      </dl>
    </section>`;
  }

  function renderPlanRegion(): void {
    const region = root.querySelector<HTMLElement>("#aiw-plan-region");
    if (!region) return;
    region.innerHTML = state.plan ? renderCommandPlan(state.locale, state.plan) : "";
  }

  function renderContextChips(): void {
    const region = root.querySelector<HTMLElement>("#aiw-context-chips");
    if (!region) return;
    const context = state.context;
    region.innerHTML = context
      ? `<span class="aiw-chip">${escapeHtml(context.project.name)}</span>
         <span class="aiw-chip">${escapeHtml(t(state.locale, "Revision", "نسخه"))} ${escapeHtml(context.project.revision)}</span>
         <span class="aiw-chip">${escapeHtml(context.permissions.can_propose ? t(state.locale, "Read and propose", "خواندن و پیشنهاد") : t(state.locale, "Read only", "فقط خواندن"))}</span>`
      : "";
  }

  function renderHelpPanel(): string {
    const studios = state.context?.studios ?? [];
    return `<h2>${escapeHtml(t(state.locale, "Help", "راهنما"))}</h2>
      <p class="aiw-hint">${escapeHtml(t(state.locale, "A control is listed only with the service that backs it. Help topics are recorded for the official Engineering reference; an exact deep link is marked pending until verified.", "هر کنترل فقط همراه با سرویس پشتیبان آن فهرست می‌شود. موضوع‌های راهنما برای مرجع رسمی مهندسی ثبت شده‌اند؛ پیوند دقیق تا زمان تأیید، در انتظار علامت‌گذاری می‌شود."))}</p>
      <ul class="aiw-help-list">
        ${studios
          .map(
            (studio) => `<li><strong>${escapeHtml(studio.id)}</strong> · ${escapeHtml(studio.status)}<br /><span>${escapeHtml(studio.help_topic)}</span> · <span>${escapeHtml(studio.help_status)}</span></li>`,
          )
          .join("")}
      </ul>
      <button type="button" data-workbench="help">${escapeHtml(t(state.locale, "Close", "بستن"))}</button>`;
  }

  async function loadSession(): Promise<boolean> {
    const session = await api.session();
    if (!session.ok) {
      redirectToLogin(session.error.code);
      return false;
    }
    sessionTenant = session.data.tenant_id;
    return true;
  }

  async function loadProjects(): Promise<void> {
    if (!(await loadSession())) return;
    const response = await fetch("/api/projects", { credentials: "same-origin" });
    if (!response.ok) {
      el("aiw-studio").innerHTML = `<section class="aiw-panel aiw-error">${escapeHtml(t(state.locale, "Projects could not be read.", "پروژه‌ها خوانده نشدند."))}</section>`;
      return;
    }
    const payload = (await response.json()) as ProjectsPayload;
    el("aiw-studio").innerHTML = renderProjectChooser(state.locale, payload.projects);
    el("aiw-tabs").innerHTML = "";
  }

  function redirectToLogin(code: string): void {
    const next = `${window.location.pathname}${window.location.search}`;
    window.location.assign(`/login?next=${encodeURIComponent(next)}&code=${encodeURIComponent(code)}`);
  }

  async function loadContext(): Promise<void> {
    if (!projectId) return;
    state.loading = "context";
    const result = await api.context(projectId);
    state.loading = null;
    if (!result.ok) {
      if (result.error.code === "SESSION_REQUIRED" || result.error.code === "SESSION_INVALID") {
        redirectToLogin(result.error.code);
        return;
      }
      el("aiw-studio").innerHTML = `<section class="aiw-panel aiw-error" data-context-error="${escapeHtml(result.error.code)}">
        <h2>${escapeHtml(t(state.locale, "Project context could not be loaded", "زمینهٔ پروژه بارگذاری نشد"))}</h2>
        <p>${escapeHtml(result.error.code)}</p>
        <button type="button" data-workbench="reload">${escapeHtml(t(state.locale, "Retry", "تلاش دوباره"))}</button>
      </section>`;
      return;
    }
    state.context = result.data;
    projectRevision = result.data.project.revision;
    state.lastUpdated = new Date().toISOString();
    renderAll();
    if (state.activeStudio === "risk-analysis") await loadRisks();
    if (state.activeStudio === "project-analysis") await loadAnalysis();
  }

  async function loadRisks(): Promise<void> {
    if (!projectId || !state.context) return;
    state.riskError = null;
    const result = await api.risks(projectId, {
      tenant_id: sessionTenant,
      project_id: projectId,
      revision: projectRevision,
    });
    if (!result.ok) {
      state.riskError = `${result.error.code}`;
      state.connected = result.error.code !== "NETWORK_ERROR" && result.error.code !== "NETWORK_TIMEOUT" ? state.connected : false;
      renderAll();
      return;
    }
    state.risks = result.data.risks;
    if (state.selectedRisk && !state.risks.some((risk) => risk.risk_id === state.selectedRisk)) {
      state.selectedRisk = null;
      state.editingRisk = null;
      state.historyRisk = null;
      state.riskHistory = [];
    }
    risksLoaded = true;
    state.lastUpdated = new Date().toISOString();
    renderAll();
  }

  async function loadAnalysis(): Promise<void> {
    if (!projectId) return;
    state.analysisError = null;
    const baselinesPromise = loadBaselines();
    const result = await api.readWorkspace(projectId, {
      tenant_id: sessionTenant,
      project_id: projectId,
      revision: projectRevision,
    });
    if (!result.ok) {
      state.analysisError = `${result.error.code}`;
      state.connected =
        result.error.code === "NETWORK_ERROR" || result.error.code === "NETWORK_TIMEOUT"
          ? false
          : state.connected;
      await baselinesPromise;
      renderAll();
      return;
    }
    state.workspace = result.data as WorkspaceReadSnapshot;
    analysisLoaded = true;
    state.lastUpdated = new Date().toISOString();
    await baselinesPromise;
    renderAll();
  }

  async function loadBaselines(): Promise<void> {
    if (!projectId) return;
    state.baselineError = null;
    const result = await api.baselines(projectId, {
      tenant_id: sessionTenant,
      project_id: projectId,
      revision: projectRevision,
    });
    if (!result.ok) {
      state.baselineError = `${result.error.code}`;
      return;
    }
    state.baselines = result.data.baselines.map((entry) => entry.baseline);
    if (
      !state.evmBaselineId ||
      !state.baselines.some((baseline) => baseline.baseline_id === state.evmBaselineId)
    ) {
      state.evmBaselineId = state.baselines[0]?.baseline_id ?? "";
    }
    if (!state.evmDataDate) {
      state.evmDataDate = state.context?.data_date ?? "";
    }
  }

  async function readEarnedValue(): Promise<void> {
    if (!projectId) return;
    const form = root.querySelector<HTMLFormElement>('[data-workbench="evm-form"]');
    if (!form) return;
    const data = new FormData(form);
    const baselineId = String(data.get("baseline_id") ?? "").trim();
    const currency = String(data.get("currency") ?? "").trim().toUpperCase();
    const dataDate = String(data.get("data_date") ?? "").trim();
    if (!baselineId || !/^[A-Z]{3}$/.test(currency) || !dataDate) {
      state.evmError = t(
        state.locale,
        "Select a baseline and enter a three-letter currency and a data date.",
        "یک مبنا انتخاب کنید و واحد پول سه‌حرفی و تاریخ داده را وارد کنید.",
      );
      renderAll();
      return;
    }
    state.evmBaselineId = baselineId;
    state.evmCurrency = currency;
    state.evmDataDate = dataDate;
    const result = await api.earnedValue(
      projectId,
      { baseline_id: baselineId, data_date: dataDate, currency },
      { tenant_id: sessionTenant, project_id: projectId, revision: projectRevision },
    );
    if (!result.ok) {
      state.evm = null;
      state.evmError = `${result.error.code}`;
      renderAll();
      return;
    }
    state.evmError = null;
    state.evm = result.data;
    renderAll();
  }

  async function submitCommand(text: string): Promise<void> {
    if (!projectId || !state.context) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    setError("aiw-command-error", null);
    const submit = root.querySelector<HTMLButtonElement>("#aiw-command-submit");
    if (submit) submit.disabled = true;
    const result = await api.command(
      projectId,
      {
        command: trimmed,
        locale: state.locale,
        correlation_id: newCorrelationId(),
      },
      { tenant_id: sessionTenant, project_id: projectId, revision: projectRevision },
    );
    if (submit) submit.disabled = false;
    if (!result.ok) {
      state.connected =
        result.error.code === "NETWORK_ERROR" || result.error.code === "NETWORK_TIMEOUT"
          ? false
          : state.connected;
      setError("aiw-command-error", result.error.code);
      return;
    }
    state.plan = result.data;
    history.unshift(result.data);
    const action = planAction(result.data);
    const historyNode = el("aiw-history");
    historyNode.innerHTML = history
      .slice(0, 5)
      .map(
        (plan) =>
          `<button type="button" class="aiw-history-item" data-workbench="replay-plan" data-plan-id="${escapeHtml(plan.correlation_id)}">
            <span>${escapeHtml((plan.command || plan.intent || "").slice(0, 80))}</span>
            <em>${escapeHtml(plan.studio ?? plan.intent)}</em>
          </button>`,
      )
      .join("");
    state.lastUpdated = new Date().toISOString();
    renderAll();
    if (action.openStudio) {
      state.activeStudio = action.openStudio;
      renderAll();
      if (action.openStudio === "risk-analysis" && !risksLoaded) await loadRisks();
      if (action.openStudio === "project-analysis" && !analysisLoaded) await loadAnalysis();
    }
  }

  function readRiskForm(): Record<string, unknown> | null {
    const form = root.querySelector<HTMLFormElement>('[data-workbench="risk-form"]');
    if (!form) return null;
    const data = new FormData(form);
    const value = (key: string): string => String(data.get(key) ?? "").trim();
    const probability = Number(value("probability"));
    const impact = Number(value("impact"));
    if (!value("risk_id") || !value("title") || !value("owner") || !value("date_identified")) {
      return null;
    }
    if (!Number.isInteger(probability) || probability < 1 || probability > 5) return null;
    if (!Number.isInteger(impact) || impact < 1 || impact > 5) return null;
    return {
      risk_id: value("risk_id"),
      title: value("title"),
      description: value("description"),
      category: value("category"),
      status: "open",
      probability,
      impact,
      response_strategy: value("response_strategy"),
      owner: value("owner"),
      date_identified: value("date_identified"),
    };
  }

  async function saveRisk(): Promise<void> {
    if (!projectId) return;
    const body = readRiskForm();
    if (!body) {
      setError("aiw-command-error", null);
      const formError = root.querySelector<HTMLElement>("[data-risk-form-error]");
      if (formError) {
        formError.textContent = t(
          state.locale,
          "Risk ID, title, owner and date are required; probability and impact must be 1 to 5.",
          "شناسه، عنوان، مالک و تاریخ الزامی است؛ احتمال و اثر باید بین ۱ تا ۵ باشد.",
        );
        formError.hidden = false;
      }
      return;
    }
    const riskId = String(body.risk_id);
    let key = riskByIdempotency.get(riskId);
    if (!key) {
      key = newCorrelationId("risk");
      riskByIdempotency.set(riskId, key);
    }
    const result = await api.createRisk(
      projectId,
      body,
      { tenant_id: sessionTenant, project_id: projectId, revision: projectRevision },
      key,
    );
    const formError = root.querySelector<HTMLElement>("[data-risk-form-error]");
    if (!result.ok) {
      if (formError) {
        formError.textContent = `${result.error.code}`;
        formError.hidden = false;
      }
      if (result.error.code === "RISK_IDEMPOTENCY_REUSE" || result.error.code.includes("CONFLICT")) {
        // The first attempt already stored the record: read it back instead of
        // creating a duplicate.
        riskByIdempotency.delete(riskId);
        await loadRisks();
      }
      return;
    }
    riskByIdempotency.delete(riskId);
    riskFormOpen = false;
    state.selectedRisk = result.data.risk_id;
    await loadRisks();
  }

  function readRiskEditForm(): { riskId: string; body: Record<string, unknown> } | null {
    const form = root.querySelector<HTMLFormElement>('[data-workbench="risk-edit-form"]');
    if (!form) return null;
    const data = new FormData(form);
    const value = (key: string): string => String(data.get(key) ?? "").trim();
    const probability = Number(value("probability"));
    const impact = Number(value("impact"));
    const expected = Number(value("expected_revision"));
    const riskId = value("risk_id");
    if (!riskId || !value("title") || !value("owner") || !value("date_identified")) return null;
    if (!Number.isInteger(probability) || probability < 1 || probability > 5) return null;
    if (!Number.isInteger(impact) || impact < 1 || impact > 5) return null;
    if (!Number.isInteger(expected) || expected < 1) return null;
    return {
      riskId,
      body: {
        risk_id: riskId,
        title: value("title"),
        description: value("description"),
        category: value("category"),
        status: value("status"),
        probability,
        impact,
        response_strategy: value("response_strategy"),
        owner: value("owner"),
        date_identified: value("date_identified"),
        expected_revision: expected,
        reason: value("reason"),
      },
    };
  }

  async function saveRiskEdit(): Promise<void> {
    if (!projectId) return;
    const formError = root.querySelector<HTMLElement>("[data-risk-form-error]");
    const draft = readRiskEditForm();
    if (!draft) {
      if (formError) {
        formError.textContent = t(
          state.locale,
          "Title, owner and date are required; probability, impact and revision must be valid.",
          "عنوان، مالک و تاریخ الزامی است؛ احتمال، اثر و نسخه باید معتبر باشند.",
        );
        formError.hidden = false;
      }
      return;
    }
    const result = await api.updateRisk(projectId, draft.riskId, draft.body, {
      tenant_id: sessionTenant,
      project_id: projectId,
      revision: projectRevision,
    });
    if (!result.ok) {
      if (formError) {
        formError.textContent = `${result.error.code}`;
        formError.hidden = false;
      }
      if (result.error.code.includes("CONFLICT") || result.error.code.includes("REVISION")) {
        // Another writer advanced the record: re-read instead of overwriting.
        await loadRisks();
      }
      return;
    }
    state.editingRisk = null;
    state.selectedRisk = result.data.risk_id;
    state.riskNotice = t(
      state.locale,
      "Saved. The record is now at revision",
      "ذخیره شد. رکورد اکنون در نسخهٔ",
    ) + ` ${result.data.revision}.`;
    await loadRisks();
  }

  async function loadRiskHistory(riskId: string): Promise<void> {
    if (!projectId) return;
    state.riskHistory = [];
    const result = await api.riskHistory(projectId, riskId, {
      tenant_id: sessionTenant,
      project_id: projectId,
      revision: projectRevision,
    });
    state.historyRisk = riskId;
    if (!result.ok) {
      state.riskNotice = `${result.error.code}`;
    } else {
      state.riskHistory = result.data.events;
    }
    renderAll();
  }

  function switchStudio(id: string): void {
    state.activeStudio = id;
    riskFormOpen = false;
    helpOpen = false;
    state.editingRisk = null;
    state.historyRisk = null;
    state.riskNotice = null;
    renderAll();
    // Navigation always re-reads the authoritative service; the studio never
    // presents a cached write as current.
    if (id === "risk-analysis") void loadRisks();
    if (id === "project-analysis") void loadAnalysis();
  }

  root.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-workbench]");
    if (!target) return;
    const action = target.dataset.workbench;
    switch (action) {
      case "toggle-command": {
        const shell = root.querySelector<HTMLElement>(".aiw-shell");
        const collapsed = shell?.classList.toggle("is-command-collapsed");
        const restore = root.querySelector<HTMLElement>(".aiw-command-restore");
        if (restore) restore.hidden = !collapsed;
        break;
      }
      case "toggle-inspector": {
        const shell = root.querySelector<HTMLElement>(".aiw-shell");
        shell?.classList.toggle("is-inspector-collapsed");
        break;
      }
      case "studio":
        if (target.dataset.studio) switchStudio(target.dataset.studio);
        break;
      case "open-studio":
        if (target.dataset.studio) switchStudio(target.dataset.studio);
        break;
      case "answer": {
        const input = root.querySelector<HTMLTextAreaElement>("#aiw-command-input");
        if (input) input.value = target.dataset.label ?? target.textContent ?? "";
        void submitCommand(input?.value ?? "");
        break;
      }
      case "select-risk":
        if (target.dataset.risk) {
          state.selectedRisk = target.dataset.risk;
          state.editingRisk = null;
          state.historyRisk = null;
          state.riskNotice = null;
          renderAll();
        }
        break;
      case "edit-risk":
        if (state.selectedRisk) {
          state.editingRisk = state.selectedRisk;
          state.historyRisk = null;
          helpOpen = false;
          riskFormOpen = false;
          renderAll();
        }
        break;
      case "cancel-edit":
        state.editingRisk = null;
        renderAll();
        break;
      case "show-history":
        if (state.selectedRisk) void loadRiskHistory(state.selectedRisk);
        break;
      case "close-history":
        state.historyRisk = null;
        state.riskHistory = [];
        renderAll();
        break;
      case "matrix-cell": {
        const probability = Number(target.dataset.probability);
        const impact = Number(target.dataset.impact);
        const match = state.risks.find(
          (risk) => risk.probability === probability && risk.impact === impact,
        );
        if (match) {
          state.selectedRisk = match.risk_id;
          state.editingRisk = null;
          state.historyRisk = null;
          renderAll();
        }
        break;
      }
      case "new-risk":
        riskFormOpen = true;
        helpOpen = false;
        state.editingRisk = null;
        state.historyRisk = null;
        renderAll();
        break;
      case "cancel-risk":
        riskFormOpen = false;
        renderAll();
        break;
      case "retry-risks":
        void loadRisks();
        break;
      case "retry-analysis":
        void loadAnalysis();
        break;
      case "retry-baselines":
        state.baselineError = null;
        void loadBaselines().then(() => renderAll());
        break;
      case "reload":
        window.location.reload();
        break;
      case "help":
        helpOpen = !helpOpen;
        riskFormOpen = false;
        renderAll();
        break;
      case "replay-plan": {
        const plan = history.find((item) => item.correlation_id === target.dataset.planId);
        if (plan) {
          state.plan = plan;
          renderAll();
        }
        break;
      }
      default:
        break;
    }
  });

  root.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (form.id === "aiw-command-form") {
      event.preventDefault();
      const input = root.querySelector<HTMLTextAreaElement>("#aiw-command-input");
      void submitCommand(input?.value ?? "");
      return;
    }
    if (form.matches('[data-workbench="risk-form"]')) {
      event.preventDefault();
      void saveRisk();
      return;
    }
    if (form.matches('[data-workbench="risk-edit-form"]')) {
      event.preventDefault();
      void saveRiskEdit();
      return;
    }
    if (form.matches('[data-workbench="evm-form"]')) {
      event.preventDefault();
      void readEarnedValue();
    }
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.matches('[data-workbench="locale"]')) {
      const next = resolveLocale(target.value);
      window.localStorage.setItem(STORAGE_KEY, next);
      const url = new URL(window.location.href);
      url.searchParams.set("lang", next);
      window.location.assign(url.toString());
    }
  });

  window.addEventListener("online", () => {
    state.connected = true;
    renderAll();
  });
  window.addEventListener("offline", () => {
    state.connected = false;
    renderAll();
  });

  if (!projectId) {
    await loadProjects();
    el("aiw-status").innerHTML = renderStatusBar(state);
    return;
  }
  // The session supplies the tenant used by the risk and analysis read
  // headers; the context endpoint supplies the project and revision.
  if (await loadSession()) await loadContext();
}

/** True when a project is pinned for every command and studio. */
export function hasProjectScope(projectId: string | null): boolean {
  return Boolean(projectId && projectId.trim().length > 0);
}

export { isWritable };
