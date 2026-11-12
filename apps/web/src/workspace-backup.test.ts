import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  BACKUP_API_VERSION,
  createSnapshot,
  loadRestoreRuns,
  loadSnapshotContent,
  loadSnapshots,
  mountWorkspaceBackupPage,
  parseContent,
  parseRestoreRun,
  parseRestoreRuns,
  parseSnapshot,
  parseSnapshots,
  restoreSnapshot,
} from "./workspace-backup.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 3 };
const BASE = "/api/projects/P-1/backup";

type Call = { method: string; path: string; body?: unknown };

function transport(
  handler: (call: Call) => ApiResult<unknown>,
): { transport: ApiTransport; calls: Call[] } {
  const calls: Call[] = [];
  const send =
    (method: string) =>
    async (path: string, body?: unknown, _context?: ProjectContext) => {
      const call = { method, path, body };
      calls.push(call);
      return handler(call);
    };
  return {
    calls,
    transport: {
      get: send("GET"),
      post: send("POST"),
    } as unknown as ApiTransport,
  };
}

const snapshot = {
  snapshot_id: "BKP-1",
  kind: "project",
  label: "Baseline",
  project_revision: 3,
  section_counts: { wbs: 2, activities: 1, resources: 1, relationships: 0 },
  content_sha256: "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  actor_id: "preview-admin",
  occurred_at: "2026-11-12T08:00:00+00:00",
};

const content = {
  contract_version: BACKUP_API_VERSION,
  snapshot_id: "BKP-1",
  kind: "project",
  content_sha256: snapshot.content_sha256,
  project_revision: 3,
  sections: {
    wbs: [{ wbs_id: "W-1" }],
    activities: [{ activity_id: "A-1" }],
    resources: [{ resource_id: "R-1" }],
    relationships: [],
  },
};

const restoreRun = {
  run_id: "RSR-1",
  snapshot_id: "BKP-1",
  mode: "merge",
  sections: {
    wbs: { created: 1, updated: 0, skipped: 1 },
    activities: { created: 1, updated: 1, skipped: 0 },
  },
  actor_id: "preview-admin",
  occurred_at: "2026-11-12T08:05:00+00:00",
  replayed: false,
};

test("snapshot, content and run parsers fail closed on a drifted contract", () => {
  assert.equal(parseSnapshot(snapshot).snapshotId, "BKP-1");
  assert.equal(parseSnapshot(snapshot).sectionCounts.wbs, 2);
  for (const bad of [
    { ...snapshot, snapshot_id: "" },
    { ...snapshot, kind: "everything" },
    { ...snapshot, label: 7 },
    { ...snapshot, project_revision: -1 },
    { ...snapshot, section_counts: { wbs: "2" } },
    { ...snapshot, content_sha256: "" },
  ]) {
    assert.throws(() => parseSnapshot(bad));
  }

  assert.equal(parseSnapshots({ contract_version: BACKUP_API_VERSION, snapshots: [snapshot] }).length, 1);
  assert.throws(() => parseSnapshots({ contract_version: "p6-backup-api.v2", snapshots: [] }));
  assert.throws(() => parseSnapshots({ contract_version: BACKUP_API_VERSION, snapshots: [null] }));

  assert.equal(parseContent(content).sections.activities.length, 1);
  for (const bad of [
    { ...content, contract_version: "x" },
    { ...content, sections: { wbs: [1] } },
    { ...content, snapshot_id: "" },
  ]) {
    assert.throws(() => parseContent(bad));
  }

  assert.equal(parseRestoreRun(restoreRun).sections.activities.updated, 1);
  for (const bad of [
    { ...restoreRun, mode: "delete" },
    { ...restoreRun, sections: { wbs: { created: 0, updated: 0 } } },
    { ...restoreRun, run_id: "" },
  ]) {
    assert.throws(() => parseRestoreRun(bad));
  }
  assert.equal(
    parseRestoreRuns({ contract_version: BACKUP_API_VERSION, runs: [restoreRun] })[0].runId,
    "RSR-1",
  );
  assert.throws(() => parseRestoreRuns({ contract_version: "x", runs: [] }));
});

