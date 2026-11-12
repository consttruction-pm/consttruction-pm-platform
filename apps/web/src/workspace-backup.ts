import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project and layout backup/recovery client.
 *
 * A snapshot is an immutable JSON document stored with its SHA-256. The page
 * only offers actions the server authorizes: planners may capture snapshots,
 * project administrators may restore, and everyone with project read access can
 * inspect a snapshot and its manifest.
 */

export const BACKUP_API_VERSION = "p6-backup-api.v1";

export type BackupTab = "snapshots" | "restore" | "history";
export type BackupKind = "project" | "layouts";
export type BackupMode = "merge" | "overwrite";

export type BackupSnapshot = {
  snapshotId: string;
  kind: BackupKind;
  label: string;
  projectRevision: number;
  sectionCounts: Record<string, number>;
  contentSha256: string;
  actorId: string;
  occurredAt: string;
  replayed: boolean;
};

export type BackupContent = {
  snapshotId: string;
  kind: BackupKind;
  contentSha256: string;
  projectRevision: number;
  sections: Record<string, Record<string, unknown>[]>;
};

export type RestoreSectionCounts = {
  created: number;
  updated: number;
  skipped: number;
};

export type BackupRestoreRun = {
  runId: string;
  snapshotId: string;
  mode: BackupMode;
  sections: Record<string, RestoreSectionCounts>;
  actorId: string;
  occurredAt: string;
  replayed: boolean;
};

export type BackupPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
  canRestore: boolean;
};

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: {
      code,
      retryable: false,
      message_key: "error.request.invalid",
      available_actions: [],
    },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function integer(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(code);
  }
  return value;
}

function optionalBoolean(value: unknown): boolean {
  return value === true;
}

