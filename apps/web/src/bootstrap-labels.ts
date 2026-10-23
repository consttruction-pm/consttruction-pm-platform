import type { WorkspaceLocale } from "./workspace-model.js";

export type BootstrapLabels = {
  loading: string;
  opening: string;
  creating: string;
  selectProject: string;
  createFirstProject: string;
  noProjects: string;
  createProject: string;
  projectName: string;
  projectNamePlaceholder: string;
  createAndOpen: string;
  constructionPm: string;
  unableToInitialize: string;
  retry: string;
  refresh: string;
};

const labels: Record<WorkspaceLocale, BootstrapLabels> = {
  en: {
    loading: "Loading workspace…",
    opening: "Opening project…",
    creating: "Creating project…",
    selectProject: "Select project",
    createFirstProject: "Create your first project",
    noProjects: "No projects are available for this workspace yet.",
    createProject: "Create project",
    projectName: "Project name",
    projectNamePlaceholder: "e.g. Riverside Tower",
    createAndOpen: "Create and open",
    constructionPm: "Construction PM",
    unableToInitialize: "Unable to initialize the Web workspace.",
    retry: "Retry",
    refresh: "Refresh",
  },
  fa: {
    loading: "در حال بارگذاری محیط کار…",
    opening: "در حال باز کردن پروژه…",
    creating: "در حال ایجاد پروژه…",
    selectProject: "انتخاب پروژه",
    createFirstProject: "اولین پروژه خود را ایجاد کنید",
    noProjects: "هنوز پروژه‌ای برای این محیط کار در دسترس نیست.",
    createProject: "ایجاد پروژه",
    projectName: "نام پروژه",
    projectNamePlaceholder: "مثلاً برج ریورساید",
    createAndOpen: "ایجاد و باز کردن",
    constructionPm: "Construction PM",
    unableToInitialize: "راه‌اندازی محیط کار وب امکان‌پذیر نیست.",
    retry: "تلاش مجدد",
    refresh: "بازخوانی",
  },
};

export function getBootstrapLabels(locale: WorkspaceLocale): BootstrapLabels {
  return labels[locale];
}

const errorMessages: Record<WorkspaceLocale, Readonly<Record<string, string>>> = {
  en: {
    "error.api": "The request could not be completed. Please try again.",
    "error.network": "Unable to connect to the server. Check your connection and try again.",
    "error.forbidden": "You do not have permission to perform this action.",
    "error.authorization.denied": "Access to this project or action is not permitted.",
    "error.session.required": "Your session is missing. Sign in and try again.",
    "error.session.invalid": "Your session is invalid or has expired. Sign in again.",
    "error.projects.none": "No projects are available for this workspace yet.",
    "error.project.not_available": "The selected project is unavailable or you do not have access.",
    "error.project.id_required": "Select a valid project and try again.",
    "error.project.lifecycle": "The project could not be opened or updated.",
    "error.route.not_found": "This service is not available right now.",
    "error.request.invalid": "The request contains invalid or incomplete information.",
    "error.revision.conflict": "Project data changed after it was loaded. Refresh and try again.",
    "error.workspace_read.not_found": "Workspace data for this project could not be found.",
    "error.workspace_read.invalid_payload": "The workspace service returned an unexpected response. Refresh and try again.",
    "error.p6.presentation.invalid": "Workspace field and layout settings could not be loaded. Refresh and try again.",
    "error.schedule_query.invalid_payload": "The schedule query service returned an unexpected response.",
    "error.generic": "Unable to load the workspace. Refresh and try again, or contact support."
  },
  fa: {
    "error.api": "درخواست انجام نشد. لطفاً دوباره تلاش کنید.",
    "error.network": "اتصال به سرور برقرار نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.",
    "error.forbidden": "اجازه انجام این کار را ندارید.",
    "error.authorization.denied": "دسترسی به این پروژه یا انجام این عملیات مجاز نیست.",
    "error.session.required": "نشست کاربری شما در دسترس نیست. دوباره وارد شوید.",
    "error.session.invalid": "نشست کاربری شما نامعتبر است یا منقضی شده است. دوباره وارد شوید.",
    "error.projects.none": "هنوز پروژه‌ای برای این محیط کار در دسترس نیست.",
    "error.project.not_available": "پروژه انتخاب‌شده در دسترس نیست یا اجازه دسترسی به آن را ندارید.",
    "error.project.id_required": "یک پروژه معتبر انتخاب کنید و دوباره تلاش کنید.",
    "error.project.lifecycle": "باز کردن یا به‌روزرسانی پروژه انجام نشد.",
    "error.route.not_found": "این سرویس در حال حاضر در دسترس نیست.",
    "error.request.invalid": "اطلاعات درخواست ناقص یا نامعتبر است.",
    "error.revision.conflict": "اطلاعات پروژه پس از بارگذاری تغییر کرده است. صفحه را بازخوانی و دوباره تلاش کنید.",
    "error.workspace_read.not_found": "اطلاعات محیط کار این پروژه پیدا نشد.",
    "error.workspace_read.invalid_payload": "پاسخ سرویس محیط کار معتبر نیست. صفحه را بازخوانی و دوباره تلاش کنید.",
    "error.p6.presentation.invalid": "بارگذاری تنظیمات فیلدها و چیدمان محیط کار انجام نشد. صفحه را بازخوانی و دوباره تلاش کنید.",
    "error.schedule_query.invalid_payload": "پاسخ سرویس پرس‌وجوی زمان‌بندی غیرمنتظره است.",
    "error.generic": "بارگذاری محیط کار انجام نشد. صفحه را بازخوانی و دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
  }
};

export function getBootstrapErrorMessage(messageKey: string, locale: WorkspaceLocale): string {
  const messages = errorMessages[locale];
  return messages[messageKey] ?? messages["error.generic"] ?? getBootstrapLabels(locale).unableToInitialize;
}
