import { withCsrfHeader } from "./csrf.js";

type Team = { team_id: string; name: string; owner_user_id: string; status: string; revision: number; created_at: string; updated_at: string | null };
type Membership = { team_id: string; user_id: string; role: string; status: string; scope_project_ids: string[]; revision: number; created_at: string; revoked_at: string | null };
type EligibleUser = { user_id: string; email: string; display_name: string };
type Account = { user_id: string; email: string; display_name: string; active: boolean; created_at: string };
type OBSNode = { obs_id: string; parent_obs_id: string | null; code: string; name: string; manager_user_id: string; sequence_number: number };
type ProjectAccessAssignment = { profile_id: string; profile_name: string; obs_id: string; revision: number };
type SecurityProfile = { profile_id: string; name: string; description: string; scope: "global" | "project"; active: boolean; is_default: boolean; revision: number; privileges: string[] };
type ProfileAssignment = { user_id: string; email: string; display_name: string; obs_id: string; revision: number; assigned_by: string; assigned_at: string; module_access: string[]; resource_access_mode: "none" | "all" | "selected"; resource_root_ids: string[] };
type GlobalUserAccess = { tenant_id: string; user_id: string; profile_id: string; module_access: string[]; resource_access_mode: "none" | "all" | "selected"; resource_root_ids: string[]; revision: number; assigned_by: string; assigned_at: string };
type PrivilegeCatalogs = { global: string[]; project: string[] };
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
    transferOwner: "Transfer ownership", newOwner: "New owner", confirmTransfer: "Transfer team ownership? Your role will become Administrator.",
    transferred: "Team ownership transferred.",
    securityProfiles: "Security profiles", profileId: "Profile ID", profileName: "Profile name", profileDescription: "Description",
    saveProfileDetails: "Save details", profileDetailsSaved: "Profile details saved.", profileDefault: "Default", profileSetDefault: "Set as default",
    profileClearDefault: "Clear default", profileDefaultSaved: "Default security profile updated.",
    profileDuplicate: "Duplicate", profileDuplicateId: "New profile ID", profileDuplicateName: "New profile name",
    profileDuplicated: "Profile duplicated with its privileges.", profileDelete: "Delete profile",
    profileDeleteConfirm: "Delete this profile? Profiles with current assignments cannot be deleted.",
    profileDeleted: "Profile deleted.", profileDeleteAssigned: "This profile still has assignments and cannot be deleted.",
    profileScope: "Profile scope", globalProfile: "Global", projectProfile: "Project",
    createProfile: "Create profile", selectProfile: "Select a profile", privileges: "Privileges",
    savePrivileges: "Save privileges", assignProfile: "Assign profile", obsId: "Responsible OBS ID",
    assignmentRevision: "Existing assignment revision (for replacement)", assignedUsers: "Assignments",
    userAdminRequired: "The V26 Add/Edit/Delete Users global privilege is required to assign profiles or manage accounts.",
    privilegeRequired: "Your assigned Global Security Profile does not grant this operation.",
    noProfiles: "No security profiles are defined.", profileCreated: "Security profile created.",
    profileSaved: "Privileges saved.", profileAssigned: "Profile assigned.", profileActive: "Active",
    profileInactive: "Inactive", profileActivate: "Activate", profileDeactivate: "Deactivate",
    profileStatusSaved: "Profile status updated.", removeAssignment: "Remove assignment",
    profileHelp: "Every user requires one Global profile. Project profiles are assigned to OBS responsibility and do not replace project membership.",
    globalAccessTitle: "Global user access", selectGlobalUser: "Assigned user", moduleAccess: "Module access",
    resourceAccess: "Resource access", noResources: "No resources", allResources: "All resources",
    selectResources: "Select up to five resource roots (unavailable until the global resource hierarchy is configured)",
    resourceAccessNote: "Module access controls which application modules are available. Project data still requires the matching OBS/project security profile. Selected resource access is not enabled until CUBI has an enterprise-wide resource hierarchy.",
    saveGlobalAccess: "Save user access", globalAccessSaved: "Global user access updated.",
    assignDefaultProjectTitle: "Assign OBS with the default Project profile",
    obsSelect: "Responsible OBS", obsAssignmentRevision: "Current assignment revision (for replacement)",
    assignDefaultProject: "Assign OBS", defaultProjectAssigned: "OBS access assigned using the current default Project profile.",
    currentObsAssignments: "Current OBS assignments", noObsAssignments: "No OBS assignments for this account.",
    noObsNodes: "No OBS nodes are available. Configure the tenant OBS hierarchy first.",
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
    transferOwner: "انتقال مالکیت", newOwner: "مالک جدید", confirmTransfer: "مالکیت تیم منتقل شود؟ نقش شما به مدیر تغییر می‌کند.",
    transferred: "مالکیت تیم منتقل شد.",
    securityProfiles: "پروفایل‌های امنیتی", profileId: "شناسه پروفایل", profileName: "نام پروفایل",
    profileDescription: "توضیحات", saveProfileDetails: "ذخیره جزئیات", profileDetailsSaved: "جزئیات پروفایل ذخیره شد.", profileDefault: "پیش‌فرض",
    profileSetDefault: "تنظیم به‌عنوان پیش‌فرض", profileClearDefault: "حذف حالت پیش‌فرض",
    profileDefaultSaved: "پروفایل امنیتی پیش‌فرض به‌روزرسانی شد.", profileDuplicate: "تکثیر",
    profileDuplicateId: "شناسه پروفایل جدید", profileDuplicateName: "نام پروفایل جدید",
    profileDuplicated: "پروفایل همراه با مجوزهایش تکثیر شد.", profileDelete: "حذف پروفایل",
    profileDeleteConfirm: "این پروفایل حذف شود؟ پروفایل دارای تخصیص فعلی قابل حذف نیست.",
    profileDeleted: "پروفایل حذف شد.", profileDeleteAssigned: "این پروفایل هنوز تخصیص دارد و قابل حذف نیست.",
    profileScope: "دامنه پروفایل", globalProfile: "سراسری", projectProfile: "پروژه‌ای",
    createProfile: "ایجاد پروفایل", selectProfile: "انتخاب پروفایل", privileges: "مجوزها",
    savePrivileges: "ذخیره مجوزها", assignProfile: "اختصاص پروفایل", obsId: "شناسه مسئولیت OBS",
    assignmentRevision: "نسخه تخصیص قبلی (برای جایگزینی)", assignedUsers: "تخصیص‌ها",
    userAdminRequired: "برای تخصیص پروفایل یا مدیریت حساب‌ها، مجوز سراسری Add/Edit/Delete Users نسخه ۲۶ لازم است.",
    privilegeRequired: "پروفایل امنیتی سراسری اختصاص‌یافته، مجوز این عملیات را ندارد.",
    noProfiles: "پروفایل امنیتی تعریف نشده است.", profileCreated: "پروفایل امنیتی ایجاد شد.",
    profileSaved: "مجوزها ذخیره شدند.", profileAssigned: "پروفایل اختصاص یافت.", profileActive: "فعال",
    profileInactive: "غیرفعال", profileActivate: "فعال‌سازی", profileDeactivate: "غیرفعال‌سازی",
    profileStatusSaved: "وضعیت پروفایل به‌روزرسانی شد.", removeAssignment: "حذف تخصیص",
    profileHelp: "هر کاربر به یک پروفایل سراسری نیاز دارد. پروفایل پروژه به مسئولیت OBS اختصاص می‌یابد و جایگزین عضویت پروژه نیست.",
    globalAccessTitle: "دسترسی سراسری کاربر", selectGlobalUser: "کاربر تخصیص‌یافته", moduleAccess: "دسترسی ماژول‌ها",
    resourceAccess: "دسترسی منابع", noResources: "بدون دسترسی به منابع", allResources: "همه منابع",
    selectResources: "انتخاب حداکثر پنج ریشه منابع (تا زمان پیکربندی سلسله‌مراتب سراسری منابع غیرفعال است)",
    resourceAccessNote: "دسترسی ماژول‌ها بخش‌های قابل استفاده برنامه را تعیین می‌کند. دسترسی به داده پروژه همچنان به پروفایل امنیتی OBS/پروژه نیاز دارد. انتخاب منابع تا ایجاد سلسله‌مراتب سراسری منابع کوبی فعال نیست.",
    saveGlobalAccess: "ذخیره دسترسی کاربر", globalAccessSaved: "دسترسی سراسری کاربر به‌روزرسانی شد.",
    assignDefaultProjectTitle: "اختصاص OBS با پروفایل پیش‌فرض پروژه",
    obsSelect: "OBS مسئول", obsAssignmentRevision: "نسخه تخصیص فعلی (برای جایگزینی)",
    assignDefaultProject: "اختصاص OBS", defaultProjectAssigned: "دسترسی OBS با پروفایل پیش‌فرض فعلی پروژه اختصاص یافت.",
    currentObsAssignments: "تخصیص‌های فعلی OBS", noObsAssignments: "برای این حساب تخصیص OBS ثبت نشده است.",
    noObsNodes: "گره OBS موجود نیست. ابتدا ساختار OBS سازمان را پیکربندی کنید.",
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
  let profiles: SecurityProfile[] = [];
  let profileAssignments: ProfileAssignment[] = [];
  let privilegeCatalogs: PrivilegeCatalogs = { global: [], project: [] };
  let selectedProfileId = "";
  let selectedGlobalAccessUserId = "";
  let globalUserAccess: GlobalUserAccess | null = null;
  let obsNodes: OBSNode[] = [];
  let selectedProjectUserId = "";
  let selectedProjectObsId = "";
  let userProjectAssignments: ProjectAccessAssignment[] = [];
  let canManageSecurityProfiles = false;
  let selectedTeamId = "";
  let busy = false;
  let notice = "";
  let failure = "";

  const loadUserProjectAssignments = async () => {
    if (!selectedProjectUserId) { userProjectAssignments = []; return; }
    const result = await api<{ assignments: ProjectAccessAssignment[] }>(
      `/api/enterprise/users/${encodeURIComponent(selectedProjectUserId)}/project-access`,
    );
    userProjectAssignments = Array.isArray(result.assignments) ? result.assignments : [];
    if (!userProjectAssignments.some((item) => item.obs_id === selectedProjectObsId)) {
      selectedProjectObsId = "";
    }
  };

  const loadGlobalUserAccess = async () => {
    if (!selectedGlobalAccessUserId) { globalUserAccess = null; return; }
    const result = await api<{ access: GlobalUserAccess }>(
      `/api/enterprise/users/${encodeURIComponent(selectedGlobalAccessUserId)}/global-access`,
    );
    globalUserAccess = result.access;
  };

  const loadProfileAssignments = async () => {
    if (!selectedProfileId) { profileAssignments = []; globalUserAccess = null; return; }
    const result = await api<{ assignments: ProfileAssignment[] }>(
      `/api/enterprise/security-profiles/${encodeURIComponent(selectedProfileId)}/assignments`,
    );
    profileAssignments = Array.isArray(result.assignments) ? result.assignments : [];
    const selectedProfile = profiles.find((profile) => profile.profile_id === selectedProfileId) ?? null;
    if (selectedProfile?.scope === "global") {
      const globalAssignments = profileAssignments.filter((assignment) => !assignment.obs_id);
      if (!globalAssignments.some((assignment) => assignment.user_id === selectedGlobalAccessUserId)) {
        selectedGlobalAccessUserId = globalAssignments[0]?.user_id ?? "";
      }
      await loadGlobalUserAccess();
    } else {
      selectedGlobalAccessUserId = "";
      globalUserAccess = null;
    }
  };

  const loadProfiles = async () => {
    const result = await api<{ profiles: SecurityProfile[]; privilege_catalogs: PrivilegeCatalogs }>(
      "/api/enterprise/security-profiles",
    );
    profiles = Array.isArray(result.profiles) ? result.profiles : [];
    privilegeCatalogs = result.privilege_catalogs ?? { global: [], project: [] };
    if (!profiles.some((profile) => profile.profile_id === selectedProfileId)) {
      selectedProfileId = profiles[0]?.profile_id ?? "";
    }
    await loadProfileAssignments();
    canManageSecurityProfiles = true;
  };

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
    const ownerCandidates = memberships.filter((item) => item.status === "active" && item.user_id !== selected?.owner_user_id);
    const ownerOptions = ownerCandidates.map((item) => {
      const account = accounts.find((candidate) => candidate.user_id === item.user_id);
      const label = account ? (account.display_name || account.email) + " · " + account.email : item.user_id;
      return `<option value="${escapeHtml(item.user_id)}" data-revision="${item.revision}">${escapeHtml(label)}</option>`;
    }).join("");
    const selectedProfile = profiles.find((profile) => profile.profile_id === selectedProfileId) ?? null;
    const selectedProfileIsBuiltIn = selectedProfile !== null && [
      "p6-admin-superuser", "p6-no-global-privileges", "p6-project-superuser", "p6-default-project-readonly",
    ].includes(selectedProfile.profile_id);
    const profileOptions = profiles.map((profile) =>
      `<option value="${escapeHtml(profile.profile_id)}" ${profile.profile_id === selectedProfileId ? "selected" : ""}>${escapeHtml(profile.name)} · ${escapeHtml(profile.scope)}${profile.is_default ? " · " + escapeHtml(t.profileDefault) : ""}</option>`
    ).join("");
    const profileCatalog = selectedProfile ? privilegeCatalogs[selectedProfile.scope] : [];
    const privilegeOptions = profileCatalog.map((privilege) =>
      `<option value="${escapeHtml(privilege)}" ${selectedProfile?.privileges.includes(privilege) ? "selected" : ""}>${escapeHtml(privilege)}</option>`
    ).join("");
    const profileAssignmentRows = profileAssignments.map((assignment) => `<tr>
      <td><strong>${escapeHtml(assignment.display_name || assignment.email)}</strong><small>${escapeHtml(assignment.email)} · ${escapeHtml(assignment.user_id)}</small></td>
      <td>${escapeHtml(assignment.obs_id || "—")}</td><td>${assignment.revision}</td>
      <td>${selectedProfile?.scope === "project" && canAdminAccounts ? `<button class="cubi-oa-button cubi-oa-danger" type="button" data-profile-unassign="${escapeHtml(assignment.user_id)}" data-obs="${escapeHtml(assignment.obs_id)}" data-revision="${assignment.revision}">${t.removeAssignment}</button>` : "—"}</td>
    </tr>`).join("");
    const activeAccountOptions = accounts.filter((account) => account.active).map((account) =>
      `<option value="${escapeHtml(account.user_id)}">${escapeHtml(account.display_name || account.email)} · ${escapeHtml(account.email)}</option>`
    ).join("");
    const globalAssignmentOptions = profileAssignments.filter((assignment) => !assignment.obs_id).map((assignment) =>
      `<option value="${escapeHtml(assignment.user_id)}" ${assignment.user_id === selectedGlobalAccessUserId ? "selected" : ""}>${escapeHtml(assignment.display_name || assignment.email)} · ${escapeHtml(assignment.email)}</option>`
    ).join("");
    const moduleLabels: Record<string, string> = locale === "fa" ? {
      projects: "پروژه‌ها", portfolios: "پورتفولیوها", resources: "منابع", contributor: "همکار",
      enterprise_reports: "گزارش‌های سازمانی", integration_api: "رابط یکپارچه‌سازی",
      p6_analytics: "تحلیل‌ها", p6_professional: "مهندسی دسکتاپ", team_member: "عضو تیم",
      timesheet: "کاربرگ زمان", visualizer: "تحلیل بصری", web_services: "خدمات یکپارچه‌سازی",
    } : {
      projects: "Projects", portfolios: "Portfolios", resources: "Resources", contributor: "Contributor",
      enterprise_reports: "Enterprise Reports", integration_api: "Integration API",
      p6_analytics: "Analytics", p6_professional: "Desktop Engineering", team_member: "Team Member",
      timesheet: "Timesheet", visualizer: "Visual Analysis", web_services: "Integration Services",
    };
    const moduleOptions = Object.entries(moduleLabels).map(([value, label]) =>
      `<label class="cubi-oa-module-option"><input type="checkbox" name="module_access" value="${value}" ${globalUserAccess?.module_access.includes(value) ? "checked" : ""}> <span>${escapeHtml(label)}</span></label>`
    ).join("");
    const selectedResourceAccess = globalUserAccess?.resource_access_mode ?? "none";
    const projectUserOptions = accounts.filter((account) => account.active).map((account) =>
      `<option value="${escapeHtml(account.user_id)}" ${account.user_id === selectedProjectUserId ? "selected" : ""}>${escapeHtml(account.display_name || account.email)} · ${escapeHtml(account.email)}</option>`
    ).join("");
    const obsNodeById = new Map<string, OBSNode>();
    obsNodes.forEach((node) => obsNodeById.set(node.obs_id, node));
    const obsDepth = (node: OBSNode) => {
      let depth = 0;
      let parentId = node.parent_obs_id;
      const visited = new Set([node.obs_id]);
      while (parentId && depth < 16 && !visited.has(parentId)) {
        visited.add(parentId);
        depth += 1;
        parentId = obsNodeById.get(parentId)?.parent_obs_id ?? null;
      }
      return depth;
    };
    const obsOptions = obsNodes.map((node) => {
      const prefix = "\u00a0\u00a0".repeat(obsDepth(node)) + (node.parent_obs_id ? "↳ " : "");
      const label = [node.code, node.name].filter(Boolean).join(" · ") || node.obs_id;
      return `<option value="${escapeHtml(node.obs_id)}" ${node.obs_id === selectedProjectObsId ? "selected" : ""}>${escapeHtml(prefix + label)}</option>`;
    }).join("");
    const selectedProjectAssignment = userProjectAssignments.find((item) => item.obs_id === selectedProjectObsId) ?? null;
    const currentProjectAssignmentRows = userProjectAssignments.map((item) => `<tr>
      <td>${escapeHtml(item.obs_id)}</td><td>${escapeHtml(item.profile_name)}</td><td>${item.revision}</td>
    </tr>`).join("");
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
        .cubi-oa-field input,.cubi-oa-field select,.cubi-oa-field textarea{width:100%;min-height:38px;border:1px solid #ccd7e3;border-radius:7px;padding:8px;background:#fff;color:#172b43}
        .cubi-oa-form{border-top:1px solid #e6ebf1;margin-top:16px;padding-top:14px}.cubi-oa-tablewrap{overflow:auto}
        .cubi-oa-actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
        .cubi-oa-module-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;padding:10px;border:1px solid #e1e8ef;border-radius:8px}
        .cubi-oa-module-option{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:#f8fafc;font-weight:500!important}
        .cubi-oa-module-option input{width:16px;min-height:16px;margin:0}
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
              ${canManage ? `<form class="cubi-oa-form" id="cubi-oa-transfer">
                <h2>${t.transferOwner}</h2>
                <div class="cubi-oa-field"><label for="cubi-oa-new-owner">${t.newOwner}</label><select id="cubi-oa-new-owner" name="new_owner_user_id" required><option value="">${t.selectAccount}</option>${ownerOptions}</select></div>
                <button class="cubi-oa-button" type="submit" ${busy || !ownerCandidates.length ? "disabled" : ""}>${t.transferOwner}</button>
              </form>` : ""}
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
        ${canManageSecurityProfiles ? `<section class="cubi-oa-card" style="margin-top:18px">
          <h2>${t.securityProfiles}</h2><p class="cubi-oa-note">${t.profileHelp}</p>
          <form class="cubi-oa-form" id="cubi-oa-profile-create">
            <div class="cubi-oa-field"><label for="cubi-oa-profile-id">${t.profileId}</label><input id="cubi-oa-profile-id" name="profile_id" maxlength="100" required></div>
            <div class="cubi-oa-field"><label for="cubi-oa-profile-name">${t.profileName}</label><input id="cubi-oa-profile-name" name="name" maxlength="120" required></div>
            <div class="cubi-oa-field"><label for="cubi-oa-profile-description">${t.profileDescription}</label><textarea id="cubi-oa-profile-description" name="description" maxlength="2000" rows="3"></textarea></div>
            <div class="cubi-oa-field"><label for="cubi-oa-profile-scope">${t.profileScope}</label><select id="cubi-oa-profile-scope" name="scope"><option value="global">${t.globalProfile}</option><option value="project">${t.projectProfile}</option></select></div>
            <button class="cubi-oa-button cubi-oa-primary" type="submit" ${busy ? "disabled" : ""}>${t.createProfile}</button>
          </form>
          ${profiles.length ? `<div class="cubi-oa-field"><label for="cubi-oa-profile-selected">${t.selectProfile}</label>
            <select id="cubi-oa-profile-selected">${profileOptions}</select></div>
            <p><strong>${escapeHtml(selectedProfile?.name ?? "")}</strong> · ${selectedProfile?.active ? t.profileActive : t.profileInactive}${selectedProfile?.is_default ? " · " + escapeHtml(t.profileDefault) : ""} · Revision ${selectedProfile?.revision ?? 0}</p>
            <p>${escapeHtml(selectedProfile?.description ?? "")}</p>
            ${selectedProfileIsBuiltIn ? "" : `<form class="cubi-oa-form" id="cubi-oa-profile-details">
              <div class="cubi-oa-field"><label for="cubi-oa-profile-edit-name">${t.profileName}</label><input id="cubi-oa-profile-edit-name" name="name" maxlength="120" required value="${escapeHtml(selectedProfile?.name ?? "")}"></div>
              <div class="cubi-oa-field"><label for="cubi-oa-profile-edit-description">${t.profileDescription}</label><textarea id="cubi-oa-profile-edit-description" name="description" maxlength="2000" rows="3">${escapeHtml(selectedProfile?.description ?? "")}</textarea></div>
              <button class="cubi-oa-button" type="submit" ${busy ? "disabled" : ""}>${t.saveProfileDetails}</button>
            </form>`}
            <div class="cubi-oa-actions">
              ${selectedProfile && (!selectedProfileIsBuiltIn
                || selectedProfile.profile_id === "p6-no-global-privileges"
                || selectedProfile.profile_id === "p6-default-project-readonly")
                && !selectedProfile.is_default
                ? `<button class="cubi-oa-button" type="button" data-profile-default="true" data-default="false" ${busy || selectedProfile.active !== true ? "disabled" : ""}>${t.profileSetDefault}</button>`
                : ""}
              ${!selectedProfileIsBuiltIn ? `<button class="cubi-oa-button" type="button" data-profile-duplicate="true" ${busy ? "disabled" : ""}>${t.profileDuplicate}</button>
              <button class="cubi-oa-button cubi-oa-danger" type="button" data-profile-delete="true" ${busy || profileAssignments.length > 0 ? "disabled" : ""}>${t.profileDelete}</button>` : ""}
              <button class="cubi-oa-button" type="button" data-profile-status="true" data-active="${selectedProfile?.active === true}" ${busy || selectedProfileIsBuiltIn ? "disabled" : ""}>${selectedProfile?.active ? t.profileDeactivate : t.profileActivate}</button>
            </div>
            <form class="cubi-oa-form" id="cubi-oa-profile-privileges">
              <div class="cubi-oa-field"><label for="cubi-oa-profile-privileges-list">${t.privileges} (${selectedProfile?.scope === "global" ? t.globalProfile : t.projectProfile})</label>
                <select id="cubi-oa-profile-privileges-list" name="privileges" multiple size="12" ${selectedProfileIsBuiltIn ? "disabled" : ""}>${privilegeOptions}</select></div>
              <button class="cubi-oa-button cubi-oa-primary" type="submit" ${busy || selectedProfileIsBuiltIn ? "disabled" : ""}>${t.savePrivileges}</button>
            </form>
            <h3>${t.assignedUsers}</h3>
            <div class="cubi-oa-tablewrap"><table><thead><tr><th>${t.user}</th><th>${t.obsId}</th><th>Revision</th><th></th></tr></thead>
              <tbody>${profileAssignmentRows || `<tr><td colspan="4">${t.noEligible}</td></tr>`}</tbody></table></div>
            ${selectedProfile?.scope === "global" && canAdminAccounts && globalAssignmentOptions ? `<form class="cubi-oa-form" id="cubi-oa-global-access">
              <h3>${t.globalAccessTitle}</h3>
              <div class="cubi-oa-field"><label for="cubi-oa-global-access-user">${t.selectGlobalUser}</label>
                <select id="cubi-oa-global-access-user" name="user_id">${globalAssignmentOptions}</select></div>
              <fieldset class="cubi-oa-field"><legend>${t.moduleAccess}</legend>
                <div class="cubi-oa-module-grid">${moduleOptions}</div></fieldset>
              <div class="cubi-oa-field"><label for="cubi-oa-resource-access">${t.resourceAccess}</label>
                <select id="cubi-oa-resource-access" name="resource_access_mode">
                  <option value="none" ${selectedResourceAccess === "none" ? "selected" : ""}>${t.noResources}</option>
                  <option value="all" ${selectedResourceAccess === "all" ? "selected" : ""}>${t.allResources}</option>
                  <option value="selected" disabled ${selectedResourceAccess === "selected" ? "selected" : ""}>${t.selectResources}</option>
                </select></div>
              <p class="cubi-oa-note">${t.resourceAccessNote}</p>
              <button class="cubi-oa-button cubi-oa-primary" type="submit" ${busy || !globalUserAccess ? "disabled" : ""}>${t.saveGlobalAccess}</button>
              <small>Revision ${globalUserAccess?.revision ?? "—"}</small>
            </form>` : ""}
            ${canAdminAccounts ? `<form class="cubi-oa-form" id="cubi-oa-profile-assign">
              <div class="cubi-oa-field"><label for="cubi-oa-profile-user">${t.user}</label><select id="cubi-oa-profile-user" name="user_id" required><option value="">${t.selectAccount}</option>${activeAccountOptions}</select></div>
              ${selectedProfile?.scope === "project" ? `<div class="cubi-oa-field"><label for="cubi-oa-profile-obs">${t.obsId}</label><select id="cubi-oa-profile-obs" name="obs_id" required><option value="">—</option>${obsOptions}</select></div>` : ""}
              <div class="cubi-oa-field"><label for="cubi-oa-profile-assignment-revision">${t.assignmentRevision}</label><input id="cubi-oa-profile-assignment-revision" name="expected_revision" type="number" min="1"></div>
              <button class="cubi-oa-button" type="submit" ${busy || !activeAccountOptions ? "disabled" : ""}>${t.assignProfile}</button>
            </form>` : `<p class="cubi-oa-note">${t.userAdminRequired}</p>`}
            ${selectedProfile?.scope === "project" && canAdminAccounts ? `<form class="cubi-oa-form" id="cubi-oa-project-default-assign">
              <h3>${t.assignDefaultProjectTitle}</h3>
              <div class="cubi-oa-field"><label for="cubi-oa-project-user">${t.user}</label>
                <select id="cubi-oa-project-user" name="user_id">${projectUserOptions}</select></div>
              <div class="cubi-oa-field"><label for="cubi-oa-project-obs">${t.obsSelect}</label>
                <select id="cubi-oa-project-obs" name="obs_id" required>
                  <option value="">—</option>${obsOptions}
                </select></div>
              <div class="cubi-oa-field"><label for="cubi-oa-project-revision">${t.obsAssignmentRevision}</label>
                <input id="cubi-oa-project-revision" name="expected_revision" type="number" min="1"
                  value="${selectedProjectAssignment?.revision ?? ""}"></div>
              <button class="cubi-oa-button" type="submit" ${busy || !obsNodes.length || !selectedProjectUserId ? "disabled" : ""}>${t.assignDefaultProject}</button>
              <h4>${t.currentObsAssignments}</h4>
              <div class="cubi-oa-tablewrap"><table><thead><tr><th>${t.obsSelect}</th><th>${t.profileName}</th><th>Revision</th></tr></thead>
                <tbody>${currentProjectAssignmentRows || `<tr><td colspan="3">${t.noObsAssignments}</td></tr>`}</tbody></table></div>
              ${!obsNodes.length ? `<p class="cubi-oa-note">${t.noObsNodes}</p>` : ""}
            </form>` : ""}
          ` : `<div class="cubi-oa-muted">${t.noProfiles}</div>`}
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
    container.querySelector<HTMLFormElement>("#cubi-oa-transfer")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const targetUserId = String(form.get("new_owner_user_id") ?? "");
      const target = ownerCandidates.find((item) => item.user_id === targetUserId);
      if (!target || !selected) return;
      if (!window.confirm(t.confirmTransfer)) return;
      void run(async () => {
        await api(`/api/enterprise/teams/${encodeURIComponent(selectedTeamId)}/owner`, "PUT", {
          contract_version: "cubi-enterprise-team-owner-transfer.v1",
          new_owner_user_id: targetUserId,
          expected_team_revision: selected.revision,
          expected_membership_revision: target.revision,
        });
        notice = t.transferred; await load(true);
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
    container.querySelector<HTMLFormElement>("#cubi-oa-profile-create")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const profileId = String(form.get("profile_id") ?? "").trim();
      const name = String(form.get("name") ?? "").trim();
      const scope = String(form.get("scope") ?? "");
      const description = String(form.get("description") ?? "");
      if (!profileId || !name || (scope !== "global" && scope !== "project")) return;
      void run(async () => {
        await api("/api/enterprise/security-profiles", "POST", {
          contract_version: "cubi-p6-security-profile.v1", profile_id: profileId, name, scope, description,
        });
        notice = t.profileCreated; selectedProfileId = profileId; await loadProfiles();
      });
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-profile-details")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!selectedProfile) return;
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const name = String(form.get("name") ?? "").trim();
      const description = String(form.get("description") ?? "");
      if (!name) return;
      void run(async () => {
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/details`, "PATCH", {
          contract_version: "cubi-p6-security-profile-details.v1",
          name, description, expected_revision: selectedProfile.revision,
        });
        notice = t.profileDetailsSaved; await loadProfiles();
      });
    });
    container.querySelector<HTMLButtonElement>("[data-profile-default]")?.addEventListener("click", (event) => {
      if (!selectedProfile) return;
      const button = event.currentTarget as HTMLButtonElement;
      const isDefault = button.dataset.default === "true";
      void run(async () => {
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/default`, "PATCH", {
          contract_version: "cubi-p6-security-profile-default.v1",
          is_default: !isDefault, expected_revision: selectedProfile.revision,
        });
        notice = t.profileDefaultSaved; await loadProfiles();
      });
    });
    container.querySelector<HTMLButtonElement>("[data-profile-duplicate]")?.addEventListener("click", () => {
      if (!selectedProfile) return;
      const newProfileId = window.prompt(t.profileDuplicateId, `${selectedProfile.profile_id}-copy`)?.trim();
      const name = window.prompt(t.profileDuplicateName, `${selectedProfile.name} copy`)?.trim();
      if (!newProfileId || !name) return;
      void run(async () => {
        const result = await api<{ profile: SecurityProfile }>(
          `/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/duplicate`, "POST", {
            contract_version: "cubi-p6-security-profile-duplicate.v1", profile_id: newProfileId, name,
          },
        );
        selectedProfileId = result.profile.profile_id;
        notice = t.profileDuplicated; await loadProfiles();
      });
    });
    container.querySelector<HTMLButtonElement>("[data-profile-delete]")?.addEventListener("click", () => {
      if (!selectedProfile || profileAssignments.length > 0 || !window.confirm(t.profileDeleteConfirm)) return;
      void run(async () => {
        const query = new URLSearchParams({ expected_revision: String(selectedProfile.revision) });
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}?${query.toString()}`, "DELETE");
        selectedProfileId = ""; notice = t.profileDeleted; await loadProfiles();
      });
    });
    container.querySelector<HTMLSelectElement>("#cubi-oa-profile-selected")?.addEventListener("change", (event) => {
      selectedProfileId = (event.currentTarget as HTMLSelectElement).value;
      selectedGlobalAccessUserId = "";
      void run(async () => { await loadProfileAssignments(); });
    });
    container.querySelector<HTMLSelectElement>("#cubi-oa-global-access-user")?.addEventListener("change", (event) => {
      selectedGlobalAccessUserId = (event.currentTarget as HTMLSelectElement).value;
      void run(async () => { await loadGlobalUserAccess(); });
    });
    container.querySelectorAll<HTMLInputElement>('input[name="module_access"]').forEach((input) => input.addEventListener("change", () => {
      if (input.value === "contributor" && input.checked) {
        container.querySelectorAll<HTMLInputElement>('input[name="module_access"]').forEach((other) => {
          if (other !== input) other.checked = false;
        });
      } else if (input.checked) {
        const contributor = container.querySelector<HTMLInputElement>('input[name="module_access"][value="contributor"]');
        if (contributor) contributor.checked = false;
      }
    }));
    container.querySelector<HTMLFormElement>("#cubi-oa-global-access")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!globalUserAccess || !selectedGlobalAccessUserId) return;
      const modules = Array.from(container.querySelectorAll<HTMLInputElement>('input[name="module_access"]:checked'))
        .map((input) => input.value);
      const resourceMode = String(new FormData(event.currentTarget as HTMLFormElement).get("resource_access_mode") ?? "none");
      void run(async () => {
        await api(`/api/enterprise/users/${encodeURIComponent(selectedGlobalAccessUserId)}/global-access`, "PATCH", {
          contract_version: "cubi-p6-user-global-access.v1",
          module_access: modules, resource_access_mode: resourceMode,
          resource_root_ids: [], expected_revision: globalUserAccess.revision,
        });
        notice = t.globalAccessSaved;
        await loadProfileAssignments();
      });
    });
    container.querySelector<HTMLButtonElement>("[data-profile-status]")?.addEventListener("click", (event) => {
      const button = event.currentTarget as HTMLButtonElement;
      if (!selectedProfile) return;
      const active = button.dataset.active === "true";
      void run(async () => {
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/status`, "PATCH", {
          contract_version: "cubi-p6-security-profile-status.v1",
          active: !active, expected_revision: selectedProfile.revision,
        });
        notice = t.profileStatusSaved; await loadProfiles();
      });
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-profile-privileges")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!selectedProfile) return;
      const select = container.querySelector<HTMLSelectElement>("#cubi-oa-profile-privileges-list");
      const privileges = select ? Array.from(select.selectedOptions).map((option) => option.value) : [];
      void run(async () => {
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/privileges`, "PATCH", {
          contract_version: "cubi-p6-security-profile-privileges.v1",
          expected_revision: selectedProfile.revision, privileges,
        });
        notice = t.profileSaved; await loadProfiles();
      });
    });
    container.querySelector<HTMLSelectElement>("#cubi-oa-project-user")?.addEventListener("change", (event) => {
      selectedProjectUserId = (event.currentTarget as HTMLSelectElement).value;
      selectedProjectObsId = "";
      void run(async () => { await loadUserProjectAssignments(); });
    });
    container.querySelector<HTMLSelectElement>("#cubi-oa-project-obs")?.addEventListener("change", (event) => {
      selectedProjectObsId = (event.currentTarget as HTMLSelectElement).value;
      render();
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-project-default-assign")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!selectedProjectUserId || !selectedProjectObsId) return;
      const rawRevision = String(new FormData(event.currentTarget as HTMLFormElement).get("expected_revision") ?? "").trim();
      const expectedRevision = rawRevision ? Number(rawRevision) : undefined;
      if (expectedRevision !== undefined && (!Number.isInteger(expectedRevision) || expectedRevision < 1)) return;
      void run(async () => {
        const path = "/api/enterprise/users/" + encodeURIComponent(selectedProjectUserId) + "/project-access";
        await api(path, "PUT", {
          contract_version: "cubi-p6-user-project-access.v1",
          obs_id: selectedProjectObsId,
          ...(expectedRevision === undefined ? {} : { expected_revision: expectedRevision }),
        });
        const defaultProject = profiles.find((profile) => profile.scope === "project" && profile.is_default);
        if (defaultProject) selectedProfileId = defaultProject.profile_id;
        notice = t.defaultProjectAssigned;
        await loadProfiles();
        await loadUserProjectAssignments();
      });
    });
    container.querySelector<HTMLFormElement>("#cubi-oa-profile-assign")?.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!selectedProfile) return;
      const form = new FormData(event.currentTarget as HTMLFormElement);
      const userId = String(form.get("user_id") ?? "");
      const obsId = String(form.get("obs_id") ?? "").trim();
      const rawRevision = String(form.get("expected_revision") ?? "").trim();
      const expectedRevision = rawRevision ? Number(rawRevision) : undefined;
      if (!userId || (selectedProfile.scope === "project" && !obsId)
          || (expectedRevision !== undefined && (!Number.isInteger(expectedRevision) || expectedRevision < 1))) return;
      void run(async () => {
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/assignments`, "PUT", {
          contract_version: "cubi-p6-security-profile-assignment.v1",
          user_id: userId, obs_id: obsId, ...(expectedRevision === undefined ? {} : { expected_revision: expectedRevision }),
        });
        notice = t.profileAssigned; await loadProfileAssignments();
      });
    });
    container.querySelectorAll<HTMLButtonElement>("[data-profile-unassign]").forEach((button) => button.addEventListener("click", () => {
      if (!selectedProfile) return;
      const userId = button.dataset.profileUnassign ?? "";
      const obsId = button.dataset.obs ?? "";
      const revision = Number(button.dataset.revision);
      if (!userId || !Number.isInteger(revision) || !window.confirm(t.removeAssignment + "?")) return;
      void run(async () => {
        const query = new URLSearchParams({ obs_id: obsId, expected_revision: String(revision) });
        await api(`/api/enterprise/security-profiles/${encodeURIComponent(selectedProfile.profile_id)}/assignments/${encodeURIComponent(userId)}?${query.toString()}`, "DELETE");
        notice = t.removeAssignment; await loadProfileAssignments();
      });
    }));
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
        P6_GLOBAL_PRIVILEGE_REQUIRED: t.privilegeRequired,
        SECURITY_PROFILE_ASSIGNED_CANNOT_DELETE: t.profileDeleteAssigned,
        SECURITY_PROFILE_CONTRIBUTOR_MODULE_EXCLUSIVE: locale === "fa"
          ? "گزینه همکار را نمی‌توان همراه با ماژول‌های دیگر فعال کرد."
          : "Contributor access cannot be combined with other modules.",
        SECURITY_PROFILE_GLOBAL_RESOURCE_HIERARCHY_REQUIRED: locale === "fa"
          ? "برای انتخاب منابع، ابتدا باید سلسله‌مراتب سراسری منابع پیکربندی شود."
          : "Selected resource access requires the enterprise-wide resource hierarchy.",
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
        const obsResult = await api<unknown>("/api/enterprise/obs");
        if (!isRecord(obsResult) || obsResult.contract_version !== "cubi-p6-obs-options.v1"
            || !Array.isArray(obsResult.obs_nodes)) throw new Error("INVALID_OBS_OPTIONS");
        obsNodes = obsResult.obs_nodes as OBSNode[];
        if (!accounts.some((account) => account.user_id === selectedProjectUserId && account.active)) {
          selectedProjectUserId = accounts.find((account) => account.active)?.user_id ?? "";
        }
        await loadUserProjectAssignments();
      } catch (error) {
        accounts = []; obsNodes = []; userProjectAssignments = []; canAdminAccounts = false;
        if (error instanceof Error && error.message === "SESSION_REQUIRED") throw error;
      }
      try {
        await loadProfiles();
      } catch (error) {
        profiles = []; profileAssignments = []; canManageSecurityProfiles = false;
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
