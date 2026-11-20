/**
 * CUBI Global Administration client.
 *
 * A system-level surface for the product owner. The server is the authority:
 * every call goes to `/api/admin/*`, which resolves the session and requires
 * the `global_admin` token. This module only renders what the server returns.
 */

import { readCookieValue, withCsrfHeader } from "./csrf.js";

export const ADMIN_CONTRACT_VERSION = "cubi-global-administration.v1";
export const ADMIN_PATH = "/admin";

export type AdminLocale = "fa" | "en" | "de" | "zh" | "ar" | "fr" | "ja" | "ko" | "ru" | "tr";

export type AdminRoleKey =
  | "global_admin"
  | "organization_admin"
  | "enterprise_admin"
  | "enterprise_user"
  | "enterprise_viewer"
  | "engineering_admin"
  | "engineering_planner"
  | "engineering_user"
  | "engineering_viewer"
  | "guest"
  | "test_user";

export type AdminSectionKey = "dashboard" | "users" | "roles" | "test" | "audit";

export type AdminUser = {
  user_id: string;
  tenant_id: string;
  email: string;
  display_name: string;
  roles: string[];
  role_keys: AdminRoleKey[];
  active: boolean;
  locked: boolean;
  expires_at: string | null;
  must_change_password: boolean;
  is_test_user: boolean;
  locale: string;
  created_at: string | null;
  last_login_at: string | null;
  sessions: number;
};

export type AdminDashboard = {
  contract_version: string;
  users_total: number;
  users_active: number;
  users_disabled: number;
  users_test: number;
  tenants: number;
  users_logged_in_7d: number;
  active_sessions: number;
  roles_defined: number;
  database: string;
  recent_actions: AdminAuditEntry[];
  viewer: { user_id: string; tenant_id: string };
};

export type AdminAuditEntry = {
  audit_id: number;
  actor_user_id: string;
  action: string;
  target_user_id: string | null;
  target_tenant_id: string | null;
  reason: string;
  occurred_at: string | null;
};

type Labels = {
  title: string;
  sections: Record<AdminSectionKey, string>;
  roles: Record<AdminRoleKey, string>;
  search: string;
  createUser: string;
  testUser: string;
  resetPassword: string;
  revokeSessions: string;
  lock: string;
  unlock: string;
  disable: string;
  enable: string;
  forbidden: string;
  signedOut: string;
  temporaryPassword: string;
  copied: string;
};

