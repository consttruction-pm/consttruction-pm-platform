import type { ApiTransport, ProjectContext } from "./client.js";
import {
  AIActionClient,
  type AIActionExecutionVerification,
  type AIActionProposal,
  type CreateActivityProposal,
  type UpdateActivityProposal,
} from "./ai-action-client.js";
import { translateWorkspaceText } from "./workspace-localization.js";

type PanelLabels = {
  title: string; description: string; createTitle: string; activityId: string;
  activityName: string; duration: string; durationUnit: string; workingDay: string;
  workingHour: string; prepare: string; refresh: string; proposals: string;
  preparing: string; loading: string; proposalReady: string; rejected: string;
  approved: string; executing: string; executed: string; noProposals: string;
  proposalCreated: string; proposalFailed: string; listFailed: string;
  executionFailed: string; stale: string; noRetry: string; approve: string;
  reject: string; execute: string; required: string; invalidResponse: string;
  action: string; projectRevision: string; recordRevision: string; result: string;
  operationFailed: string; serverUnavailable: string;
  createdVerified: string; verificationUnavailable: string; verificationFailed: string;
  verificationNotReturned: string; calculationTimezoneMissing: string;
  calculationPermissionMissing: string; calculationNotConfigured: string;
  scheduleStart: string; scheduleFinish: string; calculatedDuration: string;
  critical: string; yes: string; no: string; persistedActivity: string;
  calculationAtExecution: string; savedResultUnavailable: string; verificationNotStored: string;
  updateTitle: string; newName: string; newDuration: string; optional: string;
  updateProposalCreated: string; updateNeedsChange: string; revisionInvalid: string;
  activityCreated: string; activityUpdated: string; retry: string;
  preconditionFailed: string; permissionDenied: string; activityAlreadyExists: string;
};

export type AIActionPanelLabelKey = keyof PanelLabels;

