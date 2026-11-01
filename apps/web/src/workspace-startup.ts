export type WorkspaceStartupLocale = "en" | "fa" | "de" | "zh";
export type WorkspaceStartupMode = "loading" | "slow" | "failed";

export type WorkspaceStartupCopy = {
  title: string;
  message: string;
  progressLabel: string;
  action: string;
  code: string;
};

function baseLocale(locale: string): WorkspaceStartupLocale {
  const base = locale.split("-")[0].toLowerCase();
  return base === "fa" || base === "de" || base === "zh" ? base : "en";
}

export function getWorkspaceStartupCopy(
  locale: string,
  mode: WorkspaceStartupMode,
): WorkspaceStartupCopy {
  const language = baseLocale(locale);
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
    de: {
      loading: {
        title: "Ihr Projektarbeitsbereich wird geöffnet",
        message: "Aktivitätstabelle, Terminplan-Zeitleiste und Projektsteuerung werden geladen.",
        progressLabel: "Arbeitsbereich wird geladen",
        action: "Arbeitsbereich neu laden",
        code: "",
      },
      slow: {
        title: "Der Arbeitsbereich benötigt länger als erwartet",
        message: "Die Anwendung wurde noch nicht vollständig gestartet. Sie können diese Seite neu laden; Ihre gespeicherten Projektdaten werden dadurch nicht verändert.",
        progressLabel: "Der Start des Arbeitsbereichs ist verzögert",
        action: "Arbeitsbereich neu laden",
        code: "WORKSPACE_STARTUP_SLOW",
      },
      failed: {
        title: "Der Arbeitsbereich konnte nicht geladen werden",
        message: "Die Arbeitsbereichsanwendung konnte nicht gestartet werden. Laden Sie die Seite neu. Wenn das Problem weiterhin besteht, nennen Sie dem Support den Diagnosecode.",
        progressLabel: "Der Arbeitsbereich konnte nicht gestartet werden",
        action: "Arbeitsbereich neu laden",
        code: "WORKSPACE_ENTRY_LOAD_FAILED",
      },
    },
    zh: {
      loading: {
        title: "正在打开您的项目工作区",
        message: "正在加载活动表格、进度计划时间轴和项目控制工具。",
        progressLabel: "正在加载工作区",
        action: "重新加载工作区",
        code: "",
      },
      slow: {
        title: "工作区加载时间超出预期",
        message: "应用程序尚未完成启动。您可以重新加载此页面；重新加载不会更改已保存的项目数据。",
        progressLabel: "工作区启动延迟",
        action: "重新加载工作区",
        code: "WORKSPACE_STARTUP_SLOW",
      },
      failed: {
        title: "工作区无法加载",
        message: "工作区应用程序启动失败。请重新加载页面后再试。如果问题持续，请将诊断代码提供给支持人员。",
        progressLabel: "工作区启动失败",
        action: "重新加载工作区",
        code: "WORKSPACE_ENTRY_LOAD_FAILED",
      },
    },
  } as const;
  return copy[language][mode];
}

export function renderWorkspaceStartupMarkup(
  locale: string,
  mode: WorkspaceStartupMode,
): string {
  const language = baseLocale(locale);
  const copy = getWorkspaceStartupCopy(language, mode);
  const direction = language === "fa" ? "rtl" : "ltr";
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
  return `<main class="cp-startup cp-startup--${mode}" data-workspace-startup="${mode}" lang="${language}" dir="${direction}" role="${role}" aria-live="${live}">
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
  locale: string,
  mode: WorkspaceStartupMode,
): void {
  container.innerHTML = renderWorkspaceStartupMarkup(locale, mode);
  const reload = container.querySelector<HTMLButtonElement>("[data-workspace-startup-reload]");
  reload?.addEventListener("click", () => window.location.reload());
}