const LABELS: Record<AdminLocale, Labels> = {
  en: {
    title: "CUBI Global Administration",
    sections: { dashboard: "Dashboard", users: "Users", roles: "Roles", test: "Test users", audit: "Audit log" },
    roles: {
      global_admin: "Global Admin",
      organization_admin: "Organization Admin",
      enterprise_admin: "Enterprise Admin",
      enterprise_user: "Enterprise User",
      enterprise_viewer: "Enterprise Viewer",
      engineering_admin: "Engineering Admin",
      engineering_planner: "Engineering Planner",
      engineering_user: "Engineering User",
      engineering_viewer: "Engineering Viewer",
      guest: "Guest / Read-only",
      test_user: "Test User",
    },
    search: "Search users",
    createUser: "Create user",
    testUser: "Create test user",
    resetPassword: "Reset password",
    revokeSessions: "Revoke sessions",
    lock: "Lock",
    unlock: "Unlock",
    disable: "Disable",
    enable: "Enable",
    forbidden: "This area requires the Global Admin role.",
    signedOut: "Your session has ended. Sign in again.",
    temporaryPassword: "Temporary password (shown once)",
    copied: "Copied",
  },
  fa: {
    title: "مدیریت کل CUBI",
    sections: { dashboard: "داشبورد", users: "کاربران", roles: "نقش‌ها", test: "کاربران آزمایشی", audit: "گزارش عملیات" },
    roles: {
      global_admin: "مدیر کل سامانه",
      organization_admin: "مدیر سازمان",
      enterprise_admin: "مدیر سازمانی",
      enterprise_user: "کاربر سازمانی",
      enterprise_viewer: "بازدیدکننده سازمانی",
      engineering_admin: "مدیر مهندسی",
      engineering_planner: "برنامه‌ریز مهندسی",
      engineering_user: "کاربر مهندسی",
      engineering_viewer: "بازدیدکننده مهندسی",
      guest: "مهمان / فقط خواندن",
      test_user: "کاربر آزمایشی",
    },
    search: "جست‌وجوی کاربران",
    createUser: "ایجاد کاربر",
    testUser: "ساخت کاربر آزمایشی",
    resetPassword: "بازنشانی رمز عبور",
    revokeSessions: "لغو نشست‌ها",
    lock: "قفل",
    unlock: "بازکردن قفل",
    disable: "غیرفعال",
    enable: "فعال",
    forbidden: "این بخش به نقش مدیر کل سامانه نیاز دارد.",
    signedOut: "نشست شما پایان یافت. دوباره وارد شوید.",
    temporaryPassword: "رمز موقت (فقط یک‌بار نمایش داده می‌شود)",
    copied: "کپی شد",
  },
  de: {
    title: "CUBI Globale Administration",
    sections: { dashboard: "Übersicht", users: "Benutzer", roles: "Rollen", test: "Testbenutzer", audit: "Prüfprotokoll" },
    roles: {
      global_admin: "Globaler Administrator",
      organization_admin: "Organisationsadministrator",
      enterprise_admin: "Enterprise-Administrator",
      enterprise_user: "Enterprise-Benutzer",
      enterprise_viewer: "Enterprise-Leser",
      engineering_admin: "Engineering-Administrator",
      engineering_planner: "Engineering-Planer",
      engineering_user: "Engineering-Benutzer",
      engineering_viewer: "Engineering-Leser",
      guest: "Gast / Nur Lesen",
      test_user: "Testbenutzer",
    },
    search: "Benutzer suchen",
    createUser: "Benutzer anlegen",
    testUser: "Testbenutzer anlegen",
    resetPassword: "Passwort zurücksetzen",
    revokeSessions: "Sitzungen beenden",
    lock: "Sperren",
    unlock: "Entsperren",
    disable: "Deaktivieren",
    enable: "Aktivieren",
    forbidden: "Dieser Bereich erfordert die Rolle Globaler Administrator.",
    signedOut: "Ihre Sitzung ist beendet. Bitte erneut anmelden.",
    temporaryPassword: "Temporäres Passwort (einmalig sichtbar)",
    copied: "Kopiert",
  },
  zh: {
    title: "CUBI 全局管理",
    sections: { dashboard: "仪表板", users: "用户", roles: "角色", test: "测试用户", audit: "审计日志" },
    roles: {
      global_admin: "全局管理员",
      organization_admin: "组织管理员",
      enterprise_admin: "企业管理员",
      enterprise_user: "企业用户",
      enterprise_viewer: "企业只读用户",
      engineering_admin: "工程管理员",
      engineering_planner: "工程计划员",
      engineering_user: "工程用户",
      engineering_viewer: "工程只读用户",
      guest: "访客 / 只读",
      test_user: "测试用户",
    },
    search: "搜索用户",
    createUser: "创建用户",
    testUser: "创建测试用户",
    resetPassword: "重置密码",
    revokeSessions: "撤销会话",
    lock: "锁定",
    unlock: "解锁",
    disable: "停用",
    enable: "启用",
    forbidden: "此区域需要全局管理员角色。",
    signedOut: "会话已结束，请重新登录。",
    temporaryPassword: "临时密码（仅显示一次）",
    copied: "已复制",
  },
  ar: {
    title: "إدارة CUBI العامة",
    sections: { dashboard: "لوحة المعلومات", users: "المستخدمون", roles: "الأدوار", test: "مستخدمون تجريبيون", audit: "سجل التدقيق" },
    roles: {
      global_admin: "مدير عام للنظام",
      organization_admin: "مدير المؤسسة",
      enterprise_admin: "مدير المؤسسة الكبرى",
      enterprise_user: "مستخدم المؤسسة",
      enterprise_viewer: "مطالع المؤسسة",
      engineering_admin: "مدير الهندسة",
      engineering_planner: "مخطط الهندسة",
      engineering_user: "مستخدم الهندسة",
      engineering_viewer: "مطالع الهندسة",
      guest: "ضيف / قراءة فقط",
      test_user: "مستخدم تجريبي",
    },
    search: "البحث عن المستخدمين",
    createUser: "إنشاء مستخدم",
    testUser: "إنشاء مستخدم تجريبي",
    resetPassword: "إعادة تعيين كلمة المرور",
    revokeSessions: "إلغاء الجلسات",
    lock: "قفل",
    unlock: "فتح القفل",
    disable: "تعطيل",
    enable: "تفعيل",
    forbidden: "يتطلب هذا القسم دور المدير العام للنظام.",
    signedOut: "انتهت جلستك. يرجى تسجيل الدخول مرة أخرى.",
    temporaryPassword: "كلمة مرور مؤقتة (تُعرض مرة واحدة)",
    copied: "تم النسخ",
  },
  fr: {
    title: "Administration globale CUBI",
    sections: { dashboard: "Tableau de bord", users: "Utilisateurs", roles: "Rôles", test: "Utilisateurs de test", audit: "Journal d'audit" },
    roles: {
      global_admin: "Administrateur global",
      organization_admin: "Administrateur d'organisation",
      enterprise_admin: "Administrateur Enterprise",
      enterprise_user: "Utilisateur Enterprise",
      enterprise_viewer: "Lecteur Enterprise",
      engineering_admin: "Administrateur Engineering",
      engineering_planner: "Planificateur Engineering",
      engineering_user: "Utilisateur Engineering",
      engineering_viewer: "Lecteur Engineering",
      guest: "Invité / Lecture seule",
      test_user: "Utilisateur de test",
    },
    search: "Rechercher des utilisateurs",
    createUser: "Créer un utilisateur",
    testUser: "Créer un utilisateur de test",
    resetPassword: "Réinitialiser le mot de passe",
    revokeSessions: "Révoquer les sessions",
    lock: "Verrouiller",
    unlock: "Déverrouiller",
    disable: "Désactiver",
    enable: "Activer",
    forbidden: "Cette zone exige le rôle Administrateur global.",
    signedOut: "Votre session est terminée. Reconnectez-vous.",
    temporaryPassword: "Mot de passe temporaire (affiché une fois)",
    copied: "Copié",
  },
  ja: {
    title: "CUBI グローバル管理",
    sections: { dashboard: "ダッシュボード", users: "ユーザー", roles: "ロール", test: "テストユーザー", audit: "監査ログ" },
    roles: {
      global_admin: "グローバル管理者",
      organization_admin: "組織管理者",
      enterprise_admin: "エンタープライズ管理者",
      enterprise_user: "エンタープライズユーザー",
      enterprise_viewer: "エンタープライズ閲覧者",
      engineering_admin: "エンジニアリング管理者",
      engineering_planner: "エンジニアリングプランナー",
      engineering_user: "エンジニアリングユーザー",
      engineering_viewer: "エンジニアリング閲覧者",
      guest: "ゲスト / 閲覧のみ",
      test_user: "テストユーザー",
    },
    search: "ユーザーを検索",
    createUser: "ユーザーを作成",
    testUser: "テストユーザーを作成",
    resetPassword: "パスワードを再設定",
    revokeSessions: "セッションを取り消す",
    lock: "ロック",
    unlock: "ロック解除",
    disable: "無効化",
    enable: "有効化",
    forbidden: "この領域にはグローバル管理者ロールが必要です。",
    signedOut: "セッションが終了しました。再度サインインしてください。",
    temporaryPassword: "一時パスワード（一度だけ表示）",
    copied: "コピーしました",
  },
  ko: {
    title: "CUBI 글로벌 관리",
    sections: { dashboard: "대시보드", users: "사용자", roles: "역할", test: "테스트 사용자", audit: "감사 로그" },
    roles: {
      global_admin: "글로벌 관리자",
      organization_admin: "조직 관리자",
      enterprise_admin: "엔터프라이즈 관리자",
      enterprise_user: "엔터프라이즈 사용자",
      enterprise_viewer: "엔터프라이즈 조회자",
      engineering_admin: "엔지니어링 관리자",
      engineering_planner: "엔지니어링 플래너",
      engineering_user: "엔지니어링 사용자",
      engineering_viewer: "엔지니어링 조회자",
      guest: "게스트 / 읽기 전용",
      test_user: "테스트 사용자",
    },
    search: "사용자 검색",
    createUser: "사용자 생성",
    testUser: "테스트 사용자 생성",
    resetPassword: "비밀번호 재설정",
    revokeSessions: "세션 해지",
    lock: "잠금",
    unlock: "잠금 해제",
    disable: "비활성화",
    enable: "활성화",
    forbidden: "이 영역은 글로벌 관리자 역할이 필요합니다.",
    signedOut: "세션이 종료되었습니다. 다시 로그인하세요.",
    temporaryPassword: "임시 비밀번호(한 번만 표시)",
    copied: "복사됨",
  },
  ru: {
    title: "Глобальное администрирование CUBI",
    sections: { dashboard: "Панель", users: "Пользователи", roles: "Роли", test: "Тестовые пользователи", audit: "Журнал аудита" },
    roles: {
      global_admin: "Глобальный администратор",
      organization_admin: "Администратор организации",
      enterprise_admin: "Администратор Enterprise",
      enterprise_user: "Пользователь Enterprise",
      enterprise_viewer: "Наблюдатель Enterprise",
      engineering_admin: "Администратор Engineering",
      engineering_planner: "Планировщик Engineering",
      engineering_user: "Пользователь Engineering",
      engineering_viewer: "Наблюдатель Engineering",
      guest: "Гость / только чтение",
      test_user: "Тестовый пользователь",
    },
    search: "Поиск пользователей",
    createUser: "Создать пользователя",
    testUser: "Создать тестового пользователя",
    resetPassword: "Сбросить пароль",
    revokeSessions: "Отозвать сеансы",
    lock: "Заблокировать",
    unlock: "Разблокировать",
    disable: "Отключить",
    enable: "Включить",
    forbidden: "Этот раздел требует роли глобального администратора.",
    signedOut: "Сеанс завершён. Войдите снова.",
    temporaryPassword: "Временный пароль (показывается один раз)",
    copied: "Скопировано",
  },
  tr: {
    title: "CUBI Genel Yönetim",
    sections: { dashboard: "Panel", users: "Kullanıcılar", roles: "Roller", test: "Test kullanıcıları", audit: "Denetim kaydı" },
    roles: {
      global_admin: "Genel Yönetici",
      organization_admin: "Kuruluş Yöneticisi",
      enterprise_admin: "Kurumsal Yönetici",
      enterprise_user: "Kurumsal Kullanıcı",
      enterprise_viewer: "Kurumsal İzleyici",
      engineering_admin: "Mühendislik Yöneticisi",
      engineering_planner: "Mühendislik Planlamacısı",
      engineering_user: "Mühendislik Kullanıcısı",
      engineering_viewer: "Mühendislik İzleyicisi",
      guest: "Konuk / Salt okunur",
      test_user: "Test Kullanıcısı",
    },
    search: "Kullanıcı ara",
    createUser: "Kullanıcı oluştur",
    testUser: "Test kullanıcısı oluştur",
    resetPassword: "Parolayı sıfırla",
    revokeSessions: "Oturumları iptal et",
    lock: "Kilitle",
    unlock: "Kilidi aç",
    disable: "Devre dışı bırak",
    enable: "Etkinleştir",
    forbidden: "Bu alan Genel Yönetici rolü gerektirir.",
    signedOut: "Oturumunuz sona erdi. Lütfen tekrar giriş yapın.",
    temporaryPassword: "Geçici parola (yalnızca bir kez gösterilir)",
    copied: "Kopyalandı",
  },
};