const labels: Record<"en" | "fa", PanelLabels> = {
  en: {
    title: "AI Assistant · Actions",
    description: "Prepare an activity proposal, review it, then approve and execute it explicitly. No project change is made before approval.",
    createTitle: "Create activity proposal",
    activityId: "Activity ID", activityName: "Activity name", duration: "Duration",
    durationUnit: "Duration unit", workingDay: "Working day", workingHour: "Working hour",
    prepare: "Prepare proposal", refresh: "Refresh proposals",
    proposals: "Project proposals", preparing: "Preparing proposal…", loading: "Loading proposals…",
    proposalReady: "Proposal is ready for review.", rejected: "Proposal rejected.",
    approved: "Proposal approved.", executing: "Executing approved action…",
    executed: "Action executed successfully.", noProposals: "There are no action proposals for this project.",
    proposalCreated: "Proposal created. Review the details before approving.",
    proposalFailed: "Could not create the proposal.", listFailed: "Could not load proposals.",
    executionFailed: "The action did not complete.", stale: "Project revision changed. This proposal is stale and cannot be approved or executed.",
    noRetry: "The outcome is uncertain or execution was interrupted. Do not retry this action; it needs reconciliation.",
    approve: "Approve", reject: "Reject", execute: "Execute approved action",
    required: "This field is required.", invalidResponse: "The server returned an invalid action response.",
    action: "Action", projectRevision: "Project revision", recordRevision: "Activity record revision",
    result: "Result", operationFailed: "Request failed", serverUnavailable: "This server has not enabled AI action execution.",
    createdVerified: "The activity was saved and recalculated from saved project data.",
    verificationUnavailable: "The action was saved, but authoritative recalculation is unavailable.",
    verificationFailed: "The action was saved, but authoritative recalculation failed. No calculated dates are shown.",
    verificationNotReturned: "The action was saved. This server did not return an authoritative recalculation result.",
    calculationTimezoneMissing: "The calculation timezone was not provided.",
    calculationPermissionMissing: "This account is not allowed to run project scheduling.",
    calculationNotConfigured: "Schedule verification is not configured on this server.",
    scheduleStart: "Calculated start", scheduleFinish: "Calculated finish",
    calculatedDuration: "Calculated duration", critical: "Critical", yes: "yes", no: "no",
    persistedActivity: "Saved activity",
    calculationAtExecution: "Schedule dates are verified at execution time; this saved record shows the persisted activity.",
    savedResultUnavailable: "The saved result is not available.",
    verificationNotStored: "The calculated result could not be saved for later display.",
    updateTitle: "Update an existing activity",
    newName: "New name", newDuration: "New duration", optional: "optional",
    updateProposalCreated: "Update proposal created. Review the details before approving.",
    updateNeedsChange: "Provide a new name or both new duration fields.",
    revisionInvalid: "Enter the saved activity record revision (1 or greater).",
    activityCreated: "Activity created successfully.", activityUpdated: "Activity updated successfully.",
    retry: "Retry",
    preconditionFailed: "The activity changed or is unavailable, so no project change was made. Create a new proposal using the current activity data.",
    permissionDenied: "This account is not allowed to perform this action. No project change was made.",
    activityAlreadyExists: "An activity with this ID already exists. No project change was made.",
  },
  fa: {
    title: "دستیار هوشمند · اقدامات",
    description: "پیشنهاد ایجاد فعالیت را آماده و بررسی کنید؛ سپس آن را صریحاً تأیید و اجرا کنید. پیش از تأیید، تغییری در پروژه انجام نمی‌شود.",
    createTitle: "پیشنهاد ایجاد فعالیت",
    activityId: "شناسه فعالیت", activityName: "نام فعالیت", duration: "مدت",
    durationUnit: "واحد مدت", workingDay: "روز کاری", workingHour: "ساعت کاری",
    prepare: "تهیه پیشنهاد", refresh: "به‌روزرسانی پیشنهادها",
    proposals: "پیشنهادهای پروژه", preparing: "در حال تهیه پیشنهاد…", loading: "در حال دریافت پیشنهادها…",
    proposalReady: "پیشنهاد برای بررسی آماده است.", rejected: "پیشنهاد رد شد.",
    approved: "پیشنهاد تأیید شد.", executing: "در حال اجرای اقدام تأییدشده…",
    executed: "فعالیت با موفقیت ایجاد شد.", noProposals: "برای این پروژه پیشنهادی وجود ندارد.",
    proposalCreated: "پیشنهاد ایجاد شد؛ پیش از تأیید، جزئیات را بررسی کنید.",
    proposalFailed: "ایجاد پیشنهاد ناموفق بود.", listFailed: "دریافت پیشنهادها ناموفق بود.",
    executionFailed: "اقدام کامل نشد.", stale: "نسخه پروژه تغییر کرده است؛ این پیشنهاد منقضی شده و قابل تأیید یا اجرا نیست.",
    noRetry: "نتیجه نامطمئن است یا اجرا قطع شده؛ این اقدام را دوباره اجرا نکنید و ابتدا باید نتیجه تطبیق داده شود.",
    approve: "تأیید", reject: "رد", execute: "اجرای اقدام تأییدشده",
    required: "این فیلد الزامی است.", invalidResponse: "پاسخ سرور برای اقدام معتبر نیست.",
    action: "اقدام", projectRevision: "نسخه پروژه", recordRevision: "نسخه رکورد فعالیت",
    result: "نتیجه", operationFailed: "درخواست ناموفق بود", serverUnavailable: "اجرای اقدامات دستیار در این سرور پیکربندی نشده است.",
    createdVerified: "فعالیت ذخیره و بر اساس داده‌های ذخیره‌شده پروژه محاسبه مجدد شد.",
    verificationUnavailable: "اقدام ذخیره شد، اما محاسبه مجدد معتبر در دسترس نیست.",
    verificationFailed: "اقدام ذخیره شد، اما محاسبه مجدد معتبر ناموفق بود. هیچ تاریخ محاسبه‌شده‌ای نمایش داده نمی‌شود.",
    verificationNotReturned: "اقدام ذخیره شد؛ این سرور نتیجه محاسبه مجدد معتبر را برنگرداند.",
    calculationTimezoneMissing: "منطقه زمانی محاسبه ارائه نشده است.",
    calculationPermissionMissing: "این حساب اجازه اجرای زمان‌بندی پروژه را ندارد.",
    calculationNotConfigured: "تأیید محاسبه زمان‌بندی در این سرور پیکربندی نشده است.",
    scheduleStart: "شروع محاسبه‌شده", scheduleFinish: "پایان محاسبه‌شده",
    calculatedDuration: "مدت محاسبه‌شده", critical: "بحرانی", yes: "بله", no: "خیر",
    persistedActivity: "فعالیت ذخیره‌شده",
    calculationAtExecution: "تاریخ‌های زمان‌بندی هنگام اجرا تأیید می‌شوند؛ این رکورد ذخیره‌شده فعالیت را نشان می‌دهد.",
    savedResultUnavailable: "نتیجه ذخیره‌شده در دسترس نیست.",
    verificationNotStored: "نتیجه محاسبه‌شده برای نمایش بعدی ذخیره نشد.",
    updateTitle: "ویرایش فعالیت موجود",
    newName: "نام جدید", newDuration: "مدت جدید", optional: "اختیاری",
    updateProposalCreated: "پیشنهاد ویرایش ایجاد شد؛ پیش از تأیید، جزئیات را بررسی کنید.",
    updateNeedsChange: "یک نام جدید یا هر دو فیلد مدت جدید را ارائه کنید.",
    revisionInvalid: "نسخه ذخیره‌شده رکورد فعالیت را وارد کنید (۱ یا بیشتر).",
    activityCreated: "فعالیت با موفقیت ایجاد شد.", activityUpdated: "فعالیت با موفقیت ویرایش شد.",
    retry: "تلاش دوباره",
    preconditionFailed: "فعالیت تغییر کرده یا در دسترس نیست؛ هیچ تغییری در پروژه اعمال نشد. پیشنهاد جدیدی با داده‌های فعلی فعالیت بسازید.",
    permissionDenied: "این حساب اجازه انجام این اقدام را ندارد؛ هیچ تغییری در پروژه اعمال نشد.",
    activityAlreadyExists: "فعالیتی با این شناسه از قبل وجود دارد؛ هیچ تغییری در پروژه اعمال نشد.",
  },
};