test("requests carry the snapshot path, mode and idempotency key", async () => {
  const stub = transport((call) => {
    if (call.method === "POST" && call.path === BASE) {
      return { ok: true, data: { ...snapshot, replayed: false } };
    }
    if (call.path.endsWith("/content")) return { ok: true, data: content };
    if (call.path.endsWith("/restore")) return { ok: true, data: restoreRun };
    if (call.path.endsWith("/restores")) {
      return { ok: true, data: { contract_version: BACKUP_API_VERSION, runs: [restoreRun] } };
    }
    return { ok: true, data: { contract_version: BACKUP_API_VERSION, snapshots: [snapshot] } };
  });

  await loadSnapshots(stub.transport, context);
  await createSnapshot(stub.transport, context, "project", "Baseline", "key-1");
  await loadSnapshotContent(stub.transport, context, "BKP-1");
  await restoreSnapshot(stub.transport, context, "BKP-1", "merge", "key-2");
  await loadRestoreRuns(stub.transport, context);

  assert.equal(stub.calls[0].path, BASE);
  assert.deepEqual(stub.calls[1].body, {
    kind: "project",
    label: "Baseline",
    idempotency_key: "key-1",
  });
  assert.equal(stub.calls[2].path, `${BASE}/BKP-1/content`);
  assert.deepEqual(stub.calls[3].body, { mode: "merge", idempotency_key: "key-2" });
  assert.equal(stub.calls[4].path, `${BASE}/restores`);
});

function mountHost(): {
  host: HTMLElement;
  click: (target: Record<string, unknown>) => void;
  change: (target: Record<string, unknown>) => void;
  type: (value: string) => void;
} {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    dataset: {} as Record<string, string>,
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) =>
      listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
    appendChild: () => undefined,
  };
  const fire = (type: string, target: Record<string, unknown>): void => {
    const withClosest = {
      ...target,
      closest: (selector: string) => {
        const dataset = (target.dataset ?? {}) as Record<string, string>;
        if (selector === "[data-backup-tab]" && dataset.backupTab) return withClosest;
        if (selector === "[data-backup-action]" && dataset.backupAction) return withClosest;
        return null;
      },
    };
    listeners.get(type)?.({ target: withClosest } as unknown as Event);
  };
  return {
    host: host as unknown as HTMLElement,
    click: (target) => fire("click", target),
    change: (target) => fire("change", target),
    type: (value) => fire("input", { matches: (selector: string) => selector === "[data-backup-label]", value }),
  };
}

function mountTransport(): ApiTransport {
  return transport((call) => {
    if (call.method === "POST" && call.path === BASE) {
      return { ok: true, data: { ...snapshot, replayed: false } };
    }
    if (call.path.endsWith("/content")) return { ok: true, data: content };
    if (call.path.endsWith("/restore")) return { ok: true, data: restoreRun };
    if (call.path.endsWith("/restores")) {
      return { ok: true, data: { contract_version: BACKUP_API_VERSION, runs: [restoreRun] } };
    }
    return { ok: true, data: { contract_version: BACKUP_API_VERSION, snapshots: [snapshot] } };
  }).transport;
}

test("viewer mode inspects the manifest and history but cannot capture or restore", async () => {
  const { host, click } = mountHost();
  mountWorkspaceBackupPage(host, {
    transport: mountTransport(),
    context,
    locale: "en",
    canWrite: false,
    canRestore: false,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /data-backup-tab="snapshots"/);
  assert.match(host.innerHTML, /data-backup-tab="restore"/);
  assert.match(host.innerHTML, /data-backup-tab="history"/);
  assert.match(host.innerHTML, /data-backup-snapshot-row[^>]*data-snapshot-id="BKP-1"/);
  assert.match(host.innerHTML, /data-backup-action="create"[^>]*disabled/);

  click({ dataset: { backupAction: "manifest", snapshotId: "BKP-1" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-backup-manifest/);
  assert.match(host.innerHTML, /activities: 1/);

  click({ dataset: { backupTab: "restore" } });
  assert.match(host.innerHTML, /data-backup-action="restore"[^>]*disabled/);
  assert.match(host.innerHTML, /data-backup-mode/);

  click({ dataset: { backupTab: "history" } });
  assert.match(host.innerHTML, /data-backup-run-row[^>]*data-run-id="RSR-1"/);
});

test("writer mode creates a labelled snapshot and administrator mode restores it", async () => {
  const { host, click, type } = mountHost();
  mountWorkspaceBackupPage(host, {
    transport: mountTransport(),
    context,
    locale: "fa",
    canWrite: true,
    canRestore: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /پشتیبان‌گیری \/ بازیابی/);
  type("Baseline before changes");
  click({ dataset: { backupAction: "create" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-backup-notice[^>]*data-state="ok"/);
  assert.match(host.innerHTML, /BKP-1/);

  click({ dataset: { backupTab: "restore" } });
  click({ dataset: { backupAction: "restore" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-backup-restore-summary[^>]*data-created="2"[^>]*data-updated="1"/);
  assert.match(host.innerHTML, /RSR-1/);
});
