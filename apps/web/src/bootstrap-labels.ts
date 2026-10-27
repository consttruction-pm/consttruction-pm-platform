import type { ClientError } from "./client.js";
import type { WorkspaceLocale } from "./workspace-model.js";
import { translateWorkspaceText } from "./workspace-localization.js";

export type BootstrapLabels = {
  workspaceTitle: string;
  loading: string;
  opening: string;
  creating: string;
  selectProject: string;
  selectProjectDescription: string;
  createFirstProject: string;
  noProjects: string;
  createProject: string;
  projectName: string;
  projectNamePlaceholder: string;
  projectNameHint: string;
  createAndOpen: string;
  constructionPm: string;
  unableToInitialize: string;
  retry: string;
  refresh: string;
  switchLanguage: string;
  projectListAria: string;
  validationNameRequired: string;
  validationNameLength: string;
  createFailed: string;
  errorTitle: string;
  errorNetwork: string;
  errorSession: string;
  errorForbidden: string;
  errorProjectUnavailable: string;
  errorWorkspace: string;
  errorP6: string;
  errorGeneric: string;
  errorReference: string;
};

const labels: Partial<Record<WorkspaceLocale, BootstrapLabels>> = {
  en: {
    workspaceTitle: "CUBI Workspace",
    loading: "Loading workspace…",
    opening: "Opening project…",
    creating: "Creating project…",
    selectProject: "Select project",
    selectProjectDescription: "Choose the project you want to work on. Your last project reopens automatically on this browser.",
    createFirstProject: "Create your first project",
    noProjects: "Your account has no project yet. Create one to start building the WBS, activities and schedule.",
    createProject: "Create project",
    projectName: "Project name",
    projectNamePlaceholder: "e.g. Riverside Tower",
    projectNameHint: "Use a recognizable name of 2 to 120 characters.",
    createAndOpen: "Create and open",
    constructionPm: "CUBI Workspace",
    unableToInitialize: "Unable to initialize the web workspace.",
    retry: "Retry",
    refresh: "Refresh",
    switchLanguage: "Switch language to {language}",
    projectListAria: "Projects available to your account",
    validationNameRequired: "Enter a project name.",
    validationNameLength: "Use a project name between 2 and 120 characters.",
    createFailed: "The project was not created. Check the name and try again.",
    errorTitle: "The workspace could not open",
    errorNetwork: "The server could not be reached. Check your connection and try again.",
    errorSession: "Your session is no longer valid. Sign in again, then reload the workspace.",
    errorForbidden: "Your account does not have permission to open this workspace.",
    errorProjectUnavailable: "That project is not available to your account. Choose another project.",
    errorWorkspace: "The project data could not be loaded. The stored project was not changed.",
    errorP6: "The saved activity layout is invalid or incomplete, so the workspace was not opened.",
    errorGeneric: "The workspace could not be opened. Try again; if the problem continues, send the reference below to your administrator.",
    errorReference: "Reference",
  },
  fa: {
    workspaceTitle: "فضای کاری کوبی",
    loading: "در حال بارگذاری محیط کار…",
    opening: "در حال باز کردن پروژه…",
    creating: "در حال ایجاد پروژه…",
    selectProject: "انتخاب پروژه",
    selectProjectDescription: "پروژه‌ای را که می‌خواهید روی آن کار کنید انتخاب کنید. آخرین پروژه در این مرورگر به‌طور خودکار باز می‌شود.",
    createFirstProject: "اولین پروژه خود را ایجاد کنید",
    noProjects: "هنوز پروژه‌ای برای حساب شما ثبت نشده است. برای شروع ساخت WBS، فعالیت‌ها و زمان‌بندی، یک پروژه ایجاد کنید.",
    createProject: "ایجاد پروژه",
    projectName: "نام پروژه",
    projectNamePlaceholder: "مثلاً برج ریورساید",
    projectNameHint: "نامی روشن و قابل‌تشخیص بین ۲ تا ۱۲۰ نویسه وارد کنید.",
    createAndOpen: "ایجاد و باز کردن",
    constructionPm: "فضای کاری کوبی",
    unableToInitialize: "راه‌اندازی محیط کار وب امکان‌پذیر نیست.",
    retry: "تلاش مجدد",
    refresh: "بازخوانی",
    switchLanguage: "تغییر زبان به {language}",
    projectListAria: "پروژه‌های در دسترس حساب شما",
    validationNameRequired: "نام پروژه را وارد کنید.",
    validationNameLength: "نام پروژه باید بین ۲ تا ۱۲۰ نویسه باشد.",
    createFailed: "پروژه ایجاد نشد. نام را بررسی کنید و دوباره تلاش کنید.",
    errorTitle: "محیط کار باز نشد",
    errorNetwork: "ارتباط با سرور برقرار نشد. اتصال خود را بررسی کنید و دوباره تلاش کنید.",
    errorSession: "نشست شما دیگر معتبر نیست. دوباره وارد شوید و سپس محیط کار را بازخوانی کنید.",
    errorForbidden: "حساب شما اجازهٔ باز کردن این محیط کار را ندارد.",
    errorProjectUnavailable: "این پروژه برای حساب شما در دسترس نیست. پروژهٔ دیگری انتخاب کنید.",
    errorWorkspace: "داده‌های پروژه بارگذاری نشد. پروژهٔ ذخیره‌شده تغییری نکرده است.",
    errorP6: "چیدمان ذخیره‌شدهٔ فعالیت‌ها نامعتبر یا ناقص است؛ بنابراین محیط کار باز نشد.",
    errorGeneric: "محیط کار باز نشد. دوباره تلاش کنید؛ اگر مشکل ادامه داشت، مرجع زیر را به مدیر سامانه بدهید.",
    errorReference: "مرجع",
  },
};