function backupPath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/backup${suffix}`;
}

function counts(value: unknown, code: string): Record<string, number> {
  if (!isRecord(value)) throw new Error(code);
  const result: Record<string, number> = {};
  for (const [key, item] of Object.entries(value)) {
    result[requiredText(key, code)] = integer(item, code);
  }
  return result;
}

function kind(value: unknown, code: string): BackupKind {
  if (value !== "project" && value !== "layouts") throw new Error(code);
  return value;
}

function mode(value: unknown, code: string): BackupMode {
  if (value !== "merge" && value !== "overwrite") throw new Error(code);
  return value;
}

export function parseSnapshot(value: unknown): BackupSnapshot {
  if (!isRecord(value)) throw new Error("INVALID_BACKUP_SNAPSHOT");
  return {
    snapshotId: requiredText(value.snapshot_id, "INVALID_BACKUP_SNAPSHOT"),
    kind: kind(value.kind, "INVALID_BACKUP_SNAPSHOT"),
    label: requiredText(value.label, "INVALID_BACKUP_SNAPSHOT"),
    projectRevision: integer(value.project_revision, "INVALID_BACKUP_SNAPSHOT"),
    sectionCounts: counts(value.section_counts, "INVALID_BACKUP_SNAPSHOT"),
    contentSha256: requiredText(value.content_sha256, "INVALID_BACKUP_SNAPSHOT"),
    actorId: requiredText(value.actor_id, "INVALID_BACKUP_SNAPSHOT"),
    occurredAt: requiredText(value.occurred_at, "INVALID_BACKUP_SNAPSHOT"),
    replayed: optionalBoolean(value.replayed),
  };
}

export function parseSnapshots(value: unknown): BackupSnapshot[] {
  if (
    !isRecord(value) ||
    value.contract_version !== BACKUP_API_VERSION ||
    !Array.isArray(value.snapshots)
  ) {
    throw new Error("INVALID_BACKUP_SNAPSHOTS");
  }
  return value.snapshots.map((entry) => parseSnapshot(entry));
}

export function parseContent(value: unknown): BackupContent {
  if (
    !isRecord(value) ||
    value.contract_version !== BACKUP_API_VERSION ||
    !isRecord(value.sections)
  ) {
    throw new Error("INVALID_BACKUP_CONTENT");
  }
  const sections: Record<string, Record<string, unknown>[]> = {};
  for (const [name, rows] of Object.entries(value.sections)) {
    if (!Array.isArray(rows) || rows.some((row) => !isRecord(row))) {
      throw new Error("INVALID_BACKUP_CONTENT");
    }
    sections[requiredText(name, "INVALID_BACKUP_CONTENT")] = rows;
  }
  return {
    snapshotId: requiredText(value.snapshot_id, "INVALID_BACKUP_CONTENT"),
    kind: kind(value.kind, "INVALID_BACKUP_CONTENT"),
    contentSha256: requiredText(value.content_sha256, "INVALID_BACKUP_CONTENT"),
    projectRevision: integer(value.project_revision, "INVALID_BACKUP_CONTENT"),
    sections,
  };
}

export function parseRestoreRun(value: unknown): BackupRestoreRun {
  if (!isRecord(value) || !isRecord(value.sections)) {
    throw new Error("INVALID_BACKUP_RUN");
  }
  const sections: Record<string, RestoreSectionCounts> = {};
  for (const [name, raw] of Object.entries(value.sections)) {
    if (!isRecord(raw)) throw new Error("INVALID_BACKUP_RUN");
    sections[requiredText(name, "INVALID_BACKUP_RUN")] = {
      created: integer(raw.created, "INVALID_BACKUP_RUN"),
      updated: integer(raw.updated, "INVALID_BACKUP_RUN"),
      skipped: integer(raw.skipped, "INVALID_BACKUP_RUN"),
    };
  }
  return {
    runId: requiredText(value.run_id, "INVALID_BACKUP_RUN"),
    snapshotId: requiredText(value.snapshot_id, "INVALID_BACKUP_RUN"),
    mode: mode(value.mode, "INVALID_BACKUP_RUN"),
    sections,
    actorId: requiredText(value.actor_id, "INVALID_BACKUP_RUN"),
    occurredAt: requiredText(value.occurred_at, "INVALID_BACKUP_RUN"),
    replayed: optionalBoolean(value.replayed),
  };
}

export function parseRestoreRuns(value: unknown): BackupRestoreRun[] {
  if (
    !isRecord(value) ||
    value.contract_version !== BACKUP_API_VERSION ||
    !Array.isArray(value.runs)
  ) {
    throw new Error("INVALID_BACKUP_RUNS");
  }
  return value.runs.map((entry) => parseRestoreRun(entry));
}

export async function loadSnapshots(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<BackupSnapshot[]>> {
  const result = await transport.get<unknown>(backupPath(context, ""), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseSnapshots(result.data) };
  } catch {
    return localError("INVALID_BACKUP_SNAPSHOTS");
  }
}

export async function createSnapshot(
  transport: ApiTransport,
  context: ProjectContext,
  snapshotKind: BackupKind,
  label: string,
  idempotencyKey: string,
): Promise<ApiResult<BackupSnapshot>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    backupPath(context, ""),
    { kind: snapshotKind, label, idempotency_key: idempotencyKey },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseSnapshot(result.data) };
  } catch {
    return localError("INVALID_BACKUP_SNAPSHOT");
  }
}

export async function loadSnapshotContent(
  transport: ApiTransport,
  context: ProjectContext,
  snapshotId: string,
): Promise<ApiResult<BackupContent>> {
  const result = await transport.get<unknown>(
    backupPath(context, `/${encodeURIComponent(snapshotId)}/content`),
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseContent(result.data) };
  } catch {
    return localError("INVALID_BACKUP_CONTENT");
  }
}

export async function restoreSnapshot(
  transport: ApiTransport,
  context: ProjectContext,
  snapshotId: string,
  restoreMode: BackupMode,
  idempotencyKey: string,
): Promise<ApiResult<BackupRestoreRun>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    backupPath(context, `/${encodeURIComponent(snapshotId)}/restore`),
    { mode: restoreMode, idempotency_key: idempotencyKey },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRestoreRun(result.data) };
  } catch {
    return localError("INVALID_BACKUP_RUN");
  }
}

export async function loadRestoreRuns(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<BackupRestoreRun[]>> {
  const result = await transport.get<unknown>(
    backupPath(context, "/restores"),
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRestoreRuns(result.data) };
  } catch {
    return localError("INVALID_BACKUP_RUNS");
  }
}

function newIdempotencyKey(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }
  return `backup-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function sectionSummary(snapshot: BackupSnapshot): string {
  return Object.entries(snapshot.sectionCounts)
    .map(([name, count]) => `${name} ${count}`)
    .join(" · ");
}

