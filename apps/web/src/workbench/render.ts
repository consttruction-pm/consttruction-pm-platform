/**
 * Server-rendered markup for the CUBI AI Workbench shell and studios.
 *
 * Every dynamic value is escaped. A studio that the server marked BLOCKED is
 * never rendered with live controls: it shows its status, the missing canonical
 * service and the acceptance gate instead.
 */
import type {
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
  workspace: WorkspaceReadSnapshot | null;
  riskError: string | null;
  analysisError: string | null;
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
      <section class="aiw-panel aiw-partial" data-analysis-evm>
        <h2>${escapeHtml(t(locale, "Cost and earned value", "هزینه و ارزش کسب‌شده"))}</h2>
        <p class="aiw-status-line"><span class="aiw-status is-planned">${escapeHtml(statusLabel(locale, "PLANNED"))}</span></p>
        <p>${escapeHtml(t(locale, "Earned-value figures are not shown here. The studio does not select a baseline or currency yet, and no value is calculated in the browser.", "ارقام ارزش کسب‌شده در اینجا نمایش داده نمی‌شوند. این کارگاه هنوز مبنا و واحد پول را انتخاب نمی‌کند و هیچ مقداری در مرورگر محاسبه نمی‌شود."))}</p>
      </section>
      <section class="aiw-panel aiw-partial" data-analysis-resources>
        <h2>${escapeHtml(t(locale, "Resources and forecast", "منابع و پیش‌بینی"))}</h2>
        <p class="aiw-status-line"><span class="aiw-status is-planned">${escapeHtml(statusLabel(locale, "PLANNED"))}</span></p>
        <p>${escapeHtml(t(locale, "No resource or forecast read model is mounted for this studio. Nothing is estimated.", "هیچ مدل خواندن منابع یا پیش‌بینی برای این کارگاه متصل نیست و چیزی تخمین زده نمی‌شود."))}</p>
      </section>
    </div>`;
}

export function renderInspector(state: ShellState): string {
  const { locale } = state;
  const risk = state.selectedRisk
    ? state.risks.find((item) => item.risk_id === state.selectedRisk) ?? null
    : null;
  if (risk) {
    return `
      <h2>${escapeHtml(t(locale, "Inspector", "بازرس"))}</h2>
      <h3>${escapeHtml(risk.title)}</h3>
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