export function adminLabels(locale: string): Labels {
  const key = (locale.split("-")[0] || "en").toLowerCase() as AdminLocale;
  return LABELS[key] ?? LABELS.en;
}

export function adminLocales(): AdminLocale[] {
  return Object.keys(LABELS) as AdminLocale[];
}

export function roleLabel(locale: string, role: AdminRoleKey): string {
  const labels = adminLabels(locale);
  return labels.roles[role] ?? labels.roles.guest;
}

export function sectionLabel(locale: string, section: AdminSectionKey): string {
  return adminLabels(locale).sections[section];
}

export function isGlobalAdmin(roles: readonly string[] | null | undefined): boolean {
  return Array.isArray(roles) && roles.includes("global_admin");
}

export type AdminResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; code: string };

export class GlobalAdminClient {
  constructor(
    private readonly origin: string,
    private readonly fetchImpl: typeof fetch = (input, init) => fetch(input, init),
  ) {}

  private async request<T>(method: string, path: string, body?: unknown): Promise<AdminResult<T>> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const finalHeaders = withCsrfHeader(method, headers);
    const response = await this.fetchImpl(`${this.origin}/api/admin${path}`, {
      method,
      headers: finalHeaders,
      credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 204) return { ok: true, status: 204, data: {} as T };
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) {
      const code =
        payload && typeof payload === "object" && "code" in payload
          ? String((payload as { code: unknown }).code)
          : `HTTP_${response.status}`;
      return { ok: false, status: response.status, code };
    }
    return { ok: true, status: response.status, data: payload as T };
  }

  dashboard(): Promise<AdminResult<AdminDashboard>> {
    return this.request("GET", "/dashboard");
  }

  users(query = "", status = "", limit = 50): Promise<AdminResult<{ users: AdminUser[]; total: number }>> {
    const parameters = new URLSearchParams();
    if (query) parameters.set("query", query);
    if (status) parameters.set("status", status);
    parameters.set("limit", String(limit));
    return this.request("GET", `/users?${parameters.toString()}`);
  }

  createUser(input: Record<string, unknown>): Promise<AdminResult<{ user: AdminUser; temporary_password: string }>> {
    return this.request("POST", "/users", input);
  }

  updateUser(userId: string, patch: Record<string, unknown>): Promise<AdminResult<{ user: AdminUser }>> {
    return this.request("PATCH", `/users/${encodeURIComponent(userId)}`, patch);
  }

  resetPassword(userId: string, confirmPassword: string, reason = ""): Promise<AdminResult<{ temporary_password: string }>> {
    return this.request("POST", `/users/${encodeURIComponent(userId)}/password-reset`, {
      confirm_password: confirmPassword,
      reason,
    });
  }

  revokeSessions(userId: string, confirmPassword: string, reason = ""): Promise<AdminResult<{ sessions_revoked: number }>> {
    return this.request("POST", `/users/${encodeURIComponent(userId)}/revoke-sessions`, {
      confirm_password: confirmPassword,
      reason,
    });
  }

  audit(limit = 50): Promise<AdminResult<{ entries: AdminAuditEntry[] }>> {
    return this.request("GET", `/audit?limit=${limit}`);
  }
}

