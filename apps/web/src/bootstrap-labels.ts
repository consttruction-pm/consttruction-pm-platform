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
