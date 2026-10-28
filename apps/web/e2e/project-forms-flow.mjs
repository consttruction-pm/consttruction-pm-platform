import assert from "node:assert/strict";

/**
 * Exercise the real versioned Form Builder through the browser and authenticated
 * preview API. The same user is explicitly assigned as submitter and approver so
 * this stays deterministic without relying on demo account identifiers.
 */
export async function exerciseProjectFormsPanel(page) {
  await page.scrollTo("#cp-project-forms");
  await page.waitForSelector("#cp-project-forms [data-new-form-name]", "Form Builder create form");

  const session = await page.evaluate(`fetch("/api/session").then(async (response) => {
    if (!response.ok) throw new Error("FORM_E2E_SESSION_UNAVAILABLE");
    return response.json();
  })()`, { awaitPromise: true });
  assert(typeof session.user_id === "string" && session.user_id.length > 0, "Form Builder E2E needs the authenticated session user");

  const formId = "FORM-E2E-" + Date.now().toString(36).toUpperCase();
  const submissionId = "SUB-E2E-" + Date.now().toString(36).toUpperCase();
  await page.setInput("#cp-project-forms [data-new-form-name]", "E2E Daily Field Report");
  await page.setInput("#cp-project-forms [data-new-form-id]", formId);
  await page.setInput("#cp-project-forms [data-new-form-description]", "Typed date and yes/no values with explicit user assignment");
  await page.setInput("#cp-project-forms [data-form-shared-roles]", "");
  await page.setInput("#cp-project-forms [data-form-approver-roles]", "");
  await page.setInput("#cp-project-forms [data-form-shared-users]", session.user_id);
  await page.setInput("#cp-project-forms [data-form-approver-users]", session.user_id);

  const configured = await page.evaluate(`(() => {
    const rows = Array.from(document.querySelectorAll("#cp-project-forms [data-form-fields] [data-form-field-row]"));
    if (rows.length < 2) return { ok: false, count: rows.length };
    const setup = (row, id, label, type) => {
      row.querySelector("[data-field-id]").value = id;
      row.querySelector("[data-field-label]").value = label;
      row.querySelector("[data-field-type]").value = type;
    };
    setup(rows[0], "WORK-DATE", "Work date", "date");
    setup(rows[1], "WORK-COMPLETED", "Work completed", "boolean");
    return { ok: true, types: rows.slice(0, 2).map((row) => row.querySelector("[data-field-type]").value) };
  })()`);
  assert(configured.ok && configured.types.join(",") === "date,boolean", "Form Builder must expose date and boolean field types");

  await page.click("#cp-project-forms form[data-create-project-form] button[type=submit]");
  await page.waitForSelector(`#cp-project-forms [data-publish-form="${formId}"]`, "saved Form Builder draft");
  await page.click(`#cp-project-forms [data-publish-form="${formId}"]`);
  await page.waitForSelector(`#cp-project-forms [data-open-shared-form="${formId}"]`, "published form shared with the explicit user");
  await page.click(`#cp-project-forms [data-open-shared-form="${formId}"]`);
  await page.waitForSelector(`#cp-project-forms form[data-submit-shared-form="${formId}"]`, "shared worker form");

  await page.setInput(`#cp-project-forms input[data-answer-field="WORK-DATE"]`, "2026-10-28");
  await page.setSelect(`#cp-project-forms select[data-answer-field="WORK-COMPLETED"]`, "false");
  await page.click(`#cp-project-forms form[data-submit-shared-form="${formId}"] button[type=submit]`);
  await page.waitFor(
    `!document.querySelector('form[data-submit-shared-form="${formId}"]')`,
    "submission accepted and response form closed",
  );

  await page.click(`#cp-project-forms [data-view-form-submissions="${formId}"]`);
  await page.waitForSelector("#cp-project-forms #cp-form-submissions", "submission review list");
  const submitted = await page.evaluate(`(() => {
    const section = document.querySelector("#cp-project-forms #cp-form-submissions");
    const text = section?.textContent ?? "";
    return {
      text,
      hasDate: text.includes("2026-10-28"),
      hasFalse: text.includes("No") || text.includes("خیر"),
      pendingActions: section?.querySelectorAll('[data-review-submission][data-review-approved="true"]').length ?? 0,
    };
  })()`);
  assert(submitted.hasDate, "submitted date must survive form validation and persistence");
  assert(submitted.hasFalse, "an explicit false answer must remain false, not disappear or become true");
  assert(submitted.pendingActions === 1, "the pending submission must expose one approval action");

  await page.click(`#cp-project-forms button[data-review-submission][data-review-approved="true"][data-review-form="${formId}"]`);
  await page.waitFor(
    `document.querySelectorAll('#cp-project-forms button[data-review-submission][data-review-form="${formId}"]').length === 0`,
    "submission approval is persisted and review controls disappear",
  );
  const approved = await page.evaluate(`(() => {
    const section = document.querySelector("#cp-project-forms #cp-form-submissions");
    return {
      status: section?.querySelector(".cp-form-status")?.textContent?.trim() ?? "",
      text: section?.textContent ?? "",
    };
  })()`);
  assert(approved.text.toLowerCase().includes("approved") || approved.text.includes("تأیید"), "reviewed submission must show its approved state");

  return {
    form_id: formId,
    field_types: configured.types,
    recipient_user_id: session.user_id,
    submitted_date: "2026-10-28",
    submitted_boolean_false_preserved: submitted.hasFalse,
    approved_status_visible: true,
  };
}