function localeLabels(locale: string): PanelLabels {
  const baseline = labels[locale.toLowerCase().startsWith("fa") ? "fa" : "en"];
  return Object.fromEntries(
    Object.entries(baseline).map(([key, fallback]) => [
      key,
      translateWorkspaceText(locale, `aiAction.${key}`, fallback),
    ]),
  ) as PanelLabels;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}

function addField(
  form: HTMLFormElement,
  labelText: string,
  name: string,
  type: "text" | "number",
  requiredText: string,
): HTMLInputElement {
  const label = element("label", "cp-ai-action-field", labelText);
  const input = element("input");
  input.name = name;
  input.type = type;
  input.required = true;
  input.autocomplete = "off";
  if (type === "number") {
    input.min = "0";
    input.step = "any";
  }
  input.setAttribute("aria-label", labelText);
  input.setAttribute("data-required-message", requiredText);
  label.append(input);
  form.append(label);
  return input;
}

function addOptionalField(
  form: HTMLFormElement,
  labelText: string,
  name: string,
  type: "text" | "number",
  optionalText: string,
): HTMLInputElement {
  const label = element("label", "cp-ai-action-field", `${labelText} (${optionalText})`);
  const input = element("input");
  input.name = name;
  input.type = type;
  input.autocomplete = "off";
  if (type === "number") {
    input.min = "0";
    input.step = "any";
  }
  input.setAttribute("aria-label", `${labelText} (${optionalText})`);
  label.append(input);
  form.append(label);
  return input;
}

function button(text: string, className: string, disabled = false): HTMLButtonElement {
  const item = element("button", className, text);
  item.type = "button";
  item.disabled = disabled;
  return item;
}