export function getBootstrapLabels(locale: WorkspaceLocale): BootstrapLabels {
  const baseline = labels[locale] ?? labels.en!;
  return Object.fromEntries(Object.entries(baseline).map(([key, value]) => [key, translateWorkspaceText(locale, `bootstrap.${key}`, value)])) as BootstrapLabels;
}

export type BootstrapErrorCopy = {
  title: string;
  message: string;
  /** Technical code for support. Never a raw untranslated user-facing message. */
  reference: string;
};

const SESSION_CODES = new Set([
  "SESSION_REQUIRED",
  "SESSION_EXPIRED",
  "UNAUTHENTICATED",
  "AUTH_REQUIRED",
  "AUTHORIZATION_REQUIRED",
]);
const FORBIDDEN_CODES = new Set([
  "FORBIDDEN",
  "PERMISSION_DENIED",
  "PROJECT_READ_DENIED",
  "PROJECT_WRITE_DENIED",
  "INSUFFICIENT_PERMISSION",
]);
const PROJECT_CODES = new Set([
  "PROJECT_NOT_AVAILABLE",
  "PROJECT_NOT_FOUND",
  "PROJECT_ACCESS_DENIED",
]);
const NETWORK_CODES = new Set(["NETWORK_ERROR", "REQUEST_FAILED", "FETCH_FAILED"]);

/**
 * Map a server error to localized copy. Unknown codes deliberately fall back to
 * a translated generic message: a raw message key or server string must never
 * be shown to the user as if it were UI copy.
 */
export function getBootstrapErrorCopy(
  locale: WorkspaceLocale,
  error: Pick<ClientError, "code" | "message_key">,
): BootstrapErrorCopy {
  const t = getBootstrapLabels(locale);
  const code = String(error.code || "UNKNOWN_ERROR");
  const messageKey = String(error.message_key || "");
  let message = t.errorGeneric;
  if (NETWORK_CODES.has(code) || messageKey === "error.network") message = t.errorNetwork;
  else if (SESSION_CODES.has(code) || messageKey.startsWith("error.session")) message = t.errorSession;
  else if (FORBIDDEN_CODES.has(code) || messageKey.includes("forbidden") || messageKey.includes("permission")) message = t.errorForbidden;
  else if (PROJECT_CODES.has(code) || messageKey === "error.project.not_available") message = t.errorProjectUnavailable;
  else if (messageKey.startsWith("error.workspace")) message = t.errorWorkspace;
  else if (messageKey.startsWith("error.p6") || code === "P6_PRESENTATION_LOAD_FAILED") message = t.errorP6;
  return { title: t.errorTitle, message, reference: code };
}
