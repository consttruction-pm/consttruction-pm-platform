import { withCsrfHeader } from "./csrf.js";

type Team = { team_id: string; name: string; owner_user_id: string; status: string; revision: number; created_at: string; updated_at: string | null };
type Membership = { team_id: string; user_id: string; role: string; status: string; scope_project_ids: string[]; revision: number; created_at: string; revoked_at: string | null };
type EligibleUser = { user_id: string; email: string; display_name: string };
type Account = { user_id: string; email: string; display_name: string; active: boolean; created_at: string };
type Locale = "en" | "fa";

const COPY = {
  en: {
    title: "Organization & Access", eyebrow: "CUBI ENTERPRISE", subtitle: "Manage organization teams and their memberships.",
    back: "Task Center", refresh: "Refresh", create: "Create team", teamName: "Team name",
    teams: "My teams", members: "Team members", noTeams: "No active teams are assigned to this account.",
    chooseTeam: "Select a team to manage its members.", addMember: "Add member", user: "Account",
    role: "Team role", scope: "Project scope IDs (optional)", add: "Add to team", remove: "Remove",
    owner: "Owner", admin: "Administrator", project_manager: "Project manager", approver: "Approver",
    field_worker: "Field worker", member: "Member", viewer: "Viewer", active: "Active", removed: "Removed",
    suspended: "Suspended", created: "Team created.", added: "Member added.", removedOk: "Membership revoked.",
    loading: "Loading organization access…", noMembers: "No membership records.", noEligible: "No eligible accounts available.",
    security: "Membership and project-scope metadata do not grant project or Engineering access. Project permissions remain separately authorized.",
    error: "The request could not be completed.", session: "Your session has expired. Sign in again.",
    confirmRemove: "Revoke this team membership?", createHint: "Creating a team requires an active Pro entitlement and Enterprise administrator permission.",
    selectAccount: "Choose an account", selectTeam: "Choose a team", roleRequired: "Choose a team role.",
    teamRequired: "Enter a team name.", scopeHint: "Optional project IDs are recorded as scope metadata only; they do not grant access.",
    accounts: "User accounts", accountStatus: "Account status", deactivate: "Deactivate", activate: "Reactivate",
    confirmDeactivate: "Deactivate this account and revoke all active sessions?", confirmActivate: "Reactivate this account?",
    accountDeactivated: "Account deactivated; existing sessions revoked.", accountActivated: "Account reactivated.",
    lastAdminError: "The last active Enterprise administrator cannot be deactivated.",
    ownerTransferError: "Transfer active team ownership before deactivating this account.",
    selfDeactivateError: "You cannot deactivate your own account.",
  },
  fa: {
    title: "سازمان و دسترسی", eyebrow: "کوبی سازمانی", subtitle: "مدیریت تیم‌های سازمان و عضویت اعضا.",
    back: "مرکز وظایف", refresh: "تازه‌سازی", create: "ایجاد تیم", teamName: "نام تیم",
    teams: "تیم‌های من", members: "اعضای تیم", noTeams: "تیم فعالی برای این حساب ثبت نشده است.",
    chooseTeam: "برای مدیریت اعضا یک تیم انتخاب کنید.", addMember: "افزودن عضو", user: "حساب کاربری",
    role: "نقش تیمی", scope: "شناسه پروژه‌ها (اختیاری)", add: "افزودن به تیم", remove: "حذف عضویت",
    owner: "مالک", admin: "مدیر", project_manager: "مدیر پروژه", approver: "تأییدکننده",
    field_worker: "نیروی کارگاه", member: "عضو", viewer: "مشاهده‌گر", active: "فعال", removed: "حذف‌شده",
    suspended: "معلق", created: "تیم ایجاد شد.", added: "عضو اضافه شد.", removedOk: "عضویت لغو شد.",
    loading: "در حال دریافت دسترسی سازمان…", noMembers: "رکورد عضویتی وجود ندارد.", noEligible: "حساب واجد شرایطی موجود نیست.",
    security: "عضویت تیم و محدوده پروژه به‌تنهایی مجوز دسترسی به پروژه یا مهندسی ایجاد نمی‌کند. مجوزهای پروژه جداگانه کنترل می‌شوند.",
    error: "درخواست انجام نشد.", session: "نشست شما پایان یافته است. دوباره وارد شوید.",
    confirmRemove: "عضویت این کاربر در تیم لغو شود؟", createHint: "ایجاد تیم به اشتراک فعال Pro و مجوز مدیر سازمان نیاز دارد.",
    selectAccount: "انتخاب حساب", selectTeam: "انتخاب تیم", roleRequired: "نقش تیمی را انتخاب کنید.",
    teamRequired: "نام تیم را وارد کنید.", scopeHint: "شناسه پروژه اختیاری صرفاً فراداده محدوده است و مجوز دسترسی ایجاد نمی‌کند.",
    accounts: "حساب‌های کاربری", accountStatus: "وضعیت حساب", deactivate: "غیرفعال‌سازی", activate: "فعال‌سازی مجدد",
    confirmDeactivate: "این حساب غیرفعال و تمام نشست‌های فعال آن لغو شود؟", confirmActivate: "این حساب دوباره فعال شود؟",
    accountDeactivated: "حساب غیرفعال شد و نشست‌های قبلی لغو شدند.", accountActivated: "حساب دوباره فعال شد.",
    lastAdminError: "آخرین مدیر فعال سازمان را نمی‌توان غیرفعال کرد.",
    ownerTransferError: "پیش از غیرفعال‌سازی این حساب، مالکیت تیم فعال را منتقل کنید.",
    selfDeactivateError: "امکان غیرفعال‌سازی حساب خودتان وجود ندارد.",
  },
} as const;

