import { FetchSessionApi, type ProjectSummary } from "./session-api.js";

/**
 * Personal Workbench — the signed-in entry surface that sits between the
 * public site/login and the two product environments. It owns identity
 * display, the authorized-project summary and environment selection. It is
 * not a third workspace: every action links into Engineering or Enterprise.
 */

export const WORKBENCH_LOCALES = ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"] as const;
export type WorkbenchLocale = (typeof WORKBENCH_LOCALES)[number];

type Copy = {
  title: string;
  subtitle: string;
  identity: string;
  tenant: string;
  roles: string;
  expiresAt: string;
  environments: string;
  engineering: string;
  engineeringNote: string;
  enterprise: string;
  enterpriseNote: string;
  open: string;
  restricted: string;
  projects: string;
  projectsEmpty: string;
  tasks: string;
  tasksNone: string;
  help: string;
  helpNote: string;
  securityNote: string;
  loading: string;
  error: string;
  retry: string;
  breadcrumbHome: string;
  breadcrumb: string;
  language: string;
  signedOut: string;
};

export const WORKBENCH_COPY: Record<WorkbenchLocale, Copy> = {
  en: {
    title: "Personal Workbench",
    subtitle: "Your identity, authorized projects and the environments you can enter.",
    identity: "Signed in as",
    tenant: "Tenant",
    roles: "Roles",
    expiresAt: "Session expires",
    environments: "Environments",
    engineering: "CUBI Engineering",
    engineeringNote: "Projects, WBS, activities, scheduling, resources and reports.",
    enterprise: "CUBI Enterprise",
    enterpriseNote: "Organization, teams, tasks, approvals, workflows and portfolio.",
    open: "Open environment",
    restricted: "Not authorized for this account",
    projects: "Authorized projects",
    projectsEmpty: "No projects are authorized for this account yet.",
    tasks: "Assigned tasks",
    tasksNone: "No open tasks are assigned to you.",
    help: "Help",
    helpNote: "Task-oriented help and documentation for both environments.",
    securityNote: "Every environment and project is authorized by the server on each request.",
    loading: "Loading your workbench…",
    error: "The workbench could not be loaded. Please try again.",
    retry: "Retry",
    breadcrumbHome: "Home",
    breadcrumb: "Workbench",
    language: "Language",
    signedOut: "Your session has expired. Sign in to continue.",
  },
  fa: {
    title: "میزکار شخصی",
    subtitle: "هویت شما، پروژه‌های مجاز و محیط‌هایی که می‌توانید وارد شوید.",
    identity: "ورود به‌عنوان",
    tenant: "سازمان",
    roles: "نقش‌ها",
    expiresAt: "پایان نشست",
    environments: "محیط‌ها",
    engineering: "کوبی مهندسی",
    engineeringNote: "پروژه‌ها، ساختار شکست کار، فعالیت‌ها، زمان‌بندی، منابع و گزارش‌ها.",
    enterprise: "کوبی سازمانی",
    enterpriseNote: "سازمان، تیم‌ها، وظایف، تأییدها، گردش‌کار و پرتفولیو.",
    open: "ورود به محیط",
    restricted: "برای این حساب مجاز نیست",
    projects: "پروژه‌های مجاز",
    projectsEmpty: "هنوز هیچ پروژه‌ای برای این حساب مجاز نشده است.",
    tasks: "وظایف واگذارشده",
    tasksNone: "وظیفه باز واگذارشده‌ای ندارید.",
    help: "راهنما",
    helpNote: "راهنمای وظیفه‌محور و مستندات هر دو محیط.",
    securityNote: "دسترسی هر محیط و پروژه در هر درخواست در سمت سرور کنترل می‌شود.",
    loading: "در حال بارگذاری میزکار…",
    error: "بارگذاری میزکار انجام نشد. دوباره تلاش کنید.",
    retry: "تلاش دوباره",
    breadcrumbHome: "خانه",
    breadcrumb: "میزکار",
    language: "زبان",
    signedOut: "نشست شما پایان یافته است. برای ادامه وارد شوید.",
  },
  de: {
    title: "Persönliche Werkbank",
    subtitle: "Ihre Identität, freigegebene Projekte und die Umgebungen, die Sie öffnen dürfen.",
    identity: "Angemeldet als",
    tenant: "Mandant",
    roles: "Rollen",
    expiresAt: "Sitzung endet",
    environments: "Umgebungen",
    engineering: "CUBI Engineering",
    engineeringNote: "Projekte, WBS, Vorgänge, Terminplanung, Ressourcen und Berichte.",
    enterprise: "CUBI Enterprise",
    enterpriseNote: "Organisation, Teams, Aufgaben, Freigaben, Workflows und Portfolio.",
    open: "Umgebung öffnen",
    restricted: "Für dieses Konto nicht freigegeben",
    projects: "Freigegebene Projekte",
    projectsEmpty: "Für dieses Konto sind noch keine Projekte freigegeben.",
    tasks: "Zugewiesene Aufgaben",
    tasksNone: "Ihnen sind keine offenen Aufgaben zugewiesen.",
    help: "Hilfe",
    helpNote: "Aufgabenbezogene Hilfe und Dokumentation für beide Umgebungen.",
    securityNote: "Jede Umgebung und jedes Projekt wird bei jeder Anfrage serverseitig geprüft.",
    loading: "Werkbank wird geladen…",
    error: "Die Werkbank konnte nicht geladen werden. Bitte erneut versuchen.",
    retry: "Erneut versuchen",
    breadcrumbHome: "Start",
    breadcrumb: "Werkbank",
    language: "Sprache",
    signedOut: "Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.",
  },
  zh: {
    title: "个人工作台",
    subtitle: "您的身份、已授权项目以及可进入的环境。",
    identity: "当前登录",
    tenant: "租户",
    roles: "角色",
    expiresAt: "会话到期",
    environments: "环境",
    engineering: "CUBI 工程",
    engineeringNote: "项目、WBS、活动、排程、资源和报表。",
    enterprise: "CUBI 企业",
    enterpriseNote: "组织、团队、任务、审批、工作流和项目组合。",
    open: "进入环境",
    restricted: "此账户未获授权",
    projects: "已授权项目",
    projectsEmpty: "此账户尚未获得任何项目授权。",
    tasks: "已分配任务",
    tasksNone: "没有分配给您未完成的任务。",
    help: "帮助",
    helpNote: "面向任务的两个环境帮助与文档。",
    securityNote: "每次请求都由服务器校验环境与项目权限。",
    loading: "正在加载工作台…",
    error: "工作台加载失败，请重试。",
    retry: "重试",
    breadcrumbHome: "首页",
    breadcrumb: "工作台",
    language: "语言",
    signedOut: "会话已过期，请重新登录。",
  },
  ar: {
    title: "مساحة العمل الشخصية",
    subtitle: "هويتك ومشاريعك المصرح بها والبيئات التي يمكنك الدخول إليها.",
    identity: "مسجّل الدخول باسم",
    tenant: "المستأجر",
    roles: "الأدوار",
    expiresAt: "انتهاء الجلسة",
    environments: "البيئات",
    engineering: "كوبي الهندسية",
    engineeringNote: "المشاريع وهيكل العمل والأنشطة والجدولة والموارد والتقارير.",
    enterprise: "كوبي المؤسسية",
    enterpriseNote: "المؤسسة والفرق والمهام والموافقات وسير العمل والمحفظة.",
    open: "الدخول إلى البيئة",
    restricted: "غير مصرح لهذا الحساب",
    projects: "المشاريع المصرح بها",
    projectsEmpty: "لا توجد مشاريع مصرح بها لهذا الحساب بعد.",
    tasks: "المهام المسندة",
    tasksNone: "لا توجد مهام مفتوحة مسندة إليك.",
    help: "المساعدة",
    helpNote: "مساعدة موجّهة للمهام ووثائق للبيئتين.",
    securityNote: "يتحقق الخادم من صلاحية كل بيئة ومشروع في كل طلب.",
    loading: "جارٍ تحميل مساحة العمل…",
    error: "تعذّر تحميل مساحة العمل. حاول مرة أخرى.",
    retry: "إعادة المحاولة",
    breadcrumbHome: "الرئيسية",
    breadcrumb: "مساحة العمل",
    language: "اللغة",
    signedOut: "انتهت جلستك. سجّل الدخول للمتابعة.",
  },
  fr: {
    title: "Bureau personnel",
    subtitle: "Votre identité, vos projets autorisés et les environnements accessibles.",
    identity: "Connecté en tant que",
    tenant: "Locataire",
    roles: "Rôles",
    expiresAt: "Fin de session",
    environments: "Environnements",
    engineering: "CUBI Ingénierie",
    engineeringNote: "Projets, WBS, activités, planification, ressources et rapports.",
    enterprise: "CUBI Entreprise",
    enterpriseNote: "Organisation, équipes, tâches, approbations, workflows et portefeuille.",
    open: "Ouvrir l’environnement",
    restricted: "Non autorisé pour ce compte",
    projects: "Projets autorisés",
    projectsEmpty: "Aucun projet n’est encore autorisé pour ce compte.",
    tasks: "Tâches assignées",
    tasksNone: "Aucune tâche ouverte ne vous est assignée.",
    help: "Aide",
    helpNote: "Aide orientée tâches et documentation pour les deux environnements.",
    securityNote: "Chaque environnement et projet est autorisé par le serveur à chaque requête.",
    loading: "Chargement de votre bureau…",
    error: "Le bureau n’a pas pu être chargé. Veuillez réessayer.",
    retry: "Réessayer",
    breadcrumbHome: "Accueil",
    breadcrumb: "Bureau",
    language: "Langue",
    signedOut: "Votre session a expiré. Veuillez vous reconnecter.",
  },
  ja: {
    title: "パーソナルワークベンチ",
    subtitle: "あなたの身元、許可されたプロジェクト、入室できる環境。",
    identity: "ログイン中",
    tenant: "テナント",
    roles: "ロール",
    expiresAt: "セッション期限",
    environments: "環境",
    engineering: "CUBI エンジニアリング",
    engineeringNote: "プロジェクト、WBS、アクティビティ、スケジューリング、リソース、レポート。",
    enterprise: "CUBI エンタープライズ",
    enterpriseNote: "組織、チーム、タスク、承認、ワークフロー、ポートフォリオ。",
    open: "環境を開く",
    restricted: "このアカウントには許可されていません",
    projects: "許可されたプロジェクト",
    projectsEmpty: "このアカウントに許可されたプロジェクトはまだありません。",
    tasks: "割り当てられたタスク",
    tasksNone: "未完了の割り当てタスクはありません。",
    help: "ヘルプ",
    helpNote: "両環境のタスク指向ヘルプとドキュメント。",
    securityNote: "環境とプロジェクトの権限はリクエストごとにサーバーで検証されます。",
    loading: "ワークベンチを読み込み中…",
    error: "ワークベンチを読み込めませんでした。もう一度お試しください。",
    retry: "再試行",
    breadcrumbHome: "ホーム",
    breadcrumb: "ワークベンチ",
    language: "言語",
    signedOut: "セッションの有効期限が切れました。再度ログインしてください。",
  },
  ko: {
    title: "개인 워크벤치",
    subtitle: "사용자 신원, 권한이 부여된 프로젝트, 입장 가능한 환경.",
    identity: "로그인 사용자",
    tenant: "테넌트",
    roles: "역할",
    expiresAt: "세션 만료",
    environments: "환경",
    engineering: "CUBI 엔지니어링",
    engineeringNote: "프로젝트, WBS, 활동, 일정, 리소스 및 보고서.",
    enterprise: "CUBI 엔터프라이즈",
    enterpriseNote: "조직, 팀, 작업, 승인, 워크플로 및 포트폴리오.",
    open: "환경 열기",
    restricted: "이 계정에는 권한이 없습니다",
    projects: "권한이 부여된 프로젝트",
    projectsEmpty: "이 계정에 아직 권한이 부여된 프로젝트가 없습니다.",
    tasks: "할당된 작업",
    tasksNone: "할당된 미완료 작업이 없습니다.",
    help: "도움말",
    helpNote: "두 환경의 작업 중심 도움말과 문서.",
    securityNote: "모든 요청에서 환경과 프로젝트 권한을 서버가 검증합니다.",
    loading: "워크벤치를 불러오는 중…",
    error: "워크벤치를 불러오지 못했습니다. 다시 시도하세요.",
    retry: "다시 시도",
    breadcrumbHome: "홈 화면",
    breadcrumb: "워크벤치",
    language: "언어",
    signedOut: "세션이 만료되었습니다. 다시 로그인하세요.",
  },
  ru: {
    title: "Личное рабочее место",
    subtitle: "Ваша учётная запись, разрешённые проекты и доступные среды.",
    identity: "Вы вошли как",
    tenant: "Арендатор",
    roles: "Роли",
    expiresAt: "Сеанс истекает",
    environments: "Среды",
    engineering: "CUBI Инженерия",
    engineeringNote: "Проекты, СДР, работы, планирование, ресурсы и отчёты.",
    enterprise: "CUBI Предприятие",
    enterpriseNote: "Организация, команды, задачи, согласования, процессы и портфель.",
    open: "Открыть среду",
    restricted: "Нет доступа для этой учётной записи",
    projects: "Разрешённые проекты",
    projectsEmpty: "Для этой учётной записи пока нет разрешённых проектов.",
    tasks: "Назначенные задачи",
    tasksNone: "У вас нет открытых назначенных задач.",
    help: "Справка",
    helpNote: "Практическая справка и документация для обеих сред.",
    securityNote: "Доступ к каждой среде и проекту проверяется сервером при каждом запросе.",
    loading: "Загрузка рабочего места…",
    error: "Не удалось загрузить рабочее место. Повторите попытку.",
    retry: "Повторить",
    breadcrumbHome: "Главная",
    breadcrumb: "Рабочее место",
    language: "Язык",
    signedOut: "Сеанс истёк. Войдите снова.",
  },
  tr: {
    title: "Kişisel Çalışma Tezgahı",
    subtitle: "Kimliğiniz, yetkili projeleriniz ve girebileceğiniz ortamlar.",
    identity: "Giriş yapan",
    tenant: "Kiracı",
    roles: "Roller",
    expiresAt: "Oturum bitişi",
    environments: "Ortamlar",
    engineering: "CUBI Mühendislik",
    engineeringNote: "Projeler, WBS, faaliyetler, çizelgeleme, kaynaklar ve raporlar.",
    enterprise: "CUBI Kurumsal",
    enterpriseNote: "Organizasyon, ekipler, görevler, onaylar, iş akışları ve portföy.",
    open: "Ortamı aç",
    restricted: "Bu hesap için yetkili değil",
    projects: "Yetkili projeler",
    projectsEmpty: "Bu hesap için henüz yetkili proje yok.",
    tasks: "Atanan görevler",
    tasksNone: "Size atanmış açık görev yok.",
    help: "Yardım",
    helpNote: "Her iki ortam için görev odaklı yardım ve belgeler.",
    securityNote: "Her ortam ve proje yetkisi her istekte sunucu tarafından doğrulanır.",
    loading: "Çalışma tezgahı yükleniyor…",
    error: "Çalışma tezgahı yüklenemedi. Lütfen tekrar deneyin.",
    retry: "Tekrar dene",
    breadcrumbHome: "Ana sayfa",
    breadcrumb: "Çalışma tezgahı",
    language: "Dil",
    signedOut: "Oturumunuz sona erdi. Devam etmek için giriş yapın.",
  },
};

