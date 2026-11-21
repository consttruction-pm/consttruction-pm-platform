/**
 * Server-rendered markup for the CUBI AI Workbench shell and studios.
 *
 * Every dynamic value is escaped. A studio that the server marked BLOCKED is
 * never rendered with live controls: it shows its status, the missing canonical
 * service and the acceptance gate instead.
 */
import type {
  AIActionProposal,
  BaselineRecord,
  EarnedValueSnapshot,
  RiskHistoryEvent,
  RiskRecord,
  WorkbenchCommandPlan,
  WorkbenchContext,
  WorkbenchStudio,
  WorkspaceReadSnapshot,
} from "./api.js";
import {
  STUDIO_ORDER,
  analysisCounts,
  escapeHtml,
  formatDate,
  formatDateTime,
  formatNumber,
  metricRows,
  metricSourceSummary,
  proposalStatusLabel,
  proposalStatusTone,
  riskMatrix,
  statusLabel,
  statusTone,
  studioLabel,
  t,
} from "./model.js";

export type ShellState = {
  locale: string;
  projectId: string | null;
  context: WorkbenchContext | null;
  plan: WorkbenchCommandPlan | null;
  activeStudio: string;
  risks: readonly RiskRecord[];
  selectedRisk: string | null;
  editingRisk: string | null;
  riskHistory: readonly RiskHistoryEvent[];
  historyRisk: string | null;
  riskNotice: string | null;
  workspace: WorkspaceReadSnapshot | null;
  riskError: string | null;
  analysisError: string | null;
  baselines: readonly BaselineRecord[];
  baselineError: string | null;
  evm: EarnedValueSnapshot | null;
  evmError: string | null;
  evmBaselineId: string;
  evmCurrency: string;
  evmDataDate: string;
  proposals: readonly AIActionProposal[];
  proposalError: string | null;
  proposalNotice: string | null;
  proposalBusy: string | null;
  loading: string | null;
  lastUpdated: string | null;
  connected: boolean;
  fallbackNotice: boolean;
};

function chip(locale: string, label: string, value: string, tone = ""): string {
  return `<span class="aiw-chip ${tone}"><span class="aiw-chip-label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></span>`;
}

export function renderHeader(state: ShellState): string {
  const { locale, context } = state;
  const project = context?.project;
  const back = state.projectId
    ? `/app?project=${encodeURIComponent(state.projectId)}&view=live`
    : "/app";
  return `
    <header class="aiw-header">
      <div class="aiw-header-identity">
        <a class="aiw-back" href="${escapeHtml(back)}" data-workbench="back">← ${escapeHtml(t(locale, "Workspace", "محیط کار"))}</a>
        <div>
          <p class="aiw-eyebrow">${escapeHtml(t(locale, "Engineering", "مهندسی"))} · ${escapeHtml(t(locale, "AI Workbench", "کارگاه هوشمند"))}</p>
          <h1>${escapeHtml(project ? project.name : t(locale, "No project selected", "پروژه‌ای انتخاب نشده"))}</h1>
          <p class="aiw-project-id">${escapeHtml(project ? project.project_id : "—")}</p>
        </div>
      </div>
      <div class="aiw-header-meta">
        ${chip(locale, t(locale, "Revision", "نسخه"), project ? String(project.revision) : "—")}
        ${chip(locale, t(locale, "Data date", "تاریخ داده"), context?.data_date ? formatDate(locale, context.data_date) : t(locale, "Not published", "منتشر نشده"))}
        ${chip(locale, t(locale, "Access", "دسترسی"), context?.permissions.can_propose ? t(locale, "Read and propose", "خواندن و پیشنهاد") : t(locale, "Read only", "فقط خواندن"), context?.permissions.can_propose ? "is-live" : "is-read")}
        <label class="aiw-locale">
          <span>${escapeHtml(t(locale, "Language", "زبان"))}</span>
          <select data-workbench="locale" aria-label="${escapeHtml(t(locale, "Interface language", "زبان رابط"))}">
            ${[
              ["en", "English"],
              ["fa", "فارسی"],
              ["de", "Deutsch"],
              ["zh", "中文"],
              ["ar", "العربية"],
              ["fr", "Français"],
              ["ja", "日本語"],
              ["ko", "한국어"],
              ["ru", "Русский"],
              ["tr", "Türkçe"],
            ]
              .map(
                ([value, label]) =>
                  `<option value="${value}"${value === state.locale ? " selected" : ""}>${escapeHtml(label)}</option>`,
              )
              .join("")}
          </select>
        </label>
      </div>
    </header>`;
}

export function renderStudioTabs(state: ShellState): string {
  const { locale } = state;
  return `
    <nav class="aiw-studios" role="tablist" aria-label="${escapeHtml(t(locale, "Workbench studios", "کارگاه‌های هوشمند"))}">
      ${STUDIO_ORDER.map((id) => {
        const studio = state.context?.studios.find((item) => item.id === id);
        const status = studio ? studio.status : "PLANNED";
        const active = state.activeStudio === id;
        return `<button type="button" role="tab" data-workbench="studio" data-studio="${id}" aria-selected="${active}" class="${active ? "is-active" : ""}">
          <span>${escapeHtml(studioLabel(locale, id))}</span>
          <em class="aiw-status ${statusTone(status)}">${escapeHtml(statusLabel(locale, status))}</em>
        </button>`;
      }).join("")}
    </nav>`;
}

