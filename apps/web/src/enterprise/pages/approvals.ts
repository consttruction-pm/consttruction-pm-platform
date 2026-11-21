import type { PageContext } from "../app.js";
import { api, probe, type EnterpriseRecord } from "../api.js";
import { badge, el } from "../ui.js";
import {
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
 * Page 12 — Feedback and approval center.
 *
 * Decisions are pinned to the revision the reviewer saw. The server rejects a
 * stale expected_revision and a replayed decision; this page implements that
 * contract and never fakes an approval.
 */

export function renderApprovals(ctx: PageContext, host: HTMLElement): void {
  const intro = section("Revision-pinned decisions", "An approval is a decision about one exact revision of one item. If the item changes, the old revision cannot be approved.");
  sectionBody(intro,
    note("The client sends expected_revision and an Idempotency-Key. The server compares the revision, rejects stale or duplicate decisions and writes the audit record.", "warning"),
  );
  testId(intro, "approvals-intro");
  host.append(intro);

  const queue = section("Pending approvals", "The queue is read from the approval service. No item is listed unless the server returned it.");
  const newApproval = el("form", { class: "cubi-toolbar" });
  const newTitle = testId(textInput({ placeholder: "Approval title", required: true }), "approvals-create-title");
  const newProject = selectControl(
    [{ value: "", label: "No project" }, ...ctx.projects.map((project) => ({ value: project.project_id, label: project.name }))],
    "",
    () => {},
  );
  const newSubmit = testId(el("button", { class: "cubi-btn cubi-btn-primary", text: "New approval", attrs: { type: "submit" } }), "approvals-create-submit");
  newApproval.append(newTitle, newProject, newSubmit);
  const queueHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  newApproval.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!newTitle.value.trim()) {
      ctx.toast("A title is required.", "error");
      return;
    }
    newSubmit.disabled = true;
    const key = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `approval-${Date.now()}`;
    void api.enterpriseCreate("approvals", {
      title: newTitle.value.trim(),
      project_id: newProject.value || null,
      status: "pending",
    }, key).then(() => {
      ctx.toast("Approval created on the server.", "info");
      window.location.reload();
    }).catch((error: unknown) => {
      newSubmit.disabled = false;
      ctx.toast(error instanceof Error ? error.message : String(error), "error");
    });
  });
  sectionBody(queue, newApproval, queueHost);
  testId(queue, "approvals-queue");
  host.append(queue);

  const decision = section("Record a decision", "Approve, reject or request changes against the revision that was reviewed.");
  const form = el("form", { class: "cubi-form-grid" });
  const itemId = testId(textInput({ placeholder: "approval item id" }), "approvals-item-id");
  const revision = testId(textInput({ type: "number", placeholder: "expected revision" }), "approvals-revision");
  const outcome = testId(selectControl([
    { value: "approve", label: "Approve" },
    { value: "reject", label: "Reject" },
    { value: "request_changes", label: "Request changes" },
  ], "approve", () => {}), "approvals-outcome");
  const comment = textAreaLocal();
  const submit = testId(el("button", { class: "cubi-btn cubi-btn-primary", text: "Submit decision", attrs: { type: "submit" } }), "approvals-submit");
  const result = testId(el("p", { class: "cubi-alert cubi-alert-info", attrs: { role: "status", hidden: "hidden" } }), "approvals-result");
  form.append(
    labelled("Item", itemId, "Identifier returned by the approval queue."),
    labelled("Expected revision", revision, "The exact revision you reviewed."),
    labelled("Decision", outcome),
    labelled("Comment", comment, "Recorded with the decision."),
  );
  form.append(result, submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    result.hidden = true;
    const id = itemId.value.trim();
    const expected = Number(revision.value);
    if (!id) {
      showResult(result, "Enter the approval item identifier.", true);
      return;
    }
    if (!Number.isInteger(expected) || expected < 1) {
      showResult(result, "Enter the integer revision that was reviewed.", true);
      return;
    }
    submit.disabled = true;
    const key = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `decision-${Date.now()}`;
    const body = JSON.stringify({ expected_revision: expected, decision: outcome.value, comment: comment.value });
    fetch(`/api/enterprise/approvals/${encodeURIComponent(id)}/decisions`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": key,
        ...csrfHeader(),
      },
      body,
    })
      .then(async (response) => {
        submit.disabled = false;
        if (response.ok) {
          showResult(result, "Decision recorded by the server. The queue will refresh.", false);
          ctx.toast("Decision recorded.", "info");
          return;
        }
        const payload = await response.json().catch(() => ({} as Record<string, unknown>));
        const code = String(payload.code ?? `HTTP_${response.status}`);
        if (response.status === 409 && /STALE|REVISION/.test(code)) {
          showResult(result, `Rejected as stale (${code}). The item changed after revision ${expected}; review the new revision before deciding.`, true);
        } else if (response.status === 409 && /DUPLICATE|REPLAY/.test(code)) {
          showResult(result, `Rejected as a duplicate decision (${code}). The idempotency key was already used.`, true);
        } else if (response.status === 403) {
          showResult(result, `Forbidden (${code}). Your server roles do not allow this decision.`, true);
        } else if (response.status === 404) {
          showResult(result, "The approval service route is not mounted on this server. No decision was recorded.", true);
        } else {
          showResult(result, `The decision was not recorded: ${code} (HTTP ${response.status}).`, true);
        }
      })
      .catch(() => {
        submit.disabled = false;
        showResult(result, "The server could not be reached. No decision was recorded.", true);
      });
  });
  sectionBody(decision, form);
  testId(decision, "approvals-decision");
  host.append(decision);

  const feedback = section("Feedback queue", "Feedback items use the same revision pinning rules as approvals.");
  const feedbackHost = el("div");
  sectionBody(feedback, feedbackHost);
  testId(feedback, "approvals-feedback");
  host.append(feedback);

  const states = section("Decision outcomes", "These are the server outcomes this page is designed to show.");
  const list = el("div", { class: "cubi-list" });
  list.append(
    outcomeRow("Recorded", "The decision was accepted for the expected revision and written to audit.", "success"),
    outcomeRow("Stale revision", "HTTP 409 · the item has moved on; the reviewer must re-read it.", "danger"),
    outcomeRow("Duplicate decision", "HTTP 409 · the same idempotency key cannot decide twice.", "warning"),
    outcomeRow("Forbidden", "HTTP 403 · the server session lacks the decision permission.", "neutral"),
    outcomeRow("Not connected", "HTTP 404 · the route is not mounted; nothing is recorded.", "neutral"),
  );
  sectionBody(states, list);
  testId(states, "approvals-outcomes");
  host.append(states);

  void loadQueue(ctx, queueHost, feedbackHost, submit, (id, rev) => {
    itemId.value = id;
    revision.value = String(rev);
  });
}