const HTML_LANG: Record<WorkbenchLocale, string> = {
  en: "en", fa: "fa", de: "de", zh: "zh-CN", ar: "ar", fr: "fr", ja: "ja", ko: "ko", ru: "ru", tr: "tr-TR",
};
const INTL_LOCALE: Record<WorkbenchLocale, string> = {
  en: "en-GB", fa: "fa-IR", de: "de-DE", zh: "zh-CN", ar: "ar-SA", fr: "fr-FR", ja: "ja-JP", ko: "ko-KR", ru: "ru-RU", tr: "tr-TR",
};

export function resolveWorkbenchLocale(raw: string | null | undefined): WorkbenchLocale {
  const value = (raw ?? "").trim().toLowerCase();
  if (!value) return "en";
  if (value.startsWith("zh")) return "zh";
  if (value.startsWith("tr")) return "tr";
  if (value.startsWith("fa")) return "fa";
  if (value.startsWith("ar")) return "ar";
  if (value.startsWith("de")) return "de";
  if (value.startsWith("fr")) return "fr";
  if (value.startsWith("ja")) return "ja";
  if (value.startsWith("ko")) return "ko";
  if (value.startsWith("ru")) return "ru";
  if (value.startsWith("en")) return "en";
  return "en";
}

export function workbenchDirection(locale: WorkbenchLocale): "rtl" | "ltr" {
  return locale === "fa" || locale === "ar" ? "rtl" : "ltr";
}