export function renderBlockedStudio(locale: string, studio: WorkbenchStudio | null): string {
  if (!studio) {
    return `<section class="aiw-panel aiw-empty">${escapeHtml(t(locale, "This studio is not registered on the server.", "این کارگاه در سرور ثبت نشده است."))}</section>`;
  }
  return `
    <section class="aiw-panel aiw-blocked" data-blocked-studio="${escapeHtml(studio.id)}">
      <h2>${escapeHtml(studioLabel(locale, studio.id))}</h2>
      <p class="aiw-status-line"><span class="aiw-status ${statusTone(studio.status)}">${escapeHtml(statusLabel(locale, studio.status))}</span></p>
      <p>${escapeHtml(t(locale, "This studio is not operational. No control is shown as working and no project data is displayed.", "این کارگاه عملیاتی نیست. هیچ کنترلی عملیاتی نشان داده نمی‌شود و داده‌ای از پروژه نمایش داده نمی‌شود."))}</p>
      <dl class="aiw-facts">
        <dt>${escapeHtml(t(locale, "Canonical service", "سرویس کانونی"))}</dt><dd>${escapeHtml(studio.service)}</dd>
        <dt>${escapeHtml(t(locale, "Reason", "علت"))}</dt><dd>${escapeHtml(studio.blocked_reason || t(locale, "Not recorded.", "ثبت نشده است."))}</dd>
        <dt>${escapeHtml(t(locale, "Help topic", "موضوع راهنما"))}</dt><dd>${escapeHtml(studio.help_topic)} (${escapeHtml(studio.help_status)})</dd>
      </dl>
    </section>`;
}

export function renderProjectChooser(
  locale: string,
  projects: readonly { project_id: string; name: string; revision: number }[],
): string {
  if (projects.length === 0) {
    return `<section class="aiw-panel aiw-empty">${escapeHtml(t(locale, "You are not authorized for any project yet.", "هنوز به هیچ پروژه‌ای دسترسی ندارید."))}</section>`;
  }
  return `
    <section class="aiw-panel">
      <h2>${escapeHtml(t(locale, "Choose a project", "یک پروژه انتخاب کنید"))}</h2>
      <p>${escapeHtml(t(locale, "The Workbench pins one project revision for every command and studio.", "کارگاه هوشمند برای هر فرمان و کارگاه، یک نسخهٔ پروژه را ثابت می‌کند."))}</p>
      <ul class="aiw-project-list">
        ${projects
          .map(
            (project) =>
              `<li><a href="/ai-workbench?project=${encodeURIComponent(project.project_id)}" data-workbench="open-project" data-project="${escapeHtml(project.project_id)}">
                <strong>${escapeHtml(project.name)}</strong>
                <span>${escapeHtml(project.project_id)} · ${escapeHtml(t(locale, "revision", "نسخه"))} ${escapeHtml(project.revision)}</span>
              </a></li>`,
          )
          .join("")}
      </ul>
    </section>`;
}

function listBlock(locale: string, title: string, persianTitle: string, values: readonly string[], emptyText: string, persianEmpty: string): string {
  return `
    <div class="aiw-plan-block">
      <h4>${escapeHtml(t(locale, title, persianTitle))}</h4>
      ${
        values.length === 0
          ? `<p class="aiw-empty-line">${escapeHtml(t(locale, emptyText, persianEmpty))}</p>`
          : `<ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`
      }
    </div>`;
}

export function renderCommandPlan(locale: string, plan: WorkbenchCommandPlan): string {
  const status = plan.status;
  return `
    <article class="aiw-plan" data-plan="${escapeHtml(plan.correlation_id)}">
      <header>
        <span class="aiw-status ${statusTone(status)}">${escapeHtml(statusLabel(locale, status))}</span>
        <code>${escapeHtml(plan.intent)}</code>
      </header>
      ${plan.studio ? `<p class="aiw-plan-studio">${escapeHtml(studioLabel(locale, plan.studio))}</p>` : ""}
      ${plan.reason ? `<p class="aiw-reason">${escapeHtml(plan.reason)}</p>` : ""}
      ${
        plan.refusal
          ? `<p class="aiw-refusal" data-refusal="${escapeHtml(plan.refusal)}">${escapeHtml(t(locale, "Not executed:", "اجرا نشد:"))} ${escapeHtml(plan.refusal)}</p>`
          : ""
      }
      ${
        plan.questions.length > 0
          ? `<div class="aiw-question" data-question="${escapeHtml(plan.questions[0].id)}">
              <p>${escapeHtml(plan.questions[0].prompt)}</p>
              <div class="aiw-options">
                ${plan.questions[0].options
                  .map(
                    (option) =>
                      `<button type="button" data-workbench="answer" data-answer="${escapeHtml(option.value)}" data-label="${escapeHtml(option.label)}">${escapeHtml(option.label)}</button>`,
                  )
                  .join("")}
              </div>
            </div>`
          : ""
      }
      ${plan.can_open && plan.studio ? `<button type="button" class="aiw-open-studio" data-workbench="open-studio" data-studio="${escapeHtml(plan.studio)}">${escapeHtml(t(locale, "Open studio", "بازکردن کارگاه"))}</button>` : ""}
      <div class="aiw-plan-blocks">
        ${listBlock(locale, "Facts", "واقعیت‌ها", plan.facts, "No server fact was reported.", "هیچ واقعیت سروری گزارش نشد.")}
        ${listBlock(locale, "Calculation", "محاسبه", plan.calculated, "No calculation was run for this command.", "برای این فرمان هیچ محاسبه‌ای اجرا نشد.")}
        ${listBlock(locale, "Assumptions", "فرض‌ها", plan.assumptions, "No assumption was recorded.", "هیچ فرضی ثبت نشد.")}
        ${listBlock(locale, "Recommendations", "توصیه‌ها", plan.recommendations, "No recommendation exists until an authoritative run completes.", "تا تکمیل یک اجرای معتبر، توصیه‌ای وجود ندارد.")}
      </div>
      <footer>
        <span>${escapeHtml(plan.correlation_id)}</span>
        <span>${escapeHtml(formatDateTime(locale, plan.resolved_at))}</span>
      </footer>
    </article>`;
}

