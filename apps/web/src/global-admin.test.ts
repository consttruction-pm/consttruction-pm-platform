import assert from "node:assert/strict";
import test from "node:test";

import {
  ADMIN_CONTRACT_VERSION,
  ADMIN_ROLE_KEYS,
  GlobalAdminClient,
  adminLabels,
  adminLocales,
  buildCreateUserInput,
  buildUserPatch,
  dashboardSummary,
  isGlobalAdmin,
  renderCreateUserForm,
  renderUserRows,
  roleLabel,
  sectionLabel,
  type AdminDashboard,
  type AdminUser,
  type CreateUserForm,
} from "./global-admin.js";

const REQUIRED_LOCALES = ["fa", "en", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"];
const REQUIRED_ROLES = [
  "global_admin",
  "organization_admin",
  "enterprise_admin",
  "enterprise_user",
  "enterprise_viewer",
  "engineering_admin",
  "engineering_planner",
  "engineering_user",
  "engineering_viewer",
  "guest",
  "test_user",
] as const;

test("the ten approved locales are translated", () => {
  assert.deepEqual([...adminLocales()].sort(), [...REQUIRED_LOCALES].sort());
  for (const locale of REQUIRED_LOCALES) {
    const labels = adminLabels(locale);
    assert.ok(labels.title.length > 3, locale);
    for (const role of REQUIRED_ROLES) {
      assert.ok(labels.roles[role].length > 1, `${locale}:${role}`);
    }
    for (const section of ["dashboard", "users", "roles", "test", "audit"] as const) {
      assert.ok(labels.sections[section].length > 1, `${locale}:${section}`);
    }
  }
});

test("tr-TR resolves to the Turkish pack", () => {
  assert.equal(adminLabels("tr-TR").title, "CUBI Genel Yönetim");
  assert.equal(roleLabel("tr-TR", "global_admin"), "Genel Yönetici");
  assert.equal(sectionLabel("fa-IR", "audit"), "گزارش عملیات");
});

test("unknown locales fall back to English without throwing", () => {
  assert.equal(adminLabels("xx").title, "CUBI Global Administration");
});

test("only the global_admin role opens the surface", () => {
  assert.equal(isGlobalAdmin(["global_admin"]), true);
  assert.equal(isGlobalAdmin(["project_admin"]), false);
  assert.equal(isGlobalAdmin([]), false);
  assert.equal(isGlobalAdmin(null), false);
});

const DASHBOARD: AdminDashboard = {
  contract_version: ADMIN_CONTRACT_VERSION,
  users_total: 12,
  users_active: 9,
  users_disabled: 2,
  users_test: 4,
  tenants: 3,
  users_logged_in_7d: 5,
  active_sessions: 7,
  roles_defined: 11,
  database: "connected",
  recent_actions: [
    {
      audit_id: 1,
      actor_user_id: "usr-1",
      action: "user.create",
      target_user_id: "usr-2",
      target_tenant_id: "test-a",
      reason: "scenario",
      occurred_at: "2026-11-20T10:00:00+00:00",
    },
  ],
  viewer: { user_id: "usr-1", tenant_id: "platform-owner" },
};

test("dashboard summary is locale-aware", () => {
  const fa = dashboardSummary("fa", DASHBOARD);
  assert.equal(fa[0].value, "9 / 12");
  assert.equal(fa[1].value, "4");
  assert.equal(fa[2].value, "11");
  const en = dashboardSummary("en", DASHBOARD);
  assert.equal(en[0].label, "Users");
});

const USER: AdminUser = {
  user_id: "usr-2",
  tenant_id: "test-a",
  email: "viewer@cubisite.test",
  display_name: "Test <Viewer>",
  roles: ["viewer"],
  role_keys: ["enterprise_viewer"],
  active: true,
  locked: false,
  expires_at: null,
  must_change_password: true,
  is_test_user: true,
  locale: "fa",
  created_at: "2026-11-20T09:00:00+00:00",
  last_login_at: null,
  sessions: 1,
};

test("user rows escape markup and use translated role labels", () => {
  const html = renderUserRows("de", [USER]);
  assert.ok(html.includes("Test &lt;Viewer&gt;"));
  assert.ok(!html.includes("<Viewer>"));
  assert.ok(html.includes("Enterprise-Leser"));
  assert.ok(html.includes("test"));
});

test("empty search result renders the translated empty state", () => {
  assert.ok(renderUserRows("ja", []).includes("ユーザーを検索"));
});

test("read calls never carry a CSRF header", async () => {
  const seen: Record<string, string>[] = [];
  const client = new GlobalAdminClient("https://cubi.example", (async (_input: unknown, init?: RequestInit) => {
    seen.push((init?.headers ?? {}) as Record<string, string>);
    return new Response(JSON.stringify(DASHBOARD), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch);
  const result = await client.dashboard();
  assert.equal(result.ok, true);
  assert.equal(seen[0]["X-CSRF-Token"], undefined);
});

test("errors surface the server code, not a generic failure", async () => {
  const client = new GlobalAdminClient("https://cubi.example", (async () =>
    new Response(JSON.stringify({ code: "GLOBAL_ADMIN_REQUIRED" }), {
      status: 403,
      headers: { "Content-Type": "application/json" },
    })) as typeof fetch);
  const result = await client.dashboard();
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.equal(result.status, 403);
    assert.equal(result.code, "GLOBAL_ADMIN_REQUIRED");
  }
});

const FORM: CreateUserForm = {
  email: "  Planner@CubiSite.Test ",
  displayName: "  Hadi Planner  ",
  tenantId: "Test-Alpha",
  locale: "tr-TR",
  roles: ["engineering_planner"],
  isTestUser: true,
  expiresAt: "2026-12-01T10:00",
  reason: "  onboarding  ",
};

test("create-user input is normalised and carries the test expiry", () => {
  const input = buildCreateUserInput(FORM);
  assert.equal(input.email, "planner@cubisite.test");
  assert.equal(input.display_name, "Hadi Planner");
  assert.equal(input.tenant_id, "test-alpha");
  assert.equal(input.locale, "tr-TR");
  assert.deepEqual(input.roles, ["engineering_planner"]);
  assert.equal(input.is_test_user, true);
  assert.equal(input.expires_at, new Date("2026-12-01T10:00").toISOString());
  assert.equal(input.reason, "onboarding");
});

test("non-test users never carry an expiry", () => {
  const input = buildCreateUserInput({ ...FORM, tenantId: "org-acme", isTestUser: false, expiresAt: "" });
  assert.equal(input.is_test_user, false);
  assert.equal(input.expires_at, null);
});

test("create-user validation rejects bad input with stable codes", () => {
  const cases: [Partial<CreateUserForm>, string][] = [
    [{ email: "not-an-email" }, "EMAIL_INVALID"],
    [{ displayName: "   " }, "DISPLAY_NAME_INVALID"],
    [{ tenantId: "-bad" }, "TENANT_INVALID"],
    [{ roles: [] }, "ROLES_REQUIRED"],
    [{ locale: "english" }, "LOCALE_INVALID"],
    [{ tenantId: "org-acme", isTestUser: true, expiresAt: "" }, "TEST_USER_REQUIRES_TEST_TENANT"],
    [{ expiresAt: "" }, "TEST_USER_REQUIRES_EXPIRY"],
  ];
  for (const [override, code] of cases) {
    assert.throws(() => buildCreateUserInput({ ...FORM, ...override }), new RegExp(code));
  }
});

test("an editor patch only sends the changed fields", () => {
  assert.deepEqual(buildUserPatch({ roles: ["global_admin"], confirmPassword: "secret" }), {
    roles: ["global_admin"],
    confirm_password: "secret",
  });
  assert.deepEqual(buildUserPatch({ locked: true }), { locked: true });
  assert.throws(() => buildUserPatch({}), /NO_UPDATES/);
  assert.throws(() => buildUserPatch({ roles: [] }), /ROLES_REQUIRED/);
  assert.throws(() => buildUserPatch({ locale: "nope" }), /LOCALE_INVALID/);
  assert.throws(() => buildUserPatch({ displayName: " " }), /DISPLAY_NAME_INVALID/);
});

test("the create form offers every role and the active locale", () => {
  const html = renderCreateUserForm("tr");
  for (const role of ADMIN_ROLE_KEYS) assert.ok(html.includes(`value="${role}"`), role);
  assert.ok(html.includes('value="tr"'));
  assert.ok(html.includes("data-admin-action=\"create-user\""));
  assert.ok(html.includes("Genel Yönetici"));
});

test("user rows render the working action buttons for editing", () => {
  const html = renderUserRows("en", [USER, { ...USER, user_id: "usr-3", locked: true, active: false }]);
  for (const action of ["edit-roles", "lock", "unlock", "disable", "enable", "reset-password", "revoke-sessions"]) {
    assert.ok(html.includes(`data-admin-action="${action}"`), action);
  }
  assert.ok(html.includes('data-user-id="usr-2"'));
});

test("editing labels exist in every approved locale", () => {
  for (const locale of REQUIRED_LOCALES) {
    const labels = adminLabels(locale);
    for (const key of ["edit", "save", "cancel", "active", "confirmPassword"] as const) {
      assert.ok(labels[key].length > 1, `${locale}:${key}`);
    }
  }
  assert.equal(adminLabels("fa").save, "ذخیره");
  assert.equal(adminLabels("tr-TR").cancel, "İptal");
});

test("every user row carries a real, prefilled inline editor form", () => {
  const html = renderUserRows("fa", [USER]);
  assert.ok(html.includes('data-editor-for="usr-2" hidden'));
  assert.ok(html.includes('<form class="cp-admin-edit-form" data-user-id="usr-2">'));
  assert.ok(html.includes('name="display_name"'));
  assert.ok(html.includes('value="Test &lt;Viewer&gt;"'));
  assert.ok(html.includes('name="role" value="enterprise_viewer" checked'));
  assert.ok(!html.includes('name="role" value="global_admin" checked'));
  assert.ok(html.includes('name="active" checked'));
  assert.ok(html.includes('name="locked"'));
  assert.ok(html.includes('name="confirm_password" type="password"'));
  assert.ok(html.includes('data-admin-action="save-edit" data-user-id="usr-2"'));
  assert.ok(html.includes('data-admin-action="cancel-edit" data-user-id="usr-2"'));
  assert.ok(html.includes("ذخیره"));
  const lockedUser = renderUserRows("en", [{ ...USER, active: false, locked: true }]);
  assert.ok(lockedUser.includes('name="active" />'));
  assert.ok(lockedUser.includes('name="locked" checked'));
});