export function workbenchIntlLocale(locale: WorkbenchLocale): string {
  return INTL_LOCALE[locale];
}

export function workbenchHtmlLang(locale: WorkbenchLocale): string {
  return HTML_LANG[locale];
}

export function formatWorkbenchDate(locale: WorkbenchLocale, iso: string): string {
  const value = Date.parse(iso);
  if (Number.isNaN(value)) return iso;
  return new Intl.DateTimeFormat(INTL_LOCALE[locale], { dateStyle: "medium", timeStyle: "short" }).format(value);
}

export function formatWorkbenchNumber(locale: WorkbenchLocale, value: number): string {
  return new Intl.NumberFormat(INTL_LOCALE[locale]).format(value);
}

export type EnvironmentId = "engineering" | "enterprise";
export type EnvironmentState = {
  id: EnvironmentId;
  available: boolean;
  reason: "authorized" | "no_server_grant" | "server_unknown";
};
export type EnvironmentSignals = {
  /** GET /api/projects succeeded — the server released the authorized register. */
  projectsOk: boolean;
  /** GET /api/enterprise/tasks succeeded (200) — enterprise scope is granted. */
  enterpriseOk: boolean | null;
};

/**
 * Environment availability is decided from server responses, never from a
 * hard-coded role list: a denied endpoint means the account has no grant.
 */