export function mountWorkspaceBackupPage(
  host: HTMLElement,
  options: BackupPageOptions,
): void {
  const { transport, context, locale, canWrite, canRestore } = options;
  const state: {
    status: "loading" | "ready" | "error";
    tab: BackupTab;
    snapshots: BackupSnapshot[];
    runs: BackupRestoreRun[];
    kind: BackupKind;
    label: string;
    selectedId: string;
    mode: BackupMode;
    content: BackupContent | null;
    lastRun: BackupRestoreRun | null;
    busy: boolean;
    errorCode: string | null;
    notice: { kind: "ok" | "warn" | "error"; message: string } | null;
  } = {
    status: "loading",
    tab: "snapshots",
    snapshots: [],
    runs: [],
    kind: "project",
    label: "",
    selectedId: "",
    mode: "merge",
    content: null,
    lastRun: null,
    busy: false,
    errorCode: null,
    notice: null,
  };

  async function loadAll(): Promise<void> {
    state.status = "loading";
    render();
    const snapshots = await loadSnapshots(transport, context);
    if (!snapshots.ok) {
      state.status = "error";
      state.errorCode = snapshots.error.code;
      render();
      return;
    }
    state.snapshots = snapshots.data;
    if (
      !state.selectedId ||
      !state.snapshots.some((item) => item.snapshotId === state.selectedId)
    ) {
      state.selectedId = state.snapshots[0]?.snapshotId ?? "";
    }
    const runs = await loadRestoreRuns(transport, context);
    state.runs = runs.ok ? runs.data : [];
    state.status = "ready";
    state.errorCode = null;
    render();
  }

  async function doCreate(): Promise<void> {
    if (state.busy) return;
    if (!canWrite) {
      state.notice = {
        kind: "error",
        message: say("Your role cannot create backups.", "نقش شما اجازهٔ پشتیبان‌گیری ندارد."),
      };
      render();
      return;
    }
    if (!state.label.trim()) {
      state.notice = {
        kind: "warn",
        message: say("Enter a backup label first.", "ابتدا برچسب پشتیبان را وارد کنید."),
      };
      render();
      return;
    }
    state.busy = true;
    state.notice = null;
    render();
    const result = await createSnapshot(
      transport,
      context,
      state.kind,
      state.label.trim(),
      newIdempotencyKey(),
    );
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Backup failed", "پشتیبان‌گیری ناموفق بود")} (${result.error.code})`,
      };
    } else {
      state.label = "";
      state.notice = {
        kind: "ok",
        message: `${result.data.replayed ? say("Reused", "بازاستفاده شد") : say("Created", "ایجاد شد")} ${result.data.snapshotId}`,
      };
      state.selectedId = result.data.snapshotId;
      await loadAll();
    }
    render();
  }

  async function doManifest(snapshotId: string): Promise<void> {
    state.selectedId = snapshotId;
    state.busy = true;
    render();
    const result = await loadSnapshotContent(transport, context, snapshotId);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Manifest failed", "خواندن فهرست ناموفق بود")} (${result.error.code})`,
      };
      state.content = null;
    } else {
      state.content = result.data;
      state.notice = {
        kind: "ok",
        message: say("Manifest verified against its checksum.", "فهرست با checksum تأیید شد."),
      };
    }
    render();
  }

  function doDownload(): void {
    if (!state.content) return;
    const blob = new Blob([JSON.stringify(state.content, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${state.content.snapshotId}.json`;
    host.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function doRestore(): Promise<void> {
    if (state.busy) return;
    if (!canRestore) {
      state.notice = {
        kind: "error",
        message: say(
          "Only a project administrator can restore a backup.",
          "تنها مدیر پروژه می‌تواند پشتیبان را بازیابی کند.",
        ),
      };
      render();
      return;
    }
    if (!state.selectedId) {
      state.notice = {
        kind: "warn",
        message: say("Select a snapshot to restore.", "یک نسخهٔ پشتیبان را انتخاب کنید."),
      };
      render();
      return;
    }
    state.busy = true;
    state.notice = null;
    render();
    const result = await restoreSnapshot(
      transport,
      context,
      state.selectedId,
      state.mode,
      newIdempotencyKey(),
    );
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Restore failed", "بازیابی ناموفق بود")} (${result.error.code})`,
      };
    } else {
      state.lastRun = result.data;
      state.notice = {
        kind: "ok",
        message: `${result.data.replayed ? say("Replayed", "بازپخش شد") : say("Restored", "بازیابی شد")} ${result.data.runId}`,
      };
      const runs = await loadRestoreRuns(transport, context);
      state.runs = runs.ok ? runs.data : state.runs;
    }
    render();
  }

  function renderTabs(): string {
    const tabs: [BackupTab, string, string][] = [
      ["snapshots", "Snapshots", "نسخه‌های پشتیبان"],
      ["restore", "Restore", "بازیابی"],
      ["history", "Restore History", "تاریخچهٔ بازیابی"],
    ];
    return `<div class="cp-register-tabs" role="tablist">${tabs
      .map(
        ([key, en, fa]) =>
          `<button type="button" role="tab" data-backup-tab="${key}" aria-selected="${state.tab === key}">${escapeHtml(say(en, fa))}</button>`,
      )
      .join("")}</div>`;
  }

  function renderSnapshots(): string {
    const options = state.snapshots
      .map(
        (item) =>
          `<tr data-backup-snapshot-row data-snapshot-id="${escapeHtml(item.snapshotId)}" data-kind="${escapeHtml(item.kind)}" data-sha="${escapeHtml(item.contentSha256)}">
            <td><code>${escapeHtml(item.snapshotId)}</code></td>
            <td>${escapeHtml(item.kind)}</td>
            <td>${escapeHtml(item.label)}</td>
            <td>${item.projectRevision}</td>
            <td>${escapeHtml(sectionSummary(item))}</td>
            <td><code>${escapeHtml(item.contentSha256.slice(0, 12))}</code></td>
            <td>${escapeHtml(item.occurredAt)}</td>
            <td><button type="button" data-backup-action="manifest" data-snapshot-id="${escapeHtml(item.snapshotId)}">${escapeHtml(say("Manifest", "فهرست"))}</button></td>
          </tr>`,
      )
      .join("");
    const table = state.snapshots.length
      ? `<div class="cp-table-scroll"><table class="cp-register-table" data-backup-table><thead><tr>
          <th>${escapeHtml(say("Snapshot", "نسخه"))}</th><th>${escapeHtml(say("Kind", "نوع"))}</th><th>${escapeHtml(say("Label", "برچسب"))}</th><th>${escapeHtml(say("Revision", "ویرایش"))}</th><th>${escapeHtml(say("Sections", "بخش‌ها"))}</th><th>${escapeHtml(say("SHA-256", "SHA-256"))}</th><th>${escapeHtml(say("Created", "ایجاد"))}</th><th></th>
        </tr></thead><tbody>${options}</tbody></table></div>`
      : `<div class="cp-calendar-empty" data-backup-empty>${escapeHtml(say("No backup snapshots exist for this project.", "هیچ نسخهٔ پشتیبانی برای این پروژه وجود ندارد."))}</div>`;
    const manifest = state.content
      ? `<div class="cp-calendar-panel" data-backup-manifest>
          <strong>${escapeHtml(state.content.snapshotId)}</strong>
          <p>${escapeHtml(
            Object.entries(state.content.sections)
              .map(([name, rows]) => `${name}: ${rows.length}`)
              .join(" · "),
          )}</p>
          <button type="button" data-backup-action="download">${escapeHtml(say("Download JSON", "دانلود JSON"))}</button>
        </div>`
      : "";
    return `<div class="cp-register-filters">
        <label>${escapeHtml(say("Backup kind", "نوع پشتیبان"))}<select data-backup-kind>
          <option value="project" ${state.kind === "project" ? "selected" : ""}>${escapeHtml(say("Project", "پروژه"))}</option>
          <option value="layouts" ${state.kind === "layouts" ? "selected" : ""}>${escapeHtml(say("Layouts", "چیدمان‌ها"))}</option>
        </select></label>
        <label>${escapeHtml(say("Label", "برچسب"))}<input type="text" data-backup-label value="${escapeHtml(state.label)}" placeholder="${escapeHtml(say("Baseline before changes", "مبنا پیش از تغییرات"))}"></label>
        <button type="button" data-backup-action="create" ${canWrite && !state.busy ? "" : "disabled"}>${escapeHtml(say("Create backup", "ایجاد پشتیبان"))}</button>
        <button type="button" data-backup-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button>
      </div>
      ${table}
      ${manifest}`;
  }

  function renderRestore(): string {
    const options = state.snapshots
      .map(
        (item) =>
          `<option value="${escapeHtml(item.snapshotId)}" ${state.selectedId === item.snapshotId ? "selected" : ""}>${escapeHtml(item.snapshotId)} · ${escapeHtml(item.kind)} · ${escapeHtml(item.label)}</option>`,
      )
      .join("");
    const summary = state.lastRun
      ? `<p class="cp-register-notice" data-backup-restore-summary data-created="${Object.values(state.lastRun.sections).reduce((sum, item) => sum + item.created, 0)}" data-updated="${Object.values(state.lastRun.sections).reduce((sum, item) => sum + item.updated, 0)}" data-skipped="${Object.values(state.lastRun.sections).reduce((sum, item) => sum + item.skipped, 0)}">${escapeHtml(state.lastRun.runId)} · ${escapeHtml(
          Object.entries(state.lastRun.sections)
            .map(
              ([name, counts]) =>
                `${name}: +${counts.created} ~${counts.updated} =${counts.skipped}`,
            )
            .join(" · "),
        )}</p>`
      : "";
    return `<div class="cp-register-filters">
        <label>${escapeHtml(say("Snapshot", "نسخه"))}<select data-backup-snapshot ${state.snapshots.length ? "" : "disabled"}>${options}</select></label>
        <label>${escapeHtml(say("Mode", "حالت"))}<select data-backup-mode>
          <option value="merge" ${state.mode === "merge" ? "selected" : ""}>${escapeHtml(say("Merge (create missing)", "ادغام (ایجاد موارد نبوده)"))}</option>
          <option value="overwrite" ${state.mode === "overwrite" ? "selected" : ""}>${escapeHtml(say("Overwrite existing", "جایگزینی موارد موجود"))}</option>
        </select></label>
        <button type="button" data-backup-action="restore" ${canRestore && state.selectedId && !state.busy ? "" : "disabled"}>${escapeHtml(say("Restore", "بازیابی"))}</button>
        <button type="button" data-backup-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button>
      </div>
      <p class="cp-register-notice">${escapeHtml(say("Restore never deletes: merge creates missing records and overwrite updates records that differ, using each stored record revision.", "بازیابی چیزی را حذف نمی‌کند: ادغام موارد نبوده را می‌سازد و جایگزینی موارد متفاوت را با ویرایش ذخیره‌شدهٔ هر رکورد به‌روزرسانی می‌کند."))}</p>
      ${summary}`;
  }

  function renderHistory(): string {
    if (!state.runs.length) {
      return `<div class="cp-calendar-empty" data-backup-history-empty>${escapeHtml(say("No restore runs have been recorded for this project.", "هیچ اجرای بازیابی برای این پروژه ثبت نشده است."))}</div>`;
    }
    return `<div class="cp-table-scroll"><table class="cp-register-table" data-backup-history><thead><tr>
        <th>${escapeHtml(say("Run", "اجرا"))}</th><th>${escapeHtml(say("Snapshot", "نسخه"))}</th><th>${escapeHtml(say("Mode", "حالت"))}</th><th>${escapeHtml(say("Sections", "بخش‌ها"))}</th><th>${escapeHtml(say("Actor", "کاربر"))}</th><th>${escapeHtml(say("When", "زمان"))}</th>
      </tr></thead><tbody>${state.runs
        .map(
          (run) =>
            `<tr data-backup-run-row data-run-id="${escapeHtml(run.runId)}"><td><code>${escapeHtml(run.runId)}</code></td><td><code>${escapeHtml(run.snapshotId)}</code></td><td>${escapeHtml(run.mode)}</td><td>${escapeHtml(
              Object.entries(run.sections)
                .map(
                  ([name, counts]) =>
                    `${name}: +${counts.created} ~${counts.updated} =${counts.skipped}`,
                )
                .join(" · "),
            )}</td><td>${escapeHtml(run.actorId)}</td><td>${escapeHtml(run.occurredAt)}</td></tr>`,
        )
        .join("")}</tbody></table></div>`;
  }

  function render(): void {
    if (state.status === "loading") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Backup / Recovery", "پشتیبان‌گیری / بازیابی"))}</strong></div><div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading backup snapshots…", "در حال خواندن نسخه‌های پشتیبان…"))}</div>`;
      return;
    }
    if (state.status === "error") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Backup / Recovery", "پشتیبان‌گیری / بازیابی"))}</strong><div><button type="button" data-backup-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div><div class="cp-calendar-empty" role="alert">${escapeHtml(say("Backup snapshots could not be read", "خواندن نسخه‌های پشتیبان ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
      return;
    }
    const body =
      state.tab === "snapshots"
        ? renderSnapshots()
        : state.tab === "restore"
          ? renderRestore()
          : renderHistory();
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Backup / Recovery", "پشتیبان‌گیری / بازیابی"))}</strong><div><button type="button" data-backup-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderTabs()}
      <div class="cp-admin-body" data-backup-body data-backup-active-tab="${state.tab}">${body}</div>
      ${state.notice ? `<p class="cp-calendar-notice" data-backup-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const tab = target.closest<HTMLElement>("[data-backup-tab]")?.dataset
      .backupTab as BackupTab | undefined;
    if (tab) {
      state.tab = tab;
      state.notice = null;
      render();
      return;
    }
    const actionElement = target.closest<HTMLElement>("[data-backup-action]");
    const action = actionElement?.dataset.backupAction;
    if (action === "reload") {
      void loadAll();
    } else if (action === "create") {
      void doCreate();
    } else if (action === "manifest") {
      const snapshotId = actionElement?.dataset.snapshotId ?? "";
      if (snapshotId) void doManifest(snapshotId);
    } else if (action === "download") {
      doDownload();
    } else if (action === "restore") {
      void doRestore();
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (target.matches("[data-backup-label]")) {
      state.label = target.value;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.matches("[data-backup-kind]")) {
      state.kind = target.value === "layouts" ? "layouts" : "project";
      return;
    }
    if (target.matches("[data-backup-snapshot]")) {
      state.selectedId = target.value;
      state.lastRun = null;
      return;
    }
    if (target.matches("[data-backup-mode]")) {
      state.mode = target.value === "overwrite" ? "overwrite" : "merge";
    }
  });

  function say(en: string, fa: string): string {
    return text(locale, en, fa);
  }

  void loadAll();
}