export function csrfHeaderPresent(): boolean {
  return readCookieValue("cubi_csrf") !== null;
}

const escapeHtml = (value: unknown): string =>
  String(value ?? "").replace(/[&<>"']/g, (character) => {
    switch (character) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });

export function dashboardSummary(locale: string, dashboard: AdminDashboard): { label: string; value: string }[] {
  const labels = adminLabels(locale);
  return [
    { label: labels.sections.users, value: `${dashboard.users_active} / ${dashboard.users_total}` },
    { label: labels.sections.test, value: String(dashboard.users_test) },
    { label: labels.sections.roles, value: String(dashboard.roles_defined) },
    { label: labels.sections.audit, value: String(dashboard.recent_actions.length) },
    { label: "Tenants", value: String(dashboard.tenants) },
    { label: "Sessions", value: String(dashboard.active_sessions) },
  ];
}

export function renderUserRows(locale: string, users: readonly AdminUser[]): string {
  const labels = adminLabels(locale);
  if (!users.length) return `<p class="cp-admin-empty">${escapeHtml(labels.search)}: 0</p>`;
  return `<table class="cp-admin-table"><thead><tr>
    <th>${escapeHtml(labels.sections.users)}</th><th>${escapeHtml(labels.sections.roles)}</th><th>Status</th><th>Sessions</th>
  </tr></thead><tbody>${users
    .map((user) => {
      const roles = user.role_keys.map((role) => escapeHtml(roleLabel(locale, role))).join(", ");
      const status = user.locked ? "locked" : user.active ? "active" : "disabled";
      return `<tr data-user="${escapeHtml(user.user_id)}">
        <td><strong>${escapeHtml(user.display_name)}</strong><br /><span>${escapeHtml(user.email)}</span><br /><span>${escapeHtml(user.tenant_id)}</span></td>
        <td>${roles}${user.is_test_user ? " · test" : ""}</td>
        <td>${escapeHtml(status)}</td>
        <td>${user.sessions}</td>
      </tr>`;
    })
    .join("")}</tbody></table>`;
}