export function renderRiskStudio(state: ShellState): string {
  const { locale, risks } = state;
  if (state.riskError) {
    return `<section class="aiw-panel aiw-error" data-risk-error>
      <h2>${escapeHtml(t(locale, "Risk register could not be read", "فهرست ریسک خوانده نشد"))}</h2>
      <p>${escapeHtml(state.riskError)}</p>
      <button type="button" data-workbench="retry-risks">${escapeHtml(t(locale, "Retry", "تلاش دوباره"))}</button>
    </section>`;
  }
  if (state.risks.length === 0) {
    return `<section class="aiw-panel aiw-empty" data-risk-empty>
      <h2>${escapeHtml(t(locale, "Risk register", "فهرست ریسک"))}</h2>
      <p>${escapeHtml(t(locale, "No risk is stored for this project revision. Nothing is generated for display.", "برای این نسخهٔ پروژه ریسکی ذخیره نشده است. هیچ رکوردی برای نمایش ساخته نمی‌شود."))}</p>
      ${state.context?.permissions.can_propose ? `<button type="button" data-workbench="new-risk">${escapeHtml(t(locale, "Add the first risk", "افزودن اولین ریسک"))}</button>` : ""}
    </section>`;
  }
  return `
    <div class="aiw-risk-layout">
      <section class="aiw-panel">
        <header class="aiw-panel-header">
          <h2>${escapeHtml(t(locale, "Risk register", "فهرست ریسک"))}</h2>
          <span>${escapeHtml(t(locale, "records", "رکورد"))}: ${formatNumber(locale, state.risks.length)}</span>
          ${state.context?.permissions.can_propose ? `<button type="button" data-workbench="new-risk">${escapeHtml(t(locale, "New risk", "ریسک جدید"))}</button>` : ""}
        </header>
        ${state.riskNotice ? `<p class="aiw-hint" data-risk-notice role="status">${escapeHtml(state.riskNotice)}</p>` : ""}
        <table class="aiw-table" data-risk-table>
          <thead>
            <tr>
              <th>${escapeHtml(t(locale, "Risk ID", "شناسه ریسک"))}</th>
              <th>${escapeHtml(t(locale, "Title", "عنوان"))}</th>
              <th>${escapeHtml(t(locale, "Category", "دسته"))}</th>
              <th>${escapeHtml(t(locale, "Probability", "احتمال"))}</th>
              <th>${escapeHtml(t(locale, "Impact", "اثر"))}</th>
              <th>${escapeHtml(t(locale, "Score", "امتیاز"))}</th>
              <th>${escapeHtml(t(locale, "Status", "وضعیت"))}</th>
              <th>${escapeHtml(t(locale, "Revision", "نسخه"))}</th>
            </tr>
          </thead>
          <tbody>
            ${state.risks
              .map(
                (risk) => `<tr data-workbench="select-risk" data-risk="${escapeHtml(risk.risk_id)}" class="${state.selectedRisk === risk.risk_id ? "is-selected" : ""}" tabindex="0">
                  <td>${escapeHtml(risk.risk_id)}</td>
                  <td>${escapeHtml(risk.title)}</td>
                  <td>${escapeHtml(risk.category)}</td>
                  <td>${escapeHtml(risk.probability)}</td>
                  <td>${escapeHtml(risk.impact)}</td>
                  <td>${escapeHtml(risk.score)}</td>
                  <td>${escapeHtml(risk.status)}</td>
                  <td>${escapeHtml(risk.revision)}</td>
                </tr>`,
              )
              .join("")}
          </tbody>
        </table>
      </section>
      <section class="aiw-panel">
        <h2>${escapeHtml(t(locale, "Risk matrix", "ماتریس ریسک"))}</h2>
        <p class="aiw-hint">${escapeHtml(t(locale, "Rows: probability 5 to 1. Columns: impact 1 to 5. Cells group stored ratings; no rating is recalculated.", "سطرها: احتمال ۵ تا ۱. ستون‌ها: اثر ۱ تا ۵. خانه‌ها امتیازهای ذخیره‌شده را گروه‌بندی می‌کنند؛ هیچ امتیازی بازمحاسبه نمی‌شود."))}</p>
        <div class="aiw-matrix" role="grid" data-risk-matrix>
          ${riskMatrix(state.risks)
            .map(
              (cell) => `<button type="button" role="gridcell" class="aiw-matrix-cell${cell.risks.length ? " has-risks" : ""}" data-workbench="matrix-cell" data-probability="${cell.probability}" data-impact="${cell.impact}" aria-label="${escapeHtml(`P${cell.probability} I${cell.impact}`)}">
                <span class="aiw-matrix-axis">${escapeHtml(`P${cell.probability} · I${cell.impact}`)}</span>
                <strong>${escapeHtml(cell.risks.length)}</strong>
              </button>`,
            )
            .join("")}
        </div>
      </section>
    </div>`;
}

export function renderRiskForm(locale: string): string {
  return `
    <form class="aiw-form" data-workbench="risk-form" novalidate>
      <h3>${escapeHtml(t(locale, "New risk", "ریسک جدید"))}</h3>
      <label>${escapeHtml(t(locale, "Risk ID", "شناسه ریسک"))}<input name="risk_id" required maxlength="40" autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Title", "عنوان"))}<input name="title" required maxlength="160" autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Description", "توضیح"))}<textarea name="description" rows="3" maxlength="2000"></textarea></label>
      <label>${escapeHtml(t(locale, "Category", "دسته"))}
        <select name="category">
          ${["technical", "commercial", "schedule", "cost", "quality", "safety", "resource", "external"].map((value) => `<option value="${value}">${escapeHtml(value)}</option>`).join("")}
        </select>
      </label>
      <label>${escapeHtml(t(locale, "Probability (1-5)", "احتمال (۱ تا ۵)"))}<input name="probability" type="number" min="1" max="5" value="3" required /></label>
      <label>${escapeHtml(t(locale, "Impact (1-5)", "اثر (۱ تا ۵)"))}<input name="impact" type="number" min="1" max="5" value="3" required /></label>
      <label>${escapeHtml(t(locale, "Owner", "مالک"))}<input name="owner" required maxlength="80" autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Response strategy", "راهبرد پاسخ"))}
        <select name="response_strategy">
          ${["avoid", "transfer", "mitigate", "accept", "escalate"].map((value) => `<option value="${value}"${value === "mitigate" ? " selected" : ""}>${escapeHtml(value)}</option>`).join("")}
        </select>
      </label>
      <label>${escapeHtml(t(locale, "Date identified", "تاریخ شناسایی"))}<input name="date_identified" type="date" required /></label>
      <p class="aiw-form-error" data-risk-form-error role="alert" hidden></p>
      <div class="aiw-form-actions">
        <button type="submit">${escapeHtml(t(locale, "Save risk", "ذخیره ریسک"))}</button>
        <button type="button" data-workbench="cancel-risk">${escapeHtml(t(locale, "Cancel", "انصراف"))}</button>
      </div>
    </form>`;
}

