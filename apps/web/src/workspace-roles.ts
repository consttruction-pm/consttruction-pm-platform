import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ROLE_API_VERSION = "p6-role-api.v1";

export type RoleRecord = {
  roleId: string;
  name: string;
  description: string | null;
  recordRevision: number;
};

export type RolePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
};

export type RoleInput = {
  roleId: string;
  name: string;
  description: string | null;
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
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function rolePath(context: ProjectContext, roleId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/roles`;
  return roleId ? `${base}/${encodeURIComponent(roleId)}` : base;
}

function descriptionOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function parseRole(value: unknown): RoleRecord {
  if (!isRecord(value)) throw new Error("INVALID_ROLE_RECORD");
  const { role_id, name, description, record_revision } = value;
  if (
    typeof role_id !== "string" || !role_id.trim() ||
    typeof name !== "string" || !name.trim() ||
    typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 0 ||
    (description !== undefined && description !== null && typeof description !== "string")
  ) {
    throw new Error("INVALID_ROLE_RECORD");
  }
  return {
    roleId: role_id,
    name,
    description: descriptionOrNull(description),
    recordRevision: record_revision,
  };
}

function parseRoleEnvelope(payload: unknown): RoleRecord {
  if (!isRecord(payload) || payload.contract_version !== ROLE_API_VERSION || payload.kind !== "p6_role") {
    throw new Error("INVALID_ROLE_RESPONSE");
  }
  return parseRole(payload.role);
}

export async function loadRoles(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly RoleRecord[]>> {
  const result = await transport.get<unknown>(rolePath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ROLE_API_VERSION || !Array.isArray(payload.roles)) {
    return localError("INVALID_ROLE_LIST");
  }
  try {
    return { ok: true, data: payload.roles.map((item) => parseRoleEnvelope(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_LIST");
  }
}

export async function loadRole(
  transport: ApiTransport,
  context: ProjectContext,
  roleId: string,
): Promise<ApiResult<RoleRecord>> {
  if (!roleId.trim()) return localError("ROLE_ID_REQUIRED");
  const result = await transport.get<unknown>(rolePath(context, roleId), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

function buildRolePayload(input: RoleInput): Record<string, unknown> | null {
  if (!input.roleId.trim() || !input.name.trim()) return null;
  return {
    role_id: input.roleId.trim(),
    name: input.name.trim(),
    description: descriptionOrNull(input.description),
  };
}

export async function createRole(
  transport: ApiTransport,
  context: ProjectContext,
  input: RoleInput,
): Promise<ApiResult<RoleRecord>> {
  const payload = buildRolePayload(input);
  if (!payload) return localError("ROLE_FIELDS_REQUIRED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    rolePath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

export async function updateRole(
  transport: ApiTransport,
  context: ProjectContext,
  role: RoleRecord,
  input: { name: string; description: string | null },
): Promise<ApiResult<RoleRecord>> {
  if (!input.name.trim()) return localError("ROLE_NAME_REQUIRED");
  if (role.recordRevision < 1) return localError("ROLE_REVISION_REQUIRED");
  if (!transport.patch) return localError("ROLE_UPDATE_TRANSPORT_UNAVAILABLE");
  const payload = {
    name: input.name.trim(),
    description: descriptionOrNull(input.description),
    expected_revision: role.recordRevision,
  };
  const result = await transport.patch<typeof payload, unknown>(
    rolePath(context, role.roleId),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRoleEnvelope(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ROLE_RESPONSE");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  roles: readonly RoleRecord[];
  selectedId: string | null;
  mode: "browse" | "create" | "edit";
  draftName: string;
  draftDescription: string;
  draftRoleId: string;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

export function mountWorkspaceRolesPage(host: HTMLElement, options: RolePageOptions): void {
  if (host.dataset.rolesMounted === "true") return;
  host.dataset.rolesMounted = "true";
  const { transport, context, locale } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    roles: [],
    selectedId: null,
    mode: "browse",
    draftName: "",
    draftDescription: "",
    draftRoleId: "",
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): RoleRecord | null =>
    state.roles.find((role) => role.roleId === state.selectedId) ?? null;

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading the role register…", "در حال خواندن فهرست نقش‌ها…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Role register could not be read", "خواندن فهرست نقش‌ها ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.roles.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No roles are stored for this project.", "هیچ نقشی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.roles.map((role) => {
      const active = role.roleId === state.selectedId;
      return `<tr data-role-row data-role-id="${escapeHtml(role.roleId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(role.roleId)}</strong></td><td>${escapeHtml(role.name)}</td><td>${escapeHtml(role.description ?? "—")}</td><td>${role.recordRevision}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Role ID", "شناسه نقش"))}</th><th>${escapeHtml(say("Role Name", "نام نقش"))}</th><th>${escapeHtml(say("Description", "شرح"))}</th><th>${escapeHtml(say("Revision", "ویرایش"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderDetails(): string {
    const role = selected();
    if (state.mode === "create") {
      return `<form data-role-create-form class="cp-role-fields">
        <label>${escapeHtml(say("Role ID", "شناسه نقش"))}<input name="role-id" value="${escapeHtml(state.draftRoleId)}" required></label>
        <label>${escapeHtml(say("Role Name", "نام نقش"))}<input name="role-name" value="${escapeHtml(state.draftName)}" required></label>
        <label>${escapeHtml(say("Description", "شرح"))}<input name="role-description" value="${escapeHtml(state.draftDescription)}"></label>
        <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create role", "ایجاد نقش"))}</button><button type="button" data-role-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      </form>`;
    }
    if (!role) {
      return `<p>${escapeHtml(say("Select a role from the register to read its stored definition.", "برای خواندن تعریف ذخیره‌شده، یک نقش را از فهرست انتخاب کنید."))}</p>`;
    }
    if (state.mode === "edit") {
      return `<form data-role-edit-form class="cp-role-fields">
        <label>${escapeHtml(say("Role ID", "شناسه نقش"))}<input readonly value="${escapeHtml(role.roleId)}"></label>
        <label>${escapeHtml(say("Role Name", "نام نقش"))}<input name="role-name" value="${escapeHtml(state.draftName)}" required></label>
        <label>${escapeHtml(say("Description", "شرح"))}<input name="role-description" value="${escapeHtml(state.draftDescription)}"></label>
        <label>${escapeHtml(say("Record Revision", "ویرایش رکورد"))}<input readonly value="${role.recordRevision}"></label>
        <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Save changes", "ذخیره تغییرات"))}</button><button type="button" data-role-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      </form>`;
    }
    return `<div class="cp-role-fields">
      <label>${escapeHtml(say("Role ID", "شناسه نقش"))}<input readonly value="${escapeHtml(role.roleId)}"></label>
      <label>${escapeHtml(say("Role Name", "نام نقش"))}<input readonly value="${escapeHtml(role.name)}"></label>
      <label>${escapeHtml(say("Description", "شرح"))}<input readonly value="${escapeHtml(role.description ?? say("Not provided", "ارائه نشده"))}"></label>
      <label>${escapeHtml(say("Record Revision", "ویرایش رکورد"))}<input readonly value="${role.recordRevision}"></label>
    </div>
    <div class="cp-calendar-panel-actions"><button type="button" data-role-action="edit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Edit role", "ویرایش نقش"))}</button></div>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Role Register", "فهرست نقش‌ها"))}</strong><div><button type="button" data-role-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Role", "نقش جدید"))}</button><button type="button" data-role-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Role Details", "جزئیات نقش"))}</strong><span>${selected() ? escapeHtml(selected()?.roleId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-role-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadRoles(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.roles = result.data;
      state.selectedId = keepSelection && result.data.some((role) => role.roleId === keepSelection) ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-role-row]");
    if (row?.dataset.roleId) {
      state.selectedId = row.dataset.roleId;
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-role-action]")?.dataset.roleAction;
    if (!action) return;
    const role = selected();
    if (action === "new") {
      state.mode = "create";
      state.draftRoleId = "";
      state.draftName = "";
      state.draftDescription = "";
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel") {
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    if (action === "edit" && role) {
      state.mode = "edit";
      state.draftName = role.name;
      state.draftDescription = role.description ?? "";
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") {
      void reload(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-role-row]");
    if (!row?.dataset.roleId) return;
    event.preventDefault();
    state.selectedId = row.dataset.roleId;
    state.mode = "browse";
    state.notice = null;
    render();
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (target.name === "role-id") state.draftRoleId = target.value;
    if (target.name === "role-name") state.draftName = target.value;
    if (target.name === "role-description") state.draftDescription = target.value;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    const creating = form.matches("[data-role-create-form]");
    const editing = form.matches("[data-role-edit-form]");
    if (!creating && !editing) return;
    event.preventDefault();
    if (state.busy) return;
    const role = selected();
    if (editing && !role) return;
    void (async () => {
      state.busy = true;
      render();
      const result = creating
        ? await createRole(transport, context, {
            roleId: state.draftRoleId,
            name: state.draftName,
            description: state.draftDescription || null,
          })
        : await updateRole(transport, context, role as RoleRecord, {
            name: state.draftName,
            description: state.draftDescription || null,
          });
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${creating ? say("Role was not created", "نقش ایجاد نشد") : say("Save failed", "ذخیره ناموفق بود")} (${result.error.code})`,
        };
        render();
        return;
      }
      state.notice = {
        kind: "ok",
        message: creating ? say("Role created.", "نقش ایجاد شد.") : say("Role saved.", "نقش ذخیره شد."),
      };
      state.mode = "browse";
      await reload(result.data.roleId);
    })();
  });

  void reload(null);
}
