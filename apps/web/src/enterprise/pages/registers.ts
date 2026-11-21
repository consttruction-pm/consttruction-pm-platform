/**
 * The eight register pages that share the tenant record contract.
 *
 * Each page names its real Help topic, the exact fields it writes and the
 * columns it reads back. Nothing here calculates an Engineering fact.
 */

import type { PageContext } from "../app.js";
import { renderRecordPage, type RecordPageSpec } from "./records.js";

const RISKS: RecordPageSpec = {
  kind: "risks",
  testId: "risks",
  description: "Project risks and issues registered in Enterprise, with owner, severity and status.",
  note: "Enterprise keeps the register and its history. Schedule impact is owned by Engineering and is not computed here.",
  help: { topic: "About Risks (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6628.htm" },
  fields: [
    { name: "title", label: "Title", required: true, placeholder: "Short risk or issue statement" },
    {
      name: "risk_type",
      label: "Type",
      kind: "select",
      options: [{ value: "risk", label: "Risk" }, { value: "issue", label: "Issue" }],
    },
    {
      name: "severity",
      label: "Severity",
      kind: "select",
      options: [
        { value: "low", label: "Low" },
        { value: "medium", label: "Medium" },
        { value: "high", label: "High" },
        { value: "critical", label: "Critical" },
      ],
    },
    { name: "owner", label: "Owner", placeholder: "Responsible person" },
    { name: "description", label: "Description", kind: "textarea", placeholder: "Context, trigger and response" },
  ],
  columns: [
    { key: "title", label: "Title" },
    { key: "risk_type", label: "Type" },
    { key: "severity", label: "Severity" },
    { key: "owner", label: "Owner" },
  ],
  statusOptions: ["open", "mitigated", "closed"],
};

const DOCUMENTS: RecordPageSpec = {
  kind: "documents",
  testId: "documents",
  description: "Controlled documents with category, owner and review status.",
  note: "Binary content is not stored by this register. It records the document identity and its review state; file storage is a separate capability.",
  help: { topic: "About Documents (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6620.htm" },
  fields: [
    { name: "title", label: "Title", required: true, placeholder: "Document title" },
    { name: "category", label: "Category", placeholder: "Contract, drawing, procedure…" },
    { name: "owner", label: "Owner", placeholder: "Owner of the document" },
    { name: "link", label: "Reference", placeholder: "Repository path or URL", hint: "A reference only; the register does not fetch the file." },
    { name: "description", label: "Description", kind: "textarea" },
  ],
  columns: [
    { key: "title", label: "Title" },
    { key: "category", label: "Category" },
    { key: "owner", label: "Owner" },
    { key: "link", label: "Reference" },
  ],
  statusOptions: ["draft", "in_review", "approved", "archived"],
};

const EPS: RecordPageSpec = {
  kind: "eps",
  testId: "eps",
  description: "Enterprise project structure elements owned by CUBI, with parent, code and status.",
  note: "This is the Enterprise hierarchy register. Project schedules and CPM remain Engineering-owned; nothing is recalculated here.",
  help: {
    topic: "About the Enterprise Project Structure (EPS)",
    url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6621.htm",
  },
  fields: [
    { name: "name", label: "Element name", required: true, placeholder: "Portfolio or business unit element" },
    { name: "code", label: "Code", placeholder: "Short element code" },
    { name: "parent_id", label: "Parent element", placeholder: "Record id of the parent, if any", hint: "Leave empty for a root element." },
    { name: "description", label: "Description", kind: "textarea" },
  ],
  columns: [
    { key: "name", label: "Element" },
    { key: "code", label: "Code" },
    { key: "parent_id", label: "Parent" },
  ],
  statusOptions: ["active", "inactive"],
};

const TIMESHEETS: RecordPageSpec = {
  kind: "timesheets",
  testId: "timesheets",
  description: "Time entries recorded against a person and a working day, with server-side hour limits.",
  note: "Hours are validated by the server (0 < hours ≤ 24). These entries are CUBI records, not P6 timesheet approvals; approval stays in Engineering.",
  help: { topic: "About Timesheets (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6610.htm" },
  fields: [
    { name: "user_id", label: "Person", required: true, placeholder: "User id" },
    { name: "work_date", label: "Work date", kind: "date", required: true },
    { name: "hours", label: "Hours", kind: "number", required: true, min: "0.25", max: "24", step: "0.25" },
    { name: "project_id", label: "Project", placeholder: "Project id, optional" },
    { name: "note", label: "Note", kind: "textarea", placeholder: "What the time was spent on" },
  ],
  columns: [
    { key: "user_id", label: "Person" },
    { key: "work_date", label: "Date" },
    { key: "hours", label: "Hours" },
    { key: "project_id", label: "Project" },
  ],
  statusOptions: ["draft", "submitted", "approved", "rejected"],
};