const RISK_CATEGORIES = [
  "technical",
  "commercial",
  "schedule",
  "cost",
  "quality",
  "safety",
  "resource",
  "external",
] as const;
const RISK_STRATEGIES = ["avoid", "transfer", "mitigate", "accept", "escalate"] as const;
const RISK_STATUSES = ["open", "monitoring", "mitigating", "closed"] as const;

function option(value: string, selected: string): string {
  return `<option value="${escapeHtml(value)}"${value === selected ? " selected" : ""}>${escapeHtml(value)}</option>`;
}

export function renderRiskEditForm(locale: string, risk: RiskRecord): string {
  return `
    <form class="aiw-form" data-workbench="risk-edit-form" data-risk="${escapeHtml(risk.risk_id)}" novalidate>
      <h3>${escapeHtml(t(locale, "Edit risk", "ویرایش ریسک"))}</h3>
      <p class="aiw-hint">${escapeHtml(t(locale, "Optimistic locking: this edit submits revision", "قفل خوش‌بینانه: این ویرایش نسخه را ارسال می‌کند"))} ${escapeHtml(risk.revision)}.</p>
      <input type="hidden" name="expected_revision" value="${escapeHtml(risk.revision)}" />
      <label>${escapeHtml(t(locale, "Risk ID", "شناسه ریسک"))}<input name="risk_id" value="${escapeHtml(risk.risk_id)}" readonly /></label>
      <label>${escapeHtml(t(locale, "Title", "عنوان"))}<input name="title" required maxlength="160" value="${escapeHtml(risk.title)}" autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Description", "توضیح"))}<textarea name="description" rows="3" maxlength="2000">${escapeHtml(risk.description)}</textarea></label>
      <label>${escapeHtml(t(locale, "Category", "دسته"))}
        <select name="category">${RISK_CATEGORIES.map((value) => option(value, risk.category)).join("")}</select>
      </label>
      <label>${escapeHtml(t(locale, "Status", "وضعیت"))}
        <select name="status">${RISK_STATUSES.map((value) => option(value, risk.status)).join("")}</select>
      </label>
      <label>${escapeHtml(t(locale, "Probability (1-5)", "احتمال (۱ تا ۵)"))}<input name="probability" type="number" min="1" max="5" value="${escapeHtml(risk.probability)}" required /></label>
      <label>${escapeHtml(t(locale, "Impact (1-5)", "اثر (۱ تا ۵)"))}<input name="impact" type="number" min="1" max="5" value="${escapeHtml(risk.impact)}" required /></label>
      <label>${escapeHtml(t(locale, "Owner", "مالک"))}<input name="owner" required maxlength="80" value="${escapeHtml(risk.owner)}" autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Response strategy", "راهبرد پاسخ"))}
        <select name="response_strategy">${RISK_STRATEGIES.map((value) => option(value, risk.response_strategy)).join("")}</select>
      </label>
      <label>${escapeHtml(t(locale, "Date identified", "تاریخ شناسایی"))}<input name="date_identified" type="date" value="${escapeHtml(risk.date_identified)}" required /></label>
      <label>${escapeHtml(t(locale, "Change reason", "علت تغییر"))}<input name="reason" maxlength="200" autocomplete="off" /></label>
      <p class="aiw-form-error" data-risk-form-error role="alert" hidden></p>
      <div class="aiw-form-actions">
        <button type="submit">${escapeHtml(t(locale, "Save changes", "ذخیره تغییرات"))}</button>
        <button type="button" data-workbench="cancel-edit">${escapeHtml(t(locale, "Cancel", "انصراف"))}</button>
      </div>
    </form>`;
}

export function renderRiskHistory(
  locale: string,
  riskId: string,
  events: readonly RiskHistoryEvent[],
): string {
  return `
    <h2>${escapeHtml(t(locale, "Risk history", "تاریخچهٔ ریسک"))}</h2>
    <p class="aiw-hint">${escapeHtml(riskId)}</p>
    ${
      events.length === 0
        ? `<p class="aiw-empty-line">${escapeHtml(t(locale, "The audit service returned no event for this risk.", "سرویس حسابرسی رویدادی برای این ریسک برنگرداند."))}</p>`
        : `<ul class="aiw-history" data-risk-history>
            ${events
              .map(
                (event) => `<li>
                  <strong>${escapeHtml(event.event_type)}</strong>
                  <span>${escapeHtml(t(locale, "revision", "نسخه"))} ${escapeHtml(event.revision)}</span>
                  <span>${escapeHtml(event.actor_id)}</span>
                  <span>${escapeHtml(formatDateTime(locale, event.occurred_at))}</span>
                  ${event.reason ? `<span class="aiw-hint">${escapeHtml(event.reason)}</span>` : ""}
                </li>`,
              )
              .join("")}
          </ul>`
    }
    <button type="button" data-workbench="close-history">${escapeHtml(t(locale, "Close", "بستن"))}</button>`;
}

