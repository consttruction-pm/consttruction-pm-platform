import type { ApiTransport, ProjectContext } from "./client.js";
import {
  createProjectFormsClient,
  ProjectFormsClientError,
  type ProjectFormDefinition,
  type ProjectFormDraftInput,
  type ProjectFormField,
  type ProjectFormFieldType,
  type ProjectFormSubmission,
} from "./project-forms-api.js";

type Labels = {
  title: string; intro: string; createTitle: string; formId: string; formName: string;
  description: string; shareRoles: string; approverRoles: string; fields: string;
  fieldId: string; fieldLabel: string; fieldType: string; required: string; options: string;
  addField: string; remove: string; createDraft: string; creating: string; ownerForms: string;
  sharedForms: string; submissions: string; noForms: string; noSharedForms: string;
  noSubmissions: string; refresh: string; publish: string; open: string; viewSubmissions: string;
  status: string; version: string; sharedWith: string; approve: string; reject: string;
  reviewNote: string; submit: string; pendingApproval: string; loading: string;
  saved: string; published: string; submitted: string; rejected: string; error: string;
  nameRequired: string; fieldRequired: string; fieldIdInvalid: string;
  selectOptionsRequired: string; approvalNotice: string; workerInstructions: string;
  noModelRequired: string;
};

const LABELS: Record<"en" | "fa", Labels> = {
  en: {
    title: "Project Forms", intro: "Create versioned field forms, publish them to project roles, and review submissions. This workflow does not require the AI assistant.",
    createTitle: "Create a form draft", formId: "Form ID", formName: "Form name", description: "Purpose / description",
    shareRoles: "Share with roles (comma-separated)", approverRoles: "Approver roles (comma-separated)",
    fields: "Fields", fieldId: "Field ID", fieldLabel: "Field label", fieldType: "Type", required: "Required",
    options: "Options (comma-separated for select)", addField: "Add field", remove: "Remove",
    createDraft: "Save draft", creating: "Saving…", ownerForms: "Project forms", sharedForms: "Forms shared with me",
    submissions: "Submissions", noForms: "No forms yet. Create a draft to start.", noSharedForms: "No published forms are shared with this account or role.",
    noSubmissions: "No submissions yet.", refresh: "Refresh", publish: "Publish version", open: "Open form",
    viewSubmissions: "Review submissions", status: "Status", version: "Version", sharedWith: "Shared with",
    approve: "Approve", reject: "Reject", reviewNote: "Review note (optional)", submit: "Submit response",
    pendingApproval: "Pending approval", loading: "Loading…", saved: "Draft saved.", published: "Form published.",
    submitted: "Response sent for approval.", rejected: "Response rejected.", error: "Operation failed",
    nameRequired: "Enter a valid form ID and a form name.", fieldRequired: "Add at least one field with an ID and label.",
    fieldIdInvalid: "Field IDs must start with a letter and contain letters, digits, _ or -.",
    selectOptionsRequired: "A select field requires at least one option.",
    approvalNotice: "Responses remain pending until an authorized approver reviews them.",
    workerInstructions: "Complete the fields and submit the response. Only a published form shared with your account or role can be submitted.",
    noModelRequired: "Form Builder is a core CUBI feature; no language model or external AI key is required.",
  },
  fa: {
    title: "فرم‌های پروژه", intro: "فرم‌های نسخه‌بندی‌شده بسازید، برای نقش‌های پروژه منتشر کنید و پاسخ‌ها را بررسی کنید. این گردش کار به دستیار هوش مصنوعی نیاز ندارد.",
    createTitle: "ساخت پیش‌نویس فرم", formId: "شناسه فرم", formName: "نام فرم", description: "هدف / توضیحات",
    shareRoles: "اشتراک با نقش‌ها (با ویرگول جدا شود)", approverRoles: "نقش‌های تأییدکننده (با ویرگول جدا شود)",
    fields: "فیلدها", fieldId: "شناسه فیلد", fieldLabel: "عنوان فیلد", fieldType: "نوع", required: "الزامی",
    options: "گزینه‌ها (برای انتخابی با ویرگول جدا شود)", addField: "افزودن فیلد", remove: "حذف",
    createDraft: "ذخیره پیش‌نویس", creating: "در حال ذخیره…", ownerForms: "فرم‌های پروژه",
    sharedForms: "فرم‌های به‌اشتراک‌گذاشته‌شده با من", submissions: "پاسخ‌ها", noForms: "هنوز فرمی وجود ندارد. یک پیش‌نویس بسازید.",
    noSharedForms: "فرم منتشرشده‌ای برای حساب یا نقش شما به اشتراک گذاشته نشده است.", noSubmissions: "هنوز پاسخی ثبت نشده است.",
    refresh: "بارگذاری دوباره", publish: "انتشار نسخه", open: "بازکردن فرم", viewSubmissions: "بررسی پاسخ‌ها",
    status: "وضعیت", version: "نسخه", sharedWith: "اشتراک با", approve: "تأیید", reject: "رد",
    reviewNote: "یادداشت بررسی (اختیاری)", submit: "ارسال پاسخ", pendingApproval: "در انتظار تأیید",
    loading: "در حال بارگذاری…", saved: "پیش‌نویس ذخیره شد.", published: "فرم منتشر شد.",
    submitted: "پاسخ برای تأیید ارسال شد.", rejected: "پاسخ رد شد.", error: "عملیات ناموفق بود",
    nameRequired: "شناسه معتبر و نام فرم را وارد کنید.", fieldRequired: "حداقل یک فیلد با شناسه و عنوان اضافه کنید.",
    fieldIdInvalid: "شناسه فیلد باید با حرف شروع شود و فقط حروف، عدد، _ یا - داشته باشد.",
    selectOptionsRequired: "فیلد انتخابی به حداقل یک گزینه نیاز دارد.",
    approvalNotice: "پاسخ‌ها تا بررسی توسط تأییدکننده مجاز در انتظار تأیید می‌مانند.",
    workerInstructions: "فیلدها را تکمیل و پاسخ را ارسال کنید. فقط فرم منتشرشده‌ای که برای حساب یا نقش شما به اشتراک گذاشته شده قابل ارسال است.",
    noModelRequired: "فرم‌ساز قابلیت اصلی CUBI است و به مدل زبانی یا کلید AI خارجی نیاز ندارد.",
  },
};