const NOTIFICATIONS: RecordPageSpec = {
  kind: "notifications",
  testId: "notifications",
  description: "CUBI notification records with audience and delivery channel.",
  note: "This register stores the notification intent and its state. Delivery to an external channel is not claimed unless the server reports it.",
  help: { topic: "About email Notifications (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6605.htm" },
  fields: [
    { name: "title", label: "Title", required: true, placeholder: "Notification subject" },
    { name: "message", label: "Message", kind: "textarea", placeholder: "Message body" },
    { name: "audience", label: "Audience", placeholder: "Team, user id or project" },
    {
      name: "channel",
      label: "Channel",
      kind: "select",
      options: [{ value: "in_app", label: "In application" }, { value: "email", label: "Email" }],
    },
  ],
  columns: [
    { key: "title", label: "Title" },
    { key: "audience", label: "Audience" },
    { key: "channel", label: "Channel" },
  ],
  statusOptions: ["unread", "read", "archived"],
};

const SETTINGS: RecordPageSpec = {
  kind: "settings",
  testId: "settings",
  description: "Tenant administration settings. Only an enterprise administrator can write them.",
  note: "The server enforces the administrator role; a non-administrator receives 403 and no value is changed.",
  help: { topic: "About Application Settings (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/36403.htm" },
  fields: [
    { name: "key", label: "Setting key", required: true, placeholder: "e.g. timesheet.week_start" },
    { name: "value", label: "Value", required: true, placeholder: "Stored value" },
    { name: "description", label: "Description", kind: "textarea", placeholder: "Why this value is set" },
  ],
  columns: [
    { key: "key", label: "Key" },
    { key: "value", label: "Value" },
    { key: "description", label: "Description" },
  ],
  statusOptions: ["active", "archived"],
};

const FORMS: RecordPageSpec = {
  kind: "forms",
  testId: "forms",
  description: "CUBI form definitions: named field lists that other surfaces can reuse.",
  note: "Fields are a JSON array and the server rejects an empty or unnamed field list. Form Builder is CUBI-owned; P6 UDF topics describe the closest equivalent.",
  help: {
    topic: "About User Defined Fields (P6 EPPM V26)",
    url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6599.htm",
  },
  fields: [
    { name: "name", label: "Form name", required: true, placeholder: "e.g. Site observation" },
    { name: "description", label: "Description", kind: "textarea" },
    {
      name: "fields",
      label: "Fields (JSON)",
      kind: "textarea",
      required: true,
      placeholder: '[{"name":"title","type":"text","required":true}]',
      hint: "Array of {name, type} objects. The server rejects an empty list.",
    },
  ],
  columns: [
    { key: "name", label: "Form" },
    { key: "fields", label: "Fields" },
    { key: "description", label: "Description" },
  ],
  statusOptions: ["draft", "published", "archived"],
  jsonFields: ["fields"],
};

const DIRECTORY: RecordPageSpec = {
  kind: "directory",
  testId: "directory",
  description: "Resource directory entries: people available to Enterprise teams, with role and capacity.",
  note: "This is a CUBI directory record. Engineering resource calendars, units and rates stay authoritative in Engineering.",
  help: { topic: "About Resources (P6 EPPM V26)", url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6640.htm" },
  fields: [
    { name: "display_name", label: "Name", required: true, placeholder: "Person or resource name" },
    { name: "email", label: "Email", placeholder: "name@example.com" },
    { name: "role_title", label: "Role", placeholder: "Discipline or role title" },
    { name: "team", label: "Team", placeholder: "Team name" },
    { name: "capacity_hours", label: "Weekly capacity (hours)", kind: "number", min: "0", max: "168", step: "0.5" },
  ],
  columns: [
    { key: "display_name", label: "Name" },
    { key: "role_title", label: "Role" },
    { key: "team", label: "Team" },
    { key: "capacity_hours", label: "Capacity" },
  ],
  statusOptions: ["active", "inactive"],
};

export function renderRisks(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, RISKS);
}

export function renderDocuments(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, DOCUMENTS);
}

export function renderEps(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, EPS);
}

export function renderTimesheets(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, TIMESHEETS);
}

export function renderNotifications(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, NOTIFICATIONS);
}

export function renderSettings(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, SETTINGS);
}

export function renderForms(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, FORMS);
}

export function renderDirectory(ctx: PageContext, host: HTMLElement): void {
  renderRecordPage(ctx, host, DIRECTORY);
}