function earnedValueMetric(
  label: string,
  value: string | null,
  currency: string,
): string {
  const shown = value === null ? "—" : value;
  return `<div class="aiw-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(shown)}${value !== null && currency ? ` ${escapeHtml(currency)}` : ""}</strong></div>`;
}

function renderEarnedValue(state: ShellState): string {
  const { locale } = state;
  if (state.baselineError) {
    return `<section class="aiw-panel aiw-error" data-analysis-evm data-evm-error>
      <h2>${escapeHtml(t(locale, "Cost and earned value", "هزینه و ارزش کسب‌شده"))}</h2>
      <p>${escapeHtml(t(locale, "The baseline register could not be read.", "فهرست مبناها خوانده نشد."))}</p>
      <p>${escapeHtml(state.baselineError)}</p>
      <button type="button" data-workbench="retry-baselines">${escapeHtml(t(locale, "Retry", "تلاش دوباره"))}</button>
    </section>`;
  }
  if (state.baselines.length === 0) {
    return `<section class="aiw-panel aiw-empty" data-analysis-evm data-evm-empty>
      <h2>${escapeHtml(t(locale, "Cost and earned value", "هزینه و ارزش کسب‌شده"))}</h2>
      <p class="aiw-status-line"><span class="aiw-status is-blocked">${escapeHtml(statusLabel(locale, "INSUFFICIENT_DATA"))}</span></p>
      <p>${escapeHtml(t(locale, "No baseline is stored for this project revision. The earned-value read model is not called with guessed inputs, and nothing is calculated in the browser.", "هیچ مبنایی برای این نسخه از پروژه ذخیره نشده است. مدل خواندن ارزش کسب‌شده با ورودی حدسی فراخوانی نمی‌شود و هیچ‌چیز در مرورگر محاسبه نمی‌شود."))}</p>
    </section>`;
  }
  const snapshot = state.evm;
  const card = snapshot
    ? `<div class="aiw-cards">
        ${earnedValueMetric(t(locale, "Planned value", "ارزش برنامه‌ای"), snapshot.earned_value.planned_value, snapshot.currency)}
        ${earnedValueMetric(t(locale, "Earned value", "ارزش کسب‌شده"), snapshot.earned_value.earned_value, snapshot.currency)}
        ${earnedValueMetric(t(locale, "Actual cost", "هزینه واقعی"), snapshot.earned_value.actual_cost, snapshot.currency)}
        ${earnedValueMetric(t(locale, "Cost variance", "انحراف هزینه"), snapshot.earned_value.cost_variance, snapshot.currency)}
        ${earnedValueMetric(t(locale, "Schedule variance", "انحراف زمان‌بندی"), snapshot.earned_value.schedule_variance, "")}
        ${earnedValueMetric(t(locale, "CPI", "شاخص عملکرد هزینه"), snapshot.earned_value.cost_performance_index, "")}
        ${earnedValueMetric(t(locale, "SPI", "شاخص عملکرد زمان‌بندی"), snapshot.earned_value.schedule_performance_index, "")}
        ${earnedValueMetric(t(locale, "EAC", "برآورد هزینه نهایی"), snapshot.earned_value.estimate_at_completion, snapshot.currency)}
        ${earnedValueMetric(t(locale, "VAC", "انحراف در تکمیل"), snapshot.earned_value.variance_at_completion, snapshot.currency)}
      </div>
      <dl class="aiw-facts">
        <dt>${escapeHtml(t(locale, "Baseline", "مبنا"))}</dt><dd>${escapeHtml(snapshot.baseline_id)}</dd>
        <dt>${escapeHtml(t(locale, "Data date", "تاریخ داده"))}</dt><dd>${escapeHtml(formatDate(locale, snapshot.data_date))}</dd>
        <dt>${escapeHtml(t(locale, "Currency", "واحد پول"))}</dt><dd>${escapeHtml(snapshot.currency)}</dd>
        <dt>${escapeHtml(t(locale, "ETC method", "روش برآورد تا تکمیل"))}</dt><dd>${escapeHtml(snapshot.earned_value.etc_method)}</dd>
      </dl>`
    : "";
  return `<section class="aiw-panel" data-analysis-evm>
    <h2>${escapeHtml(t(locale, "Cost and earned value", "هزینه و ارزش کسب‌شده"))}</h2>
    <p class="aiw-hint">${escapeHtml(t(locale, "Select the stored baseline and state the currency and data date. Values are returned by the canonical earned-value read model; the browser does not calculate.", "مبنای ذخیره‌شده را انتخاب و واحد پول و تاریخ داده را مشخص کنید. مقادیر از مدل خواندن ارزش کسب‌شدهٔ معتبر بازگردانده می‌شوند و مرورگر محاسبه نمی‌کند."))}</p>
    <form class="aiw-form" data-workbench="evm-form" novalidate>
      <label>${escapeHtml(t(locale, "Baseline", "مبنا"))}
        <select name="baseline_id">${state.baselines
          .map(
            (baseline) =>
              `<option value="${escapeHtml(baseline.baseline_id)}"${baseline.baseline_id === state.evmBaselineId ? " selected" : ""}>${escapeHtml(`${baseline.name} (${baseline.baseline_id})`)}</option>`,
          )
          .join("")}</select>
      </label>
      <label>${escapeHtml(t(locale, "Currency", "واحد پول"))}<input name="currency" maxlength="3" value="${escapeHtml(state.evmCurrency)}" required autocomplete="off" /></label>
      <label>${escapeHtml(t(locale, "Data date", "تاریخ داده"))}<input name="data_date" type="date" value="${escapeHtml(state.evmDataDate)}" required /></label>
      <button type="submit">${escapeHtml(t(locale, "Read earned value", "خواندن ارزش کسب‌شده"))}</button>
    </form>
    ${state.evmError ? `<p class="aiw-form-error" data-evm-error role="alert">${escapeHtml(state.evmError)}</p>` : ""}
    ${card}
  </section>`;
}

