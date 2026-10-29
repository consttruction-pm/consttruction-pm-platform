export type WorkspaceStartupLocale = "en" | "fa";
export type WorkspaceStartupMode = "loading" | "slow" | "failed";

export type WorkspaceStartupCopy = {
  title: string;
  message: string;
  progressLabel: string;
  action: string;
  code: string;
};

export function getWorkspaceStartupCopy(
  locale: WorkspaceStartupLocale,
  mode: WorkspaceStartupMode,
): WorkspaceStartupCopy {
  const copy = {
    en: {
      loading: {
        title: "Opening your project workspace",
        message: "Loading the activity table, schedule timeline and project controls.",
        progressLabel: "Loading workspace",
        action: "Reload workspace",
        code: "",
      },
      slow: {
        title: "The workspace is taking longer than expected",
        message: "The application has not finished starting. You can reload this page; your saved project data is not changed by reloading.",
        progressLabel: "Workspace startup is delayed",
        action: "Reload workspace",
        code: "WORKSPACE_STARTUP_SLOW",
      },
      failed: {
        title: "The workspace could not be loaded",
        message: "The workspace application failed to start. Reload the page and try again. If this continues, share the diagnostic code with support.",
        progressLabel: "Workspace failed to start",
        action: "Reload workspace",
        code: "WORKSPACE_ENTRY_LOAD_FAILED",
      },
    },
    fa: {
      loading: {
        title: "در حال باز کردن محیط کار پروژه",
        message: "جدول فعالیت‌ها، خط زمان‌بندی و ابزارهای کنترل پروژه در حال بارگذاری هستند.",
        progressLabel: "بارگذاری محیط کار",
        action: "بارگذاری مجدد محیط کار",
        code: "",
      },
      slow: {
        title: "بارگذاری محیط کار بیش از حد معمول طول کشیده است",
        message: "راه‌اندازی برنامه هنوز کامل نشده است. می‌توانید صفحه را دوباره بارگذاری کنید؛ بارگذاری مجدد، داده‌های ذخیره‌شده پروژه را تغییر نمی‌دهد.",
        progressLabel: "راه‌اندازی محیط کار با تأخیر روبه‌رو است",
        action: "بارگذاری مجدد محیط کار",
        code: "WORKSPACE_STARTUP_SLOW",
      },
      failed: {
        title: "محیط کار بارگذاری نشد",
        message: "برنامه محیط کار با خطا راه‌اندازی شد. صفحه را دوباره بارگذاری کنید. اگر مشکل ادامه داشت، کد تشخیصی را به پشتیبانی بدهید.",
        progressLabel: "راه‌اندازی محیط کار ناموفق بود",
        action: "بارگذاری مجدد محیط کار",
        code: "WORKSPACE_ENTRY_LOAD_FAILED",
      },
    },
  } as const;
  return copy[locale][mode];
}

export function renderWorkspaceStartupMarkup(
  locale: WorkspaceStartupLocale,
  mode: WorkspaceStartupMode,
): string {
  const copy = getWorkspaceStartupCopy(locale, mode);
  const direction = locale === "fa" ? "rtl" : "ltr";
  const role = mode === "failed" ? "alert" : "status";
  const live = mode === "failed" ? "assertive" : "polite";
  const progress = mode === "loading"
    ? `<div class="cp-startup-progress" role="progressbar" aria-label="${copy.progressLabel}"><span></span></div>`
    : "";
  const code = copy.code
    ? `<p class="cp-startup-code" data-startup-code="${copy.code}">${copy.code}</p>`
    : "";
  const action = mode === "loading"
    ? ""
    : `<button type="button" class="cp-startup-reload" data-workspace-startup-reload>${copy.action}</button>`;
  return `<main class="cp-startup cp-startup--${mode}" data-workspace-startup="${mode}" lang="${locale}" dir="${direction}" role="${role}" aria-live="${live}">
    <section class="cp-startup-card" aria-labelledby="cp-startup-title">
      <div class="cp-startup-brand" aria-label="CUBI Platform"><span class="cp-startup-mark" aria-hidden="true">C</span><span>CUBI</span><span class="cp-startup-brand-caption">PROJECT WORKSPACE</span></div>
      <h1 id="cp-startup-title">${copy.title}</h1>
      <p class="cp-startup-message">${copy.message}</p>
      ${progress}
      ${code}
      ${action}
    </section>
  </main>`;
}

export function renderWorkspaceStartup(
  container: HTMLElement,
  locale: WorkspaceStartupLocale,
  mode: WorkspaceStartupMode,
): void {
  container.innerHTML = renderWorkspaceStartupMarkup(locale, mode);
  const reload = container.querySelector<HTMLButtonElement>("[data-workspace-startup-reload]");
  reload?.addEventListener("click", () => window.location.reload());
}
