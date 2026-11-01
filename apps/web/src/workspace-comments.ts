/**
 * Comments rail for the workspace. Comments are a local collaboration aid: they
 * are stored in this browser only and are never presented as project database
 * records. The panel overlays the workspace so opening it cannot resize the
 * activity table, Gantt or details pane.
 */
import { translateWorkspaceUiText } from "./workspace-localization.js";

export type WorkspaceCommentsInput = {
  projectId: string;
  locale: string;
  entityKind: "activity" | "wbs" | "project" | "resources" | "documents" | "cost" | "control" | "reports" | "settings" | "progress";
  entityId: string;
  entityLabel: string;
};

type CommentEntry = {
  id: string;
  projectId: string;
  entityKind: WorkspaceCommentsInput["entityKind"];
  entityId: string;
  author: string;
  body: string;
  createdAt: string;
  parentId: string | null;
};

export const WORKSPACE_COMMENTS_STORAGE_KEY = "cubi:workspace-comments:v1";

function t(locale: string, en: string, persian: string): string {
  return translateWorkspaceUiText(locale, en, persian);
}

function intlLocale(locale: string): string {
  switch (locale.split("-")[0]) {
    case "fa": return "fa-IR";
    case "de": return "de-DE";
    case "zh": return "zh-CN";
    default: return "en-GB";
  }
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function readComments(): CommentEntry[] {
  try {
    const raw = window.localStorage.getItem(WORKSPACE_COMMENTS_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((entry): entry is CommentEntry => {
      if (!entry || typeof entry !== "object") return false;
      const candidate = entry as Partial<CommentEntry>;
      return typeof candidate.id === "string"
        && typeof candidate.projectId === "string"
        && typeof candidate.entityId === "string"
        && typeof candidate.body === "string"
        && typeof candidate.createdAt === "string";
    });
  } catch {
    return [];
  }
}

function writeComments(entries: readonly CommentEntry[]): void {
  try {
    window.localStorage.setItem(WORKSPACE_COMMENTS_STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // Storage is a convenience; the panel still works for the current session.
  }
}

function formatCreatedAt(entry: CommentEntry, locale: string): string {
  try {
    const date = new Date(entry.createdAt);
    if (Number.isNaN(date.getTime())) return entry.createdAt;
    return new Intl.DateTimeFormat(intlLocale(locale), {
      dateStyle: "short",
      timeStyle: "short",
    }).format(date);
  } catch {
    return entry.createdAt;
  }
}

function entityEntries(input: WorkspaceCommentsInput): CommentEntry[] {
  return readComments()
    .filter((entry) => entry.projectId === input.projectId && entry.entityKind === input.entityKind && entry.entityId === input.entityId)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

function renderEntry(entry: CommentEntry, replies: readonly CommentEntry[], input: WorkspaceCommentsInput): string {
  return `<article class="cp-comment" data-comment-id="${esc(entry.id)}">
    <header><strong>${esc(entry.author)}</strong><time datetime="${esc(entry.createdAt)}">${esc(formatCreatedAt(entry, input.locale))}</time></header>
    <p>${esc(entry.body)}</p>
    <button type="button" class="cp-comment-reply" data-comment-reply="${esc(entry.id)}" data-comment-reply-author="${esc(entry.author)}" data-comment-reply-body="${esc(entry.body.slice(0, 80))}">${esc(t(input.locale, "Reply", "پاسخ"))}</button>
    ${replies.length ? `<div class="cp-comment-replies">${replies.map((reply) => renderEntry(reply, [], input)).join("")}</div>` : ""}
  </article>`;
}

export function renderWorkspaceComments(input: WorkspaceCommentsInput): string {
  const entries = entityEntries(input);
  const roots = entries.filter((entry) => !entry.parentId || !entries.some((candidate) => candidate.id === entry.parentId));
  return `<div class="cp-comments-head">
      <div><strong>${esc(t(input.locale, "Comments", "یادداشت‌ها"))}</strong><span>${esc(input.entityLabel)}</span></div>
      <button type="button" data-comments-close title="${esc(t(input.locale, "Close comments", "بستن یادداشت‌ها"))}" aria-label="${esc(t(input.locale, "Close comments", "بستن یادداشت‌ها"))}">×</button>
    </div>
    <p class="cp-comments-local" role="note">${esc(t(input.locale, "Browser-local notes for this project. They are not written to the project database.", "یادداشت‌های محلی این مرورگر برای این پروژه. این یادداشت‌ها در پایگاه دادهٔ پروژه ذخیره نمی‌شوند."))}</p>
    <div class="cp-comments-history" role="log" aria-live="polite">
      <h3>${esc(t(input.locale, "History", "تاریخچه"))} <span>${entries.length}</span></h3>
      ${roots.length
        ? roots.map((entry) => renderEntry(entry, entries.filter((reply) => reply.parentId === entry.id), input)).join("")
        : `<p class="cp-comment-empty">${esc(t(input.locale, "No comments have been recorded for this item yet.", "هنوز یادداشتی برای این مورد ثبت نشده است."))}</p>`}
    </div>
    <form class="cp-comment-form" data-comment-form>
      <label>${esc(t(input.locale, "Your name", "نام شما"))}
        <input name="author" maxlength="60" autocomplete="name" value="${esc(t(input.locale, "Local user", "کاربر محلی"))}" required>
      </label>
      <label>${esc(t(input.locale, "Comment", "یادداشت"))}
        <textarea name="body" rows="3" maxlength="2000" required placeholder="${esc(t(input.locale, "Add a note for this item…", "یادداشتی برای این مورد بنویسید…"))}"></textarea>
      </label>
      <input type="hidden" name="parent_id" value="">
      <div class="cp-comment-form-actions">
        <button type="button" data-comment-cancel-reply hidden>${esc(t(input.locale, "Cancel reply", "لغو پاسخ"))}</button>
        <button type="submit">${esc(t(input.locale, "Add comment", "افزودن یادداشت"))}</button>
      </div>
    </form>`;
}

type CommentsRuntime = { input: WorkspaceCommentsInput };
const commentsRuntime = new WeakMap<HTMLElement, CommentsRuntime>();
const commentsBound = new WeakSet<HTMLElement>();

function renderPanel(host: HTMLElement, input: WorkspaceCommentsInput): void {
  host.innerHTML = renderWorkspaceComments(input);
  const form = host.querySelector<HTMLFormElement>("[data-comment-form]");
  if (!form) return;
  const parent = form.querySelector<HTMLInputElement>('[name="parent_id"]');
  const body = form.querySelector<HTMLTextAreaElement>('[name="body"]');
  if (!parent || !body) return;
  const cancel = form.querySelector<HTMLButtonElement>("[data-comment-cancel-reply]");
  cancel?.addEventListener("click", () => {
    parent.value = "";
    body.value = "";
    if (cancel) cancel.hidden = true;
    body.focus();
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const author = (form.elements.namedItem("author") as HTMLInputElement | null)?.value.trim() || "Local user";
    const text = body.value.trim();
    if (!text) return;
    const entries = readComments();
    entries.push({
      id: `CM-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
      projectId: input.projectId,
      entityKind: input.entityKind,
      entityId: input.entityId,
      author,
      body: text,
      createdAt: new Date().toISOString(),
      parentId: parent.value || null,
    });
    writeComments(entries);
    const open = host.hidden === false;
    host.hidden = !open;
    renderPanel(host, input);
    if (open) body.focus();
  });
}

export function enhanceWorkspaceComments(workspace: HTMLElement, input: WorkspaceCommentsInput): void {
  const host = workspace.querySelector<HTMLElement>("[data-comments-panel]");
  if (!host) return;
  commentsRuntime.set(host, { input });
  const open = !host.hidden;
  host.dataset.entityKind = input.entityKind;
  host.dataset.entityId = input.entityId;
  host.dataset.entityLabel = input.entityLabel;
  if (open) renderPanel(host, input);
  if (commentsBound.has(workspace)) return;
  commentsBound.add(workspace);
  workspace.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-comments-toggle],[data-comments-close],[data-comment-reply]");
    if (!target) return;
    const panel = workspace.querySelector<HTMLElement>("[data-comments-panel]");
    const runtime = panel ? commentsRuntime.get(panel) : undefined;
    if (!panel || !runtime) return;
    if (target.dataset.commentsToggle !== undefined) {
      if (panel.hidden) {
        renderPanel(panel, runtime.input);
        panel.hidden = false;
        panel.querySelector<HTMLTextAreaElement>('[name="body"]')?.focus({ preventScroll: true });
      } else {
        panel.hidden = true;
      }
      workspace.querySelectorAll<HTMLElement>("[data-comments-toggle]").forEach((button) => button.setAttribute("aria-pressed", panel.hidden ? "false" : "true"));
      return;
    }
    if (target.dataset.commentsClose !== undefined) {
      panel.hidden = true;
      workspace.querySelectorAll<HTMLElement>("[data-comments-toggle]").forEach((button) => button.setAttribute("aria-pressed", "false"));
      return;
    }
    if (target.dataset.commentReply) {
      const form = panel.querySelector<HTMLFormElement>("[data-comment-form]");
      if (!form) return;
      const parent = form.querySelector<HTMLInputElement>('[name="parent_id"]');
      const body = form.querySelector<HTMLTextAreaElement>('[name="body"]');
      const cancel = form.querySelector<HTMLButtonElement>("[data-comment-cancel-reply]");
      if (parent) parent.value = target.dataset.commentReply;
      if (body) {
        body.value = `@${target.dataset.commentReplyAuthor ?? ""} ${target.dataset.commentReplyBody ? `“${target.dataset.commentReplyBody}”\n` : ""}`;
        body.focus();
      }
      if (cancel) cancel.hidden = false;
    }
  });
  workspace.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const panel = workspace.querySelector<HTMLElement>("[data-comments-panel]");
    if (panel && !panel.hidden) {
      panel.hidden = true;
      workspace.querySelectorAll<HTMLElement>("[data-comments-toggle]").forEach((button) => button.setAttribute("aria-pressed", "false"));
    }
  });
}