export function renderAnalysisStudio(state: ShellState): string {
  const { locale, workspace } = state;
  if (state.analysisError) {
    return `<section class="aiw-panel aiw-error" data-analysis-error>
      <h2>${escapeHtml(t(locale, "Project analysis could not be read", "تحلیل پروژه خوانده نشد"))}</h2>
      <p>${escapeHtml(state.analysisError)}</p>
      <button type="button" data-workbench="retry-analysis">${escapeHtml(t(locale, "Retry", "تلاش دوباره"))}</button>
    </section>`;
  }
  const counts = analysisCounts(workspace);
  const metrics = metricRows(workspace);
  const sources = metricSourceSummary(workspace);
  const max = metrics.reduce((value, row) => Math.max(value, Math.abs(row.value)), 0);
  const intelligence = workspace?.control_intelligence ?? null;
  return `
    <div class="aiw-analysis">
      <section class="aiw-panel">
        <header class="aiw-panel-header">
          <h2>${escapeHtml(t(locale, "Executive overview", "نمای کلی اجرایی"))}</h2>
          <span>${escapeHtml(t(locale, "Source revision", "نسخه منبع"))}: ${escapeHtml(state.context?.project.revision ?? "—")}</span>
        </header>
        ${
          counts
            ? `<div class="aiw-cards">
                ${[
                  [t(locale, "Activities", "فعالیت‌ها"), counts.activities],
                  [t(locale, "WBS elements", "عناصر WBS"), counts.wbs],
                  [t(locale, "Relationships", "روابط"), counts.relationships],
                  [t(locale, "Critical activities", "فعالیت‌های بحرانی"), counts.critical],
                ]
                  .map(
                    ([label, value]) =>
                      `<div class="aiw-card"><span>${escapeHtml(label)}</span><strong>${formatNumber(locale, Number(value))}</strong></div>`,
                  )
                  .join("")}
              </div>
              <p class="aiw-hint">${escapeHtml(t(locale, "Counts describe the records returned by the workspace read model. They are not a performance index.", "این اعداد رکوردهای بازگشتی مدل خواندن محیط کار را توصیف می‌کنند و شاخص عملکرد نیستند."))}</p>`
            : `<p class="aiw-empty-line">${escapeHtml(t(locale, "No workspace read model is available for this revision.", "برای این نسخه مدل خواندن محیط کار موجود نیست."))}</p>`
        }
      </section>
      <section class="aiw-panel" data-analysis-metrics>
        <h2>${escapeHtml(t(locale, "Stored control metrics", "سنجه‌های کنترل ذخیره‌شده"))}</h2>
        ${
          metrics.length
            ? `<p class="aiw-hint">${escapeHtml(t(locale, "Values are returned by the control-intelligence read model. Bars are scaled to the largest displayed value and are not a new calculation.", "مقادیر از مدل خواندن هوش کنترل بازگردانده شده‌اند. میله‌ها نسبت به بزرگ‌ترین مقدار نمایش‌داده‌شده مقیاس شده‌اند و محاسبهٔ جدیدی نیستند."))}</p>
              <ul class="aiw-metrics">
                ${metrics
                  .map(
                    (row) => `<li><span class="aiw-metric-label">${escapeHtml(row.label)}</span>
                      <span class="aiw-metric-bar"><span style="width:${max ? Math.round((Math.abs(row.value) / max) * 100) : 0}%"></span></span>
                      <strong>${formatNumber(locale, row.value)}</strong></li>`,
                  )
                  .join("")}
              </ul>
              <dl class="aiw-facts">
                <dt>${escapeHtml(t(locale, "Result", "نتیجه"))}</dt><dd>${escapeHtml(intelligence?.result_id ?? "—")}</dd>
                <dt>${escapeHtml(t(locale, "Generated", "تولیدشده"))}</dt><dd>${escapeHtml(formatDateTime(locale, intelligence?.generated_at ?? null))}</dd>
                <dt>${escapeHtml(t(locale, "Source references", "منابع"))}</dt><dd>${escapeHtml(sources.length ? sources.join(", ") : "—")}</dd>
              </dl>`
            : `<p class="aiw-empty-line">${escapeHtml(t(locale, "The control-intelligence read model returned no metrics for this revision.", "مدل خواندن هوش کنترل برای این نسخه سنجه‌ای برنگرداند."))}</p>`
        }
      </section>
      ${renderEarnedValue(state)}
      <section class="aiw-panel aiw-partial" data-analysis-resources>
        <h2>${escapeHtml(t(locale, "Resources and forecast", "منابع و پیش‌بینی"))}</h2>
        <p class="aiw-status-line"><span class="aiw-status is-planned">${escapeHtml(statusLabel(locale, "PLANNED"))}</span></p>
        <p>${escapeHtml(t(locale, "No resource or forecast read model is mounted for this studio. Nothing is estimated.", "هیچ مدل خواندن منابع یا پیش‌بینی برای این کارگاه متصل نیست و چیزی تخمین زده نمی‌شود."))}</p>
      </section>
    </div>`;
}

