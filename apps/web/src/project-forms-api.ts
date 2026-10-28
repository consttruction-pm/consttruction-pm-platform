import type { ApiTransport, ApiResult, ProjectContext } from "./client.js";

export const PROJECT_FORM_CONTRACT_VERSION = "project-form.v1";
export type ProjectFormFieldType = "text" | "number" | "select";

export type ProjectFormField = {
  field_id: string;
  section_id: string;
  field_type: ProjectFormFieldType;
  label: string;
  required: boolean;
  options: readonly string[];
  localized_labels: Readonly<Record<string, string>>;
  minimum: string | null;
  maximum: string | null;
  min_length: number | null;
  max_length: number | null;
};

export type ProjectFormSection = {
  section_id: string;
  title: string;
  localized_titles: Readonly<Record<string, string>>;
};

export type ProjectFormDefinition = {
  contract_version: typeof PROJECT_FORM_CONTRACT_VERSION;
  scope: { tenant_id: string; project_id: string; project_revision: number };
  form_id: string;
  version: number;
  name: string;
  description: string;
  status: "draft" | "published" | "retired";
  sections: readonly ProjectFormSection[];
  fields: readonly ProjectFormField[];
  shared_with_user_ids: readonly string[];
  shared_with_roles: readonly string[];
  approver_user_ids: readonly string[];
  approver_roles: readonly string[];
  output_mappings: readonly {
    field_id: string;
    target_domain: string;
    target_field: string;
  }[];
  requires_approval: boolean;
  created_by: string;
  created_at: string;
  published_by: string | null;
  published_at: string | null;
};

export type ProjectFormSubmission = {
  contract_version: "project-form-submission.v1";
  scope: { tenant_id: string; project_id: string; project_revision: number };
  submission_id: string;
  form_id: string;
  form_version: number;
  submitted_by: string;
  answers: Readonly<Record<string, string>>;
  status: "pending_approval" | "approved" | "rejected";
  submitted_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
};

export type ProjectFormDraftInput = {
  form_id: string;
  name: string;
  description: string;
  sections: readonly ProjectFormSection[];
  fields: readonly ProjectFormField[];
  shared_with_user_ids: readonly string[];
  shared_with_roles: readonly string[];
  approver_user_ids: readonly string[];
  approver_roles: readonly string[];
  output_mappings: readonly {
    field_id: string;
    target_domain: string;
    target_field: string;
  }[];
  requires_approval: boolean;
  expected_latest_version: number | null;
};

export class ProjectFormsClientError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "ProjectFormsClientError";
  }
}

function invalid(code: string): never {
  throw new ProjectFormsClientError(code);
}

function record(value: unknown, code: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) invalid(code);
  return value as Record<string, unknown>;
}

function text(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) invalid(code);
  return value;
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null) return null;
  return text(value, code);
}

function listText(value: unknown, code: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) invalid(code);
  return value as string[];
}

function labelMap(value: unknown, code: string): Record<string, string> {
  const raw = record(value, code);
  const entries = Object.entries(raw);
  if (entries.some(([key, item]) => !key.trim() || typeof item !== "string")) invalid(code);
  return Object.fromEntries(entries) as Record<string, string>;
}

function scope(value: unknown, context: ProjectContext): ProjectFormDefinition["scope"] {
  const raw = record(value, "PROJECT_FORM_SCOPE_INVALID");
  if (
    raw.tenant_id !== context.tenant_id ||
    raw.project_id !== context.project_id ||
    Number(raw.project_revision) !== context.revision
  ) invalid("PROJECT_FORM_SCOPE_MISMATCH");
  return {
    tenant_id: text(raw.tenant_id, "PROJECT_FORM_SCOPE_INVALID"),
    project_id: text(raw.project_id, "PROJECT_FORM_SCOPE_INVALID"),
    project_revision: Number(raw.project_revision),
  };
}