export async function mountGlobalAdmin(container: HTMLElement, locale: string, client: GlobalAdminClient): Promise<void> {
  const labels = adminLabels(locale);
  const direction = locale.startsWith("ar") || locale.startsWith("fa") ? "rtl" : "ltr";
  container.innerHTML = `<main class="cp-admin" dir="${direction}"><h1>${escapeHtml(labels.title)}</h1><p>Loading…</p></main>`;
  const dashboard = await client.dashboard();
  if (!dashboard.ok) {
    const message =
      dashboard.status === 401
        ? labels.signedOut
        : dashboard.status === 403
          ? labels.forbidden
          : dashboard.code;
    container.innerHTML = `<main class="cp-admin" dir="${direction}"><h1>${escapeHtml(labels.title)}</h1><p role="alert">${escapeHtml(message)}</p></main>`;
    return;
  }
  const summary = dashboardSummary(locale, dashboard.data)
    .map((item) => `<li><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></li>`)
    .join("");
  const actions = dashboard.data.recent_actions
    .map(
      (entry) =>
        `<tr><td>${escapeHtml(entry.action)}</td><td>${escapeHtml(entry.target_user_id ?? "")}</td><td>${escapeHtml(entry.occurred_at ?? "")}</td></tr>`,
    )
    .join("");
  container.innerHTML = `<main class="cp-admin" dir="${direction}">
    <header><h1>${escapeHtml(labels.title)}</h1><p>${escapeHtml(dashboard.data.viewer.user_id)}</p></header>
    <section aria-label="${escapeHtml(labels.sections.dashboard)}"><ul class="cp-admin-summary">${summary}</ul></section>
    <section aria-label="${escapeHtml(labels.sections.audit)}">
      <h2>${escapeHtml(labels.sections.audit)}</h2>
      <table class="cp-admin-table"><thead><tr><th>Action</th><th>Target</th><th>When</th></tr></thead><tbody>${actions}</tbody></table>
    </section>
  </main>`;
}
