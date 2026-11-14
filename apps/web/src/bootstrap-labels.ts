import type { ClientError } from "./client.js";
import type { WorkspaceLocale } from "./workspace-model.js";
import { translateWorkspaceText } from "./workspace-localization.js";
import { translateUiString } from "./workspace-ui-translations.js";

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
  projectDescription: string;
  projectDescriptionPlaceholder: string;
  projectStartDate: string;
  projectStartDateJalaliPlaceholder: string;
  projectDateSystem: string;
  dateSystemGregorian: string;
  dateSystemJalali: string;
  projectBusinessDomain: string;
  projectObsResponsibleManager: string;
  projectObsResponsibleManagerHint: string;
  projectWebsite: string;
  projectWebsiteHint: string;
  projectLevelingPriority: string;
  projectLevelingPriorityHint: string;
  projectLevelingPrioritySave: string;
  projectLevelingPrioritySaved: string;
  projectLevelingPriorityUnavailable: string;
  projectCheckout: string;
  projectCheckoutCheckedIn: string;
  projectCheckoutCheckedOut: string;
  projectCheckoutOwner: string;
  projectCheckoutCheckOut: string;
  projectCheckoutCheckIn: string;
  projectCheckoutConflict: string;
  projectDefaults: string;
  projectDefaultsHint: string;
  projectDefaultActivityType: string;
  projectDefaultPercentCompleteType: string;
  projectActivityIdPrefix: string;
  projectActivityIdSuffix: string;
  projectActivityIdIncrement: string;
  projectActivityIdIncrementHint: string;
  projectIncrementActivityId: string;
  activityTypeTaskDependent: string;
  activityTypeResourceDependent: string;
  activityTypeLevelOfEffort: string;
  activityTypeStartMilestone: string;
  activityTypeFinishMilestone: string;
  activityTypeWbsSummary: string;
  percentTypeDuration: string;
  percentTypeUnits: string;
  percentTypePhysical: string;
  percentTypeScope: string;
  businessDomainNotClassified: string;
  businessDomainConstruction: string;
  businessDomainOilGas: string;
  businessDomainInfrastructure: string;
  businessDomainIndustrial: string;
  businessDomainEnergy: string;
  businessDomainOther: string;
  projectSettings: string;
  settingsTitle: string;
  settingsClose: string;
  settingsSave: string;
  settingsSaving: string;
  settingsSaved: string;
  settingsRetry: string;
  settingsFailed: string;
  settingsConflict: string;
  settingsForbidden: string;
  settingsPrimaryCalendar: string;
  settingsPrimaryCalendarHint: string;
  settingsRevision: string;
  settingsReloadLatest: string;
  settingsProjectStatus: string;
  settingsProjectStatusHint: string;
  settingsStatusSave: string;
  settingsStatusSaved: string;
  settingsStatusHistory: string;
  settingsStatusHistoryEmpty: string;
  settingsStatusActive: string;
  settingsStatusInactive: string;
  settingsStatusPlanned: string;
  settingsStatusWhatIf: string;
  createAndOpen: string;
  constructionPm: string;
  unableToInitialize: string;
  retry: string;
  refresh: string;
  languageLabel: string;
  switchLanguage: string;
  projectListAria: string;
  validationNameRequired: string;
  validationStartDateInvalid: string;
  validationNameLength: string;
  createFailed: string;
  errorTitle: string;
  errorNetwork: string;
  errorSession: string;
  errorSignIn: string;
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
    projectDescription: "Description",
    projectDescriptionPlaceholder: "Optional scope, client or contract note",
    projectStartDate: "Start date",
    projectStartDateJalaliPlaceholder: "1405/07/15",
    projectDateSystem: "Date system",
    dateSystemGregorian: "Gregorian",
    dateSystemJalali: "Jalali",
    projectBusinessDomain: "Business Domain",
    projectObsResponsibleManager: "OBS responsible manager",
    projectObsResponsibleManagerHint: "Recorded on the project and shown in Project Details after reload.",
    projectWebsite: "Web-site",
    projectWebsiteHint: "Optional absolute http:// or https:// address.",
    projectLevelingPriority: "Leveling priority",
    projectLevelingPriorityHint: "1–100. Stored with the project schedule settings used by the leveler.",
    projectLevelingPrioritySave: "Save leveling priority",
    projectLevelingPrioritySaved: "Leveling priority saved.",
    projectLevelingPriorityUnavailable: "No schedule settings are stored for this project yet.",
    projectCheckout: "Project checkout",
    projectCheckoutCheckedIn: "Not checked out. Other users may edit this project.",
    projectCheckoutCheckedOut: "Checked out. Only the checkout owner can edit the project.",
    projectCheckoutOwner: "Checked out by {user} at {time}.",
    projectCheckoutCheckOut: "Check out",
    projectCheckoutCheckIn: "Check in",
    projectCheckoutConflict: "This project is checked out by another user. Check it in there before editing.",
    projectDefaults: "Defaults",
    projectDefaultsHint: "Applied when a new activity is created. Existing activities keep their values.",
    projectDefaultActivityType: "Default activity type",
    projectDefaultPercentCompleteType: "Percent complete type",
    projectActivityIdPrefix: "Activity ID prefix",
    projectActivityIdSuffix: "Activity ID suffix",
    projectActivityIdIncrement: "Increment",
    projectActivityIdIncrementHint: "1 to 10000. Used to propose the next Activity ID.",
    projectIncrementActivityId: "Increment Activity ID based on selected activity",
    activityTypeTaskDependent: "Task Dependent",
    activityTypeResourceDependent: "Resource Dependent",
    activityTypeLevelOfEffort: "Level of Effort",
    activityTypeStartMilestone: "Start Milestone",
    activityTypeFinishMilestone: "Finish Milestone",
    activityTypeWbsSummary: "WBS Summary",
    percentTypeDuration: "Duration",
    percentTypeUnits: "Units",
    percentTypePhysical: "Physical",
    percentTypeScope: "Scope",
    businessDomainNotClassified: "Not classified",
    businessDomainConstruction: "Construction",
    businessDomainOilGas: "Oil & Gas",
    businessDomainInfrastructure: "Infrastructure",
    businessDomainIndustrial: "Industrial",
    businessDomainEnergy: "Energy",
    businessDomainOther: "Other",
    projectSettings: "Project settings",
    settingsTitle: "Project settings",
    settingsClose: "Close",
    settingsSave: "Save changes",
    settingsSaving: "Saving…",
    settingsSaved: "Saved. The project configuration now has revision",
    settingsRetry: "Retry",
    settingsFailed: "The changes were not saved. The stored project was not changed.",
    settingsConflict: "This project changed in another session. Reload the latest values before saving again.",
    settingsForbidden: "Your account does not have permission to edit this project.",
    settingsPrimaryCalendar: "Primary calendar",
    settingsPrimaryCalendarHint: "Leave empty to keep the calendar created with the project.",
    settingsRevision: "Configuration revision",
    settingsReloadLatest: "Reload latest values",
    settingsProjectStatus: "Project status",
    settingsProjectStatusHint: "Active, Inactive, Planned or What-If. Changing it is recorded with the actor and revision.",
    settingsStatusSave: "Save status",
    settingsStatusSaved: "Status saved.",
    settingsStatusHistory: "Status history",
    settingsStatusHistoryEmpty: "No status changes are stored for this project.",
    settingsStatusActive: "Active",
    settingsStatusInactive: "Inactive",
    settingsStatusPlanned: "Planned",
    settingsStatusWhatIf: "What-If",
    createAndOpen: "Create and open",
    constructionPm: "CUBI Workspace",
    unableToInitialize: "Unable to initialize the web workspace.",
    retry: "Retry",
    refresh: "Refresh",
    languageLabel: "Language",
    switchLanguage: "Switch language to {language}",
    projectListAria: "Projects available to your account",
    validationNameRequired: "Enter a project name.",
    validationStartDateInvalid: "Enter a valid date in the selected calendar.",
    validationNameLength: "Use a project name between 2 and 120 characters.",
    createFailed: "The project was not created. Check the name and try again.",
    errorTitle: "The workspace could not open",
    errorNetwork: "The server could not be reached. Check your connection and try again.",
    errorSession: "Your session is no longer valid. Sign in again to reopen this workspace.",
    errorSignIn: "Sign in again",
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
    projectDescription: "توضیحات",
    projectDescriptionPlaceholder: "دامنه، کارفرما یا یادداشت قرارداد (اختیاری)",
    projectStartDate: "تاریخ شروع",
    projectStartDateJalaliPlaceholder: "۱۴۰۵/۰۷/۱۵",
    projectDateSystem: "تقویم نمایشی",
    dateSystemGregorian: "میلادی",
    dateSystemJalali: "شمسی",
    projectBusinessDomain: "حوزهٔ کاری",
    projectObsResponsibleManager: "مدیر مسئول OBS",
    projectObsResponsibleManagerHint: "روی پروژه ذخیره می‌شود و پس از بازخوانی در جزئیات پروژه نمایش داده می‌شود.",
    projectWebsite: "وب‌سایت",
    projectWebsiteHint: "نشانی کامل و اختیاری با http:// یا https://.",
    projectLevelingPriority: "اولویت تسطیح",
    projectLevelingPriorityHint: "۱ تا ۱۰۰. همراه با تنظیمات زمان‌بندی پروژه که موتور تسطیح استفاده می‌کند ذخیره می‌شود.",
    projectLevelingPrioritySave: "ذخیرهٔ اولویت تسطیح",
    projectLevelingPrioritySaved: "اولویت تسطیح ذخیره شد.",
    projectLevelingPriorityUnavailable: "هنوز تنظیمات زمان‌بندی برای این پروژه ذخیره نشده است.",
    projectCheckout: "قفل ویرایش پروژه",
    projectCheckoutCheckedIn: "پروژه قفل نیست. کاربران دیگر می‌توانند آن را ویرایش کنند.",
    projectCheckoutCheckedOut: "پروژه قفل شده است. فقط صاحب قفل می‌تواند آن را ویرایش کند.",
    projectCheckoutOwner: "قفل‌شده توسط {user} در {time}.",
    projectCheckoutCheckOut: "قفل کردن",
    projectCheckoutCheckIn: "باز کردن قفل",
    projectCheckoutConflict: "این پروژه توسط کاربر دیگری قفل شده است. پیش از ویرایش، قفل آن را باز کنید.",
    projectDefaults: "پیش‌فرض‌ها",
    projectDefaultsHint: "هنگام ساخت فعالیت جدید اعمال می‌شود. فعالیت‌های موجود مقادیر خود را نگه می‌دارند.",
    projectDefaultActivityType: "نوع پیش‌فرض فعالیت",
    projectDefaultPercentCompleteType: "نوع درصد تکمیل",
    projectActivityIdPrefix: "پیشوند شناسهٔ فعالیت",
    projectActivityIdSuffix: "پسوند شناسهٔ فعالیت",
    projectActivityIdIncrement: "گام افزایش",
    projectActivityIdIncrementHint: "۱ تا ۱۰۰۰۰. برای پیشنهاد شناسهٔ بعدی به کار می‌رود.",
    projectIncrementActivityId: "افزایش شناسهٔ فعالیت بر پایهٔ فعالیت انتخاب‌شده",
    activityTypeTaskDependent: "وابسته به وظیفه",
    activityTypeResourceDependent: "وابسته به منبع",
    activityTypeLevelOfEffort: "تلاش مستمر",
    activityTypeStartMilestone: "نقطه عطف آغاز",
    activityTypeFinishMilestone: "نقطه عطف پایان",
    activityTypeWbsSummary: "خلاصهٔ WBS",
    percentTypeDuration: "مدت",
    percentTypeUnits: "واحدها",
    percentTypePhysical: "فیزیکی",
    percentTypeScope: "دامنه",
    businessDomainNotClassified: "طبقه‌بندی‌نشده",
    businessDomainConstruction: "ساخت‌وساز",
    businessDomainOilGas: "نفت و گاز",
    businessDomainInfrastructure: "زیرساخت",
    businessDomainIndustrial: "صنعتی",
    businessDomainEnergy: "انرژی",
    businessDomainOther: "سایر",
    projectSettings: "تنظیمات پروژه",
    settingsTitle: "تنظیمات پروژه",
    settingsClose: "بستن",
    settingsSave: "ذخیرهٔ تغییرات",
    settingsSaving: "در حال ذخیره…",
    settingsSaved: "ذخیره شد. شمارهٔ بازبینی پیکربندی پروژه اکنون",
    settingsRetry: "تلاش مجدد",
    settingsFailed: "تغییرات ذخیره نشد. پروژهٔ ذخیره‌شده تغییری نکرده است.",
    settingsConflict: "این پروژه در نشست دیگری تغییر کرده است. پیش از ذخیرهٔ دوباره، آخرین مقادیر را بازخوانی کنید.",
    settingsForbidden: "حساب شما اجازهٔ ویرایش این پروژه را ندارد.",
    settingsPrimaryCalendar: "تقویم اصلی",
    settingsPrimaryCalendarHint: "برای نگه‌داشتن تقویمی که همراه پروژه ساخته شد، خالی بگذارید.",
    settingsRevision: "بازبینی پیکربندی",
    settingsReloadLatest: "بازخوانی آخرین مقادیر",
    settingsProjectStatus: "وضعیت پروژه",
    settingsProjectStatusHint: "فعال، غیرفعال، برنامه‌ریزی‌شده یا فرضی. هر تغییر همراه با کاربر و بازبینی ثبت می‌شود.",
    settingsStatusSave: "ذخیرهٔ وضعیت",
    settingsStatusSaved: "وضعیت ذخیره شد.",
    settingsStatusHistory: "تاریخچهٔ وضعیت",
    settingsStatusHistoryEmpty: "هیچ تغییر وضعیتی برای این پروژه ذخیره نشده است.",
    settingsStatusActive: "فعال",
    settingsStatusInactive: "غیرفعال",
    settingsStatusPlanned: "برنامه‌ریزی‌شده",
    settingsStatusWhatIf: "فرضی",
    createAndOpen: "ایجاد و باز کردن",
    constructionPm: "فضای کاری کوبی",
    unableToInitialize: "راه‌اندازی محیط کار وب امکان‌پذیر نیست.",
    retry: "تلاش مجدد",
    refresh: "بازخوانی",
    languageLabel: "زبان",
    switchLanguage: "تغییر زبان به {language}",
    projectListAria: "پروژه‌های در دسترس حساب شما",
    validationNameRequired: "نام پروژه را وارد کنید.",
    validationStartDateInvalid: "تاریخ معتبری مطابق تقویم انتخاب‌شده وارد کنید.",
    validationNameLength: "نام پروژه باید بین ۲ تا ۱۲۰ نویسه باشد.",
    createFailed: "پروژه ایجاد نشد. نام را بررسی کنید و دوباره تلاش کنید.",
    errorTitle: "محیط کار باز نشد",
    errorNetwork: "ارتباط با سرور برقرار نشد. اتصال خود را بررسی کنید و دوباره تلاش کنید.",
    errorSession: "نشست شما دیگر معتبر نیست. برای باز کردن دوبارهٔ محیط کار، مجدداً وارد شوید.",
    errorSignIn: "ورود دوباره",
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
  return Object.fromEntries(
    Object.entries(baseline).map(([key, value]) => {
      const packValue = translateWorkspaceText(locale, `bootstrap.${key}`, value);
      return [key, translateUiString(locale, packValue) ?? packValue];
    }),
  ) as BootstrapLabels;
}

export type BootstrapErrorCopy = {
  title: string;
  message: string;
  /** Technical code for support. Never a raw untranslated user-facing message. */
  reference: string;
};

const SESSION_CODES = new Set([
  "SESSION_REQUIRED",
  "SESSION_NOT_FOUND",
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

export function isSessionBootstrapError(
  error: Pick<ClientError, "code" | "message_key">,
): boolean {
  const code = String(error.code || "");
  const messageKey = String(error.message_key || "");
  return SESSION_CODES.has(code) || messageKey.startsWith("error.session");
}

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
  else if (isSessionBootstrapError(error)) message = t.errorSession;
  else if (FORBIDDEN_CODES.has(code) || messageKey.includes("forbidden") || messageKey.includes("permission")) message = t.errorForbidden;
  else if (PROJECT_CODES.has(code) || messageKey === "error.project.not_available") message = t.errorProjectUnavailable;
  else if (messageKey.startsWith("error.workspace")) message = t.errorWorkspace;
  else if (messageKey.startsWith("error.p6") || code === "P6_PRESENTATION_LOAD_FAILED") message = t.errorP6;
  return { title: t.errorTitle, message, reference: code };
}