export function resolveEnvironments(signals: EnvironmentSignals): EnvironmentState[] {
  return [
    {
      id: "engineering",
      available: signals.projectsOk,
      reason: signals.projectsOk ? "authorized" : "no_server_grant",
    },
    {
      id: "enterprise",
      available: signals.enterpriseOk === true,
      reason: signals.enterpriseOk === true ? "authorized" : signals.enterpriseOk === null ? "server_unknown" : "no_server_grant",
    },
  ];
}

export function environmentHref(id: EnvironmentId, projectId?: string): string {
  if (id === "engineering") {
    return projectId
      ? `/app?project=${encodeURIComponent(projectId)}&view=live`
      : "/app?view=live";
  }
  return "/enterprise/";
}

async function probeEnterprise(): Promise<boolean | null> {
  try {
    const response = await fetch("/api/enterprise/tasks?limit=1", {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (response.status === 401) return null;
    return response.ok;
  } catch {
    return null;
  }
}

function element<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export async function mountPersonalWorkbench(container: HTMLElement, requestedLocale?: string): Promise<void> {
  const parameters = new URLSearchParams(window.location.search);
  const stored = (() => {
    try { return window.localStorage.getItem("cubi.workbench.locale"); } catch { return null; }
  })();
  const locale = resolveWorkbenchLocale(
    requestedLocale ?? parameters.get("lang") ?? stored ?? navigator.language,
  );
  const copy = WORKBENCH_COPY[locale];
  const direction = workbenchDirection(locale);
  document.documentElement.lang = workbenchHtmlLang(locale);
  document.documentElement.dir = direction;
  document.title = `CUBI · ${copy.title}`;
  container.replaceChildren();

  const shell = element("main", "cp-wb");
  shell.dir = direction;

  const header = element("header", "cp-wb-header");
  const brand = element("a", "cp-wb-brand", "CUBI");
  brand.href = "/";
  const crumb = element("nav", "cp-wb-crumbs");
  crumb.setAttribute("aria-label", copy.breadcrumb);
  const homeLink = element("a", "", copy.breadcrumbHome);
  homeLink.href = "/";
  crumb.append(homeLink, element("span", "", "/"), element("span", "", copy.breadcrumb));
  const localeLabel = element("label", "cp-wb-locale");
  localeLabel.append(element("span", "", copy.language));
  const select = element("select") as HTMLSelectElement;
  select.setAttribute("aria-label", copy.language);
  for (const value of WORKBENCH_LOCALES) {
    const option = element("option", "", value) as HTMLOptionElement;
    option.value = value;
    option.selected = value === locale;
    select.append(option);
  }
  select.addEventListener("change", () => {
    try { window.localStorage.setItem("cubi.workbench.locale", select.value); } catch { /* storage disabled */ }
    const url = new URL(window.location.href);
    url.searchParams.set("lang", select.value);
    window.location.assign(url.toString());
  });
  localeLabel.append(select);
  header.append(brand, crumb, localeLabel);
  shell.append(header);

  const hero = element("section", "cp-wb-hero");
  hero.append(element("p", "cp-wb-eyebrow", "CUBI"), element("h1", "", copy.title), element("p", "cp-wb-subtitle", copy.subtitle));
  shell.append(hero);

  const status = element("p", "cp-wb-status", copy.loading);
  status.setAttribute("role", "status");
  const alert = element("p", "cp-wb-alert");
  alert.setAttribute("role", "alert");
  alert.hidden = true;
  shell.append(status, alert);
  container.append(shell);

  const sessionApi = new FetchSessionApi(window.location.origin);
  const session = await sessionApi.getSession();
  if (!session.ok) {
    if (session.error.code === "UNAUTHENTICATED" || session.error.code === "SESSION_REQUIRED") {
      window.location.assign(`/login?next=${encodeURIComponent("/workbench/")}`);
      return;
    }
    status.hidden = true;
    alert.hidden = false;
    alert.textContent = copy.error;
    const retry = element("button", "cp-wb-button", copy.retry);
    retry.type = "button";
    retry.addEventListener("click", () => window.location.reload());
    alert.append(" ", retry);
    return;
  }
  status.hidden = true;

  const identity = element("section", "cp-wb-identity");
  identity.setAttribute("aria-label", copy.identity);
  const identityList = element("dl");
  const rows: Array<[string, string]> = [
    [copy.identity, session.data.user_id],
    [copy.tenant, session.data.tenant_id],
    [copy.roles, session.data.roles.length ? session.data.roles.join(", ") : "—"],
    [copy.expiresAt, formatWorkbenchDate(locale, session.data.expires_at)],
  ];
  for (const [label, value] of rows) {
    const term = element("dt", "", label);
    const detail = element("dd", "", value);
    identityList.append(term, detail);
  }
  identity.append(identityList);
  shell.append(identity);

  const projectsResult = await sessionApi.listProjects();
  const projects: ProjectSummary[] = projectsResult.ok ? projectsResult.data.projects : [];
  const enterpriseOk = await probeEnterprise();
  const environments = resolveEnvironments({ projectsOk: projectsResult.ok, enterpriseOk });

  const environmentSection = element("section", "cp-wb-environments");
  environmentSection.append(element("h2", "", copy.environments));
  const grid = element("div", "cp-wb-cards");
  for (const environment of environments) {
    const card = element("article", `cp-wb-card cp-wb-card-${environment.id}`);
    const name = environment.id === "engineering" ? copy.engineering : copy.enterprise;
    const note = environment.id === "engineering" ? copy.engineeringNote : copy.enterpriseNote;
    card.append(element("h3", "", name), element("p", "", note));
    if (environment.available) {
      const link = element("a", "cp-wb-button cp-wb-button-primary", copy.open) as HTMLAnchorElement;
      link.href = environmentHref(environment.id, environment.id === "engineering" ? projects[0]?.project_id : undefined);
      card.append(link);
    } else {
      const blocked = element("p", "cp-wb-restricted", copy.restricted);
      blocked.setAttribute("role", "note");
      card.append(blocked);
    }
    grid.append(card);
  }
  environmentSection.append(grid);
  shell.append(environmentSection);

  const projectSection = element("section", "cp-wb-projects");
  projectSection.append(element("h2", "", copy.projects));
  if (projects.length) {
    const list = element("ul", "cp-wb-project-list");
    for (const project of projects) {
      const item = element("li");
      const link = element("a", "", project.name) as HTMLAnchorElement;
      link.href = environmentHref("engineering", project.project_id);
      const meta = element("span", "cp-wb-project-meta", `${project.project_id} · ${project.status ?? "active"}`);
      item.append(link, meta);
      list.append(item);
    }
    projectSection.append(list);
  } else {
    projectSection.append(element("p", "cp-wb-empty", copy.projectsEmpty));
  }
  shell.append(projectSection);

  if (enterpriseOk === true) {
    const taskSection = element("section", "cp-wb-tasks");
    taskSection.append(element("h2", "", copy.tasks));
    const taskLink = element("a", "cp-wb-inline-link", copy.enterprise) as HTMLAnchorElement;
    taskLink.href = "/enterprise/";
    taskSection.append(element("p", "cp-wb-empty", copy.tasksNone), taskLink);
    shell.append(taskSection);
  }

  const helpSection = element("section", "cp-wb-help");
  helpSection.append(element("h2", "", copy.help), element("p", "", copy.helpNote));
  const helpLinks = element("div", "cp-wb-help-links");
  for (const [label, href] of [["/help/", "/help/"], ["/documentation/", "/documentation/"], ["/environments/", "/environments/"]] as const) {
    const link = element("a", "", label) as HTMLAnchorElement;
    link.href = href;
    helpLinks.append(link);
  }
  helpSection.append(helpLinks);
  shell.append(helpSection);

  shell.append(element("p", "cp-wb-security", copy.securityNote));
}