async function loadQueue(
  ctx: PageContext,
  queueHost: HTMLElement,
  feedbackHost: HTMLElement,
  submit: HTMLButtonElement,
  fill: (id: string, revision: number) => void,
): Promise<void> {
  const [queue, feedback] = await Promise.all([
    probe("/api/enterprise/approvals"),
    probe("/api/enterprise/feedback"),
  ]);
  if (queue.state === "available") {
    try {
      const items = (await api.enterpriseList("approvals")).items.filter((item) => !item.deleted_at);
      if (items.length === 0) {
        queueHost.replaceChildren(el("p", { class: "cubi-field-hint", text: "The approval service answered with zero items for this tenant." }));
      } else {
        queueHost.replaceChildren(approvalTable(ctx, items, fill));
      }
      submit.disabled = false;
    } catch (error) {
      queueHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: String(error) }));
      submit.disabled = true;
    }
  } else {
    queueHost.replaceChildren(sourceState(queue, ctx.t, { title: "Approval queue is not connected", source: "Enterprise approval API", detail: "Submit remains disabled until the server route is mounted." }));
    submit.disabled = true;
    submit.title = "The approval service is not connected.";
  }
  feedbackHost.replaceChildren(
    feedback.state === "available"
      ? el("p", { class: "cubi-field-hint", text: "The feedback service responded." })
      : sourceState(feedback, ctx.t, { title: "Feedback queue is not connected", source: "Enterprise feedback API" }),
  );
}

function approvalTable(ctx: PageContext, items: EnterpriseRecord[], fill: (id: string, revision: number) => void): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  testId(wrap, "approvals-table");
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Item" }),
    el("th", { text: "Status" }),
    el("th", { text: "Revision" }),
    el("th", { text: "Project" }),
    el("th", { text: "" }),
  )));
  const body = el("tbody");
  for (const item of items) {
    const review = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Review", attrs: { type: "button" } });
    review.addEventListener("click", () => fill(item.record_id, item.revision));
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: String(item.title ?? item.record_id) }), el("div", { class: "cubi-field-hint", text: item.record_id })),
      el("td", {}, badge(String(item.status ?? "—"), item.status === "approved" ? "success" : item.status === "rejected" ? "danger" : "info")),
      el("td", { text: String(item.revision) }),
      el("td", { text: String(item.project_id ?? "—") }),
      el("td", {}, review),
    ));
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function textAreaLocal(): HTMLTextAreaElement {
  return textArea({ placeholder: "Decision comment", rows: 3 });
}

function csrfHeader(): Record<string, string> {
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === "cp_csrf") return { "x-csrf-token": decodeURIComponent(rest.join("=")) };
  }
  return {};
}

function showResult(node: HTMLElement, message: string, error: boolean): void {
  node.textContent = message;
  node.className = `cubi-alert ${error ? "cubi-alert-error" : "cubi-alert-info"}`;
  node.hidden = false;
}

function outcomeRow(title: string, body: string, tone: "success" | "danger" | "warning" | "neutral"): HTMLElement {
  return el("div", { class: "cubi-list-item" }, el("div", {}, el("strong", { text: title }), el("p", { class: "cubi-field-hint", text: body })), badge(title.toLowerCase(), tone));
}