function escapeHtml(value: unknown): string {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function api<T>(path: string, method = "GET", body?: Record<string, unknown>): Promise<T> {
  const headers = withCsrfHeader(method, body ? { "Content-Type": "application/json" } : {});
  const response = await fetch(path, {
    method, credentials: "same-origin", headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const payload: unknown = await response.json().catch(() => ({}));
  if (!response.ok) {
    const code = isRecord(payload) && typeof payload.code === "string" ? payload.code : "REQUEST_FAILED";
    if (response.status === 401) {
      window.location.assign(`/login?next=${encodeURIComponent("/enterprise/organization")}`);
      throw new Error("SESSION_REQUIRED");
    }
    throw new Error(code);
  }
  return payload as T;
}

function teamList(value: unknown): Team[] {
  if (!isRecord(value) || value.contract_version !== "cubi-enterprise-team-list.v1" || !Array.isArray(value.teams)) {
    throw new Error("INVALID_TEAM_LIST");
  }
  return value.teams.map((item) => {
    if (!isRecord(item) || typeof item.team_id !== "string" || typeof item.name !== "string"
      || typeof item.owner_user_id !== "string" || typeof item.status !== "string"
      || typeof item.revision !== "number" || typeof item.created_at !== "string") throw new Error("INVALID_TEAM_LIST");
    return item as Team;
  });
}

function memberList(value: unknown): Membership[] {
  if (!isRecord(value) || value.contract_version !== "cubi-enterprise-team-membership-list.v1"
    || !Array.isArray(value.memberships)) throw new Error("INVALID_MEMBERSHIP_LIST");
  return value.memberships.map((item) => {
    if (!isRecord(item) || typeof item.team_id !== "string" || typeof item.user_id !== "string"
      || typeof item.role !== "string" || typeof item.status !== "string" || typeof item.revision !== "number"
      || !Array.isArray(item.scope_project_ids)) throw new Error("INVALID_MEMBERSHIP_LIST");
    return item as Membership;
  });
}

function accountList(value: unknown): Account[] {
  if (!isRecord(value) || value.contract_version !== "cubi-enterprise-user-list.v1"
    || !Array.isArray(value.users)) throw new Error("INVALID_ENTERPRISE_USER_LIST");
  return value.users.map((item) => {
    if (!isRecord(item) || typeof item.user_id !== "string" || typeof item.email !== "string"
      || typeof item.display_name !== "string" || typeof item.active !== "boolean"
      || typeof item.created_at !== "string") throw new Error("INVALID_ENTERPRISE_USER_LIST");
    return item as Account;
  });
}

function eligibleList(value: unknown): EligibleUser[] {
  if (!isRecord(value) || value.contract_version !== "cubi-enterprise-eligible-users.v1"
    || !Array.isArray(value.users)) throw new Error("INVALID_ELIGIBLE_USERS");
  return value.users.map((item) => {
    if (!isRecord(item) || typeof item.user_id !== "string" || typeof item.email !== "string"
      || typeof item.display_name !== "string") throw new Error("INVALID_ELIGIBLE_USERS");
    return item as EligibleUser;
  });
}

export async function mountEnterpriseOrganizationAccess(container: HTMLElement): Promise<void> {
  const locale: Locale = navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  const t = COPY[locale];
  const roleNames: Record<string, string> = {
    owner: t.owner, admin: t.admin, project_manager: t.project_manager, approver: t.approver,
    field_worker: t.field_worker, member: t.member, viewer: t.viewer,
  };
  let teams: Team[] = [];
  let memberships: Membership[] = [];
  let eligibleUsers: EligibleUser[] = [];
  let accounts: Account[] = [];
  let canManage = false;
  let canAdminAccounts = false;
  let selectedTeamId = "";
  let busy = false;
  let notice = "";
  let failure = "";

  const render = () => {
    const selected = teams.find((team) => team.team_id === selectedTeamId) ?? null;
    const teamOptions = teams.map((team) => `<option value="${escapeHtml(team.team_id)}" ${team.team_id === selectedTeamId ? "selected" : ""}>${escapeHtml(team.name)}</option>`).join("");
    const memberRows = memberships.map((item) => `<tr>
      <td><strong>${escapeHtml(item.user_id)}</strong><small>${escapeHtml(item.scope_project_ids.join(", ") || "—")}</small></td>
      <td>${escapeHtml(roleNames[item.role] ?? item.role)}</td>
      <td><span class="cubi-oa-status cubi-oa-${escapeHtml(item.status)}">${escapeHtml(item.status === "active" ? t.active : item.status === "removed" ? t.removed : t.suspended)}</span></td>
      <td>${item.revision}</td>
      <td>${canManage && item.status === "active" && item.role !== "owner" ? `<button class="cubi-oa-button cubi-oa-danger" data-remove="${escapeHtml(item.user_id)}" data-revision="${item.revision}" type="button">${escapeHtml(t.remove)}</button>` : "—"}</td>
    </tr>`).join("");
    const usersOptions = eligibleUsers.map((user) => `<option value="${escapeHtml(user.user_id)}">${escapeHtml(user.display_name || user.email)} · ${escapeHtml(user.email)}</option>`).join("");
    const accountRows = accounts.map((account) => `<tr>
      <td><strong>${escapeHtml(account.display_name || account.email)}</strong><small>${escapeHtml(account.email)} · ${escapeHtml(account.user_id)}</small></td>
      <td><span class="cubi-oa-status ${account.active ? "cubi-oa-active" : "cubi-oa-removed"}">${account.active ? t.active : t.removed}</span></td>
      <td><button class="cubi-oa-button ${account.active ? "cubi-oa-danger" : ""}" data-account-status="${escapeHtml(account.user_id)}" data-active="${account.active}" type="button">${account.active ? t.deactivate : t.activate}</button></td>
    </tr>`).join("");
    container.innerHTML = `
      <style>
        .cubi-oa{min-height:100vh;background:#f3f6fa;color:#18283c;font:14px/1.5 Inter,Arial,sans-serif;padding:28px;box-sizing:border-box}
        .cubi-oa *{box-sizing:border-box}.cubi-oa-shell{max-width:1180px;margin:auto}
        .cubi-oa-head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}
        .cubi-oa-eyebrow{font-size:11px;font-weight:800;letter-spacing:.14em;color:#59718d}.cubi-oa h1{font-size:28px;margin:4px 0}.cubi-oa p{margin:4px 0;color:#617187}
        .cubi-oa-button{border:1px solid #cbd5e1;border-radius:8px;background:#fff;padding:9px 13px;color:#24364b;cursor:pointer;font-weight:650}
        .cubi-oa-primary{background:#173b63;color:white;border-color:#173b63}.cubi-oa-danger{color:#a33232;border-color:#e8c6c6}
        .cubi-oa-grid{display:grid;grid-template-columns:minmax(260px,.8fr) minmax(500px,1.8fr);gap:18px}
        .cubi-oa-card{background:white;border:1px solid #dfe6ee;border-radius:13px;padding:18px;box-shadow:0 3px 14px #19324b08}
        .cubi-oa-card h2{font-size:17px;margin:0 0 14px}.cubi-oa-list{display:grid;gap:8px}
        .cubi-oa-team{width:100%;text-align:left;border:1px solid #e0e7ef;background:#fff;border-radius:8px;padding:11px;cursor:pointer}
        .cubi-oa-team[aria-pressed=true]{border-color:#356b9e;background:#eff6fc}.cubi-oa-team small,.cubi-oa small{display:block;color:#718198;font-size:11px}
        .cubi-oa-field{display:grid;gap:5px;margin:10px 0}.cubi-oa-field label{font-weight:650;font-size:12px;color:#42566e}
        .cubi-oa-field input,.cubi-oa-field select{width:100%;min-height:38px;border:1px solid #ccd7e3;border-radius:7px;padding:8px;background:#fff;color:#172b43}
        .cubi-oa-form{border-top:1px solid #e6ebf1;margin-top:16px;padding-top:14px}.cubi-oa-tablewrap{overflow:auto}
        .cubi-oa table{width:100%;border-collapse:collapse;min-width:650px}.cubi-oa th,.cubi-oa td{text-align:left;padding:10px;border-bottom:1px solid #e9eef3;vertical-align:middle}
        .cubi-oa th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#6b7b8f}.cubi-oa-status{font-size:11px;border-radius:20px;padding:3px 8px;background:#e7f5ed;color:#23643f}
        .cubi-oa-removed{background:#f1f2f4;color:#6a7481}.cubi-oa-suspended{background:#fff3d8;color:#805a11}
        .cubi-oa-note{margin-top:16px;padding:12px 14px;background:#edf4fb;border:1px solid #d7e5f2;border-radius:9px;color:#395673;font-size:12px}
        .cubi-oa-alert{margin:0 0 14px;padding:10px 12px;border-radius:8px;background:#e8f5ed;color:#23643f}.cubi-oa-alert.error{background:#fff0f0;color:#9a3030}
        .cubi-oa-muted{padding:16px;color:#718198;background:#f8fafc;border-radius:8px}
        @media(max-width:760px){.cubi-oa{padding:14px}.cubi-oa-grid{grid-template-columns:1fr}.cubi-oa-head{align-items:flex-start;flex-direction:column}}
      </style>
      <main class="cubi-oa" dir="${locale === "fa" ? "rtl" : "ltr"}"><div class="cubi-oa-shell">
        <header class="cubi-oa-head"><div><div class="cubi-oa-eyebrow">${t.eyebrow}</div><h1>${t.title}</h1><p>${t.subtitle}</p></div>
          <div><a class="cubi-oa-button" href="/enterprise">${t.back}</a> <button class="cubi-oa-button" id="cubi-oa-refresh" type="button">${t.refresh}</button></div>
        </header>
        ${notice ? `<div class="cubi-oa-alert" role="status">${escapeHtml(notice)}</div>` : ""}
        ${failure ? `<div class="cubi-oa-alert error" role="alert">${escapeHtml(failure)}</div>` : ""}
        <section class="cubi-oa-grid">
          <aside class="cubi-oa-card"><h2>${t.teams}</h2>
            <div class="cubi-oa-list">${teams.length ? teams.map((team) => `<button class="cubi-oa-team" data-team="${escapeHtml(team.team_id)}" aria-pressed="${team.team_id === selectedTeamId}"><strong>${escapeHtml(team.name)}</strong><small>${escapeHtml(team.team_id)} · ${escapeHtml(team.status)}</small></button>`).join("") : `<div class="cubi-oa-muted">${t.noTeams}</div>`}</div>
            <form class="cubi-oa-form" id="cubi-oa-create">
              <div class="cubi-oa-field"><label for="cubi-oa-team-name">${t.teamName}</label><input id="cubi-oa-team-name" name="name" maxlength="200" required></div>
              <button class="cubi-oa-button cubi-oa-primary" type="submit" ${busy ? "disabled" : ""}>${t.create}</button>
              <small>${t.createHint}</small>
            </form>
          </aside>
          <section class="cubi-oa-card"><h2>${t.members}</h2>
            ${selected ? `<div class="cubi-oa-field"><label for="cubi-oa-selected">${t.selectTeam}</label><select id="cubi-oa-selected">${teamOptions}</select></div>
              <div class="cubi-oa-tablewrap"><table><thead><tr><th>${t.user}</th><th>${t.role}</th><th>Status</th><th>Revision</th><th></th></tr></thead><tbody>${memberRows || `<tr><td colspan="5">${t.noMembers}</td></tr>`}</tbody></table></div>
              ${canManage ? `<form class="cubi-oa-form" id="cubi-oa-add">
                <h2>${t.addMember}</h2>
                <div class="cubi-oa-field"><label for="cubi-oa-user">${t.user}</label><select id="cubi-oa-user" name="user_id" required><option value="">${t.selectAccount}</option>${usersOptions}</select></div>
                <div class="cubi-oa-field"><label for="cubi-oa-role">${t.role}</label><select id="cubi-oa-role" name="role" required><option value="">—</option>${["admin","project_manager","approver","field_worker","member","viewer"].map(role => `<option value="${role}">${escapeHtml(roleNames[role])}</option>`).join("")}</select></div>
                <div class="cubi-oa-field"><label for="cubi-oa-scope">${t.scope}</label><input id="cubi-oa-scope" name="scope" placeholder="PROJECT-001, PROJECT-002"></div>
                <button class="cubi-oa-button cubi-oa-primary" type="submit" ${busy || !eligibleUsers.length ? "disabled" : ""}>${t.add}</button>
                <small>${eligibleUsers.length ? t.scopeHint : t.noEligible}</small>
              </form>` : ""}` : `<div class="cubi-oa-muted">${t.chooseTeam}</div>`}
          </section>
        </section>
        <p class="cubi-oa-note">${t.security}</p>
        ${canAdminAccounts ? `<section class="cubi-oa-card" style="margin-top:18px"><h2>${t.accounts}</h2>
          <div class="cubi-oa-tablewrap"><table><thead><tr><th>${t.user}</th><th>${t.accountStatus}</th><th></th></tr></thead>
          <tbody>${accountRows || `<tr><td colspan="3">${t.noEligible}</td></tr>`}</tbody></table></div>
        </section>` : ""}
      </div></main>`;
    container.querySelector<HTMLButtonElement>("#cubi-oa-refresh")?.addEventListener("click", () => void load());
    container.querySelectorAll<HTMLButtonElement>("[data-team]").forEach((button) => button.addEventListener("click", () => {
      selectedTeamId = button.dataset.team ?? ""; void loadTeam();
    }));
    container.querySelector<HTMLSelectElement>("#cubi-oa-selected")?.addEventListener("change", (event) => {
      selectedTeamId = (event.currentTarget as HTMLSelectElement).value; void loadTeam();
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-create")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const name = String(form.get("name") ?? "").trim();
      if (!name) { failure = t.teamRequired; render(); return; }
      void run(async () => {
        const result = await api<{ team: Team }>("/api/enterprise/teams", "POST", { contract_version: "cubi-enterprise-team.v1", name });
        notice = t.created; selectedTeamId = result.team.team_id; await load(true);
      });
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-add")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const userId = String(form.get("user_id") ?? "");
      const role = String(form.get("role") ?? "");
      if (!role) { failure = t.roleRequired; render(); return; }
      const scopes = String(form.get("scope") ?? "").split(",").map(value => value.trim()).filter(Boolean);
      void run(async () => {
        await api(`/api/enterprise/teams/${encodeURIComponent(selectedTeamId)}/members`, "POST", {
          contract_version: "cubi-enterprise-team.v1", user_id: userId, role, scope_project_ids: scopes,
        });
        notice = t.added; await loadTeam();
      });
    });
    container.querySelectorAll<HTMLButtonElement>("[data-account-status]").forEach((button) => button.addEventListener("click", () => {
      const userId = button.dataset.accountStatus ?? "";
      const wasActive = button.dataset.active === "true";
      if (!userId || !window.confirm(wasActive ? t.confirmDeactivate : t.confirmActivate)) return;
      void run(async () => {
        await api(`/api/enterprise/users/${encodeURIComponent(userId)}/status`, "PATCH", {
          contract_version: "cubi-enterprise-user-admin.v1", active: !wasActive,
        });
        notice = wasActive ? t.accountDeactivated : t.accountActivated;
        await load(true);
      });
    }));
    container.querySelectorAll<HTMLButtonElement>("[data-remove]").forEach((button) => button.addEventListener("click", () => {
      const userId = button.dataset.remove ?? "";
      const revision = Number(button.dataset.revision);
      if (!userId || !Number.isInteger(revision) || !window.confirm(t.confirmRemove)) return;
      void run(async () => {
        await api(`/api/enterprise/teams/${encodeURIComponent(selectedTeamId)}/members/${encodeURIComponent(userId)}`, "DELETE", {
          contract_version: "cubi-enterprise-team.v1", expected_revision: revision,
        });
        notice = t.removedOk; await loadTeam();
      });
    }));
  };

  const run = async (action: () => Promise<void>) => {
    if (busy) return;
    busy = true; failure = ""; render();
    try { await action(); } catch (error) {
      const code = error instanceof Error ? error.message : "";
      const messages: Record<string, string> = {
        LAST_ENTERPRISE_ADMIN_CANNOT_BE_DEACTIVATED: t.lastAdminError,
        TEAM_OWNER_TRANSFER_REQUIRED: t.ownerTransferError,
        SELF_DEACTIVATION_NOT_ALLOWED: t.selfDeactivateError,
      };
      failure = code === "SESSION_REQUIRED" ? t.session : messages[code] ?? (code || t.error);
    } finally { busy = false; render(); }
  };

  const loadTeam = async () => {
    if (!selectedTeamId) { memberships = []; eligibleUsers = []; render(); return; }
    try {
      const members = await api<unknown>(`/api/enterprise/teams/${encodeURIComponent(selectedTeamId)}/members`);
      memberships = memberList(members);
      try {
        const users = await api<unknown>(`/api/enterprise/teams/${encodeURIComponent(selectedTeamId)}/eligible-users`);
        eligibleUsers = eligibleList(users); canManage = true;
      } catch (error) {
        eligibleUsers = []; canManage = false;
        if (error instanceof Error && error.message === "SESSION_REQUIRED") throw error;
      }
      failure = "";
    } catch (error) {
      memberships = []; eligibleUsers = []; canManage = false;
      failure = error instanceof Error && error.message === "SESSION_REQUIRED" ? t.session
        : error instanceof Error ? error.message : t.error;
    }
    render();
  };

  const load = async (preserveNotice = false) => {
    failure = "";
    if (!preserveNotice) notice = "";
    render();
    try {
      teams = teamList(await api<unknown>("/api/enterprise/teams"));
      if (!teams.some(team => team.team_id === selectedTeamId)) selectedTeamId = teams[0]?.team_id ?? "";
      await loadTeam();
      try {
        accounts = accountList(await api<unknown>("/api/enterprise/users"));
        canAdminAccounts = true;
      } catch (error) {
        accounts = []; canAdminAccounts = false;
        if (error instanceof Error && error.message === "SESSION_REQUIRED") throw error;
      }
      render();
    } catch (error) {
      failure = error instanceof Error && error.message === "SESSION_REQUIRED" ? t.session
        : error instanceof Error ? error.message : t.error;
      render();
    }
  };

  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  document.title = `CUBI Enterprise · ${t.title}`;
  render();
  await load();
}