const boundRoots = new WeakSet<HTMLElement>();
function e(value: string): string {
  return value.replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]!);
}
function localeBase(locale: string): "en" | "fa" { return locale.toLowerCase().startsWith("fa") ? "fa" : "en"; }
function csv(value: string): string[] { return [...new Set(value.split(",").map((x) => x.trim()).filter(Boolean))]; }
function safeIdentifier(value: string): boolean { return /^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(value); }
function formIdentifier(name: string): string {
  const clean = name.toUpperCase().replace(/[^A-Z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32) || "FIELD-FORM";
  return "FORM-" + clean + "-" + Date.now().toString(36).toUpperCase().slice(-5);
}
function latestForms(forms: readonly ProjectFormDefinition[]): ProjectFormDefinition[] {
  const map = new Map<string, ProjectFormDefinition>();
  for (const form of forms) {
    const current = map.get(form.form_id);
    if (!current || form.version > current.version) map.set(form.form_id, form);
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}
function statusText(status: string, labels: Labels): string {
  return status === "pending_approval" ? labels.pendingApproval : status.replace(/_/g, " ");
}
function fieldRow(labels: Labels, fieldId: string, label: string, type: ProjectFormFieldType, required: boolean, options = ""): string {
  return "<div class=\"cp-form-field-row\" data-form-field-row>" +
    "<label><span>" + e(labels.fieldId) + "</span><input data-field-id value=\"" + e(fieldId) + "\" maxlength=\"64\" required></label>" +
    "<label><span>" + e(labels.fieldLabel) + "</span><input data-field-label value=\"" + e(label) + "\" maxlength=\"160\" required></label>" +
    "<label><span>" + e(labels.fieldType) + "</span><select data-field-type>" +
      "<option value=\"text\"" + (type === "text" ? " selected" : "") + ">Text</option>" +
      "<option value=\"number\"" + (type === "number" ? " selected" : "") + ">Number</option>" +
      "<option value=\"select\"" + (type === "select" ? " selected" : "") + ">Select</option>" +
    "</select></label>" +
    "<label class=\"cp-form-required\"><input type=\"checkbox\" data-field-required" + (required ? " checked" : "") + "><span>" + e(labels.required) + "</span></label>" +
    "<label class=\"cp-form-options\"><span>" + e(labels.options) + "</span><input data-field-options value=\"" + e(options) + "\"></label>" +
    "<button type=\"button\" data-remove-form-field>" + e(labels.remove) + "</button></div>";
}
function definitionCard(form: ProjectFormDefinition, labels: Labels): string {
  const shared = [...form.shared_with_roles, ...form.shared_with_user_ids].join(", ") || "—";
  return "<article class=\"cp-form-card\"><div class=\"cp-form-card-heading\"><strong>" + e(form.name) +
    "</strong><span class=\"cp-form-status is-" + e(form.status) + "\">" + e(form.status) + "</span></div>" +
    "<code>" + e(form.form_id) + "</code><p>" + e(form.description || "—") + "</p>" +
    "<div class=\"cp-form-card-meta\"><span>" + e(labels.version) + " " + form.version + "</span><span>" +
    e(labels.sharedWith) + ": " + e(shared) + "</span><span>" + form.fields.length + " fields</span></div><div class=\"cp-form-actions\">" +
    (form.status === "draft" ? "<button type=\"button\" data-publish-form=\"" + e(form.form_id) + "\" data-form-version=\"" + form.version + "\">" + e(labels.publish) + "</button>" : "") +
    (form.status === "published" ? "<button type=\"button\" data-view-form-submissions=\"" + e(form.form_id) + "\">" + e(labels.viewSubmissions) + "</button>" : "") +
    "</div></article>";
}
function sharedCard(form: ProjectFormDefinition, labels: Labels): string {
  return "<article class=\"cp-form-card\"><div class=\"cp-form-card-heading\"><strong>" + e(form.name) +
    "</strong><span class=\"cp-form-status is-published\">" + e(form.status) + "</span></div><p>" +
    e(form.description || "—") + "</p><div class=\"cp-form-card-meta\"><code>" + e(form.form_id) + "</code><span>" +
    e(labels.version) + " " + form.version + "</span></div><button type=\"button\" data-open-shared-form=\"" +
    e(form.form_id) + "\" data-form-version=\"" + form.version + "\">" + e(labels.open) + "</button></article>";
}
function submissionsHtml(formId: string, items: readonly ProjectFormSubmission[], labels: Labels): string {
  const rows = items.map((item) => "<article class=\"cp-form-submission\"><div class=\"cp-form-card-heading\"><strong>" +
    e(item.submission_id) + "</strong><span class=\"cp-form-status is-" + e(item.status) + "\">" + e(statusText(item.status, labels)) +
    "</span></div><p>Submitted by " + e(item.submitted_by) + " · " + e(item.submitted_at) + "</p><dl>" +
    Object.entries(item.answers).map(([key, value]) => "<div><dt>" + e(key) + "</dt><dd>" + e(value) + "</dd></div>").join("") +
    "</dl>" + (item.status === "pending_approval" ?
      "<label><span>" + e(labels.reviewNote) + "</span><input data-review-note=\"" + e(item.submission_id) + "\" maxlength=\"1000\"></label>" +
      "<div class=\"cp-form-actions\"><button type=\"button\" data-review-submission=\"" + e(item.submission_id) + "\" data-review-approved=\"true\" data-review-form=\"" + e(formId) + "\">" + e(labels.approve) +
      "</button><button type=\"button\" data-review-submission=\"" + e(item.submission_id) + "\" data-review-approved=\"false\" data-review-form=\"" + e(formId) + "\">" + e(labels.reject) + "</button></div>" : "") + "</article>").join("");
  return "<section id=\"cp-form-submissions\" class=\"cp-form-section\"><h3>" + e(labels.submissions) + " · " + e(formId) + "</h3>" +
    (rows || "<p class=\"cp-empty\">" + e(labels.noSubmissions) + "</p>") + "</section>";
}
function workerFormHtml(form: ProjectFormDefinition, labels: Labels, locale: string): string {
  const lang = localeBase(locale);
  const fields = form.fields.map((field) => {
    const label = field.localized_labels[lang] || field.label;
    const id = "answer-" + field.field_id;
    let input: string;
    if (field.field_type === "select") {
      input = "<select id=\"" + e(id) + "\" data-answer-field=\"" + e(field.field_id) + "\"" + (field.required ? " required" : "") + "><option value=\"\">—</option>" +
        field.options.map((option) => "<option value=\"" + e(option) + "\">" + e(option) + "</option>").join("") + "</select>";
    } else if (field.field_type === "number") {
      input = "<input id=\"" + e(id) + "\" type=\"number\" data-answer-field=\"" + e(field.field_id) + "\"" +
        (field.minimum !== null ? " min=\"" + e(field.minimum) + "\"" : "") +
        (field.maximum !== null ? " max=\"" + e(field.maximum) + "\"" : "") + (field.required ? " required" : "") + ">";
    } else {
      input = "<input id=\"" + e(id) + "\" type=\"text\" data-answer-field=\"" + e(field.field_id) + "\"" +
        (field.min_length !== null ? " minlength=\"" + field.min_length + "\"" : "") +
        (field.max_length !== null ? " maxlength=\"" + field.max_length + "\"" : "") + (field.required ? " required" : "") + ">";
    }
    return "<label class=\"cp-form-worker-field\" for=\"" + e(id) + "\"><span>" + e(label) + (field.required ? " *" : "") + "</span>" + input + "</label>";
  }).join("");
  const sections = form.sections.map((section) => "<h4>" + e(section.localized_titles[lang] || section.title) + "</h4>").join("");
  return "<section id=\"cp-shared-form-response\" class=\"cp-form-section\"><h3>" + e(form.name) + " · " + e(labels.version) + " " + form.version +
    "</h3><p>" + e(labels.workerInstructions) + "</p>" + sections +
    "<form data-submit-shared-form=\"" + e(form.form_id) + "\" data-form-version=\"" + form.version + "\"><div class=\"cp-form-worker-fields\">" + fields +
    "</div><button type=\"submit\">" + e(labels.submit) + "</button></form></section>";
}

function makeDraftInput(root: HTMLElement, labels: Labels): ProjectFormDraftInput {
  const name = root.querySelector<HTMLInputElement>("[data-new-form-name]")?.value.trim() || "";
  const formId = (root.querySelector<HTMLInputElement>("[data-new-form-id]")?.value.trim() || "").toUpperCase();
  const description = root.querySelector<HTMLTextAreaElement>("[data-new-form-description]")?.value.trim() || "";
  if (name.length < 2 || !/^[A-Z0-9][A-Z0-9_.-]{0,63}$/.test(formId)) throw new Error(labels.nameRequired);
  const fields: ProjectFormField[] = [...root.querySelectorAll<HTMLElement>("[data-form-field-row]")].map((row) => {
    const fieldId = row.querySelector<HTMLInputElement>("[data-field-id]")?.value.trim() || "";
    const fieldLabel = row.querySelector<HTMLInputElement>("[data-field-label]")?.value.trim() || "";
    const fieldType = row.querySelector<HTMLSelectElement>("[data-field-type]")?.value || "text";
    const required = row.querySelector<HTMLInputElement>("[data-field-required]")?.checked || false;
    const options = csv(row.querySelector<HTMLInputElement>("[data-field-options]")?.value || "");
    if (!safeIdentifier(fieldId)) throw new Error(labels.fieldIdInvalid);
    if (!fieldLabel) throw new Error(labels.fieldRequired);
    if (fieldType !== "text" && fieldType !== "number" && fieldType !== "select") throw new Error(labels.fieldRequired);
    if (fieldType === "select" && options.length === 0) throw new Error(labels.selectOptionsRequired);
    return {
      field_id: fieldId, section_id: "GENERAL", field_type: fieldType as ProjectFormFieldType,
      label: fieldLabel, required, options: fieldType === "select" ? options : [],
      localized_labels: {}, minimum: null, maximum: null, min_length: null, max_length: null,
    };
  });
  if (fields.length === 0) throw new Error(labels.fieldRequired);
  if (new Set(fields.map((field) => field.field_id.toUpperCase())).size !== fields.length) throw new Error(labels.fieldIdInvalid);
  return {
    form_id: formId, name, description,
    sections: [{ section_id: "GENERAL", title: "General", localized_titles: { fa: "عمومی" } }],
    fields,
    shared_with_user_ids: [],
    shared_with_roles: csv(root.querySelector<HTMLInputElement>("[data-form-shared-roles]")?.value || ""),
    approver_user_ids: [],
    approver_roles: csv(root.querySelector<HTMLInputElement>("[data-form-approver-roles]")?.value || ""),
    output_mappings: [], requires_approval: true, expected_latest_version: null,
  };
}

type PanelState = {
  ownerForms: readonly ProjectFormDefinition[];
  sharedForms: readonly ProjectFormDefinition[];
  submissions: readonly ProjectFormSubmission[];
  selectedFormId: string;
  workerForm: ProjectFormDefinition | null;
  loading: boolean;
  notice: string;
  error: string;
};

function renderPanel(root: HTMLElement, state: PanelState, labels: Labels, locale: string): void {
  const owner = latestForms(state.ownerForms);
  const shared = latestForms(state.sharedForms).filter((form) => form.status === "published");
  root.innerHTML = "<header class=\"cp-form-header\"><div><h2>" + e(labels.title) + "</h2><p>" + e(labels.intro) +
    "</p><p class=\"cp-form-no-ai\">" + e(labels.noModelRequired) + "</p></div><button type=\"button\" data-refresh-project-forms>" + e(labels.refresh) + "</button></header>" +
    (state.loading ? "<p role=\"status\" class=\"cp-empty\">" + e(labels.loading) + "</p>" : "") +
    (state.notice ? "<p role=\"status\" class=\"cp-form-notice\">" + e(state.notice) + "</p>" : "") +
    (state.error ? "<p role=\"alert\" class=\"cp-form-error\"><strong>" + e(labels.error) + "</strong>: " + e(state.error) + "</p>" : "") +
    "<section id=\"cp-form-builder-create\" class=\"cp-form-section\"><h3>" + e(labels.createTitle) + "</h3><form data-create-project-form>" +
    "<div class=\"cp-form-definition-grid\">" +
    "<label><span>" + e(labels.formName) + "</span><input data-new-form-name required maxlength=\"180\" placeholder=\"Daily field log\"></label>" +
    "<label><span>" + e(labels.formId) + "</span><input data-new-form-id required maxlength=\"64\" value=\"" + e(formIdentifier("Daily field log")) + "\"></label>" +
    "<label class=\"cp-form-wide\"><span>" + e(labels.description) + "</span><textarea data-new-form-description rows=\"2\" maxlength=\"3000\"></textarea></label>" +
    "<label><span>" + e(labels.shareRoles) + "</span><input data-form-shared-roles value=\"field_worker\"></label>" +
    "<label><span>" + e(labels.approverRoles) + "</span><input data-form-approver-roles value=\"project_admin\"></label></div>" +
    "<div class=\"cp-form-fields-heading\"><h4>" + e(labels.fields) + "</h4><button type=\"button\" data-add-form-field>" + e(labels.addField) + "</button></div>" +
    "<div data-form-fields>" + fieldRow(labels, "ACTIVITY-ID", "Activity ID", "text", true) + fieldRow(labels, "QUANTITY", "Quantity completed", "number", true) + "</div>" +
    "<p class=\"cp-form-help\">" + e(labels.approvalNotice) + "</p><button type=\"submit\">" + e(labels.createDraft) + "</button></form></section>" +
    "<section id=\"cp-form-builder\" class=\"cp-form-section\"><h3>" + e(labels.ownerForms) + "</h3><div class=\"cp-form-card-grid\">" +
    (owner.map((form) => definitionCard(form, labels)).join("") || "<p class=\"cp-empty\">" + e(labels.noForms) + "</p>") + "</div></section>" +
    "<section id=\"cp-shared-forms\" class=\"cp-form-section\"><h3>" + e(labels.sharedForms) + "</h3><div class=\"cp-form-card-grid\">" +
    (shared.map((form) => sharedCard(form, labels)).join("") || "<p class=\"cp-empty\">" + e(labels.noSharedForms) + "</p>") + "</div></section>" +
    (state.selectedFormId ? submissionsHtml(state.selectedFormId, state.submissions, labels) : "") +
    (state.workerForm ? workerFormHtml(state.workerForm, labels, locale) : "");
}

function errorCode(error: unknown): string {
  return error instanceof ProjectFormsClientError ? error.code : error instanceof Error ? error.message : "PROJECT_FORM_OPERATION_FAILED";
}

export function mountProjectFormsPanel(workspace: HTMLElement, transport: ApiTransport, context: ProjectContext, locale: string): void {
  const root = workspace.querySelector<HTMLElement>("[data-form-builder-panel]");
  if (!root) return;
  const labels = LABELS[localeBase(locale)];
  const client = createProjectFormsClient(transport, context);
  const state: PanelState = {
    ownerForms: [], sharedForms: [], submissions: [], selectedFormId: "", workerForm: null,
    loading: false, notice: "", error: "",
  };
  const refresh = async (): Promise<void> => {
    state.loading = true;
    state.error = "";
    renderPanel(root, state, labels, locale);
    const results = await Promise.allSettled([client.listDefinitions(), client.listSharedForms()]);
    state.ownerForms = results[0].status === "fulfilled" ? results[0].value : [];
    state.sharedForms = results[1].status === "fulfilled" ? results[1].value : [];
    state.loading = false;
    if (results.every((result) => result.status === "rejected")) state.error = errorCode((results[0] as PromiseRejectedResult).reason);
    renderPanel(root, state, labels, locale);
  };
  const fail = (error: unknown): void => {
    state.error = errorCode(error);
    state.notice = "";
    renderPanel(root, state, labels, locale);
  };

  if (!boundRoots.has(root)) {
    boundRoots.add(root);
    root.addEventListener("click", async (event) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLElement>(
        "[data-refresh-project-forms],[data-add-form-field],[data-remove-form-field],[data-publish-form],[data-view-form-submissions],[data-open-shared-form],[data-review-submission]",
      ) : null;
      if (!target) return;
      event.preventDefault();
      if (target.hasAttribute("data-refresh-project-forms")) { await refresh(); return; }
      if (target.hasAttribute("data-add-form-field")) {
        const fields = root.querySelector<HTMLElement>("[data-form-fields]");
        if (fields) fields.insertAdjacentHTML("beforeend", fieldRow(labels, "FIELD-" + (fields.querySelectorAll("[data-form-field-row]").length + 1), "", "text", false));
        return;
      }
      if (target.hasAttribute("data-remove-form-field")) {
        const row = target.closest<HTMLElement>("[data-form-field-row]");
        const fields = root.querySelector<HTMLElement>("[data-form-fields]");
        if (row && fields && fields.querySelectorAll("[data-form-field-row]").length > 1) row.remove();
        return;
      }
      if (target.dataset.publishForm) {
        try {
          await client.publish(target.dataset.publishForm, Number(target.dataset.formVersion));
          state.notice = labels.published;
          await refresh();
          state.notice = labels.published;
          renderPanel(root, state, labels, locale);
        } catch (error) { fail(error); }
        return;
      }
      if (target.dataset.viewFormSubmissions) {
        try {
          state.selectedFormId = target.dataset.viewFormSubmissions;
          state.submissions = await client.listSubmissions(state.selectedFormId);
          state.error = "";
          state.notice = "";
          renderPanel(root, state, labels, locale);
        } catch (error) { fail(error); }
        return;
      }
      if (target.dataset.openSharedForm) {
        try {
          state.workerForm = await client.getSharedForm(target.dataset.openSharedForm, Number(target.dataset.formVersion));
          state.error = "";
          state.notice = "";
          renderPanel(root, state, labels, locale);
          root.querySelector<HTMLElement>("#cp-shared-form-response")?.scrollIntoView({ block: "start", behavior: "smooth" });
        } catch (error) { fail(error); }
        return;
      }
      if (target.dataset.reviewSubmission) {
        const formId = target.dataset.reviewForm || state.selectedFormId;
        const submissionId = target.dataset.reviewSubmission;
        const approved = target.dataset.reviewApproved === "true";
        const noteElement = [...root.querySelectorAll<HTMLInputElement>("[data-review-note]")].find((item) => item.dataset.reviewNote === submissionId);
        try {
          await client.reviewSubmission(formId, submissionId, approved, noteElement?.value.trim() || null);
          state.submissions = await client.listSubmissions(formId);
          state.notice = approved ? labels.saved : labels.rejected;
          state.error = "";
          renderPanel(root, state, labels, locale);
        } catch (error) { fail(error); }
      }
    });
    root.addEventListener("submit", async (event) => {
      const form = event.target instanceof HTMLFormElement ? event.target : null;
      if (!form) return;
      if (form.hasAttribute("data-create-project-form")) {
        event.preventDefault();
        state.error = "";
        state.notice = "";
        let input: ProjectFormDraftInput;
        try { input = makeDraftInput(root, labels); }
        catch (error) { fail(error); return; }
        const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
        if (submit) { submit.disabled = true; submit.textContent = labels.creating; }
        try {
          await client.createDraft(input);
          state.notice = labels.saved;
          await refresh();
          state.notice = labels.saved;
          renderPanel(root, state, labels, locale);
        } catch (error) { fail(error); }
        finally {
          const button = root.querySelector<HTMLButtonElement>('[data-create-project-form] button[type="submit"]');
          if (button) { button.disabled = false; button.textContent = labels.createDraft; }
        }
        return;
      }
      if (form.dataset.submitSharedForm && state.workerForm) {
        event.preventDefault();
        const answers: Record<string, string> = {};
        form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>("[data-answer-field]").forEach((input) => {
          const value = input.value.trim();
          if (value) answers[input.dataset.answerField!] = value;
        });
        const submissionId = "SUB-" + Date.now().toString(36).toUpperCase();
        const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]');
        if (submit) { submit.disabled = true; submit.textContent = labels.loading; }
        try {
          await client.submitSharedForm(state.workerForm.form_id, state.workerForm.version, submissionId, answers);
          state.notice = labels.submitted;
          state.error = "";
          state.workerForm = null;
          await refresh();
          state.notice = labels.submitted;
          renderPanel(root, state, labels, locale);
        } catch (error) { fail(error); }
      }
    });
  }
  void refresh();
}
