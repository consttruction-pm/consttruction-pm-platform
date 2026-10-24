import type { ApiTransport, ProjectContext } from "./client.js";
import { AIActionClient, type AIActionProposal } from "./ai-action-client.js";

type PanelLabels = {
  title: string; description: string; createTitle: string; activityId: string;
  activityName: string; duration: string; durationUnit: string; workingDay: string;
  calendarDay: string; hour: string; prepare: string; refresh: string; proposals: string;
  preparing: string; loading: string; proposalReady: string; rejected: string;
  approved: string; executing: string; executed: string; noProposals: string;
  proposalCreated: string; proposalFailed: string; listFailed: string;
  executionFailed: string; stale: string; noRetry: string; approve: string;
  reject: string; execute: string; required: string; invalidResponse: string;
  action: string; projectRevision: string; result: string; operationFailed: string;
};

const labels: Record<"en" | "fa", PanelLabels> = {
  en: {
    title: "AI Assistant · Actions",
    description: "Prepare an activity proposal, review it, then approve and execute it explicitly. No project change is made before approval.",
    createTitle: "Create activity proposal",
    activityId: "Activity ID", activityName: "Activity name", duration: "Duration",
    durationUnit: "Duration unit", workingDay: "Working day", calendarDay: "Calendar day",
    hour: "Hour", prepare: "Prepare proposal", refresh: "Refresh proposals",
    proposals: "Project proposals", preparing: "Preparing proposal…", loading: "Loading proposals…",
    proposalReady: "Proposal is ready for review.", rejected: "Proposal rejected.",
    approved: "Proposal approved.", executing: "Executing approved action…",
    executed: "Activity created successfully.", noProposals: "There are no action proposals for this project.",
    proposalCreated: "Proposal created. Review the details before approving.",
    proposalFailed: "Could not create the proposal.", listFailed: "Could not load proposals.",
    executionFailed: "The action did not complete.", stale: "Project revision changed. This proposal is stale and cannot be approved or executed.",
    noRetry: "The outcome is uncertain or execution was interrupted. Do not retry this action; it needs reconciliation.",
    approve: "Approve", reject: "Reject", execute: "Execute approved action",
    required: "This field is required.", invalidResponse: "The server returned an invalid action response.",
    action: "Action", projectRevision: "Project revision", result: "Result", operationFailed: "Request failed",
  },
  fa: {
    title: "دستیار هوشمند · اقدامات",
    description: "پیشنهاد ایجاد فعالیت را آماده و بررسی کنید؛ سپس آن را صریحاً تأیید و اجرا کنید. پیش از تأیید، تغییری در پروژه انجام نمی‌شود.",
    createTitle: "پیشنهاد ایجاد فعالیت",
    activityId: "شناسه فعالیت", activityName: "نام فعالیت", duration: "مدت",
    durationUnit: "واحد مدت", workingDay: "روز کاری", calendarDay: "روز تقویمی",
    hour: "ساعت", prepare: "تهیه پیشنهاد", refresh: "به‌روزرسانی پیشنهادها",
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
    action: "اقدام", projectRevision: "نسخه پروژه", result: "نتیجه", operationFailed: "درخواست ناموفق بود",
  },
};

function localeLabels(locale: string): PanelLabels {
  return labels[locale.toLowerCase().startsWith("fa") ? "fa" : "en"];
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

function button(text: string, className: string, disabled = false): HTMLButtonElement {
  const item = element("button", className, text);
  item.type = "button";
  item.disabled = disabled;
  return item;
}

function statusText(status: string, t: PanelLabels): string {
  const known: Record<string, string> = {
    proposed: t.proposalReady,
    approved: t.approved,
    rejected: t.rejected,
    executing: t.executing,
    executed: t.executed,
    stale: t.stale,
    uncertain: t.noRetry,
    denied: t.operationFailed,
    blocked: t.operationFailed,
  };
  return known[status] ?? status;
}

function proposalLabel(proposal: AIActionProposal, t: PanelLabels): string {
  const name = typeof proposal.payload.name === "string" ? proposal.payload.name : proposal.proposal_id;
  const id = typeof proposal.payload.activity_id === "string" ? proposal.payload.activity_id : "";
  return id ? `${name} (${id})` : name;
}

/** Mounts the authenticated project's explicitly approval-gated AI action surface. */
export function mountAIActionPanel(
  appShell: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
): void {
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
    ["calendar-day", t.calendarDay],
    ["hour", t.hour],
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

  content.append(form, message, listSection);
  details.append(content);
  appShell.append(details);

  const setMessage = (text: string, kind = ""): void => {
    message.textContent = text;
    message.dataset.kind = kind;
  };

  const operationError = (code: string): string => {
    if (code === "AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN" ||
        code === "AI_ACTION_EXECUTION_STATE_NOT_PERSISTED" ||
        code === "AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED") return t.noRetry;
    if (code === "INVALID_AI_ACTION_RESPONSE") return t.invalidResponse;
    return `${t.operationFailed}: ${code}`;
  };

  const refreshProposals = async (): Promise<void> => {
    refresh.disabled = true;
    const result = await client.listProposals(context);
    refresh.disabled = false;
    list.replaceChildren();
    if (!result.ok) {
      setMessage(operationError(result.error.code), "error");
      return;
    }
    if (result.data.proposals.length === 0) {
      list.append(element("li", "cp-ai-action-empty", t.noProposals));
      return;
    }
    for (const proposal of result.data.proposals) {
      const item = element("li", "cp-ai-action-proposal");
      const heading = element("h4", "", proposalLabel(proposal, t));
      const state = element("p", "cp-ai-action-state", statusText(proposal.status, t));
      const idLine = element("p", "cp-ai-action-metadata", `ID: ${proposal.proposal_id}`);
      const revisionLine = element("p", "cp-ai-action-metadata", `${t.projectRevision}: ${proposal.project_revision_id}`);
      item.append(heading, state, idLine, revisionLine);
      if (proposal.is_stale || proposal.project_revision_id !== String(context.revision)) {
        item.append(element("p", "cp-ai-action-warning", t.stale));
      } else if (proposal.status === "uncertain" || proposal.status === "executing" ||
                 proposal.status === "blocked") {
        item.append(element("p", "cp-ai-action-warning", t.noRetry));
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
          const result = await client.execute(context, proposal.proposal_id);
          if (!result.ok) {
            setMessage(operationError(result.error.code), "error");
          } else if (result.data.status === "executed") {
            setMessage(t.executed, "success");
          } else {
            setMessage(statusText(result.data.status, t), "warning");
          }
          await refreshProposals();
        });
        item.append(execute);
      } else if (proposal.status === "executed" && proposal.result) {
        const serialized = JSON.stringify(proposal.result);
        item.append(element("p", "cp-ai-action-result", `${t.result}: ${serialized}`));
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

  refresh.addEventListener("click", () => { void refreshProposals(); });
  details.addEventListener("toggle", () => {
    if (details.open) void refreshProposals();
  });
  if (details.open) void refreshProposals();
}