function projectField(value: unknown): ProjectFormField {
  const raw = record(value, "PROJECT_FORM_FIELD_INVALID");
  const fieldType = text(raw.field_type, "PROJECT_FORM_FIELD_TYPE_INVALID");
  if (fieldType !== "text" && fieldType !== "number" && fieldType !== "select") {
    invalid("PROJECT_FORM_FIELD_TYPE_UNSUPPORTED");
  }
  const optionalInteger = (item: unknown, code: string): number | null => {
    if (item === null) return null;
    if (typeof item !== "number" || !Number.isInteger(item)) invalid(code);
    return item;
  };
  const optionalDecimal = (item: unknown, code: string): string | null => {
    if (item === null) return null;
    if (typeof item !== "string" && typeof item !== "number") invalid(code);
    return String(item);
  };
  if (typeof raw.required !== "boolean") invalid("PROJECT_FORM_FIELD_REQUIRED_INVALID");
  return {
    field_id: text(raw.field_id, "PROJECT_FORM_FIELD_ID_INVALID"),
    section_id: text(raw.section_id, "PROJECT_FORM_SECTION_ID_INVALID"),
    field_type: fieldType,
    label: text(raw.label, "PROJECT_FORM_FIELD_LABEL_INVALID"),
    required: raw.required,
    options: listText(raw.options, "PROJECT_FORM_FIELD_OPTIONS_INVALID"),
    localized_labels: labelMap(raw.localized_labels, "PROJECT_FORM_FIELD_LABELS_INVALID"),
    minimum: optionalDecimal(raw.minimum, "PROJECT_FORM_FIELD_MINIMUM_INVALID"),
    maximum: optionalDecimal(raw.maximum, "PROJECT_FORM_FIELD_MAXIMUM_INVALID"),
    min_length: optionalInteger(raw.min_length, "PROJECT_FORM_FIELD_MIN_LENGTH_INVALID"),
    max_length: optionalInteger(raw.max_length, "PROJECT_FORM_FIELD_MAX_LENGTH_INVALID"),
  };
}

function projectSection(value: unknown): ProjectFormSection {
  const raw = record(value, "PROJECT_FORM_SECTION_INVALID");
  return {
    section_id: text(raw.section_id, "PROJECT_FORM_SECTION_ID_INVALID"),
    title: text(raw.title, "PROJECT_FORM_SECTION_TITLE_INVALID"),
    localized_titles: labelMap(raw.localized_titles, "PROJECT_FORM_SECTION_LABELS_INVALID"),
  };
}

function projectDefinition(value: unknown, context: ProjectContext): ProjectFormDefinition {
  const raw = record(value, "PROJECT_FORM_DEFINITION_INVALID");
  if (raw.contract_version !== PROJECT_FORM_CONTRACT_VERSION) invalid("PROJECT_FORM_CONTRACT_UNSUPPORTED");
  const formStatus = text(raw.status, "PROJECT_FORM_STATUS_INVALID");
  if (formStatus !== "draft" && formStatus !== "published" && formStatus !== "retired") {
    invalid("PROJECT_FORM_STATUS_INVALID");
  }
  if (!Array.isArray(raw.sections) || !Array.isArray(raw.fields) || !Array.isArray(raw.output_mappings)) {
    invalid("PROJECT_FORM_DEFINITION_INVALID");
  }
  if (typeof raw.version !== "number" || !Number.isSafeInteger(raw.version) || raw.version < 1) {
    invalid("PROJECT_FORM_VERSION_INVALID");
  }
  if (typeof raw.requires_approval !== "boolean") invalid("PROJECT_FORM_APPROVAL_FLAG_INVALID");
  const mappings = raw.output_mappings.map((item) => {
    const mapping = record(item, "PROJECT_FORM_OUTPUT_MAPPING_INVALID");
    return {
      field_id: text(mapping.field_id, "PROJECT_FORM_OUTPUT_MAPPING_INVALID"),
      target_domain: text(mapping.target_domain, "PROJECT_FORM_OUTPUT_MAPPING_INVALID"),
      target_field: text(mapping.target_field, "PROJECT_FORM_OUTPUT_MAPPING_INVALID"),
    };
  });
  return {
    contract_version: PROJECT_FORM_CONTRACT_VERSION,
    scope: scope(raw.scope, context),
    form_id: text(raw.form_id, "PROJECT_FORM_ID_INVALID"),
    version: raw.version,
    name: text(raw.name, "PROJECT_FORM_NAME_INVALID"),
    description: typeof raw.description === "string" ? raw.description : invalid("PROJECT_FORM_DESCRIPTION_INVALID"),
    status: formStatus,
    sections: raw.sections.map(projectSection),
    fields: raw.fields.map(projectField),
    shared_with_user_ids: listText(raw.shared_with_user_ids, "PROJECT_FORM_SHARE_USERS_INVALID"),
    shared_with_roles: listText(raw.shared_with_roles, "PROJECT_FORM_SHARE_ROLES_INVALID"),
    approver_user_ids: listText(raw.approver_user_ids, "PROJECT_FORM_APPROVERS_INVALID"),
    approver_roles: listText(raw.approver_roles, "PROJECT_FORM_APPROVERS_INVALID"),
    output_mappings: mappings,
    requires_approval: raw.requires_approval,
    created_by: text(raw.created_by, "PROJECT_FORM_CREATED_BY_INVALID"),
    created_at: text(raw.created_at, "PROJECT_FORM_CREATED_AT_INVALID"),
    published_by: optionalText(raw.published_by, "PROJECT_FORM_PUBLISHED_BY_INVALID"),
    published_at: optionalText(raw.published_at, "PROJECT_FORM_PUBLISHED_AT_INVALID"),
  };
}