export function proposalStatusLabelKey(
  status: string,
  toolName?: string,
): AIActionPanelLabelKey | null {
  if (status === "executed" && toolName === "activity.update") return "activityUpdated";
  if (status === "executed" && toolName === "activity.create") return "activityCreated";
  const known: Record<string, AIActionPanelLabelKey> = {
    proposed: "proposalReady",
    approved: "approved",
    rejected: "rejected",
    executing: "executing",
    executed: "executed",
    stale: "stale",
    uncertain: "noRetry",
    denied: "permissionDenied",
    blocked: "preconditionFailed",
  };
  return known[status] ?? null;
}

function statusText(status: string, t: PanelLabels, toolName?: string): string {
  const key = proposalStatusLabelKey(status, toolName);
  return key ? t[key] : status;
}

export function actionErrorLabelKey(code: string): AIActionPanelLabelKey | null {
  if (code === "AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN" ||
      code === "AI_ACTION_EXECUTION_STATE_NOT_PERSISTED" ||
      code === "AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED") return "noRetry";
  if (code === "AI_ACTION_ACTIVITY_REVISION_CONFLICT" ||
      code === "AI_ACTION_ACTIVITY_NOT_FOUND") return "preconditionFailed";
  if (code === "AI_ACTION_ACTIVITY_ALREADY_EXISTS") return "activityAlreadyExists";
  if (code === "AI_TOOL_NOT_PERMITTED" ||
      code === "AI_ACTION_PERMISSION_CHECK_FAILED") return "permissionDenied";
  if (code === "AI_ACTION_PROPOSAL_STALE_REVISION") return "stale";
  if (code === "INVALID_AI_ACTION_RESPONSE") return "invalidResponse";
  if (code === "ROUTE_NOT_FOUND") return "serverUnavailable";
  return null;
}

function proposalLabel(proposal: AIActionProposal, t: PanelLabels): string {
  const name = typeof proposal.payload.name === "string" ? proposal.payload.name : proposal.proposal_id;
  const id = typeof proposal.payload.activity_id === "string" ? proposal.payload.activity_id : "";
  return id ? `${name} (${id})` : name;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function durationUnitText(unit: unknown, t: PanelLabels): string {
  if (unit === "working-hour") return t.workingHour;
  if (unit === "working-day") return t.workingDay;
  return typeof unit === "string" ? unit : "";
}

function verificationOutcome(
  verification: AIActionExecutionVerification | null | undefined,
  t: PanelLabels,
): { text: string; kind: "success" | "warning" | "error" } {
  if (!verification) {
    return { text: t.verificationNotReturned, kind: "warning" };
  }
  if (verification.status === "COMPUTED" && verification.activity) {
    const activity = verification.activity;
    const unit = durationUnitText(activity.duration_unit, t);
    const details = [
      t.createdVerified,
      `${t.scheduleStart}: ${activity.start}`,
      `${t.scheduleFinish}: ${activity.finish}`,
    ];
    if (activity.duration !== null) {
      details.push(`${t.calculatedDuration}: ${activity.duration} ${unit}`.trim());
    }
    if (activity.critical !== null) {
      details.push(`${t.critical}: ${activity.critical ? t.yes : t.no}`);
    }
    return { text: details.join(" "), kind: "success" };
  }
  if (verification.status === "UNAVAILABLE") {
    const reason = verification.reason_code === "CALCULATION_TIMEZONE_REQUIRED"
      ? t.calculationTimezoneMissing
      : verification.reason_code === "PROJECT_SCHEDULE_PERMISSION_REQUIRED"
        ? t.calculationPermissionMissing
        : verification.reason_code === "SCHEDULE_VERIFICATION_NOT_COMPOSED"
          ? t.calculationNotConfigured
          : "";
    return {
      text: reason ? `${t.verificationUnavailable} ${reason}` : t.verificationUnavailable,
      kind: "warning",
    };
  }
  return { text: t.verificationFailed, kind: "error" };
}

function persistedActivitySummary(
  result: Readonly<Record<string, unknown>> | null,
  t: PanelLabels,
): string {
  const activity = asRecord(asRecord(result)?.activity);
  if (!activity) return t.savedResultUnavailable;
  const id = typeof activity.activity_id === "string" ? activity.activity_id : "";
  const name = typeof activity.name === "string" ? activity.name : "";
  const durationValue = typeof activity.duration_value === "string" || typeof activity.duration_value === "number"
    ? String(activity.duration_value)
    : "";
  const unit = durationUnitText(activity.duration_unit, t);
  const revision = typeof activity.record_revision === "number" ? String(activity.record_revision) : "";
  const parts = [id ? `${name || t.persistedActivity} (${id})` : name || t.persistedActivity];
  if (durationValue) parts.push(`${t.duration}: ${durationValue} ${unit}`.trim());
  if (revision) parts.push(`${t.recordRevision}: ${revision}`);
  return parts.join(" · ");
}

function browserTimeZone(): string | null {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return typeof zone === "string" && zone.trim() ? zone : null;
  } catch {
    return null;
  }
}