export function renderDecisionStudio(state: ShellState): string {
  const { locale } = state;
  if (!state.context?.permissions.can_propose) {
    return `<section class="aiw-panel aiw-readonly" data-decision-readonly>
      <h2>${escapeHtml(t(locale, "Decision & Approval Workspace", "فضای تصمیم و تأیید"))}</h2>
      <p class="aiw-status-line"><span class="aiw-status is-read">${escapeHtml(t(locale, "Read only", "فقط خواندن"))}</span></p>
      <p>${escapeHtml(t(locale, "Proposal payloads are visible to project editors only. This session cannot read or decide proposals; no list is fabricated.", "بارهای پیشنهاد فقط برای ویرایشگران پروژه قابل مشاهده است. این نشست نمی‌تواند پیشنهادها را بخواند یا درباره آن‌ها تصمیم بگیرد؛ فهرستی ساختگی نمایش داده نمی‌شود."))}</p>
    </section>`;
  }
  if (state.proposalError) {
    return `<section class="aiw-panel aiw-error" data-decision-error>
      <h2>${escapeHtml(t(locale, "Proposals could not be read", "پیشنهادها خوانده نشدند"))}</h2>
      <p>${escapeHtml(state.proposalError)}</p>
      <button type="button" data-workbench="retry-decisions">${escapeHtml(t(locale, "Retry", "تلاش دوباره"))}</button>
    </section>`;
  }
  const header = `<header class="aiw-panel-header">
      <h2>${escapeHtml(t(locale, "Decision & Approval Workspace", "فضای تصمیم و تأیید"))}</h2>
      <span>${escapeHtml(t(locale, "Source revision", "نسخه منبع"))}: ${escapeHtml(state.context?.project.revision ?? "—")}</span>
    </header>`;
  if (state.proposals.length === 0) {
    return `<section class="aiw-panel aiw-empty" data-decision-empty>
      ${header}
      <p>${escapeHtml(t(locale, "No proposal is stored for this project revision. The studio never creates one to fill the space.", "برای این نسخهٔ پروژه هیچ پیشنهادی ذخیره نشده است. این کارگاه برای پر کردن فضا پیشنهادی نمی‌سازد."))}</p>
    </section>`;
  }
  return `<section class="aiw-panel" data-decision-list>
    ${header}
    <p class="aiw-hint">${escapeHtml(t(locale, "Proposals come from the canonical AI action runtime. A decision records the approval only; execution applies the proposed change with the pinned revision.", "پیشنهادها از زمان‌اجرای متعارف اقدام هوشمند می‌آیند. تصمیم فقط تأیید را ثبت می‌کند؛ اجرا تغییر پیشنهادی را با نسخهٔ ثابت‌شده اعمال می‌کند."))}</p>
    ${state.proposalNotice ? `<p class="aiw-hint" data-decision-notice role="status">${escapeHtml(state.proposalNotice)}</p>` : ""}
    <div class="aiw-decisions">
      ${state.proposals.map((proposal) => renderProposal(state, proposal)).join("")}
    </div>
  </section>`;
}

function renderProposal(state: ShellState, proposal: AIActionProposal): string {
  const { locale } = state;
  const payload = escapeHtml(JSON.stringify(proposal.payload, null, 2));
  const result = proposal.result
    ? `<details class="aiw-proposal-result"><summary>${escapeHtml(t(locale, "Result", "نتیجه"))}</summary><pre>${escapeHtml(JSON.stringify(proposal.result, null, 2))}</pre></details>`
    : "";
  const busy = state.proposalBusy === proposal.proposal_id;
  let controls = "";
  if (proposal.is_stale) {
    controls = `<p class="aiw-hint is-warning" data-proposal-stale>${escapeHtml(t(locale, "Stale proposal: the project revision advanced after this proposal; it cannot be approved or executed.", "پیشنهاد کهنه: نسخهٔ پروژه پس از این پیشنهاد پیش رفته است؛ نمی‌توان آن را تأیید یا اجرا کرد."))}</p>`;
  } else if (proposal.status === "proposed" && proposal.requires_human_approval) {
    controls = `<div class="aiw-decision-actions">
      <button type="button" data-workbench="decide-proposal" data-proposal="${escapeHtml(proposal.proposal_id)}" data-approved="true"${busy ? " disabled" : ""}>${escapeHtml(t(locale, "Approve", "تأیید"))}</button>
      <button type="button" data-workbench="decide-proposal" data-proposal="${escapeHtml(proposal.proposal_id)}" data-approved="false"${busy ? " disabled" : ""}>${escapeHtml(t(locale, "Reject", "رد"))}</button>
    </div>`;
  } else if (proposal.status === "approved") {
    controls = `<div class="aiw-decision-actions">
      <button type="button" data-workbench="execute-proposal" data-proposal="${escapeHtml(proposal.proposal_id)}"${busy ? " disabled" : ""}>${escapeHtml(t(locale, "Execute", "اجرا"))}</button>
    </div>`;
  }
  return `<article class="aiw-decision" data-proposal="${escapeHtml(proposal.proposal_id)}" data-proposal-status="${escapeHtml(proposal.status)}">
    <header>
      <strong>${escapeHtml(proposal.tool_name)}</strong>
      <span class="aiw-status ${proposalStatusTone(proposal.status)}">${escapeHtml(proposalStatusLabel(locale, proposal.status))}</span>
    </header>
    <dl class="aiw-facts">
      <dt>${escapeHtml(t(locale, "Action", "اقدام"))}</dt><dd>${escapeHtml(proposal.action)}</dd>
      <dt>${escapeHtml(t(locale, "Requested by", "درخواست‌کننده"))}</dt><dd>${escapeHtml(proposal.requested_by)}</dd>
      <dt>${escapeHtml(t(locale, "Recorded", "ثبت‌شده"))}</dt><dd>${escapeHtml(formatDateTime(locale, proposal.created_at))}</dd>
      <dt>${escapeHtml(t(locale, "Proposal revision", "نسخهٔ پیشنهاد"))}</dt><dd>${escapeHtml(proposal.project_revision_id)}</dd>
      <dt>${escapeHtml(t(locale, "Evidence", "شواهد"))}</dt><dd>${escapeHtml(proposal.evidence_refs.length ? proposal.evidence_refs.join(", ") : "—")}</dd>
      ${proposal.decided_by ? `<dt>${escapeHtml(t(locale, "Decided by", "تصمیم‌گیرنده"))}</dt><dd>${escapeHtml(proposal.decided_by)}</dd>` : ""}
    </dl>
    <details class="aiw-proposal-payload"><summary>${escapeHtml(t(locale, "Payload", "بار"))}</summary><pre>${payload}</pre></details>
    ${result}
    ${busy ? `<p class="aiw-hint">${escapeHtml(t(locale, "Working…", "در حال انجام…"))}</p>` : ""}
    ${controls}
  </article>`;
}