function projectSubmission(value: unknown, context: ProjectContext): ProjectFormSubmission {
  const raw = record(value, "PROJECT_FORM_SUBMISSION_INVALID");
  if (raw.contract_version !== "project-form-submission.v1") invalid("PROJECT_FORM_SUBMISSION_CONTRACT_UNSUPPORTED");
  const status = text(raw.status, "PROJECT_FORM_SUBMISSION_STATUS_INVALID");
  if (status !== "pending_approval" && status !== "approved" && status !== "rejected") {
    invalid("PROJECT_FORM_SUBMISSION_STATUS_INVALID");
  }
  const answersRaw = record(raw.answers, "PROJECT_FORM_ANSWERS_INVALID");
  if (Object.values(answersRaw).some((answer) => typeof answer !== "string")) invalid("PROJECT_FORM_ANSWERS_INVALID");
  if (typeof raw.form_version !== "number" || !Number.isSafeInteger(raw.form_version) || raw.form_version < 1) {
    invalid("PROJECT_FORM_VERSION_INVALID");
  }
  return {
    contract_version: "project-form-submission.v1",
    scope: scope(raw.scope, context),
    submission_id: text(raw.submission_id, "PROJECT_FORM_SUBMISSION_ID_INVALID"),
    form_id: text(raw.form_id, "PROJECT_FORM_ID_INVALID"),
    form_version: raw.form_version,
    submitted_by: text(raw.submitted_by, "PROJECT_FORM_SUBMITTED_BY_INVALID"),
    answers: answersRaw as Record<string, string>,
    status,
    submitted_at: text(raw.submitted_at, "PROJECT_FORM_SUBMITTED_AT_INVALID"),
    reviewed_by: optionalText(raw.reviewed_by, "PROJECT_FORM_REVIEWED_BY_INVALID"),
    reviewed_at: optionalText(raw.reviewed_at, "PROJECT_FORM_REVIEWED_AT_INVALID"),
    review_note: optionalText(raw.review_note, "PROJECT_FORM_REVIEW_NOTE_INVALID"),
  };
}

async function requireSuccess<T>(result: Promise<ApiResult<T>>, defaultCode: string): Promise<T> {
  const response = await result;
  if (!response.ok) invalid(response.error.code || defaultCode);
  return response.data;
}

