import assert from "node:assert/strict";
import test from "node:test";

import {
  filterEnterpriseTasks,
  type EnterpriseTaskRecord,
} from "./enterprise-task-center.js";

function task(overrides: Partial<EnterpriseTaskRecord> = {}): EnterpriseTaskRecord {
  return {
    contract_version: "cubi-enterprise-task.v1",
    task_id: "task-1",
    tenant_id: "tenant-1",
    title: "Prepare handover",
    description: "Review package",
    created_by_user_id: "user-1",
    created_at: "2026-11-01T09:00:00Z",
    status: "open",
    priority: "normal",
    assigned_user_id: "user-1",
    assigned_team_id: null,
    project_id: null,
    due_at: "2026-11-20T12:00:00Z",
    dependency_ids: [],
    revision: 1,
    updated_at: "2026-11-01T09:00:00Z",
    completed_at: null,
    completed_by_user_id: null,
    ...overrides,
  };
}

test("Task Center active filter includes open and in-progress tasks only", () => {
  const rows = [
    task({ task_id: "open", status: "open" }),
    task({ task_id: "progress", status: "in_progress" }),
    task({ task_id: "blocked", status: "blocked" }),
    task({ task_id: "done", status: "completed" }),
  ];
  assert.deepEqual(
    filterEnterpriseTasks(rows, "active").map((item) => item.task_id).sort(),
    ["open", "progress"],
  );
});

test("Task Center overdue filter excludes completed and cancelled tasks", () => {
  const rows = [
    task({ task_id: "late", due_at: "2026-11-01T00:00:00Z" }),
    task({ task_id: "done", status: "completed", due_at: "2026-11-01T00:00:00Z" }),
    task({ task_id: "cancelled", status: "cancelled", due_at: "2026-11-01T00:00:00Z" }),
    task({ task_id: "future", due_at: "2026-12-01T00:00:00Z" }),
  ];
  assert.deepEqual(
    filterEnterpriseTasks(rows, "overdue", "", Date.parse("2026-11-15T00:00:00Z")).map((item) => item.task_id),
    ["late"],
  );
});

test("Task Center search is case-insensitive across title and description", () => {
  const rows = [
    task({ task_id: "title", title: "Review Concrete Package", description: null }),
    task({ task_id: "description", title: "Handover", description: "Concrete quality dossier" }),
    task({ task_id: "other", title: "Procurement", description: "Vendor documents" }),
  ];
  assert.deepEqual(
    filterEnterpriseTasks(rows, "all", "CONCRETE").map((item) => item.task_id).sort(),
    ["description", "title"],
  );
});

test("Task Center due-today filter includes only unfinished tasks due on the current local day", () => {
  const now = Date.parse("2026-11-15T12:00:00Z");
  const rows = [
    task({ task_id: "due-today", due_at: "2026-11-15T18:00:00Z" }),
    task({ task_id: "overdue", due_at: "2026-11-14T18:00:00Z" }),
    task({ task_id: "future", due_at: "2026-11-16T18:00:00Z" }),
    task({ task_id: "done", status: "completed", due_at: "2026-11-15T18:00:00Z" }),
  ];
  assert.deepEqual(
    filterEnterpriseTasks(rows, "due", "", now).map((item) => item.task_id),
    ["due-today"],
  );
});