/** Mounts the authenticated project's explicitly approval-gated AI action surface. */
export function mountAIActionPanel(
  appShell: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
): () => Promise<void> {
  const previous = appShell.querySelector<HTMLDetailsElement>("#cp-ai-action-panel");
  const wasOpen = previous?.open ?? false;
  previous?.remove();

  const t = localeLabels(locale);
  const client = new AIActionClient(transport);
  const details = element("details", "cp-ai-action-panel");
  details.id = "cp-ai-action-panel";
  details.open = wasOpen;
  details.dir = locale.toLowerCase().startsWith("fa") ? "rtl" : "ltr";

  const summary = element("summary", "cp-ai-action-summary", t.title);
  details.append(summary);
  const content = element("div", "cp-ai-action-content");
  content.append(element("p", "cp-ai-action-description", t.description));

  const form = element("form", "cp-ai-action-form");
  const formHeading = element("h3", "", t.createTitle);
  form.append(formHeading);
  const activityId = addField(form, t.activityId, "activity_id", "text", t.required);
  const activityName = addField(form, t.activityName, "name", "text", t.required);
  const duration = addField(form, t.duration, "duration_value", "number", t.required);
  const unitLabel = element("label", "cp-ai-action-field", t.durationUnit);
  const unit = element("select");
  unit.name = "duration_unit";
  for (const [value, text] of [
    ["working-day", t.workingDay],
    ["working-hour", t.workingHour],
  ] as const) {
    const option = element("option", "", text);
    option.value = value;
    unit.append(option);
  }
  unitLabel.append(unit);
  form.append(unitLabel);
  const submit = element("button", "cp-ai-action-primary", t.prepare);
  submit.type = "submit";
  form.append(submit);

  const updateForm = element("form", "cp-ai-action-form");
  updateForm.append(element("h3", "", t.updateTitle));
  const updateActivityId = addField(updateForm, t.activityId, "activity_id", "text", t.required);
  const expectedRevision = addField(
    updateForm, t.recordRevision, "expected_revision", "number", t.required,
  );
  expectedRevision.min = "1";
  expectedRevision.step = "1";
  const newName = addOptionalField(updateForm, t.newName, "name", "text", t.optional);
  const newDuration = addOptionalField(
    updateForm, t.newDuration, "duration_value", "number", t.optional,
  );
  const updateUnitLabel = element("label", "cp-ai-action-field", t.durationUnit);
  const updateUnit = element("select");
  updateUnit.name = "duration_unit";
  const emptyUnit = element("option", "", "—");
  emptyUnit.value = "";
  updateUnit.append(emptyUnit);
  for (const [value, text] of [
    ["working-day", t.workingDay],
    ["working-hour", t.workingHour],
  ] as const) {
    const option = element("option", "", text);
    option.value = value;
    updateUnit.append(option);
  }
  updateUnitLabel.append(updateUnit);
  updateForm.append(updateUnitLabel);
  const updateSubmit = element("button", "cp-ai-action-primary", t.prepare);
  updateSubmit.type = "submit";
  updateForm.append(updateSubmit);

  const message = element("p", "cp-ai-action-message");
  message.setAttribute("role", "status");
  message.setAttribute("aria-live", "polite");

  const listSection = element("section", "cp-ai-action-proposals");
  const listHeader = element("div", "cp-ai-action-list-header");
  listHeader.append(element("h3", "", t.proposals));
  const refresh = button(t.refresh, "cp-ai-action-secondary");
  listHeader.append(refresh);
  const list = element("ul", "cp-ai-action-list");
  listSection.append(listHeader, list);

  content.append(form, updateForm, message, listSection);
  details.append(content);
  appShell.append(details);

  const setMessage = (text: string, kind = ""): void => {
    message.textContent = text;
    message.dataset.kind = kind;
  };

  const operationError = (code: string): string => {
    const key = actionErrorLabelKey(code);
    return key ? t[key] : `${t.operationFailed}: ${code}`;
  };

  let listGeneration = 0;
  const refreshProposals = async (): Promise<void> => {
    const generation = ++listGeneration;
    refresh.disabled = true;
    list.setAttribute("aria-busy", "true");
    list.replaceChildren(element("li", "cp-ai-action-empty", t.loading));
    const result = await client.listProposals(context);
    if (generation !== listGeneration) return;
    refresh.disabled = false;
    list.removeAttribute("aria-busy");
    list.replaceChildren();
    if (!result.ok) {
      setMessage(operationError(result.error.code), "error");
      const errorItem = element(
        "li", "cp-ai-action-empty", `${t.listFailed}: ${result.error.code}`,
      );
      const retry = button(t.retry, "cp-ai-action-secondary");
      retry.addEventListener("click", () => { void refreshProposals(); });
      errorItem.append(retry);
      list.append(errorItem);
      return;
    }
    if (result.data.proposals.length === 0) {
      list.append(element("li", "cp-ai-action-empty", t.noProposals));
      return;
    }
    for (const proposal of result.data.proposals) {
      const item = element("li", "cp-ai-action-proposal");
      const heading = element("h4", "", proposalLabel(proposal, t));
      const state = element("p", "cp-ai-action-state", statusText(proposal.status, t, proposal.tool_name));
      const idLine = element("p", "cp-ai-action-metadata", `ID: ${proposal.proposal_id}`);
      const revisionLine = element("p", "cp-ai-action-metadata", `${t.projectRevision}: ${proposal.project_revision_id}`);
      item.append(heading, state, idLine, revisionLine);
      if (proposal.is_stale || proposal.project_revision_id !== String(context.revision)) {
        item.append(element("p", "cp-ai-action-warning", t.stale));
      } else if (proposal.status === "uncertain" || proposal.status === "executing") {
        item.append(element("p", "cp-ai-action-warning", t.noRetry));
      } else if (proposal.status === "blocked") {
        item.append(element("p", "cp-ai-action-warning", t.preconditionFailed));
      } else if (proposal.status === "denied") {
        item.append(element("p", "cp-ai-action-warning", t.permissionDenied));
      } else if (proposal.status === "proposed" && proposal.requires_human_approval) {
        const controls = element("div", "cp-ai-action-controls");
        const approve = button(t.approve, "cp-ai-action-primary");
        const reject = button(t.reject, "cp-ai-action-secondary");
        approve.addEventListener("click", async () => {
          approve.disabled = true;
          reject.disabled = true;
          const decision = await client.decide(context, proposal.proposal_id, true);
          if (!decision.ok) setMessage(operationError(decision.error.code), "error");
          else setMessage(t.approved, "success");
          await refreshProposals();
        });
        reject.addEventListener("click", async () => {
          approve.disabled = true;
          reject.disabled = true;
          const decision = await client.decide(context, proposal.proposal_id, false);
          if (!decision.ok) setMessage(operationError(decision.error.code), "error");
          else setMessage(t.rejected, "success");
          await refreshProposals();
        });
        controls.append(approve, reject);
        item.append(controls);
      } else if (proposal.status === "approved") {
        const execute = button(t.execute, "cp-ai-action-primary");
        execute.addEventListener("click", async () => {
          execute.disabled = true;
          setMessage(t.executing);
          const result = await client.execute(context, proposal.proposal_id, browserTimeZone());
          if (!result.ok) {
            setMessage(operationError(result.error.code), "error");
          } else if (result.data.status === "executed") {
            const outcome = verificationOutcome(result.data.execution_verification, t);
            const notStored = result.data.execution_verification_stored === false;
            setMessage(
              notStored ? `${outcome.text} ${t.verificationNotStored}` : outcome.text,
              notStored ? "warning" : outcome.kind,
            );
          } else {
            setMessage(statusText(result.data.status, t, proposal.tool_name), "warning");
          }
          await refreshProposals();
        });
        item.append(execute);
      } else if (proposal.status === "executed" && proposal.result) {
        item.append(element(
          "p",
          "cp-ai-action-result",
          `${t.result}: ${persistedActivitySummary(proposal.result, t)}`,
        ));
        if (proposal.execution_verification) {
          const storedOutcome = verificationOutcome(proposal.execution_verification, t);
          item.append(element(
            "p",
            storedOutcome.kind === "success" ? "cp-ai-action-result" : "cp-ai-action-metadata",
            storedOutcome.text,
          ));
        }
        item.append(element("p", "cp-ai-action-metadata", t.calculationAtExecution));
      }
      list.append(item);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const rawDuration = duration.value.trim();
    if (!activityId.value.trim() || !activityName.value.trim() || !rawDuration ||
        !Number.isFinite(Number(rawDuration)) || Number(rawDuration) < 0) {
      setMessage(t.required, "error");
      return;
    }
    submit.disabled = true;
    setMessage(t.preparing);
    const result = await client.proposeActivity(context, {
      activity_id: activityId.value.trim(),
      name: activityName.value.trim(),
      duration_value: rawDuration,
      duration_unit: unit.value as CreateActivityProposal["duration_unit"],
    });
    submit.disabled = false;
    if (!result.ok) {
      // A network error can happen after the server persisted the proposal; refresh
      // first and let the user inspect state before submitting another proposal.
      setMessage(`${t.proposalFailed}: ${result.error.code}`, "error");
      await refreshProposals();
      return;
    }
    form.reset();
    setMessage(t.proposalCreated, "success");
    await refreshProposals();
  });

  updateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const activityIdValue = updateActivityId.value.trim();
    const revisionValue = expectedRevision.value.trim();
    const newNameValue = newName.value.trim();
    const newDurationValue = newDuration.value.trim();
    const unitValue = updateUnit.value;
    const revisionNumber = Number(revisionValue);
    if (!activityIdValue || !revisionValue || !Number.isInteger(revisionNumber) || revisionNumber < 1) {
      setMessage(t.revisionInvalid, "error");
      return;
    }
    const hasName = newNameValue.length > 0;
    const hasDuration = newDurationValue.length > 0 || unitValue.length > 0;
    if (!hasName && !hasDuration) {
      setMessage(t.updateNeedsChange, "error");
      return;
    }
    if (hasDuration && (!newDurationValue || !unitValue ||
        !Number.isFinite(Number(newDurationValue)) || Number(newDurationValue) < 0)) {
      setMessage(t.updateNeedsChange, "error");
      return;
    }
    const payload: UpdateActivityProposal = {
      activity_id: activityIdValue,
      expected_revision: revisionNumber,
      ...(hasName ? { name: newNameValue } : {}),
      ...(hasDuration
        ? {
            duration_value: newDurationValue,
            duration_unit: unitValue as NonNullable<UpdateActivityProposal["duration_unit"]>,
          }
        : {}),
    };
    updateSubmit.disabled = true;
    setMessage(t.preparing);
    const result = await client.proposeActivityUpdate(context, payload);
    updateSubmit.disabled = false;
    if (!result.ok) {
      setMessage(`${t.proposalFailed}: ${result.error.code}`, "error");
      await refreshProposals();
      return;
    }
    updateForm.reset();
    setMessage(t.updateProposalCreated, "success");
    await refreshProposals();
  });

  refresh.addEventListener("click", () => { void refreshProposals(); });
  details.addEventListener("toggle", () => {
    if (details.open) void refreshProposals();
  });
  if (details.open) void refreshProposals();
  return refreshProposals;
}