export type ProjectFormsClient = {
  listDefinitions(): Promise<readonly ProjectFormDefinition[]>;
  listSharedForms(): Promise<readonly ProjectFormDefinition[]>;
  createDraft(input: ProjectFormDraftInput): Promise<ProjectFormDefinition>;
  publish(formId: string, version: number): Promise<ProjectFormDefinition>;
  listSubmissions(formId: string): Promise<readonly ProjectFormSubmission[]>;
  reviewSubmission(formId: string, submissionId: string, approved: boolean, reviewNote: string | null): Promise<ProjectFormSubmission>;
  getSharedForm(formId: string, version: number): Promise<ProjectFormDefinition>;
  submitSharedForm(formId: string, version: number, submissionId: string, answers: Readonly<Record<string, string>>): Promise<ProjectFormSubmission>;
};

export function createProjectFormsClient(transport: ApiTransport, context: ProjectContext): ProjectFormsClient {
  const base = "/api/projects/" + encodeURIComponent(context.project_id) + "/forms";

  const readDefinitionList = async (path: string, allowedContracts: readonly string[]) => {
    const payload = record(await requireSuccess(transport.get<unknown>(path, context), "PROJECT_FORM_LIST_FAILED"), "PROJECT_FORM_LIST_INVALID");
    if (!allowedContracts.includes(String(payload.contract_version))) invalid("PROJECT_FORM_LIST_CONTRACT_UNSUPPORTED");
    if (!Array.isArray(payload.forms)) invalid("PROJECT_FORM_LIST_INVALID");
    return payload.forms.map((item) => projectDefinition(item, context));
  };

  return {
    listDefinitions: () => readDefinitionList(base, ["project-form.list.v1"]),
    listSharedForms: () => readDefinitionList(base + "/shared", ["project-form.shared-list.v1", "project-form.list.v1"]),
    async createDraft(input) {
      const payload = await requireSuccess(
        transport.post<ProjectFormDraftInput, unknown>(base, input, context),
        "PROJECT_FORM_CREATE_FAILED",
      );
      return projectDefinition(payload, context);
    },
    async publish(formId, version) {
      const payload = await requireSuccess(
        transport.post<Record<string, never>, unknown>(base + "/" + encodeURIComponent(formId) + "/" + version + "/publish", {}, context),
        "PROJECT_FORM_PUBLISH_FAILED",
      );
      return projectDefinition(payload, context);
    },
    async listSubmissions(formId) {
      const path = base + "/" + encodeURIComponent(formId) + "/submissions";
      const payload = record(await requireSuccess(transport.get<unknown>(path, context), "PROJECT_FORM_SUBMISSIONS_FAILED"), "PROJECT_FORM_SUBMISSIONS_INVALID");
      if (payload.contract_version !== "project-form.submission-list.v1" || !Array.isArray(payload.submissions)) {
        invalid("PROJECT_FORM_SUBMISSIONS_CONTRACT_UNSUPPORTED");
      }
      return payload.submissions.map((item) => projectSubmission(item, context));
    },
    async reviewSubmission(formId, submissionId, approved, reviewNote) {
      const path = base + "/" + encodeURIComponent(formId) + "/submissions/" + encodeURIComponent(submissionId) + "/review";
      const payload = await requireSuccess(
        transport.post(path, { approved, review_note: reviewNote }, context),
        "PROJECT_FORM_REVIEW_FAILED",
      );
      return projectSubmission(payload, context);
    },
    async getSharedForm(formId, version) {
      const payload = await requireSuccess(
        transport.get<unknown>(base + "/shared/" + encodeURIComponent(formId) + "/" + version, context),
        "PROJECT_FORM_SHARED_READ_FAILED",
      );
      return projectDefinition(payload, context);
    },
    async submitSharedForm(formId, version, submissionId, answers) {
      const payload = await requireSuccess(
        transport.post(base + "/shared/" + encodeURIComponent(formId) + "/" + version + "/submissions", { submission_id: submissionId, answers }, context),
        "PROJECT_FORM_SUBMIT_FAILED",
      );
      return projectSubmission(payload, context);
    },
  };
}