export function renderInspector(state: ShellState): string {
  const { locale } = state;
  const risk = state.selectedRisk
    ? state.risks.find((item) => item.risk_id === state.selectedRisk) ?? null
    : null;
  if (risk && state.editingRisk === risk.risk_id) {
    return renderRiskEditForm(locale, risk);
  }
  if (risk && state.historyRisk === risk.risk_id) {
    return renderRiskHistory(locale, risk.risk_id, state.riskHistory);
  }
  if (risk) {
    return `
      <h2>${escapeHtml(t(locale, "Inspector", "بازرس"))}</h2>
      <h3>${escapeHtml(risk.title)}</h3>
      <div class="aiw-inspector-actions">
        ${state.context?.permissions.can_propose ? `<button type="button" data-workbench="edit-risk">${escapeHtml(t(locale, "Edit", "ویرایش"))}</button>` : ""}
        <button type="button" data-workbench="show-history">${escapeHtml(t(locale, "History", "تاریخچه"))}</button>
      </div>
      <dl class="aiw-facts">
        <dt>${escapeHtml(t(locale, "Risk ID", "شناسه ریسک"))}</dt><dd>${escapeHtml(risk.risk_id)}</dd>
        <dt>${escapeHtml(t(locale, "Category", "دسته"))}</dt><dd>${escapeHtml(risk.category)}</dd>
        <dt>${escapeHtml(t(locale, "Status", "وضعیت"))}</dt><dd>${escapeHtml(risk.status)}</dd>
        <dt>${escapeHtml(t(locale, "Probability × impact", "احتمال × اثر"))}</dt><dd>${escapeHtml(`${risk.probability} × ${risk.impact} = ${risk.score}`)}</dd>
        <dt>${escapeHtml(t(locale, "Exposure", "مواجهه"))}</dt><dd>${escapeHtml(risk.exposure_level)}</dd>
        <dt>${escapeHtml(t(locale, "Owner", "مالک"))}</dt><dd>${escapeHtml(risk.owner)}</dd>
        <dt>${escapeHtml(t(locale, "Response", "پاسخ"))}</dt><dd>${escapeHtml(risk.response_strategy)}</dd>
        <dt>${escapeHtml(t(locale, "Identified", "شناسایی"))}</dt><dd>${escapeHtml(formatDate(locale, risk.date_identified))}</dd>
        <dt>${escapeHtml(t(locale, "Revision", "نسخه"))}</dt><dd>${escapeHtml(risk.revision)}</dd>
        <dt>${escapeHtml(t(locale, "Description", "توضیح"))}</dt><dd>${escapeHtml(risk.description || "—")}</dd>
      </dl>`;
  }
  if (state.plan) {
    return `
      <h2>${escapeHtml(t(locale, "Inspector", "بازرس"))}</h2>
      <p class="aiw-hint">${escapeHtml(t(locale, "Command evidence", "شواهد فرمان"))}</p>
      <dl class="aiw-facts">
        <dt>${escapeHtml(t(locale, "Intent", "نیت"))}</dt><dd>${escapeHtml(state.plan.intent)}</dd>
        <dt>${escapeHtml(t(locale, "Matched text", "متن منطبق"))}</dt><dd>${escapeHtml(state.plan.evidence || "—")}</dd>
        <dt>${escapeHtml(t(locale, "Project", "پروژه"))}</dt><dd>${escapeHtml(state.plan.project.project_id)}</dd>
        <dt>${escapeHtml(t(locale, "Revision", "نسخه"))}</dt><dd>${escapeHtml(state.plan.project.revision)}</dd>
      </dl>`;
  }
  return `<h2>${escapeHtml(t(locale, "Inspector", "بازرس"))}</h2>
    <p class="aiw-hint">${escapeHtml(t(locale, "Select a record to inspect its stored fields, revision and source.", "برای بررسی فیلدهای ذخیره‌شده، نسخه و منبع، یک رکورد انتخاب کنید."))}</p>`;
}

export function renderStatusBar(state: ShellState): string {
  const { locale, context } = state;
  return `
    <span><strong>${escapeHtml(t(locale, "Revision", "نسخه"))}</strong> ${escapeHtml(context?.project.revision ?? "—")}</span>
    <span><strong>${escapeHtml(t(locale, "Data date", "تاریخ داده"))}</strong> ${escapeHtml(context?.data_date ? formatDate(locale, context.data_date) : t(locale, "Not published", "منتشر نشده"))}</span>
    <span><strong>${escapeHtml(t(locale, "Calculation", "محاسبه"))}</strong> ${escapeHtml(t(locale, "Not run in this session", "در این نشست اجرا نشده"))}</span>
    <span><strong>${escapeHtml(t(locale, "Selected", "انتخاب‌شده"))}</strong> ${escapeHtml(state.selectedRisk ?? "—")}</span>
    <span><strong>${escapeHtml(t(locale, "Jobs", "کارهای پس‌زمینه"))}</strong> ${escapeHtml(t(locale, "None", "هیچ"))}</span>
    <span><strong>${escapeHtml(t(locale, "Updated", "به‌روزرسانی"))}</strong> ${escapeHtml(state.lastUpdated ? formatDateTime(locale, state.lastUpdated) : "—")}</span>
    <span class="aiw-connection ${state.connected ? "is-live" : "is-blocked"}">${escapeHtml(state.connected ? t(locale, "Connected", "متصل") : t(locale, "Offline", "قطع"))}</span>`;
}

export function renderFallbackNotice(locale: string): string {
  if (locale.split("-")[0] === "en") return "";
  return `<p class="aiw-fallback" data-locale-fallback>${escapeHtml(t(locale, "Some Workbench labels are shown in English because this language catalog does not contain them yet.", "برخی برچسب‌های کارگاه به انگلیسی نمایش داده می‌شوند چون فهرست زبان این عبارت‌ها را ندارد."))}</p>`;
}
