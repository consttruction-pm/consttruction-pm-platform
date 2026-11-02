import type { WorkspaceActivityRow, WorkspaceCalendarMode, WorkspaceCellValue, WorkspaceColumn, WorkspaceGanttScale, WorkspaceRelationshipRow, WorkspaceRelationshipType, WorkspaceState } from "./workspace-model.js";
import { createGanttAxisTicks, createGanttBarGeometry, createGanttLinkGeometry, createGanttScale, type GanttBarGeometry } from "./workspace-gantt.js";
import { filterAndSortActivities } from "./workspace-filter-sort.js";
import { formatWorkspaceCalendarDate } from "./workspace-calendar-display.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel, getWorkspaceNavigationSubmenuLabel } from "./workspace-navigation.js";
import { localizeWorkspaceLabel, translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";
import { SCHEDULING_REFERENCE_CATALOG } from "./scheduling-reference-catalog.generated.js";
import { cubiPlatformLogoUrl } from "./cubi-brand-assets.js";
import { workspaceIcon } from "./workspace-icons.js";
import { renderWorkspaceCommandShell } from "./workspace-command-shell.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings", mainMenu: "Main Menu", currentSurface: "Current workspace surface", submenu: "submenu", formulaColumn: "formula column", fieldChooser: "Field Chooser", fields: "Fields", undo: "Undo", redo: "Redo", layoutHistory: "Layout history", layoutUndone: "Last layout change undone.", layoutRedone: "Layout change reapplied.", layoutRestored: "Layout revision restored.", layoutHistoryEmpty: "No earlier layout revision is available.", layoutSaveFailed: "Layout change was not saved.", layoutConflict: "Another session changed this layout. The latest saved revision was reloaded.", restore: "Restore", revisionOption: "revision", columnUnit: "column(s)", add: "Add", remove: "Remove", moveUp: "Move up", moveDown: "Move down", narrower: "Narrower", wider: "Wider", alignStart: "Align left", alignCenter: "Align center", alignEnd: "Align right", pin: "Pin", unpin: "Unpin", freeze: "Freeze", unfreeze: "Unfreeze", hide: "Hide", show: "Show", rename: "Rename", findings: "Findings", proposedActions: "Proposed Actions", traceability: "Traceability", sources: "Sources", approvalRequired: "Approval Required", humanApprovalRequired: "Human approval required", noApprovalFlag: "No approval flag", sourceUnit: "source(s)", activityLinkUnit: "activity link(s)", evidenceUnit: "evidence", inspections: "Inspections", qualityNcr: "Quality / NCR", safety: "Safety", punchCloseout: "Punch / Closeout", due: "Due", supplier: "Supplier", reference: "Ref", amount: "Amount", itemUnit: "item(s)", linkedReferenceUnit: "linked reference(s)", stored: "stored", noStorage: "no storage", approval: "Approval", date: "Date", notices: "Notices", changeCases: "Change Cases", claims: "Claims", impactLinks: "Impact Links", scheduleLabel: "Schedule", costLabel: "Cost", noticeLabel: "Notice", changeLabel: "Change", entitlement: "Entitlement", decision: "Decision", impactLinkLabel: "Impact links",
    referenceTitle: "Scheduling logic & implementation reference", referenceDescription: "Browse scheduling requirements, calculation contracts and review evidence. A listed requirement is not proof of implementation; status is evidence-based.", referenceSearch: "Search the reference", referenceSearchPlaceholder: "Search by ID, rule, option, or status…", referenceNoMatches: "No matching entries.", referenceVersion: "Reference version", referenceAsOf: "Catalog date", referenceRequirementCount: "requirements", referenceFormulaCount: "calculation contracts", referenceDocumentationCount: "documentation review tracks", referenceMappedStatus: "Mapped; parity not yet proven", referenceGapStatus: "Known implementation gap", referenceInventoryStatus: "Inventory / acceptance evidence required", referenceFormulaStatus: "Formula contract; parity not yet proven", referenceRuleLabel: "Required behavior", referenceOptionsLabel: "Options", referenceGapLabel: "Known gap / remaining work", referenceInputsLabel: "Inputs", referenceCalendarRulesLabel: "Units & calendar rules", referenceEdgeCasesLabel: "Edge cases", referenceReviewLabel: "Review status", referenceRemainingLabel: "Remaining review work", referenceLinkedReqLabel: "Related requirement IDs", referenceRelationshipsGroupLabel: "Relationships & lag", referenceCalendarsGroupLabel: "Calendars & work time", referenceOptionsGroupLabel: "Schedule options & Data Date", referenceResourcesGroupLabel: "Resources & leveling", referenceProgressGroupLabel: "Progress & baselines", referenceOtherGroupLabel: "Other project-control areas", referenceFormulaGroupLabel: "Calculation formula contracts", referenceDocumentationGroupLabel: "Documentation review register", referenceCatalogGroupLabel: "Requirement catalogue", referenceDocReviewedLabel: "Core behavior extracted", referenceDocPartialLabel: "Partially reviewed", referenceDocPendingLabel: "Review not complete", referenceReviewNotice: "This catalogue is for traceability. Editing controls, persistent schedule updates and execution must be wired to the shared scheduling core and acceptance-tested separately.",
    wbs: "Project / WBS", wbsCreate: "Add WBS", wbsEdit: "Edit selected WBS", wbsCode: "Code", wbsName: "Name", wbsParent: "Parent WBS", wbsProjectRoot: "Project root", wbsSequence: "Sequence", wbsSave: "Save WBS", wbsDelete: "Delete selected", wbsSelectPrompt: "Select a WBS node to edit.", wbsMutationFailed: "WBS change failed.", wbsDeleteConfirm: "Delete this WBS node?", activities: "Activity Grid", activityCreate: "Add activity", activityEdit: "Edit activity", activityId: "Activity ID", activityName: "Activity name", activityDuration: "Duration", activityDurationUnit: "Duration unit", activityWbs: "WBS", activityCreateFailed: "Activity could not be saved.", activityFilter: "Filter activities", activityFilterPlaceholder: "ID, name, WBS, status…", activitySort: "Sort by", groupBy: "Group by", groupNone: "No grouping", sortNone: "Original order", sortAscending: "Ascending", sortDescending: "Descending", matchingActivities: "activities shown", noMatchingActivities: "No activities match the current filter.", gantt: "Gantt Chart", details: "Details", interchange: "Import / Export", resourceCapacity: "Resource Max Units / Time", scheduleOptions: "Schedule Options", runSchedule: "Run Schedule", formulaEditor: "Formula editor", scheduleReference: "Scheduling Code Reference", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noWbs: "No WBS elements loaded", noSchedule: "No scheduled activities", revision: "Revision", projectSettings: "Project settings", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
    logic: "Logic / Relationships", predecessorsColumn: "Predecessors", relationshipCreate: "Add relationship", predecessor: "Predecessor", successor: "Successor", relationshipType: "Type", relationshipLag: "Lag", relationshipLagUnit: "Lag unit", relationshipDelete: "Delete", relationshipEdit: "Edit", relationshipSave: "Save relationship", noRelationships: "No relationships defined yet.", relationshipCreateFailed: "Relationship could not be saved.", relationshipDeleteFailed: "Relationship could not be deleted.", relationshipConflict: "The relationship changed in another session. Reload and try again.", workingDay: "Working day", workingHour: "Working hour",
    ganttScaleLabel: "Timeline scale", scaleDay: "Day", scaleWeek: "Week", scaleMonth: "Month", scaleQuarter: "Quarter", scaleYear: "Year", ganttLinks: "Dependency links", ganttLinksToggle: "Dependency links", ganttLinksOn: "Shown", ganttLinksOff: "Hidden", milestone: "Milestone",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات", mainMenu: "منوی اصلی", currentSurface: "سطح فعلی محیط کار", submenu: "زیرمنو", formulaColumn: "ستون فرمول", fieldChooser: "انتخاب‌گر فیلد", fields: "فیلدها", undo: "بازگردانی", redo: "تکرار", layoutHistory: "تاریخچهٔ چیدمان", layoutUndone: "آخرین تغییر چیدمان بازگردانی شد.", layoutRedone: "تغییر چیدمان دوباره اعمال شد.", layoutRestored: "نسخهٔ چیدمان بازگردانی شد.", layoutHistoryEmpty: "نسخهٔ قدیمی‌تری از چیدمان در دسترس نیست.", layoutSaveFailed: "تغییر چیدمان ذخیره نشد.", layoutConflict: "نشست دیگری این چیدمان را تغییر داد. آخرین نسخهٔ ذخیره‌شده دوباره بارگذاری شد.", restore: "بازگردانی نسخه", revisionOption: "نسخه", columnUnit: "ستون", add: "افزودن", remove: "حذف", moveUp: "جابجایی به بالا", moveDown: "جابجایی به پایین", narrower: "باریک‌تر", wider: "عریض‌تر", alignStart: "تراز چپ", alignCenter: "تراز وسط", alignEnd: "تراز راست", pin: "سنجاق کردن", unpin: "برداشتن سنجاق", freeze: "ثابت کردن", unfreeze: "لغو ثابت‌سازی", hide: "پنهان کردن", show: "نمایش", rename: "تغییر نام", findings: "یافته‌ها", proposedActions: "اقدامات پیشنهادی", traceability: "ردیابی", sources: "منابع", approvalRequired: "نیازمند تأیید", humanApprovalRequired: "نیازمند تأیید انسانی", noApprovalFlag: "بدون پرچم تأیید", sourceUnit: "منبع", activityLinkUnit: "پیوند فعالیت", evidenceUnit: "مستند", inspections: "بازرسی‌ها", qualityNcr: "کیفیت / NCR", safety: "ایمنی", punchCloseout: "پانچ / بستن موارد", due: "سررسید", supplier: "تأمین‌کننده", reference: "مرجع", amount: "مبلغ", itemUnit: "مورد", linkedReferenceUnit: "مرجع پیوندشده", stored: "ذخیره‌شده", noStorage: "بدون ذخیره‌سازی", approval: "تأیید", date: "تاریخ", notices: "اعلان‌ها", changeCases: "موارد تغییر", claims: "ادعاها", impactLinks: "پیوندهای اثر", scheduleLabel: "زمان‌بندی", costLabel: "هزینه", noticeLabel: "اعلان", changeLabel: "تغییر", entitlement: "استحقاق", decision: "تصمیم", impactLinkLabel: "پیوندهای اثر",
    referenceTitle: "مرجع منطق و پیاده‌سازی زمان‌بندی", referenceDescription: "الزامات زمان‌بندی، قراردادهای محاسباتی و شواهد بازبینی را مرور کنید. ثبت یک الزام به‌معنای اثبات پیاده‌سازی نیست؛ وضعیت بر پایهٔ شواهد است.", referenceSearch: "جست‌وجو در مرجع", referenceSearchPlaceholder: "جست‌وجو بر اساس شناسه، قاعده، گزینه یا وضعیت…", referenceNoMatches: "موردی با این جست‌وجو یافت نشد.", referenceVersion: "نسخه مرجع", referenceAsOf: "تاریخ کاتالوگ", referenceRequirementCount: "الزام", referenceFormulaCount: "قرارداد محاسباتی", referenceDocumentationCount: "مسیر بازبینی مستندات", referenceMappedStatus: "مسیر کد شناسایی شده؛ تطبیق هنوز اثبات نشده", referenceGapStatus: "شکاف اجرایی شناخته‌شده", referenceInventoryStatus: "تکمیل فهرست و شواهد پذیرش لازم است", referenceFormulaStatus: "قرارداد فرمول؛ تطبیق هنوز اثبات نشده", referenceRuleLabel: "رفتار الزامی", referenceOptionsLabel: "گزینه‌ها", referenceGapLabel: "شکاف شناخته‌شده / کار باقیمانده", referenceInputsLabel: "ورودی‌ها", referenceCalendarRulesLabel: "واحدها و قواعد تقویم", referenceEdgeCasesLabel: "حالت‌های مرزی", referenceReviewLabel: "وضعیت بازبینی", referenceRemainingLabel: "کار باقیمانده در بازبینی", referenceLinkedReqLabel: "شناسه‌های الزامات مرتبط", referenceRelationshipsGroupLabel: "روابط و وقفه‌ها", referenceCalendarsGroupLabel: "تقویم‌ها و ساعات کاری", referenceOptionsGroupLabel: "گزینه‌های زمان‌بندی و تاریخ داده", referenceResourcesGroupLabel: "منابع و تسطیح", referenceProgressGroupLabel: "پیشرفت و مبناها", referenceOtherGroupLabel: "سایر حوزه‌های کنترل پروژه", referenceFormulaGroupLabel: "قرارداد فرمول‌های محاسباتی", referenceDocumentationGroupLabel: "دفتر ثبت بازبینی مستندات", referenceCatalogGroupLabel: "فهرست الزامات", referenceDocReviewedLabel: "رفتار اصلی استخراج شده", referenceDocPartialLabel: "بازبینی جزئی", referenceDocPendingLabel: "بازبینی کامل نشده", referenceReviewNotice: "این فهرست برای ردیابی الزامات است. کنترل‌های ویرایش، به‌روزرسانی پایدار زمان‌بندی و اجرای محاسبه باید جداگانه به هستهٔ مشترک متصل و با آزمون پذیرش تأیید شوند.",
    wbs: "پروژه / WBS", wbsCreate: "افزودن ساختار شکست", wbsEdit: "ویرایش ساختار انتخاب‌شده", wbsCode: "کد", wbsName: "نام", wbsParent: "والد", wbsProjectRoot: "ریشهٔ پروژه", wbsSequence: "ترتیب", wbsSave: "ذخیره", wbsDelete: "حذف مورد انتخاب‌شده", wbsSelectPrompt: "برای ویرایش یک ردیف را انتخاب کنید.", wbsMutationFailed: "تغییر ساختار شکست ناموفق بود.", wbsDeleteConfirm: "این ردیف ساختار شکست حذف شود؟", activities: "جدول فعالیت‌ها", activityCreate: "افزودن فعالیت", activityEdit: "ویرایش فعالیت", activityId: "شناسه فعالیت", activityName: "نام فعالیت", activityDuration: "مدت", activityDurationUnit: "واحد مدت", activityWbs: "ساختار شکست", activityCreateFailed: "ذخیره فعالیت انجام نشد.", activityFilter: "پالایش فعالیت‌ها", activityFilterPlaceholder: "شناسه، نام، WBS، وضعیت…", activitySort: "ترتیب بر اساس", groupBy: "گروه‌بندی بر اساس", groupNone: "بدون گروه‌بندی", sortNone: "ترتیب اصلی", sortAscending: "صعودی", sortDescending: "نزولی", matchingActivities: "فعالیت نمایش‌داده‌شده", noMatchingActivities: "هیچ فعالیتی با پالایهٔ فعلی مطابقت ندارد.", gantt: "گانت", details: "جزئیات", interchange: "ورود / خروجی", resourceCapacity: "حداکثر واحد / زمان منبع", scheduleOptions: "تنظیمات زمان‌بندی", runSchedule: "اجرای زمان‌بندی", formulaEditor: "ویرایشگر فرمول", scheduleReference: "مرجع کد زمان‌بندی", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noWbs: "ساختار شکست کار بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", projectSettings: "تنظیمات پروژه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
    logic: "منطق / روابط", predecessorsColumn: "پیش‌نیازها", relationshipCreate: "افزودن رابطه", predecessor: "پیش‌نیاز", successor: "پس‌نیاز", relationshipType: "نوع", relationshipLag: "وقفه", relationshipLagUnit: "واحد وقفه", relationshipDelete: "حذف", relationshipEdit: "ویرایش", relationshipSave: "ذخیرهٔ رابطه", noRelationships: "هنوز رابطه‌ای تعریف نشده است.", relationshipCreateFailed: "ذخیره رابطه انجام نشد.", relationshipDeleteFailed: "حذف رابطه انجام نشد.", relationshipConflict: "رابطه در نشست دیگری تغییر کرده است. صفحه را دوباره بارگذاری کنید.", workingDay: "روز کاری", workingHour: "ساعت کاری",
    ganttScaleLabel: "مقیاس زمان‌بندی", scaleDay: "روز", scaleWeek: "هفته", scaleMonth: "ماه", scaleQuarter: "فصل", scaleYear: "سال", ganttLinks: "پیوندهای وابستگی", ganttLinksToggle: "نمایش پیوندهای وابستگی", ganttLinksOn: "نمایش", ganttLinksOff: "پنهان", milestone: "نقطه عطف",
  },
} as const;

const ACTIVITY_CREATE_FIELDS = {
  activity_type: {
    label: { en: "Activity type", fa: "نوع فعالیت" },
    defaultValue: "Task Dependent",
    options: [
      { value: "Task Dependent", en: "Task Dependent", fa: "وابسته به فعالیت" },
      { value: "Resource Dependent", en: "Resource Dependent", fa: "وابسته به منابع" },
      { value: "Level of Effort", en: "Level of Effort", fa: "سطح تلاش" },
      { value: "Start Milestone", en: "Start Milestone", fa: "نقطه عطف شروع" },
      { value: "Finish Milestone", en: "Finish Milestone", fa: "نقطه عطف پایان" },
      { value: "WBS Summary", en: "WBS Summary", fa: "خلاصه WBS" },
    ],
  },
  status: {
    label: { en: "Status", fa: "وضعیت" },
    defaultValue: "Not Started",
    options: [
      { value: "Not Started", en: "Not Started", fa: "شروع‌نشده" },
      { value: "In Progress", en: "In Progress", fa: "در حال اجرا" },
      { value: "Completed", en: "Completed", fa: "تکمیل‌شده" },
    ],
  },
  status_code: {
    label: { en: "Status code", fa: "کد وضعیت" },
    defaultValue: "Planned",
    options: [
      { value: "Planned", en: "Planned", fa: "برنامه‌ریزی‌شده" },
      { value: "Active", en: "Active", fa: "فعال" },
      { value: "Inactive", en: "Inactive", fa: "غیرفعال" },
      { value: "What-If", en: "What-If", fa: "فرضی" },
      { value: "Requested", en: "Requested", fa: "درخواست‌شده" },
      { value: "Template", en: "Template", fa: "الگو" },
    ],
  },
  percent_complete_type: {
    label: { en: "Percent complete type", fa: "نوع درصد تکمیل" },
    defaultValue: "DURATION",
    options: [
      { value: "DURATION", en: "Duration", fa: "مدت" },
      { value: "UNITS", en: "Units", fa: "واحد" },
      { value: "PHYSICAL", en: "Physical", fa: "فیزیکی" },
      { value: "SCOPE", en: "Scope", fa: "دامنه" },
    ],
  },
  leveling_priority: {
    label: { en: "Leveling priority", fa: "اولویت تسطیح منابع" },
    defaultValue: "Normal",
    options: [
      { value: "Top", en: "Top", fa: "بالاترین" },
      { value: "High", en: "High", fa: "زیاد" },
      { value: "Normal", en: "Normal", fa: "عادی" },
      { value: "Low", en: "Low", fa: "کم" },
      { value: "Lowest", en: "Lowest", fa: "پایین‌ترین" },
    ],
  },
} as const;

type ActivityCreateChoiceField = keyof typeof ACTIVITY_CREATE_FIELDS;

function getActivityCreateFieldLabel(locale: string, field: ActivityCreateChoiceField): string {
  const label = ACTIVITY_CREATE_FIELDS[field].label;
  return translateWorkspaceUiText(locale, label.en, label.fa);
}

function renderActivityCreateOptions(locale: string, field: ActivityCreateChoiceField): string {
  const config = ACTIVITY_CREATE_FIELDS[field];
  return config.options.map((option) =>
    `<option value="${escapeAttribute(option.value)}" ${option.value === config.defaultValue ? "selected" : ""}>${escapeHtml(translateWorkspaceUiText(locale, option.en, option.fa))}</option>`
  ).join("");
}

type WorkspaceLabels = Record<keyof typeof labels.en, string>;

function getWorkspaceLabels(locale: string): WorkspaceLabels {
  return Object.fromEntries(Object.entries(labels.en).map(([key, english]) => {
    const packed = translateWorkspaceText(locale, `workspace.${key}`, "");
    if (packed) return [key, packed];
    const persian = (labels.fa as Record<string, string>)[key] ?? english;
    return [key, translateWorkspaceUiText(locale, english, persian)];
  })) as WorkspaceLabels;
}

function uiText(locale: string, en: string, fa: string): string {
  return translateWorkspaceUiText(locale, en, fa);
}

type WorkspaceRenderRecord = { state: WorkspaceState; options: WorkspaceRendererOptions };
const workspaceRenderRecords = new WeakMap<HTMLElement, WorkspaceRenderRecord>();
const activityDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const activityDetailsVisibleTabsByContainer = new WeakMap<HTMLElement, Set<string>>();
const projectDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const wbsDetailsTabByContainer = new WeakMap<HTMLElement, string>();
const ACTIVITY_DETAILS_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v1";
const workspaceEventDelegation = new WeakSet<HTMLElement>();
const workspaceStickyOffsetsCache = new WeakMap<readonly WorkspaceColumn[], ReadonlyMap<string, number>>();

function toggleDrawer(container: HTMLElement, selector: string): void {
  const drawer = container.querySelector<HTMLElement>(selector);
  if (!drawer) return;
  const willOpen = drawer.hidden;
  if (willOpen) {
    container.querySelectorAll<HTMLElement>("[data-tools-drawer],[data-wbs-drawer],[data-nav-flyout]").forEach((other) => {
      if (other !== drawer) other.hidden = true;
    });
  }
  drawer.hidden = !willOpen;
}

function closeDrawer(container: HTMLElement, selector: string): void {
  const drawer = typeof container.querySelector === "function" ? container.querySelector<HTMLElement>(selector) : null;
  if (drawer) drawer.hidden = true;
}

function openToolsDrawer(container: HTMLElement): void {
  const drawer = container.querySelector<HTMLElement>("[data-tools-drawer]");
  if (!drawer) return;
  container.querySelectorAll<HTMLElement>("[data-wbs-drawer],[data-nav-flyout]").forEach((other) => { other.hidden = true; });
  drawer.hidden = false;
  drawer.querySelector<HTMLElement>("[data-tools-close]")?.focus({ preventScroll: true });
}

function openWbsDrawer(container: HTMLElement): void {
  const drawer = container.querySelector<HTMLElement>("[data-wbs-drawer]");
  if (!drawer) return;
  container.querySelectorAll<HTMLElement>("[data-tools-drawer],[data-nav-flyout]").forEach((other) => { other.hidden = true; });
  drawer.hidden = false;
}

function bindWorkspaceEvents(container: HTMLElement): void {
  if (typeof container.addEventListener !== "function" || workspaceEventDelegation.has(container)) return;
  workspaceEventDelegation.add(container);
  container.addEventListener("pointerdown", (event) => {
    const splitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (!splitter) return;
    const split = splitter.closest<HTMLElement>("[data-panel-split]");
    if (!split) return;
    event.preventDefault();
    const move = (moveEvent: PointerEvent): void => {
      const rect = split.getBoundingClientRect();
      if (rect.width <= 0) return;
      const percent = ((moveEvent.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(70, Math.max(30, percent));
      split.style.setProperty("--cp-split-table", `${clamped.toFixed(2)}%`);
      splitter.setAttribute("aria-valuenow", clamped.toFixed(0));
    };
    const stop = (): void => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop, { once: true });
  });
  container.addEventListener("input", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!target) return;
    const filterInput = target.closest<HTMLInputElement>("[data-activity-filter]");
    if (filterInput) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      record.options.onActivityFilterChange?.(filterInput.value);
      const next = container.querySelector<HTMLInputElement>("[data-activity-filter]");
      if (next) {
        next.focus({ preventScroll: true });
        next.setSelectionRange(next.value.length, next.value.length);
      }
      return;
    }
    const searchInput = target.closest<HTMLInputElement>("[data-reference-search-input]");
    if (!searchInput) return;
    const query = searchInput.value.trim().toLocaleLowerCase();
    const entries = Array.from(container.querySelectorAll<HTMLElement>("[data-reference-search]"));
    let visible = 0;
    for (const entry of entries) {
      const match = !query || (entry.dataset.referenceSearch ?? "").includes(query);
      entry.hidden = !match;
      if (match) visible++;
    }
    container.querySelectorAll<HTMLElement>("[data-reference-group]").forEach((group) => {
      group.hidden = !Array.from(group.querySelectorAll<HTMLElement>("[data-reference-search]")).some((entry) => !entry.hidden);
    });
    const empty = container.querySelector<HTMLElement>("[data-reference-no-matches]");
    if (empty) empty.hidden = visible > 0;
  });
  container.addEventListener("submit", (event) => {
    const form = event.target && typeof (event.target as { matches?: unknown }).matches === "function" ? event.target as HTMLFormElement : null;
    if (!form) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const readText = (name: string): string => form.querySelector<HTMLInputElement>(`[name="${name}"]`)?.value.trim() ?? "";
    const sequenceRaw = form.querySelector<HTMLInputElement>('[name="sequence_number"]')?.value ?? "0";
    const sequenceNumber = Number.parseInt(sequenceRaw, 10);
    if (form.matches("[data-activity-create-form]")) {
      event.preventDefault();
      const durationValue = Number(form.querySelector<HTMLInputElement>('[name="duration_value"]')?.value ?? "");
      const wbsId = form.querySelector<HTMLSelectElement>('[name="wbs_id"]')?.value ?? "";
      if (!readText("activity_id") || !readText("name") || !Number.isFinite(durationValue) || durationValue < 0 || !wbsId) return;
      const selected = (name: string, fallback: string): string => form.querySelector<HTMLSelectElement>(`[name="${name}"]`)?.value ?? fallback;
      void record.options.onActivityCreate?.({
        activityId: readText("activity_id"),
        name: readText("name"),
        durationValue,
        durationUnit: selected("duration_unit", "working-day"),
        wbsId,
        activityType: selected("activity_type", "Task Dependent"),
        status: selected("status", "Not Started"),
        statusCode: selected("status_code", "Planned"),
        percentCompleteType: selected("percent_complete_type", "DURATION"),
        levelingPriority: selected("leveling_priority", "Normal"),
      });
    } else if (form.matches("[data-relationship-create-form]")) {
      event.preventDefault();
      const predecessorId = form.querySelector<HTMLSelectElement>('[name="predecessor_id"]')?.value ?? "";
      const successorId = form.querySelector<HTMLSelectElement>('[name="successor_id"]')?.value ?? "";
      const type = form.querySelector<HTMLSelectElement>('[name="relationship_type"]')?.value ?? "FS";
      const lagValue = form.querySelector<HTMLInputElement>('[name="lag_value"]')?.value.trim() ?? "";
      const lagUnit = form.querySelector<HTMLSelectElement>('[name="lag_unit"]')?.value ?? "working-day";
      if (
        !predecessorId || !successorId || predecessorId === successorId ||
        !["FS", "SS", "FF", "SF"].includes(type) ||
        !/^-?\d+(\.\d+)?$/.test(lagValue) ||
        !["working-day", "working-hour"].includes(lagUnit)
      ) return;
      void record.options.onRelationshipCreate?.({
        predecessorId,
        successorId,
        type: type as WorkspaceRelationshipType,
        lagValue,
        lagUnit,
      });
    } else if (form.matches("[data-relationship-edit-form]")) {
      event.preventDefault();
      const relationshipId = form.dataset.relationshipEditForm ?? "";
      const recordRevision = Number(form.dataset.relationshipRevision ?? "");
      const predecessorId = form.querySelector<HTMLSelectElement>('[name="predecessor_id"]')?.value ?? "";
      const successorId = form.querySelector<HTMLSelectElement>('[name="successor_id"]')?.value ?? "";
      const type = form.querySelector<HTMLSelectElement>('[name="relationship_type"]')?.value ?? "FS";
      const lagValue = form.querySelector<HTMLInputElement>('[name="lag_value"]')?.value.trim() ?? "";
      const lagUnit = form.querySelector<HTMLSelectElement>('[name="lag_unit"]')?.value ?? "working-day";
      if (
        !relationshipId || !Number.isInteger(recordRevision) || recordRevision < 1 ||
        !predecessorId || !successorId || predecessorId === successorId ||
        !["FS", "SS", "FF", "SF"].includes(type) ||
        !/^-?\d+(\.\d+)?$/.test(lagValue) ||
        !["working-day", "working-hour"].includes(lagUnit)
      ) return;
      void record.options.onRelationshipUpdate?.(relationshipId, recordRevision, {
        predecessorId,
        successorId,
        type: type as WorkspaceRelationshipType,
        lagValue,
        lagUnit,
      });
    } else if (!Number.isInteger(sequenceNumber) || sequenceNumber < 0) return;
    else if (form.matches("[data-wbs-create-form]")) {
      event.preventDefault();
      const parentWbsId = form.querySelector<HTMLSelectElement>('[name="parent_wbs_id"]')?.value || null;
      void record.options.onWbsCreate?.({ code: readText("code"), name: readText("name"), sequenceNumber, parentWbsId });
    } else if (form.matches("[data-wbs-edit-form]")) {
      event.preventDefault();
      const wbsId = form.dataset.wbsEditForm;
      if (wbsId) void record.options.onWbsUpdate?.(wbsId, { code: readText("code"), name: readText("name"), sequenceNumber });
    }
  });
  container.addEventListener("click", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-project-settings],[data-wbs-detail-tab],[data-project-detail-tab],[data-activity-details-options-open],[data-activity-details-options-close],[data-activity-details-apply],[data-activity-detail-tab],[data-window-close],[data-shell-command],[data-layout-options-open],[data-layout-options-close],[data-menu],[data-rail-action],[data-tools-open],[data-tools-close],[data-wbs-drawer-close],[data-wbs-id],[data-wbs-delete],[data-relationship-delete],[data-p6-field-add],[data-p6-field-remove],[data-p6-field-visibility],[data-p6-field-width],[data-p6-field-alignment],[data-p6-field-pin],[data-p6-field-freeze],[data-p6-field-move],[data-p6-layout-undo],[data-p6-layout-redo],[data-p6-layout-restore],[data-gantt-scale],[data-gantt-relationships-toggle],[data-gantt-activity-id],[data-activity-id],[data-activity-edit],[data-activity-sort-direction]") : null;
    if (!target) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const { state, options } = record;
    if (target.dataset.wbsDetailTab) {
      const tab = target.dataset.wbsDetailTab;
      wbsDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-wbs-detail-tab]").forEach((button) => {
        const active = button.dataset.wbsDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-wbs-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.wbsDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.projectDetailTab) {
      const tab = target.dataset.projectDetailTab;
      projectDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-project-detail-tab]").forEach((button) => {
        const active = button.dataset.projectDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-project-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.projectDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.activityDetailsOptionsOpen !== undefined || target.dataset.activityDetailsOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (target.dataset.activityDetailsOptionsOpen !== undefined) {
        const visible = getActivityDetailsVisibleTabs(container);
        dialog?.querySelectorAll<HTMLInputElement>("[data-activity-detail-visible]").forEach((input) => {
          input.checked = visible.has(input.dataset.activityDetailVisible ?? "");
        });
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailsApply !== undefined) {
      const dialog = container.querySelector<HTMLElement>("[data-activity-details-options-dialog]");
      const selected = new Set(Array.from(dialog?.querySelectorAll<HTMLInputElement>("[data-activity-detail-visible]") ?? [])
        .filter((input) => input.checked)
        .map((input) => input.dataset.activityDetailVisible ?? ""));
      if (!selected.size) return;
      activityDetailsVisibleTabsByContainer.set(container, selected);
      try { window.localStorage.setItem(ACTIVITY_DETAILS_TABS_STORAGE_KEY, JSON.stringify([...selected])); } catch { /* optional local preference storage */ }
      const currentTab = activityDetailsTabByContainer.get(container) ?? "general";
      const nextTab = selected.has(currentTab) ? currentTab : ACTIVITY_DETAIL_TABS.find(([key]) => selected.has(key))?.[0] ?? "general";
      activityDetailsTabByContainer.set(container, nextTab);
      const record = workspaceRenderRecords.get(container);
      const details = container.querySelector<HTMLElement>("#cp-details");
      if (record && details) details.innerHTML = renderActivityDetailsPanel(record.state, getWorkspaceLabels(record.state.locale), nextTab, selected);
      const optionsDialog = container.querySelector<HTMLDialogElement>("[data-activity-details-options-dialog]");
      if (optionsDialog && typeof optionsDialog.close === "function") optionsDialog.close();
      else optionsDialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.activityDetailTab) {
      const tab = target.dataset.activityDetailTab;
      activityDetailsTabByContainer.set(container, tab);
      container.querySelectorAll<HTMLElement>("[data-activity-detail-tab]").forEach((button) => {
        const active = button.dataset.activityDetailTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-activity-detail-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.activityDetailPanel !== tab;
      });
      return;
    }
    if (target.dataset.windowClose) {
      if (["project", "schedule", "progress", "resources", "cost", "documents", "reports", "control", "settings"].includes(target.dataset.windowClose)) {
        options.onWindowClose?.(target.dataset.windowClose as WorkspaceState["activeMenu"]);
      }
      return;
    }
    if (target.dataset.shellCommand) {
      const command = target.dataset.shellCommand;
      if (command === "Timescale") {
        const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
        if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        else dialog?.setAttribute("open", "");
      } else if (command === "Columns" || command === "Bars" || command === "Bar Chart Options") {
        openToolsDrawer(container);
      } else if (command === "Filter By") {
        container.querySelector<HTMLInputElement>("[data-activity-filter]")?.focus();
      } else if (command === "Group and Sort By") {
        container.querySelector<HTMLSelectElement>("[data-activity-group]")?.focus();
      }
      return;
    }
    if ("projectSettings" in target.dataset) return void options.onProjectSettings?.();
    if (target.dataset.toolsOpen !== undefined) { openToolsDrawer(container); return; }
    if (target.dataset.toolsClose !== undefined) { closeDrawer(container, "[data-tools-drawer]"); return; }
    if (target.dataset.wbsDrawerClose !== undefined) { closeDrawer(container, "[data-wbs-drawer]"); return; }
    if (target.dataset.railAction) {
      const action = target.dataset.railAction;
      if (action === "navigation") { toggleDrawer(container, "[data-nav-flyout]"); return; }
      if (action === "wbs") { openWbsDrawer(container); return; }
      if (action === "tools") { toggleDrawer(container, "[data-tools-drawer]"); return; }
      options.onRailAction?.(action);
      return;
    }
    if (target.dataset.menu) {
      closeDrawer(container, "[data-nav-flyout]");
      return void options.onMenuSelect?.(target.dataset.menu as WorkspaceState["activeMenu"]);
    }
    if (target.dataset.activityEdit) return void options.onActivityEdit?.(target.dataset.activityEdit);
    if (target.dataset.activitySortDirection !== undefined) return void options.onActivitySortDirectionToggle?.();
    if (target.dataset.wbsId) return void options.onWbsSelect?.(target.dataset.wbsId);
    if ("wbsDelete" in target.dataset) { const selectedId = state.selectedWbsId ?? ""; if (selectedId && window.confirm(getWorkspaceLabels(state.locale).wbsDeleteConfirm)) void options.onWbsDelete?.(selectedId); return; }
    if (target.dataset.relationshipDelete) {
      const revision = Number.parseInt(target.dataset.relationshipRevision ?? "", 10);
      if (!Number.isInteger(revision) || revision < 1) return;
      void options.onRelationshipDelete?.(target.dataset.relationshipDelete, revision);
      return;
    }
    if ("p6LayoutUndo" in target.dataset) return void options.onP6LayoutUndo?.();
    if ("p6LayoutRedo" in target.dataset) return void options.onP6LayoutRedo?.();
    if ("p6LayoutRestore" in target.dataset) {
      const selected = container.querySelector<HTMLSelectElement>("[data-p6-layout-revision-select]")?.value ?? "";
      const revision = Number.parseInt(selected, 10);
      if (Number.isInteger(revision)) options.onP6LayoutRestore?.(revision);
      return;
    }
    if (target.dataset.p6FieldAdd) return void options.onP6FieldAdd?.(target.dataset.p6FieldAdd);
    if (target.dataset.p6FieldRemove) return void options.onP6FieldRemove?.(target.dataset.p6FieldRemove);
    if (target.dataset.p6FieldVisibility) return void options.onP6FieldVisibilityChange?.(target.dataset.p6FieldVisibility, target.dataset.p6FieldVisible === "true");
    if (target.dataset.p6FieldWidth) {
      const delta = target.dataset.p6FieldWidthDelta;
      if (delta !== "increase" && delta !== "decrease") return;
      const column = state.p6Layout?.columns.find((item) => item.field_id === target.dataset.p6FieldWidth);
      if (column) options.onP6FieldWidthChange?.(target.dataset.p6FieldWidth, Math.max(40, column.width + (delta === "increase" ? 20 : -20)));
      return;
    }
    if (target.dataset.p6FieldAlignment) {
      const alignment = target.dataset.p6FieldAlignmentValue;
      if (alignment === "start" || alignment === "center" || alignment === "end") options.onP6FieldPresentationChange?.(target.dataset.p6FieldAlignment, { alignment });
      return;
    }
    if (target.dataset.p6FieldPin) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldPin, { pinned: target.dataset.p6FieldPinned !== "true" });
    if (target.dataset.p6FieldFreeze) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldFreeze, { frozen: target.dataset.p6FieldFrozen !== "true" });
    if (target.dataset.p6FieldMove) {
      const direction = target.dataset.p6FieldDirection;
      if (direction !== "up" && direction !== "down") return;
      const fieldId = target.dataset.p6FieldMove;
      const visible = state.p6Layout?.columns.filter((column) => column.visible).sort((a, b) => a.order - b.order) ?? [];
      const ordered = state.p6Layout?.columns.slice().sort((a, b) => a.order - b.order).map((column) => column.field_id) ?? [];
      const index = ordered.indexOf(fieldId);
      const visibleIndex = visible.findIndex((column) => column.field_id === fieldId);
      const nextVisibleIndex = direction === "up" ? visibleIndex - 1 : visibleIndex + 1;
      if (visibleIndex < 0 || nextVisibleIndex < 0 || nextVisibleIndex >= visible.length || index < 0) return;
      const adjacentIndex = ordered.indexOf(visible[nextVisibleIndex].field_id);
      if (adjacentIndex < 0) return;
      [ordered[index], ordered[adjacentIndex]] = [ordered[adjacentIndex], ordered[index]];
      options.onP6FieldReorder?.(ordered);
      return;
    }
    if (target.dataset.layoutOptionsOpen !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    if (target.dataset.layoutOptionsClose !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.ganttScale) {
      const mode = target.dataset.ganttScale;
      if (mode === "day" || mode === "week" || mode === "month" || mode === "quarter" || mode === "year") options.onGanttScaleChange?.(mode);
      return;
    }
    if (target.dataset.ganttRelationshipsToggle !== undefined) {
      options.onGanttRelationshipsChange?.(target.dataset.ganttRelationshipsToggle === "true");
      return;
    }
    if (target.dataset.ganttActivityId) return void options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    if (target.dataset.activityId) options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("keydown", (event) => {
    const splitter = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (splitter && splitter.dataset && "panelSplitter" in splitter.dataset) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const split = splitter.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      event.preventDefault();
      const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table")) || 53.5;
      const next = Math.min(70, Math.max(30, current + (event.key === "ArrowRight" ? 2 : -2)));
      split.style.setProperty("--cp-split-table", `${next}%`);
      splitter.setAttribute("aria-valuenow", next.toFixed(0));
      return;
    }
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-gantt-activity-id],[data-activity-id]") : null;
    if (!target) return;
    event.preventDefault();
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    if (target.dataset.ganttActivityId) record.options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    else if (target.dataset.activityId) record.options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("change", (event) => {
    const element = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!element) return;
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutTimescale")) {
      const mode = (element as HTMLSelectElement).value;
      if (mode === "day" || mode === "week" || mode === "month" || mode === "quarter" || mode === "year") {
        workspaceRenderRecords.get(container)?.options.onGanttScaleChange?.(mode);
      }
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutLinks")) {
      workspaceRenderRecords.get(container)?.options.onGanttRelationshipsChange?.((element as HTMLInputElement).checked);
      return;
    }
    const isGroupSelect = Object.prototype.hasOwnProperty.call(element.dataset, "activityGroup");
    if (isGroupSelect) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value;
      if (value === "wbs" || value === "none") record.options.onActivityGroupByChange?.(value);
      return;
    }
    const isSortSelect = Object.prototype.hasOwnProperty.call(element.dataset, "activitySort");
    if (isSortSelect) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value.trim();
      record.options.onActivitySortChange?.(value || null);
      return;
    }
    const target = element.closest<HTMLInputElement>("[data-p6-field-rename]");
    if (!target) return;
    const fieldId = target.dataset.p6FieldRename;
    const label = target.value.trim();
    if (fieldId && label) workspaceRenderRecords.get(container)?.options.onP6FieldPresentationChange?.(fieldId, { label });
  });
}

function renderWbsTree(
  nodes: WorkspaceState["wbsNodes"],
  selectedWbsId: string | null,
  labels: WorkspaceLabels,
): string {
  if (!nodes.length) return `<div class="cp-empty">${escapeHtml(labels.noWbs)}</div>`;
  const children = new Map<string | null, WorkspaceState["wbsNodes"][number][]>();
  for (const node of nodes) {
    const parentId = node.parentKind === "project" ? null : node.parentWbsId;
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort((a, b) => a.sequenceNumber - b.sequenceNumber || a.id.localeCompare(b.id));
  }
  const renderChildren = (
    parentId: string | null,
    level: number,
    ancestors: ReadonlySet<string>,
  ): string => (children.get(parentId) ?? []).map((node) => {
    if (ancestors.has(node.id)) {
      return `<li class="cp-wbs-invalid" role="treeitem"><span class="cp-empty">Invalid WBS hierarchy</span></li>`;
    }
    const nested = children.get(node.id) ?? [];
    const selected = selectedWbsId === node.id;
    const nextAncestors = new Set(ancestors);
    nextAncestors.add(node.id);
    return `<li class="cp-wbs-item" role="treeitem" aria-level="${level}"${nested.length ? ' aria-expanded="true"' : ""}>
      <button type="button" class="cp-wbs-node${selected ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(node.id)}" aria-current="${selected ? "true" : "false"}">
        <span class="cp-wbs-code">${escapeHtml(node.localCode)}</span>
        <span class="cp-wbs-name">${escapeHtml(node.name)}</span>
      </button>
      ${nested.length ? `<ul class="cp-wbs-children" role="group">${renderChildren(node.id, level + 1, nextAncestors)}</ul>` : ""}
    </li>`;
  }).join("");
  return `<ul class="cp-wbs-tree" role="tree" aria-label="${escapeAttribute(labels.wbs)}">${renderChildren(null, 1, new Set())}</ul>`;
}

function canIncrementallyUpdate(previous: WorkspaceState, next: WorkspaceState): boolean {
  return previous.context === next.context && previous.locale === next.locale && previous.direction === next.direction && previous.calendarMode === next.calendarMode && previous.ganttScale === next.ganttScale && previous.showGanttRelationships === next.showGanttRelationships && previous.visiblePanels === next.visiblePanels && previous.columns === next.columns && previous.activities === next.activities && previous.wbsNodes === next.wbsNodes && previous.relationships === next.relationships && previous.activityFilter === next.activityFilter && previous.activityGroupBy === next.activityGroupBy && previous.activitySort === next.activitySort && previous.controlSummary === next.controlSummary && previous.smartGuide === next.smartGuide && previous.siteDailyLogs === next.siteDailyLogs && previous.timecards === next.timecards && previous.equipmentReports === next.equipmentReports && previous.fieldIssues === next.fieldIssues && previous.changeNotices === next.changeNotices && previous.changeCases === next.changeCases && previous.claims === next.claims && previous.changeClaimImpacts === next.changeClaimImpacts && previous.documents === next.documents && previous.procurementRecords === next.procurementRecords && previous.inspections === next.inspections && previous.qualityRecords === next.qualityRecords && previous.safetyObservations === next.safetyObservations && previous.punchItems === next.punchItems && previous.p6FieldRegistry === next.p6FieldRegistry && previous.p6Layout === next.p6Layout;
}

function applyIncrementalWorkspaceUpdate(container: HTMLElement, previous: WorkspaceState, next: WorkspaceState): boolean {
  if (!canIncrementallyUpdate(previous, next)) return false;
  const menuChanged = previous.activeMenu !== next.activeMenu;
  const wbsChanged = previous.selectedWbsId !== next.selectedWbsId;
  const activityChanged = previous.selectedActivityId !== next.selectedActivityId;
  if (Number(menuChanged) + Number(wbsChanged) + Number(activityChanged) !== 1) return false;
  if (menuChanged) {
    container.querySelector<HTMLElement>(".cp-workspace")?.setAttribute("data-active-menu", next.activeMenu);
    container.querySelectorAll<HTMLElement>("[data-menu]").forEach((button) => {
      const active = button.dataset.menu === next.activeMenu;
      button.setAttribute("aria-current", active ? "page" : "false");
      if (button.dataset.windowTab !== undefined) button.setAttribute("aria-selected", String(active));
    });
    const navigation = container.querySelector<HTMLElement>(".cp-navigation-surface");
    if (navigation) navigation.outerHTML = renderNavigationSurface(next);
    const labels = getWorkspaceLabels(next.locale);
    const navigationItem = getWorkspaceNavigation(next.activeMenu);
    const title = container.querySelector<HTMLElement>("[data-activity-header] .cp-p6-activity-heading strong");
    if (title) title.textContent = getWorkspaceNavigationLabel(navigationItem, next.locale);
    const kind = container.querySelector<HTMLElement>("[data-activity-header] .cp-p6-activity-heading span");
    if (kind) kind.textContent = next.activeMenu === "schedule" ? uiText(next.locale, "Activity workspace", "محیط کار فعالیت") : uiText(next.locale, "Workspace page", "صفحهٔ محیط کار");
    const stage = container.querySelector<HTMLElement>("#cp-p6-module-stage");
    if (stage) stage.outerHTML = renderP6ModuleStage(next, labels);
    container.querySelector<HTMLElement>("[data-nav-flyout]")?.setAttribute("hidden", "");
    const schedulingReference = container.querySelector<HTMLElement>("#cp-scheduling-reference");
    if (schedulingReference) schedulingReference.hidden = next.activeMenu !== "schedule";
    const details = container.querySelector<HTMLElement>("#cp-details");
    if (details) details.innerHTML = renderWindowDetailsPanel(next, labels, container);
    return true;
  }
  if (wbsChanged) {
    container.querySelectorAll<HTMLElement>("[data-wbs-id]").forEach((button) => {
      const selected = button.dataset.wbsId === next.selectedWbsId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", selected ? "true" : "false");
    });
    const wbsDetails = container.querySelector<HTMLElement>(".cp-wbs-details");
    if (wbsDetails) wbsDetails.outerHTML = renderWbsDetails(next, wbsDetailsTabByContainer.get(container) ?? "general");
    return true;
  }
  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const selected = row.dataset.activityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
  });
  container.querySelectorAll<HTMLElement>("[data-gantt-activity-id]").forEach((row) => {
    const selected = row.dataset.ganttActivityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-pressed", selected ? "true" : "false");
  });
  const details = container.querySelector<HTMLElement>("#cp-details");
  if (details) {
    const t = getWorkspaceLabels(next.locale);
    details.innerHTML = renderWindowDetailsPanel(next, t, container);
  }
  return true;
}


export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  openWindows?: readonly WorkspaceState["activeMenu"][];
  onWindowClose?: (menu: WorkspaceState["activeMenu"]) => void;
  onWbsSelect?: (wbsId: string) => void;
  onWbsCreate?: (input: { code: string; name: string; sequenceNumber: number; parentWbsId: string | null }) => void | Promise<void>;
  onWbsUpdate?: (wbsId: string, input: { code: string; name: string; sequenceNumber: number }) => void | Promise<void>;
  onWbsDelete?: (wbsId: string) => void | Promise<void>;
  onActivityCreate?: (input: { activityId: string; name: string; durationValue: number; durationUnit: string; wbsId: string; activityType: string; status: string; statusCode: string; percentCompleteType: string; levelingPriority: string }) => void | Promise<void>;
  onActivityEdit?: (activityId: string) => void | Promise<void>;
  onRelationshipCreate?: (input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipUpdate?: (relationshipId: string, recordRevision: number, input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipDelete?: (relationshipId: string, recordRevision: number) => void | Promise<void>;
  onActivitySelect?: (activityId: string) => void;
  onGanttActivitySelect?: (activityId: string) => void;
  onGanttScaleChange?: (ganttScale: WorkspaceGanttScale) => void;
  onGanttRelationshipsChange?: (visible: boolean) => void;
  onProjectSettings?: () => void;
  onActivityFilterChange?: (filterText: string) => void;
  onActivitySortChange?: (columnId: string | null) => void;
  onActivityGroupByChange?: (groupBy: "wbs" | "none") => void;
  onActivitySortDirectionToggle?: () => void;
  onP6FieldAdd?: (fieldId: string) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldWidthChange?: (fieldId: string, width: number) => void;
  onP6FieldVisibilityChange?: (fieldId: string, visible: boolean) => void;
  onP6FieldPresentationChange?: (fieldId: string, patch: { label?: string; alignment?: "start" | "center" | "end"; pinned?: boolean; frozen?: boolean }) => void;
  onP6LayoutUndo?: () => void;
  onP6LayoutRedo?: () => void;
  onP6LayoutRestore?: (revision: number) => void;
  layoutHistory?: {
    canUndo: boolean;
    canRedo: boolean;
    noticeKey?: "undone" | "redone" | "restored" | "empty" | "failed" | "conflict" | null;
    revisions?: readonly { revision: number; columnCount: number }[];
  };
  onRailAction?: (action: string) => void;
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const previous = workspaceRenderRecords.get(container);
  if (previous && applyIncrementalWorkspaceUpdate(container, previous.state, state)) {
    workspaceRenderRecords.set(container, { state, options });
    return;
  }
  const t = getWorkspaceLabels(state.locale);
  const visibleActivities = filterAndSortActivities(
    state.activities,
    state.activityFilter,
    state.activitySort,
    state.activityGroupBy,
    state.wbsNodes,
  );
  const scale = createGanttScale(visibleActivities);
  let stickyOffsets = workspaceStickyOffsetsCache.get(state.columns);
  if (!stickyOffsets) {
    const nextStickyOffsets = new Map<string, number>();
    let stickyOffset = 0;
    for (const column of state.columns) {
      if (column.pinned || column.frozen) {
        nextStickyOffsets.set(column.id, stickyOffset);
        stickyOffset += column.width;
      }
    }
    stickyOffsets = nextStickyOffsets;
    workspaceStickyOffsetsCache.set(state.columns, stickyOffsets);
  }
  // The P6 grid uses a fixed table layout so the persisted column widths are
  // honoured exactly; long values and headers are clipped instead of widening
  // the table and pushing the required columns out of the initial view.
  const activityTableWidth =
    state.columns.reduce((total, column) => total + column.width, 0) + 48 + 44;

  const navigationLabel = getWorkspaceNavigationLabel(getWorkspaceNavigation(state.activeMenu), state.locale);
  const rail = {
    menu: uiText(state.locale, "Workspace menu", "منوی محیط کار"),
    projects: uiText(state.locale, "Projects", "پروژه‌ها"),
    eps: uiText(state.locale, "EPS / Portfolio", "EPS / سبد پروژه"),
    wbs: uiText(state.locale, "WBS", "ساختار شکست"),
    activities: uiText(state.locale, "Activities", "فعالیت‌ها"),
    resources: uiText(state.locale, "Resources", "منابع"),
    assignments: uiText(state.locale, "Resource assignments", "تخصیص منابع"),
    reports: uiText(state.locale, "Reports", "گزارش‌ها"),
    documents: uiText(state.locale, "Documents", "اسناد"),
    expenses: uiText(state.locale, "Expenses", "هزینه‌ها"),
    risks: uiText(state.locale, "Risks", "ریسک‌ها"),
    issues: uiText(state.locale, "Issues", "مسائل"),
    forms: uiText(state.locale, "Forms", "فرم‌ها"),
    settings: uiText(state.locale, "Settings", "تنظیمات"),
    tools: uiText(state.locale, "Tools", "ابزارها"),
    comments: uiText(state.locale, "Comments", "یادداشت‌ها"),
    notes: uiText(state.locale, "Notebook", "دفترچه"),
    attachments: uiText(state.locale, "Attachments", "پیوست‌ها"),
    close: uiText(state.locale, "Close", "بستن"),
    columns: uiText(state.locale, "Columns", "ستون‌ها"),
    bars: uiText(state.locale, "Bars", "میله‌ها"),
    openTools: uiText(state.locale, "Open workspace tools", "بازکردن ابزارهای محیط کار"),
    showDetails: uiText(state.locale, "Show details", "نمایش جزئیات"),
    activityWorkspace: uiText(state.locale, "Activity workspace", "محیط کار فعالیت"),
    moduleWorkspace: uiText(state.locale, "Workspace page", "صفحهٔ محیط کار"),
    dataDate: uiText(state.locale, "Data date", "تاریخ داده"),
    filter: uiText(state.locale, "Filter", "پالایه"),
    layout: uiText(state.locale, "Layout", "چیدمان"),
    noDataDate: uiText(state.locale, "Not provided", "ارائه نشده"),
  };
  const railMenuIcons: Record<WorkspaceState["activeMenu"], string> = {
    project: "folder",
    schedule: "activity",
    progress: "progress",
    resources: "resource",
    calendars: "calendar",
    cost: "money",
    documents: "file",
    reports: "print",
    control: "network",
    settings: "settings",
  };
  const activityFilterLabel = state.activityFilter.trim() || uiText(state.locale, "All Activities", "همهٔ فعالیت‌ها");
  const windowTabs = ([
    ["project", uiText(state.locale, "Projects", "پروژه‌ها")],
    ["schedule", uiText(state.locale, "Activities", "فعالیت‌ها")],
    ["progress", uiText(state.locale, "Progress", "پیشرفت")],
    ["resources", uiText(state.locale, "Resources", "منابع")],
    ["calendars", uiText(state.locale, "Calendars", "تقویم‌ها")],
    ["cost", uiText(state.locale, "Cost", "هزینه")],
    ["documents", uiText(state.locale, "Documents", "اسناد")],
    ["reports", uiText(state.locale, "Reports", "گزارش‌ها")],
    ["control", uiText(state.locale, "Project Controls", "کنترل پروژه")],
    ["settings", uiText(state.locale, "Settings", "تنظیمات")],
  ] as const).filter(([key]) => (options.openWindows ?? [state.activeMenu]).includes(key));
  const contextCommands: Array<{ label: string; action?: "project-settings" | "wbs" | "tools"; disabled?: boolean }> = state.activeMenu === "project"
    ? [
      { label: uiText(state.locale, "Project properties", "مشخصات پروژه"), action: "project-settings" },
      { label: uiText(state.locale, "WBS structure", "ساختار شکست"), action: "wbs" },
      { label: uiText(state.locale, "Import / Export", "ورود و خروج اطلاعات"), disabled: true },
    ]
    : state.activeMenu === "schedule"
      ? [
        { label: uiText(state.locale, "Add activity", "افزودن فعالیت"), action: "tools" },
        { label: uiText(state.locale, "WBS", "ساختار شکست"), action: "wbs" },
        { label: uiText(state.locale, "Columns & fields", "ستون‌ها و فیلدها"), action: "tools" },
        { label: uiText(state.locale, "Relationships", "روابط"), disabled: true },
        { label: uiText(state.locale, "Timescale & bars", "مقیاس زمانی و میله‌ها"), disabled: true },
      ]
      : [
        { label: uiText(state.locale, "Open tools", "بازکردن ابزارها"), action: "tools" },
        { label: uiText(state.locale, "Configure layout", "تنظیم چیدمان"), disabled: true },
        { label: uiText(state.locale, "Page options", "گزینه‌های صفحه"), disabled: true },
      ];
  const contextCommandMarkup = contextCommands.map((command) => command.action === "project-settings"
    ? `<button type="button" data-project-settings>${escapeHtml(command.label)}</button>`
    : command.action === "wbs"
      ? `<button type="button" data-rail-action="wbs">${escapeHtml(command.label)}</button>`
      : command.action === "tools"
        ? `<button type="button" data-tools-open>${escapeHtml(command.label)}</button>`
        : `<button type="button" disabled title="${escapeAttribute(uiText(state.locale, "This visual command is not connected yet.", "این فرمان بصری هنوز متصل نشده است."))}">${escapeHtml(command.label)}</button>`).join("");

  container.innerHTML = `
    <section class="cp-workspace cp-p6-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}" data-active-menu="${state.activeMenu}">
      <header class="cp-header">
        <div class="cp-brand"><img class="cp-brand-logo" src="${escapeAttribute(cubiPlatformLogoUrl())}" width="1536" height="664" alt="CUBI Platform" /></div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
        <button type="button" id="cp-project-settings-open" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
      </header>
      <div class="cp-p6-shell">
        <nav class="cp-menu cp-p6-rail cp-navigation-tree" aria-label="${escapeAttribute(t.mainMenu)}">
          <div class="cp-nav-tree-title">${workspaceIcon("group")}<strong>${escapeHtml(rail.menu)}</strong></div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Project workspace", "محیط پروژه"))}</span>
            ${menuButton("project", t.project, state, railMenuIcons.project)}
            ${railActionButton("eps", rail.eps, "portfolio")}
            ${railActionButton("wbs", rail.wbs, "wbs")}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Planning & execution", "برنامه‌ریزی و اجرا"))}</span>
            ${menuButton("schedule", t.schedule, state, railMenuIcons.schedule)}
            ${railActionButton("activities", rail.activities, "activity")}
            ${menuButton("progress", t.progress, state, railMenuIcons.progress)}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Resources & cost", "منابع و هزینه"))}</span>
            ${menuButton("resources", t.resources, state, railMenuIcons.resources)}
            ${railActionButton("assignments", rail.assignments, "link")}
            ${menuButton("calendars", uiText(state.locale, "Calendars", "تقویم‌ها"), state, railMenuIcons.calendars)}
            <button type="button" class="cp-rail-button cp-nav-unavailable" disabled aria-disabled="true" title="${escapeAttribute(uiText(state.locale, "Role management window is catalogued; its page is not implemented yet.", "پنجره مدیریت نقش‌ها ثبت شده، اما صفحه آن هنوز پیاده‌سازی نشده است."))}"><span aria-hidden="true">♙</span><span class="cp-rail-label">${escapeHtml(uiText(state.locale, "Roles", "نقش‌ها"))}</span></button>
            ${menuButton("cost", t.cost, state, railMenuIcons.cost)}
            ${railActionButton("expenses", rail.expenses, "money")}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "Project information", "اطلاعات پروژه"))}</span>
            ${menuButton("documents", t.documents, state, railMenuIcons.documents)}
            ${menuButton("reports", t.reports, state, railMenuIcons.reports)}
            <button type="button" class="cp-rail-button cp-nav-unavailable" disabled aria-disabled="true" title="${escapeAttribute(uiText(state.locale, "Tracking window design is catalogued; its page is not implemented yet.", "پنجره رهگیری ثبت شده، اما صفحه آن هنوز پیاده‌سازی نشده است."))}"><span aria-hidden="true">▤</span><span class="cp-rail-label">${escapeHtml(uiText(state.locale, "Tracking", "رهگیری"))}</span></button>
            ${menuButton("control", t.control, state, railMenuIcons.control)}
            <button type="button" class="cp-rail-button cp-nav-unavailable" disabled aria-disabled="true" title="${escapeAttribute(uiText(state.locale, "Thresholds window design is catalogued; its page is not implemented yet.", "پنجره آستانه‌ها ثبت شده، اما صفحه آن هنوز پیاده‌سازی نشده است."))}"><span aria-hidden="true">⌁</span><span class="cp-rail-label">${escapeHtml(uiText(state.locale, "Thresholds", "آستانه‌ها"))}</span></button>
            ${railActionButton("risks", rail.risks, "warning")}
            ${railActionButton("issues", rail.issues, "warning")}
          </div>
          <div class="cp-nav-tree-group"><span>${escapeHtml(uiText(state.locale, "CUBI tools & administration", "ابزارها و مدیریت CUBI"))}</span>
            ${railActionButton("forms", uiText(state.locale, "Form Builder", "فرم‌ساز"), "forms")}
            ${menuButton("settings", t.settings, state, railMenuIcons.settings)}
            ${railActionButton("tools", rail.tools, "tools")}
          </div>
        </nav>
        <div class="cp-p6-body">
          ${renderWorkspaceCommandShell(state.locale, state.activeMenu)}
          <nav class="cp-window-tabs" aria-label="${escapeAttribute(uiText(state.locale, "Workspace windows", "پنجره‌های محیط کار"))}" role="tablist">
            ${windowTabs.map(([key, label]) => `<span class="cp-window-tab-item"><button type="button" role="tab" data-window-tab="${key}" data-menu="${key}" aria-selected="${key === state.activeMenu}" aria-current="${key === state.activeMenu ? "page" : "false"}" class="cp-window-tab${key === state.activeMenu ? " is-active" : ""}">${escapeHtml(label)}</button>${windowTabs.length > 1 ? `<button type="button" class="cp-window-tab-close" data-window-close="${key}" aria-label="${escapeAttribute(uiText(state.locale, `Close ${label}`, `بستن ${label}`))}" title="${escapeAttribute(uiText(state.locale, `Close ${label}`, `بستن ${label}`))}">×</button>` : ""}</span>`).join("")}
          </nav>
          <header class="cp-p6-activity-header" data-activity-header>
            <span class="cp-p6-activity-heading">
              <strong>${escapeHtml(navigationLabel)}</strong>
              <span>${escapeHtml(state.activeMenu === "schedule" ? rail.activityWorkspace : rail.moduleWorkspace)}</span>
            </span>
            <span class="cp-p6-activity-meta">${escapeHtml(t.project)}: ${escapeHtml(state.context.project_id)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.dataDate)}: ${escapeHtml(rail.noDataDate)}</span>
            <span class="cp-p6-activity-meta">${escapeHtml(rail.filter)}: ${escapeHtml(activityFilterLabel)}</span>
            <span class="cp-p6-activity-spacer"></span>
            <button type="button" class="cp-p6-chip" data-rail-action="wbs" title="${escapeAttribute(rail.wbs)}">${workspaceIcon("wbs")}<span>${escapeHtml(rail.wbs)}</span></button>
            <button type="button" class="cp-p6-chip" data-tools-open title="${escapeAttribute(rail.columns)}">${workspaceIcon("columns")}<span>${escapeHtml(rail.columns)}</span></button>
            <button type="button" class="cp-p6-chip" data-comments-toggle title="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}<span>${escapeHtml(rail.comments)}</span></button>
          </header>
          <div class="cp-context-command-bar" role="toolbar" aria-label="${escapeAttribute(uiText(state.locale, "Current window commands", "فرمان‌های پنجره جاری"))}">
            <span>${escapeHtml(uiText(state.locale, "Commands", "فرمان‌ها"))}</span>${contextCommandMarkup}${state.activeMenu === "schedule" ? `<button type="button" data-layout-options-open>${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</button>` : ""}
          </div>
          ${state.activeMenu === "schedule" ? renderLayoutOptionsDialog(state, t) : ""}
          <main class="cp-main">
            <div class="cp-p6-primary">
              <section class="cp-p6-split" data-panel-split data-workspace-menu="schedule">
                <section id="cp-activity-grid" class="cp-panel cp-grid" ${!state.visiblePanels.activity_grid ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-grid-head">
                    <h2>${escapeHtml(t.activities)}</h2>
                    <span class="cp-p6-grid-actions">
                      <button type="button" data-rail-action="wbs" title="${escapeAttribute(rail.wbs)}">${workspaceIcon("wbs")}</button>
                      <button type="button" data-tools-open title="${escapeAttribute(rail.columns)}">${workspaceIcon("columns")}</button>
                      <button type="button" data-comments-toggle title="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}</button>
                    </span>
                  </div>
                  ${renderActivityFilterSort(state, visibleActivities.length, t)}
                  <div class="cp-table-wrap">
                    <table role="grid" aria-label="${escapeAttribute(t.activities)}" aria-multiselectable="false" style="width:${activityTableWidth}px">
                      <thead><tr role="row">${state.columns.map((column) => `<th role="columnheader" scope="col" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="width:${column.width}px;text-align:${column.alignment}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}${column.formula ? `<span aria-label="${escapeAttribute(t.formulaColumn)}">ƒx</span>` : ""}</th>`).join("")}<th role="columnheader" scope="col" class="cp-logic-column">${escapeHtml(t.predecessorsColumn)}</th><th role="columnheader" scope="col" class="cp-actions-column"></th></tr></thead>
                      <tbody>${visibleActivities.length ? visibleActivities.map((activity) => renderActivityRow(activity, state, stickyOffsets)).join("") : `<tr role="row"><td role="gridcell" colspan="${Math.max(1, state.columns.length + 2)}">${escapeHtml(state.activities.length ? t.noMatchingActivities : t.noActivities)}</td></tr>`}</tbody>
                    </table>
                  </div>
                </section>
                <div class="cp-p6-splitter" data-panel-splitter role="separator" aria-orientation="vertical" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize table and Gantt", "تغییر اندازهٔ جدول و گانت"))}"><span></span></div>
                <section id="cp-gantt" class="cp-panel cp-gantt" ${!state.visiblePanels.gantt ? "hidden" : ""} data-workspace-menu="schedule">
                  <div class="cp-p6-gantt-head">
                    <h2>${escapeHtml(t.gantt)}</h2>
                    <button type="button" data-tools-open title="${escapeAttribute(rail.bars)}">${workspaceIcon("bars")}</button>
                  </div>
                  ${renderGantt(visibleActivities, state.relationships, state.ganttScale, state.calendarMode, scale, t, state.selectedActivityId, state.showGanttRelationships)}
                </section>
              </section>
              ${renderP6ModuleStage(state, t)}
            </div>
            <aside id="cp-details" class="cp-panel cp-details" ${!state.visiblePanels.details ? "hidden" : ""} data-workspace-menu="project schedule progress resources cost documents reports control settings" aria-labelledby="cp-details-heading">${renderWindowDetailsPanel(state, t, container)}</aside>
          </main>
          <div class="cp-p6-drawer cp-p6-wbs-drawer" data-wbs-drawer hidden aria-label="${escapeAttribute(t.wbs)}">
            <div class="cp-p6-drawer-head"><strong>${escapeHtml(t.wbs)}</strong><button type="button" data-wbs-drawer-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
            <aside id="cp-project-wbs" class="cp-panel cp-wbs" ${!state.visiblePanels.project_wbs ? "hidden" : ""} data-workspace-menu="project schedule" aria-label="${escapeAttribute(t.wbs)}">
              <h2>${escapeHtml(t.wbs)}</h2>
              ${renderWbsTree(state.wbsNodes, state.selectedWbsId, t)}
              ${renderWbsDetails(state, wbsDetailsTabByContainer.get(container) ?? "general")}
              <form class="cp-wbs-editor" data-wbs-create-form>
                <h3>${escapeHtml(t.wbsCreate)}</h3>
                <label>${escapeHtml(t.wbsCode)} <input name="code" required maxlength="80" autocomplete="off"></label>
                <label>${escapeHtml(t.wbsName)} <input name="name" required maxlength="180" autocomplete="off"></label>
                <label>${escapeHtml(t.wbsParent)}
                  <select name="parent_wbs_id" required>
                    ${state.wbsNodes.length ? state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}" ${node.id === (state.selectedWbsId ?? state.wbsNodes.find((item) => item.parentKind === "project")?.id) ? "selected" : ""}>${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("") : `<option value="__project__" selected>${escapeHtml(t.wbsProjectRoot)}</option>`}
                  </select>
                </label>
                <label>${escapeHtml(t.wbsSequence)} <input name="sequence_number" type="number" min="0" step="1" value="0" required></label>
                <button type="submit">${escapeHtml(t.wbsCreate)}</button>
              </form>
              ${state.selectedWbsId ? (() => {
                const selected = state.wbsNodes.find((node) => node.id === state.selectedWbsId);
                if (!selected) return "";
                return `<form class="cp-wbs-editor" data-wbs-edit-form="${escapeAttribute(selected.id)}">
                  <h3>${escapeHtml(t.wbsEdit)}</h3>
                  <label>${escapeHtml(t.wbsCode)} <input name="code" required maxlength="80" value="${escapeAttribute(selected.localCode)}"></label>
                  <label>${escapeHtml(t.wbsName)} <input name="name" required maxlength="180" value="${escapeAttribute(selected.name)}"></label>
                  <label>${escapeHtml(t.wbsSequence)} <input name="sequence_number" type="number" min="0" step="1" value="${selected.sequenceNumber}" required></label>
                  <button type="submit">${escapeHtml(t.wbsSave)}</button>
                  <button type="button" data-wbs-delete>${escapeHtml(t.wbsDelete)}</button>
                </form>`;
              })() : `<p class="cp-empty">${escapeHtml(t.wbsSelectPrompt)}</p>`}
            </aside>
          </div>
        </div>
        <aside class="cp-comments-dock-rail cp-context-command-rail" aria-label="${escapeAttribute(uiText(state.locale, "Contextual commands", "فرمان‌های زمینه‌ای"))}">
          <details class="cp-context-add-menu">
            <summary title="${escapeAttribute(uiText(state.locale, "Add", "افزودن"))}" aria-label="${escapeAttribute(uiText(state.locale, "Add", "افزودن"))}">+</summary>
            <div class="cp-context-add-popup" role="menu" aria-label="${escapeAttribute(uiText(state.locale, "Add to current window", "افزودن به پنجره جاری"))}">
              <strong>${escapeHtml(uiText(state.locale, "Add to current window", "افزودن به پنجره جاری"))}</strong>
              ${["Activity","WBS element","Relationship","Resource assignment","Expense","Document","Issue","Risk"].map((label) => `<button type="button" role="menuitem" disabled title="${escapeAttribute(uiText(state.locale, "Visual entry only; the owning create workflow is not connected yet.", "گزینه نمایشی است؛ گردش‌کار ایجاد هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, label, label))}</button>`).join("")}
            </div>
          </details>
          <span class="cp-rail-separator" aria-hidden="true"></span>
          <button type="button" class="cp-rail-button cp-comments-toggle" data-comments-toggle title="${escapeAttribute(rail.comments)}" aria-label="${escapeAttribute(rail.comments)}">${workspaceIcon("comment")}<span class="cp-rail-label">${escapeHtml(rail.comments)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="notebook" title="${escapeAttribute(rail.notes)}" aria-label="${escapeAttribute(rail.notes)}">${workspaceIcon("book")}<span class="cp-rail-label">${escapeHtml(rail.notes)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="documents" title="${escapeAttribute(rail.documents)}" aria-label="${escapeAttribute(rail.documents)}">${workspaceIcon("file")}<span class="cp-rail-label">${escapeHtml(rail.documents)}</span></button>
          <button type="button" class="cp-rail-button" data-rail-action="risks" title="${escapeAttribute(rail.risks)}" aria-label="${escapeAttribute(rail.risks)}">${workspaceIcon("warning")}<span class="cp-rail-label">${escapeHtml(rail.risks)}</span></button>
        </aside>
      </div>
      <div class="cp-p6-flyout" data-nav-flyout hidden>${renderNavigationSurface(state)}</div>
      <div class="cp-p6-drawer cp-p6-tools-drawer" data-tools-drawer hidden aria-label="${escapeAttribute(rail.tools)}">
        <div class="cp-p6-drawer-head"><strong>${escapeHtml(rail.tools)}</strong><button type="button" data-tools-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
        <div class="cp-p6-tool-scroll">
          ${renderP6FieldChooser(state, options.layoutHistory)}
          <section class="cp-panel cp-p6-tool-panel" aria-label="${escapeAttribute(t.activityCreate)}">
            <h2>${escapeHtml(t.activityCreate)}</h2>
            <form class="cp-activity-editor" data-activity-create-form>
              <h3>${escapeHtml(t.activityCreate)}</h3>
              <label>${escapeHtml(t.activityId)} <input name="activity_id" required maxlength="80" autocomplete="off"></label>
              <label>${escapeHtml(t.activityName)} <input name="name" required maxlength="180" autocomplete="off"></label>
              <label>${escapeHtml(t.activityDuration)} <input name="duration_value" type="number" min="0" step="any" value="1" required></label>
              <label>${escapeHtml(t.activityDurationUnit)} <select name="duration_unit"><option value="working-day">${escapeHtml(t.workingDay)}</option><option value="working-hour">${escapeHtml(t.workingHour)}</option></select></label>
              <label>${escapeHtml(t.activityWbs)} <select name="wbs_id" required ${state.wbsNodes.length ? "" : "disabled"}>${state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}" ${node.id === state.selectedWbsId ? "selected" : ""}>${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "activity_type"))} <select name="activity_type">${renderActivityCreateOptions(state.locale, "activity_type")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status"))} <select name="status">${renderActivityCreateOptions(state.locale, "status")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status_code"))} <select name="status_code">${renderActivityCreateOptions(state.locale, "status_code")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "percent_complete_type"))} <select name="percent_complete_type">${renderActivityCreateOptions(state.locale, "percent_complete_type")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "leveling_priority"))} <select name="leveling_priority">${renderActivityCreateOptions(state.locale, "leveling_priority")}</select></label>
              <button type="submit" ${state.wbsNodes.length ? "" : "disabled"}>${escapeHtml(t.activityCreate)}</button>
              ${state.wbsNodes.length ? "" : `<p class="cp-empty">${escapeHtml(t.noWbs)}</p>`}
            </form>
          </section>
          ${renderSmartGuide(state.smartGuide, t.smartGuide, t)}
          ${renderControlSummary(state.controlSummary, t.controlSummary, t.metrics, t.findings)}
          ${renderSiteDailyLogs(state.siteDailyLogs, t.siteLogs)}
          ${renderFieldOperations(state.fieldIssues, state.timecards, state.equipmentReports, t)}
          ${renderFieldAssurance(state.inspections, state.qualityRecords, state.safetyObservations, state.punchItems, t.assurance, t)}
          ${renderChangeClaimControl(state.changeNotices, state.changeCases, state.claims, state.changeClaimImpacts, t.commercial, state.documents, t)}
          ${renderProcurement(state.procurementRecords, t.procurement, t)}
          ${renderModuleEmptyState(state)}
          <section id="cp-schedule-options" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.scheduleOptions)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-schedule-run" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.runSchedule)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-logic" class="cp-panel cp-logic" data-workspace-menu="schedule"><h2>${escapeHtml(t.logic)}</h2>${renderRelationships(state, t)}</section>
          <section id="cp-formula-editor" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.formulaEditor)}</h2><div data-formula-editor><p class="cp-empty">—</p></div></section>
          <section id="cp-schedule-reference" class="cp-panel cp-schedule-panel" data-workspace-menu="schedule"><h2>${escapeHtml(t.scheduleReference)}</h2><div data-schedule-panel><p class="cp-empty">—</p></div>${renderSchedulingReference(state.locale, t, state.activeMenu === "schedule")}</section>
          <section id="cp-interchange" class="cp-panel cp-interchange-panel" data-workspace-menu="project"><h2>${escapeHtml(t.interchange)}</h2><div data-interchange-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-resource-capacity" class="cp-panel cp-capacity-panel" data-workspace-menu="resources"><h2>${escapeHtml(t.resourceCapacity)}</h2><div data-capacity-panel><p class="cp-empty">—</p></div></section>
          <section id="cp-settings-panel" class="cp-panel" data-workspace-menu="settings" aria-label="${escapeAttribute(t.settings)}">
            <h2>${escapeHtml(t.settings)}</h2>
            <p>${escapeHtml(t.projectSettings)}</p>
            <button type="button" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
          </section>
        </div>
      </div>
      <aside class="cp-comments-dock" data-comments-panel hidden aria-label="${escapeAttribute(rail.comments)}"></aside>
    </section>
  `;

  workspaceRenderRecords.set(container, { state, options });
  if (!workspaceEventDelegation.has(container)) bindWorkspaceEvents(container);
}

function renderP6ModuleStage(state: WorkspaceState, t: WorkspaceLabels): string {
  if (state.activeMenu === "schedule") return `<section id="cp-p6-module-stage" class="cp-p6-module-stage" data-workspace-menu="schedule" hidden></section>`;
  const navigation = getWorkspaceNavigation(state.activeMenu);
  const title = getWorkspaceNavigationLabel(navigation, state.locale);
  const status = getWorkspaceNavigationStatusLabel(navigation, state.locale);
  const controls = (items: string): string => `<div class="cp-p6-module-actions">${items}</div>`;
  const metric = (value: string | number, label: string): string =>
    `<span class="cp-p6-module-metric"><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(label)}</span></span>`;
  let body = "";
  switch (state.activeMenu) {
    case "project": {
      const projectRows = [
        [uiText(state.locale, "Project ID", "شناسه پروژه"), state.context.project_id],
        [uiText(state.locale, "Workspace revision", "ویرایش محیط کار"), `R${state.context.revision}`],
        [uiText(state.locale, "WBS elements", "عناصر WBS"), String(state.wbsNodes.length)],
        [uiText(state.locale, "Activities", "فعالیت‌ها"), String(state.activities.length)],
        [uiText(state.locale, "Relationships", "روابط"), String(state.relationships.length)],
        [uiText(state.locale, "Documents", "اسناد"), String(state.documents.length)],
      ];
      body = `
        <div class="cp-project-window-toolbar">
          ${controls(`${moduleButton("wbs", "wbs", uiText(state.locale, "Open WBS structure", "بازکردن ساختار WBS"))}${moduleButton("tools", "tools", uiText(state.locale, "Import / Export", "ورود / خروجی"))}${projectSettingsButton(state, t)}`)}
          <span class="cp-project-window-scope">${escapeHtml(uiText(state.locale, "Current project · server-authorized session", "پروژه جاری · نشست تأییدشده توسط سرور"))}</span>
        </div>
        <div class="cp-project-window-overview">
          <section class="cp-project-register" aria-label="${escapeAttribute(uiText(state.locale, "Current project register", "دفتر ثبت پروژه جاری"))}">
            <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(state.locale, "Project Register", "دفتر ثبت پروژه"))}</h3><span>${escapeHtml(uiText(state.locale, "Current session project", "پروژه نشست جاری"))}</span></div>
            <table class="cp-project-register-table">
              <thead><tr><th>${escapeHtml(uiText(state.locale, "Property", "مشخصه"))}</th><th>${escapeHtml(uiText(state.locale, "Current value", "مقدار فعلی"))}</th></tr></thead>
              <tbody>${projectRows.map(([label, value]) => `<tr><th scope="row">${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`).join("")}</tbody>
            </table>
          </section>
          <section class="cp-project-structure-summary" aria-label="${escapeAttribute(uiText(state.locale, "Project structure summary", "خلاصه ساختار پروژه"))}">
            <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(state.locale, "Project Structure", "ساختار پروژه"))}</h3><span>${escapeHtml(uiText(state.locale, "Loaded WBS hierarchy", "سلسله‌مراتب WBS بارگذاری‌شده"))}</span></div>
            ${state.wbsNodes.length ? `<div class="cp-project-wbs-list">${state.wbsNodes.map((node) => `<div class="cp-project-wbs-row"><span>${escapeHtml(node.localCode)}</span><strong>${escapeHtml(node.name)}</strong><small>R${node.recordRevision}</small></div>`).join("")}</div>` : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No WBS elements are loaded for this project.", "هیچ عنصر WBS برای این پروژه بارگذاری نشده است."))}</p>`}
          </section>
        </div>
        <p class="cp-project-window-note">${escapeHtml(uiText(state.locale, "This build displays the project authorized for the current session. Organization-wide domains, portfolios and additional projects are not invented when the API does not provide them.", "این نسخه پروژه مجاز برای نشست جاری را نمایش می‌دهد. حوزه‌های سازمانی، سبدها و پروژه‌های دیگر در صورت نبود داده از API ساخته یا حدس زده نمی‌شوند."))}</p>`;
      break;
    }
    case "calendars":
      body = `
        <div class="cp-calendar-window">
          <div class="cp-calendar-window-toolbar">
            <strong>${escapeHtml(uiText(state.locale, "Calendar Register", "فهرست تقویم‌ها"))}</strong>
            <div><button type="button" disabled title="${escapeAttribute(uiText(state.locale, "Calendar persistence is not connected yet.", "ذخیره‌سازی تقویم هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, "New Calendar", "تقویم جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button></div>
          </div>
          <div class="cp-calendar-window-layout">
            <section class="cp-calendar-register">
              <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Available Calendars", "تقویم‌های موجود"))}</strong><span>0</span></div>
              <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No calendar records have been loaded for this project.", "هیچ رکورد تقویمی برای این پروژه بارگذاری نشده است."))}</div>
            </section>
            <section class="cp-calendar-editor">
              <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Calendar Details", "جزئیات تقویم"))}</strong><span>${escapeHtml(uiText(state.locale, "No selection", "بدون انتخاب"))}</span></div>
              <div class="cp-calendar-editor-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Calendar detail tabs", "زبانه‌های جزئیات تقویم"))}">
                ${[["general","General","عمومی"],["workweek","Workweek","هفته کاری"],["exceptions","Exceptions","استثناها"],["assignments","Assignments","تخصیص‌ها"]].map(([key,en,fa],index)=>`<button type="button" role="tab" aria-selected="${index===0}" class="${index===0?"is-active":""}" data-calendar-editor-tab="${key}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}
              </div>
              <div class="cp-calendar-editor-content">
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="general">
                  <div class="cp-calendar-fields">
                    <label>${escapeHtml(uiText(state.locale, "Calendar Name", "نام تقویم"))}<input disabled placeholder="${escapeAttribute(uiText(state.locale, "Select or create a calendar", "یک تقویم انتخاب یا ایجاد کنید"))}"></label>
                    <label>${escapeHtml(uiText(state.locale, "Calendar Scope", "دامنه تقویم"))}<select disabled><option>${escapeHtml(uiText(state.locale, "Select scope", "انتخاب دامنه"))}</option><option>Global</option><option>Project</option><option>Resource</option></select></label>
                    <label>${escapeHtml(uiText(state.locale, "Parent Calendar", "تقویم والد"))}<select disabled><option>—</option></select></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Day", "ساعت در روز"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Week", "ساعت در هفته"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Month", "ساعت در ماه"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Hours per Year", "ساعت در سال"))}<input type="number" disabled placeholder="—"></label>
                    <label>${escapeHtml(uiText(state.locale, "Effective From", "اعتبار از"))}<input type="date" disabled></label>
                  </div>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="workweek" hidden>
                  <div class="cp-calendar-table-wrap"><table><thead><tr><th>${escapeHtml(uiText(state.locale, "Day", "روز"))}</th><th>${escapeHtml(uiText(state.locale, "Working Day", "روز کاری"))}</th><th>${escapeHtml(uiText(state.locale, "Start", "شروع"))}</th><th>${escapeHtml(uiText(state.locale, "Finish", "پایان"))}</th><th>${escapeHtml(uiText(state.locale, "Break", "وقفه"))}</th><th>${escapeHtml(uiText(state.locale, "Add Interval", "افزودن بازه"))}</th></tr></thead><tbody>
                    ${[["Saturday","شنبه"],["Sunday","یکشنبه"],["Monday","دوشنبه"],["Tuesday","سه‌شنبه"],["Wednesday","چهارشنبه"],["Thursday","پنجشنبه"],["Friday","جمعه"]].map(([en,fa])=>`<tr><th>${escapeHtml(uiText(state.locale,en,fa))}</th><td><input type="checkbox" disabled aria-label="${escapeAttribute(uiText(state.locale,"Working day","روز کاری"))}"></td><td><input type="time" disabled></td><td><input type="time" disabled></td><td><input type="text" disabled placeholder="—"></td><td><button type="button" disabled>+</button></td></tr>`).join("")}
                  </tbody></table></div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Supports split shifts, multiple work intervals, overnight shifts and nonworking days.", "پشتیبانی از شیفت‌های چندبخشی، چند بازه کاری، شیفت شبانه و روزهای غیرکاری."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="exceptions" hidden>
                  <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Exceptions and Holidays", "استثناها و تعطیلات"))}</strong><button type="button" disabled>${escapeHtml(uiText(state.locale, "Add Exception", "افزودن استثنا"))}</button></div>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No exceptions are loaded.", "هیچ استثنایی بارگذاری نشده است."))}</div>
                  <p class="cp-calendar-hint">${escapeHtml(uiText(state.locale, "Exception types include nonworking days, modified working hours and recurring holidays.", "انواع استثنا شامل روز غیرکاری، ساعات کاری اصلاح‌شده و تعطیلات تکرارشونده است."))}</p>
                </section>
                <section class="cp-calendar-editor-panel" data-calendar-editor-panel="assignments" hidden>
                  <div class="cp-calendar-empty">${escapeHtml(uiText(state.locale, "No project, resource or activity calendar assignments are loaded.", "هیچ تخصیص تقویم پروژه، منبع یا فعالیت بارگذاری نشده است."))}</div>
                </section>
              </div>
              <p class="cp-calendar-notice">${escapeHtml(uiText(state.locale, "Visual editor structure is present. Editing and saving are disabled until the authoritative calendar service and scheduling-core assignment contract are connected; no sample calendar values are fabricated.", "ساختار ویرایشگر بصری آماده است. ویرایش و ذخیره تا اتصال سرویس مرجع تقویم و قرارداد تخصیص هسته زمان‌بندی غیرفعال است؛ هیچ مقدار نمونه‌ای ساخته نشده است."))}</p>
            </section>
          </div>
        </div>`;
      break;
    case "resources":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Resource capacity and assignment surfaces are kept in the workspace tools. Existing capacity limits and assignments are read from the project service; this page does not invent resource values.", "سطوح ظرفیت و تخصیص منابع در ابزارهای محیط کار نگهداری می‌شوند. محدودیت‌های ظرفیت و تخصیص‌های موجود از سرویس پروژه خوانده می‌شوند؛ این صفحه مقدار ساختگی منبع نمی‌سازد."))}</p>
        <div class="cp-p6-module-metrics">
          ${metric(state.activities.length, uiText(state.locale, "Activities", "فعالیت‌ها"))}
          ${metric(state.relationships.length, uiText(state.locale, "Assignments in logic", "تخصیص در منطق"))}
        </div>
        ${controls(`${moduleButton("tools", "resource", uiText(state.locale, "Open resource capacity", "بازکردن ظرفیت منابع"))}${moduleButton("assignments", "link", uiText(state.locale, "Resource assignments", "تخصیص منابع"))}`)}`;
      break;
    case "documents":
      body = state.documents.length
        ? `<div class="cp-p6-module-list">${state.documents.map((document) => `<article><strong>${escapeHtml(document.documentId)}</strong><span>${escapeHtml(document.title)}</span><small>${escapeHtml(document.resourceType)} · ${escapeHtml(document.status)} · R${document.revision}</small></article>`).join("")}</div>`
        : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No project documents have been recorded yet.", "هنوز سندی برای این پروژه ثبت نشده است."))}</p>`;
      body += controls(moduleButton("tools", "file", uiText(state.locale, "Open workspace tools", "بازکردن ابزارهای محیط کار")));
      break;
    case "cost":
      body = `
        <div class="cp-p6-module-metrics">
          ${metric(state.procurementRecords.length, t.procurement)}
          ${metric(state.changeNotices.length + state.changeCases.length + state.claims.length, t.commercial)}
        </div>
        <p>${escapeHtml(uiText(state.locale, "Cost presentation uses the procurement, change and claim records already loaded for this project. Financial calculations remain in the authoritative core.", "نمایش هزینه از سوابق تدارکات، تغییر و ادعای بارگذاری‌شده برای این پروژه استفاده می‌کند. محاسبات مالی در هستهٔ مرجع باقی می‌ماند."))}</p>
        ${controls(moduleButton("tools", "money", uiText(state.locale, "Open cost records", "بازکردن سوابق هزینه")))}`;
      break;
    case "progress":
      body = `
        <div class="cp-p6-module-metrics">
          ${metric(state.siteDailyLogs.length, t.siteLogs)}
          ${metric(state.timecards.length + state.equipmentReports.length, `${t.attendance} / ${t.equipment}`)}
          ${metric(state.fieldIssues.length, t.issues)}
        </div>
        <p>${escapeHtml(uiText(state.locale, "Progress presentation reads the field records already saved for this project. No progress percentages are computed on this page.", "نمایش پیشرفت از سوابق کارگاهی ذخیره‌شده برای این پروژه می‌خواند. هیچ درصد پیشرفتی در این صفحه محاسبه نمی‌شود."))}</p>
        ${controls(moduleButton("tools", "progress", uiText(state.locale, "Open field records", "بازکردن سوابق کارگاه")))}`;
      break;
    case "control":
      body = `
        <div class="cp-p6-module-metrics">
          ${metric(state.inspections.length + state.qualityRecords.length, t.assurance)}
          ${metric(state.safetyObservations.length, t.safety)}
          ${metric(state.fieldIssues.length, t.issues)}
          ${metric(state.punchItems.length, t.punchCloseout)}
        </div>
        ${controls(`${moduleButton("forms", "forms", uiText(state.locale, "Forms & Workflows", "فرم‌ها و گردش‌کار"))}${moduleButton("tools", "warning", uiText(state.locale, "Open control records", "بازکردن سوابق کنترل"))}`)}`;
      break;
    case "reports":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Report generation and print layouts are not available in this preview yet. No report is generated or claimed here.", "تولید گزارش و قالب چاپ در این پیش‌نمایش فعال نیست. هیچ گزارشی در این صفحه تولید یا ادعا نمی‌شود."))}</p>
        ${controls(moduleButton("tools", "print", uiText(state.locale, "Open reports and print tools", "بازکردن ابزارهای گزارش و چاپ")))}`;
      break;
    case "settings":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Project settings are edited through the existing authoritative project service.", "تنظیمات پروژه از طریق سرویس مرجع موجود پروژه ویرایش می‌شود."))}</p>
        ${controls(projectSettingsButton(state, t))}`;
      break;
    default:
      body = "";
  }
  return `<section id="cp-p6-module-stage" class="cp-p6-module-stage" data-p6-module="${escapeAttribute(state.activeMenu)}" data-workspace-menu="${escapeAttribute(state.activeMenu)}">
    <header class="cp-p6-module-head"><div><h2>${escapeHtml(title)}</h2><span>${escapeHtml(status)}</span></div><span class="cp-p6-module-surface">${escapeHtml(uiText(state.locale, "Workspace page", "صفحهٔ محیط کار"))}</span></header>
    <div class="cp-p6-module-body">${body}</div>
  </section>`;
}

function moduleButton(action: string, icon: string, label: string): string {
  return `<button type="button" class="cp-p6-module-button" data-rail-action="${escapeAttribute(action)}" title="${escapeAttribute(label)}">${workspaceIcon(icon)}<span>${escapeHtml(label)}</span></button>`;
}

function projectSettingsButton(state: WorkspaceState, t: WorkspaceLabels): string {
  return `<button type="button" class="cp-p6-module-button" data-project-settings title="${escapeAttribute(t.projectSettings)}">${workspaceIcon("settings")}<span>${escapeHtml(t.projectSettings)}</span></button>`;
}

function renderModuleEmptyState(state: WorkspaceState): string {
  const locale = state.locale.split("-")[0] === "fa" ? "fa" : "en";
  const hasControlRecords = Boolean(state.controlSummary || state.smartGuide)
    || state.siteDailyLogs.length > 0
    || state.fieldIssues.length > 0
    || state.timecards.length > 0
    || state.equipmentReports.length > 0
    || state.changeNotices.length > 0
    || state.changeCases.length > 0
    || state.claims.length > 0
    || state.changeClaimImpacts.length > 0
    || state.inspections.length > 0
    || state.qualityRecords.length > 0
    || state.safetyObservations.length > 0
    || state.punchItems.length > 0;
  let copy: { title: string; message: string } | null = null;

  if (state.activeMenu === "reports") {
    copy = locale === "fa"
      ? { title: "گزارش‌ها و چاپ", message: "ساخت گزارش و قالب چاپ در این پیش‌نمایش هنوز فعال نیست. این صفحه گزارشی تولید یا ادعایی درباره کامل بودن گزارش‌ها نمی‌کند." }
      : { title: "Reports & print", message: "Report generation and print layouts are not available in this preview yet. This page has not generated a report or claimed that reporting is complete." };
  } else if (state.activeMenu === "progress") {
    copy = locale === "fa"
      ? { title: "نمای پیشرفت پروژه", message: "داشبورد و نمودارهای اختصاصی پیشرفت هنوز در مرحله پیش‌نمایش هستند. داده‌های ثبت‌شده را از جدول فعالیت‌ها و سوابق کارگاه بررسی کنید؛ در این صفحه شاخص یا درصد ساختگی نمایش داده نمی‌شود." }
      : { title: "Project progress", message: "The dedicated progress dashboard and charts are still in preview. Review recorded data in the activity grid and field records; this page does not invent metrics or percentages." };
  } else if (state.activeMenu === "cost") {
    copy = locale === "fa"
      ? { title: "هزینه و جریان مالی", message: "نمای کامل هزینه، پیش‌بینی و نمودارهای مالی هنوز در این پیش‌نمایش تکمیل نشده است. سوابق موجودِ تدارکات، تغییرات و ادعاها فقط در بخش‌های مربوط به خود نمایش داده می‌شوند." }
      : { title: "Cost & financial control", message: "The full cost view, forecast and financial charts are not complete in this preview. Existing procurement, change and claim records remain available only in their respective panels." };
  } else if (state.activeMenu === "documents" && state.documents.length === 0) {
    copy = locale === "fa"
      ? { title: "اسناد پروژه", message: "هنوز سندی برای این پروژه ثبت یا پیوند داده نشده است. وقتی سندی افزوده شود، در این بخش نمایش داده خواهد شد." }
      : { title: "Project documents", message: "No project documents have been added or linked yet. Documents will appear here after they are recorded." };
  } else if (state.activeMenu === "control" && !hasControlRecords) {
    copy = locale === "fa"
      ? { title: "کنترل پروژه", message: "هنوز سابقه‌ای برای خلاصه کنترل، گزارش روزانه، بازرسی، مسئله، تغییر یا ادعا در دسترس نیست. با ثبت داده‌های معتبر، این بخش پر می‌شود." }
      : { title: "Project controls", message: "No control summary, daily log, inspection, issue, change or claim records are available yet. This area will populate when authoritative records are saved." };
  }

  if (!copy) return "";
  return `<section class="cp-panel cp-module-empty-state" data-workspace-menu="${state.activeMenu}" aria-live="polite"><h2>${escapeHtml(copy.title)}</h2><p>${escapeHtml(copy.message)}</p></section>`;
}

function renderNavigationSurface(state: WorkspaceState): string {
  const t = getWorkspaceLabels(state.locale);
  const item = getWorkspaceNavigation(state.activeMenu);
  const statusLabel = getWorkspaceNavigationStatusLabel(item, state.locale);
  const label = getWorkspaceNavigationLabel(item, state.locale);
  const links = navigationAnchors(item.key);

  return `<section class="cp-panel cp-navigation-surface" aria-label="${escapeAttribute(t.currentSurface)}" data-current-menu="${state.activeMenu}">
    <div><strong>${escapeHtml(label)}</strong><span data-surface-status="${item.status}">${escapeHtml(statusLabel)}</span></div>
    <nav aria-label="${escapeAttribute(label + " " + t.submenu)}">
      ${item.submenus.map((submenu, index) => {
        const anchor = links[index];
        return anchor
          ? navigationTargetAvailable(state, anchor) ? `<a class="cp-submenu-item" href="${escapeAttribute(anchor)}">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</a>` : `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</span>`
          : `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${escapeHtml(getWorkspaceNavigationSubmenuLabel(item, index, state.locale))}</span>`;
      }).join("")}
    </nav>
  </section>`;
}

function navigationAnchors(menu: WorkspaceState["activeMenu"]): readonly (string | null)[] {
  switch (menu) {
    case "project":
      return ["#cp-project-wbs", "#cp-details", "#cp-interchange"];
    case "schedule":
      return ["#cp-activity-grid", "#cp-gantt", "#cp-reference-relationships", "#cp-reference-calendars", "#cp-schedule-options", "#cp-reference-resources", "#cp-reference-progress", "#cp-schedule-run", "#cp-formula-editor", "#cp-schedule-reference", "#cp-reference-options", "#cp-scheduling-reference-formulas", "#cp-scheduling-reference-documentation"];
    case "progress":
      return ["#cp-site-logs", "#cp-field-operations"];
    case "resources":
      return ["#cp-resource-capacity", "#cp-field-operations"];
    case "calendars":
      return [];
    case "cost":
      return ["#cp-procurement", "#cp-change-claim"];
    case "documents":
      return ["#cp-documents", null];
    case "reports":
      return [];
    case "control":
      return ["#cp-control-summary", "#cp-change-claim"];
    case "settings":
      return ["#cp-project-settings-open", "#cp-settings-panel"];

  }
}

function navigationTargetAvailable(state: WorkspaceState, anchor: string): boolean {
  switch (anchor) {
    case "#cp-site-logs":
      return state.siteDailyLogs.length > 0;
    case "#cp-field-operations":
      return state.fieldIssues.length > 0 || state.timecards.length > 0 || state.equipmentReports.length > 0;
    case "#cp-procurement":
      return state.procurementRecords.length > 0;
    case "#cp-change-claim":
      return state.changeNotices.length > 0 || state.changeCases.length > 0 || state.claims.length > 0 || state.changeClaimImpacts.length > 0 || state.documents.length > 0;
    case "#cp-documents":
      return state.documents.length > 0;
    case "#cp-control-summary":
      return state.controlSummary !== null;
    case "#cp-smart-guide":
      return state.smartGuide !== null;
    case "#cp-project-wbs":
      return state.visiblePanels.project_wbs;
    case "#cp-details":
      return state.visiblePanels.details;
    case "#cp-activity-grid":
      return state.visiblePanels.activity_grid;
    case "#cp-gantt":
      return state.visiblePanels.gantt;
    default:
      return true;
  }
}

type SchedulingReferenceRequirement = (typeof SCHEDULING_REFERENCE_CATALOG.requirements)[number];
type SchedulingReferenceFormula = (typeof SCHEDULING_REFERENCE_CATALOG.formulas)[number];
type SchedulingReferenceDocument = (typeof SCHEDULING_REFERENCE_CATALOG.documentation)[number];

function referenceStatusLabel(status: string, t: WorkspaceLabels): string {
  if (status === "MAPPED_NOT_PROVEN" || status.includes("PARITY_NOT_PROVEN")) return t.referenceMappedStatus;
  if (status === "KNOWN_GAP") return t.referenceGapStatus;
  if (status === "INVENTORY_REQUIRED") return t.referenceInventoryStatus;
  if (status === "CORE_RULES_EXTRACTED_NOT_FULL_PARITY_PROVEN" || status === "DOC_CORE_RULES_EXTRACTED") return t.referenceDocReviewedLabel;
  if (status === "TOPIC_MAP_PARTIAL" || status === "DOC_TOPIC_MAP_PARTIAL") return t.referenceDocPartialLabel;
  if (status === "INDEXED_NOT_LINE_REVIEWED" || status === "DOC_INDEXED_NOT_LINE_REVIEWED" || status === "PRODUCT_SCOPE_AND_DETAIL_REVIEW_PENDING" || status === "DOC_PRODUCT_SCOPE_PENDING") return t.referenceDocPendingLabel;
  return t.referenceDocPendingLabel;
}

function renderReferenceRequirement(item: SchedulingReferenceRequirement, t: WorkspaceLabels): string {
  const search = [item.id, item.area, item.feature, item.semantics, ...item.options, item.gap].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.feature)}</strong><span class="cp-reference-status is-${item.status.toLowerCase().replace(/[^a-z0-9-]/g, "-")}">${escapeHtml(referenceStatusLabel(item.status, t))}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceRuleLabel)}:</span> ${escapeHtml(item.semantics)}</p>
      ${item.options.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceOptionsLabel)}:</span><ul>${item.options.map((option) => `<li>${escapeHtml(option)}</li>`).join("")}</ul></div>` : ""}
      ${item.gap ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceGapLabel)}:</span> ${escapeHtml(item.gap)}</p>` : ""}
    </div>
  </details>`;
}

function renderReferenceFormula(item: SchedulingReferenceFormula, t: WorkspaceLabels): string {
  const search = [item.id, item.feature, item.algorithm, ...item.inputs, ...item.options, item.calendarRules, ...item.edgeCases, item.gap].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.feature)}</strong><span class="cp-reference-status">${escapeHtml(t.referenceFormulaStatus)}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceRuleLabel)}:</span> ${escapeHtml(item.algorithm)}</p>
      ${item.inputs.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceInputsLabel)}:</span><ul>${item.inputs.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.options.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceOptionsLabel)}:</span><ul>${item.options.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.calendarRules ? `<p><span class="cp-reference-field-label">${escapeHtml(t.referenceCalendarRulesLabel)}:</span> ${escapeHtml(item.calendarRules)}</p>` : ""}
      ${item.edgeCases.length ? `<div><span class="cp-reference-field-label">${escapeHtml(t.referenceEdgeCasesLabel)}:</span><ul>${item.edgeCases.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : ""}
      ${item.gap ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceGapLabel)}:</span> ${escapeHtml(item.gap)}</p>` : ""}
    </div>
  </details>`;
}

function renderReferenceDocument(item: SchedulingReferenceDocument, t: WorkspaceLabels): string {
  const search = [item.id, item.title, item.scope, item.status, item.reviewed, item.remaining, ...item.requirements].join(" ").toLocaleLowerCase();
  return `<details class="cp-reference-entry" data-reference-search="${escapeAttribute(search)}">
    <summary><code>${escapeHtml(item.id)}</code><strong>${escapeHtml(item.title)}</strong><span class="cp-reference-status">${escapeHtml(referenceStatusLabel(item.status, t))}</span></summary>
    <div class="cp-reference-detail">
      <p><span class="cp-reference-field-label">${escapeHtml(t.referenceReviewLabel)}:</span> ${escapeHtml(item.scope)} — ${escapeHtml(referenceStatusLabel(item.status, t))}</p>
      ${item.reviewed ? `<p>${escapeHtml(item.reviewed)}</p>` : ""}
      ${item.requirements.length ? `<p><span class="cp-reference-field-label">${escapeHtml(t.referenceLinkedReqLabel)}:</span> ${escapeHtml(item.requirements.join(", "))}</p>` : ""}
      ${item.remaining ? `<p class="cp-reference-gap"><span class="cp-reference-field-label">${escapeHtml(t.referenceRemainingLabel)}:</span> ${escapeHtml(item.remaining)}</p>` : ""}
    </div>
  </details>`;
}

function renderSchedulingReference(_locale: string, t: WorkspaceLabels, visible = true): string {
  const used = new Set<string>();
  const groupDefs: { id: string; label: string; includes: (item: SchedulingReferenceRequirement) => boolean }[] = [
    { id: "relationships", label: t.referenceRelationshipsGroupLabel, includes: (item) => ["SCH-007", "SCH-008", "SCH-012"].includes(item.id) || item.area.toLowerCase().includes("relationships") },
    { id: "calendars", label: t.referenceCalendarsGroupLabel, includes: (item) => item.id.startsWith("CAL-") },
    { id: "options", label: t.referenceOptionsGroupLabel, includes: (item) => ["SCH-001", "SCH-002", "SCH-003", "SCH-004", "SCH-005", "SCH-006", "SCH-009", "SCH-010", "SCH-011", "SCH-013", "SCH-014", "PREF-001"].includes(item.id) },
    { id: "resources", label: t.referenceResourcesGroupLabel, includes: (item) => item.id.startsWith("RES-") || item.id.startsWith("ROLE-") || item.id.startsWith("ANALYSIS-") },
    { id: "progress", label: t.referenceProgressGroupLabel, includes: (item) => item.id.startsWith("PROG-") || item.id.startsWith("BAS-") || item.id.startsWith("EVM-") },
  ];
  const groupHtml = groupDefs.map((group) => {
    const entries = SCHEDULING_REFERENCE_CATALOG.requirements.filter((item) => !used.has(item.id) && group.includes(item));
    entries.forEach((item) => used.add(item.id));
    return `<section id="cp-reference-${group.id}" class="cp-reference-group" data-reference-group><h3>${escapeHtml(group.label)} <span>${entries.length}</span></h3>${entries.map((item) => renderReferenceRequirement(item, t)).join("") || `<p class="cp-empty">${escapeHtml(t.referenceNoMatches)}</p>`}</section>`;
  }).join("");
  const remaining = SCHEDULING_REFERENCE_CATALOG.requirements.filter((item) => !used.has(item.id));
  return `<section id="cp-scheduling-reference" class="cp-panel cp-scheduling-reference" ${visible ? "" : "hidden"} dir="${_locale.startsWith("fa") ? "rtl" : "ltr"}" aria-labelledby="cp-scheduling-reference-title">
    <header class="cp-reference-header">
      <div><h2 id="cp-scheduling-reference-title">${escapeHtml(t.referenceTitle)}</h2><p>${escapeHtml(t.referenceDescription)}</p></div>
      <div class="cp-reference-version"><span>${escapeHtml(t.referenceVersion)} ${escapeHtml(SCHEDULING_REFERENCE_CATALOG.version)}</span><span>${escapeHtml(t.referenceAsOf)} ${escapeHtml(SCHEDULING_REFERENCE_CATALOG.asOf)}</span></div>
    </header>
    <p class="cp-reference-notice">${escapeHtml(t.referenceReviewNotice)}</p>
    <div class="cp-reference-metrics" aria-label="${escapeAttribute(t.referenceTitle)}">
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.requirements.length}</strong><span>${escapeHtml(t.referenceRequirementCount)}</span></div>
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.formulas.length}</strong><span>${escapeHtml(t.referenceFormulaCount)}</span></div>
      <div><strong>${SCHEDULING_REFERENCE_CATALOG.documentation.length}</strong><span>${escapeHtml(t.referenceDocumentationCount)}</span></div>
    </div>
    <label class="cp-reference-search"><span>${escapeHtml(t.referenceSearch)}</span><input type="search" data-reference-search-input placeholder="${escapeAttribute(t.referenceSearchPlaceholder)}" /></label>
    <p class="cp-reference-empty" data-reference-no-matches hidden>${escapeHtml(t.referenceNoMatches)}</p>
    <section id="cp-reference-catalog" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceCatalogGroupLabel)} <span>${remaining.length}</span></h3>${remaining.map((item) => renderReferenceRequirement(item, t)).join("")}</section>
    ${groupHtml}
    <section id="cp-scheduling-reference-formulas" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceFormulaGroupLabel)} <span>${SCHEDULING_REFERENCE_CATALOG.formulas.length}</span></h3>${SCHEDULING_REFERENCE_CATALOG.formulas.map((item) => renderReferenceFormula(item, t)).join("")}</section>
    <section id="cp-scheduling-reference-documentation" class="cp-reference-group" data-reference-group><h3>${escapeHtml(t.referenceDocumentationGroupLabel)} <span>${SCHEDULING_REFERENCE_CATALOG.documentation.length}</span></h3>${SCHEDULING_REFERENCE_CATALOG.documentation.map((item) => renderReferenceDocument(item, t)).join("")}</section>
  </section>`;
}

function renderSmartGuide(
  guide: WorkspaceState["smartGuide"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!guide) return "";

  const findings = guide.findings.length
    ? guide.findings
        .slice(0, 5)
        .map((finding) =>
          `<article class="cp-control-finding is-${escapeAttribute(finding.severity)}">
            <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
            <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
          </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  const actions = guide.proposedActions.length
    ? guide.proposedActions
        .map(
          (action) =>
            `<article class="cp-field-card" data-ai-action-id="${escapeAttribute(action.actionId)}">
              <strong>${escapeHtml(action.titleKey)}</strong>
              <span>${escapeHtml(action.actionType)}</span>
              <span>${escapeHtml(action.requiresApproval ? t.humanApprovalRequired : t.noApprovalFlag)}</span>
              <span>${action.sourceCount} ${escapeHtml(t.sourceUnit)}</span>
            </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section id="cp-smart-guide" class="cp-panel cp-smart-guide" aria-label="${escapeAttribute(label)}" data-workspace-menu="control reports">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(label)}</h2>
          <div class="cp-control-result">${escapeHtml(guide.summaryKey)}</div>
        </div>
        <span>${escapeHtml(guide.locale)} · ${escapeHtml(guide.module)}</span>
      </div>
      <div class="cp-field-grid">
        <div>
          <h3>${escapeHtml(t.findings)}</h3>
          <div class="cp-field-list">${findings}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.proposedActions)}</h3>
          <div class="cp-field-list">${actions}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.traceability)}</h3>
          <div class="cp-control-metrics">
            <div class="cp-control-metric"><span>${escapeHtml(t.sources)}</span><strong>${guide.sourceCount}</strong></div>
            <div class="cp-control-metric"><span>${escapeHtml(t.approvalRequired)}</span><strong>${guide.approvalRequiredCount}</strong></div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderControlSummary(
  summary: WorkspaceState["controlSummary"],
  summaryLabel: string,
  metricsLabel: string,
  findingsLabel: string,
): string {
  if (!summary) return "";

  const metrics = Object.entries(summary.metrics)
    .map(([key, value]) => `<div class="cp-control-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");

  const findings = summary.findings.length
    ? summary.findings.map((finding) => `
        <article class="cp-control-finding is-${finding.severity}">
          <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
          <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
        </article>`).join("")
    : "<div class=\"cp-empty\">—</div>";

  return `
    <section id="cp-control-summary" class="cp-panel cp-control-summary" aria-label="${escapeAttribute(summaryLabel)}" data-workspace-menu="control reports">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(summaryLabel)}</h2>
          <div class="cp-control-result">${escapeHtml(summary.resultId)}</div>
        </div>
        <time datetime="${escapeAttribute(summary.generatedAt)}">${escapeHtml(summary.generatedAt)}</time>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(metricsLabel)}</h3>
        <div class="cp-control-metrics">${metrics || '<div class="cp-empty">—</div>'}</div>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(findingsLabel)}</h3>
        <div class="cp-control-findings">${findings}</div>
      </div>
    </section>
  `;
}

function renderSiteDailyLogs(
  logs: WorkspaceState["siteDailyLogs"],
  label: string,
): string {
  if (!logs.length) return "";

  return `
    <section id="cp-site-logs" class="cp-panel cp-site-logs" aria-label="${escapeAttribute(label)}" data-workspace-menu="progress">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-site-log-list">
        ${logs.map((log) => `
          <article class="cp-site-log" data-log-id="${escapeAttribute(log.logId)}">
            <div class="cp-site-log-meta">
              <strong>${escapeHtml(log.locationKey)}</strong>
              <span>${escapeHtml(log.logDate)}</span>
              <span>${escapeHtml(log.status)}</span>
            </div>
            <div class="cp-site-log-entries">
              ${log.entries.map((entry) => `
                <div class="cp-site-log-entry">
                  <span>${escapeHtml(entry.category)}</span>
                  <span>${escapeHtml(entry.text_key)}</span>
                  ${entry.quantity !== null ? `<span>${escapeHtml(entry.quantity)} ${escapeHtml(entry.unit ?? "")}</span>` : ""}
                </div>`).join("")}
            </div>
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderFieldOperations(
  fieldIssues: WorkspaceState["fieldIssues"],
  timecards: WorkspaceState["timecards"],
  equipmentReports: WorkspaceState["equipmentReports"],
  t: WorkspaceLabels,
): string {
  if (!fieldIssues.length && !timecards.length && !equipmentReports.length) return "";

  const issues = fieldIssues.length
    ? fieldIssues.map((issue) => `
        <div class="cp-field-card" data-field-issue-id="${escapeAttribute(issue.issueId)}">
          <strong>${escapeHtml(issue.titleKey)}</strong>
          <span>${escapeHtml(issue.category)}</span>
          <span>${escapeHtml(issue.severity)} · ${escapeHtml(issue.status)}</span>
          <span>${escapeHtml(issue.locationKey ?? "—")}</span>
          <span>${issue.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${issue.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const attendance = timecards.length
    ? timecards.map((card) => `
        <div class="cp-field-card" data-timecard-id="${escapeAttribute(card.timecardId)}">
          <strong>${escapeHtml(card.personId)}</strong>
          <span>${escapeHtml(card.workplaceKey)}</span>
          <span>${escapeHtml(card.attendanceStatus)}</span>
          <span>${escapeHtml(card.logDate)}</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const equipment = equipmentReports.length
    ? equipmentReports.map((report) => `
        <div class="cp-field-card" data-equipment-report-id="${escapeAttribute(report.reportId)}">
          <strong>${escapeHtml(report.equipmentId)}</strong>
          <span>${escapeHtml(report.workplaceKey)}</span>
          <span>${escapeHtml(report.status)}</span>
          ${report.breakdownCauseKey ? `<span>${escapeHtml(report.breakdownCauseKey)}</span>` : ""}
          ${report.meterHours !== null ? `<span>${escapeHtml(report.meterHours)} h</span>` : ""}
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section id="cp-field-operations" class="cp-panel cp-field-ops" aria-label="${escapeAttribute(t.issues + " / " + t.attendance + " / " + t.equipment)}" data-workspace-menu="progress resources">
      <div class="cp-field-grid">
        <div>
          <h2>${escapeHtml(t.issues)}</h2>
          <div class="cp-field-list">${issues}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.attendance)}</h2>
          <div class="cp-field-list">${attendance}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.equipment)}</h2>
          <div class="cp-field-list">${equipment}</div>
        </div>
      </div>
    </section>
  `;
}

function renderFieldAssurance(
  inspections: WorkspaceState["inspections"],
  qualityRecords: WorkspaceState["qualityRecords"],
  safetyObservations: WorkspaceState["safetyObservations"],
  punchItems: WorkspaceState["punchItems"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!inspections.length && !qualityRecords.length && !safetyObservations.length && !punchItems.length) return "";

  return `
    <section class="cp-panel cp-field-assurance" aria-label="${escapeAttribute(label)}" data-workspace-menu="control">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-field-assurance-grid">
        <div>
          <h3>${escapeHtml(t.inspections)}</h3>
          ${inspections.length ? inspections.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.inspectionTypeKey)}</strong>
              <span>${escapeHtml(item.subjectId)}</span>
              <span>${escapeHtml(item.result)} · ${escapeHtml(item.status)}</span>
              <span>${item.checklist.length} ${escapeHtml(t.itemUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.qualityNcr)}</h3>
          ${qualityRecords.length ? qualityRecords.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(item.correctiveActionKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.safety)}</h3>
          ${safetyObservations.length ? safetyObservations.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.punchCloseout)}</h3>
          ${punchItems.length ? punchItems.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.priority)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
              <span>${escapeHtml(t.due)}: ${escapeHtml(item.dueDate ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderProcurement(
  records: WorkspaceState["procurementRecords"],
  label: string,
  t: WorkspaceLabels,
): string {
  if (!records.length) return "";

  return `
    <section id="cp-procurement" class="cp-panel cp-procurement" aria-label="${escapeAttribute(label)}" data-workspace-menu="resources cost">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-field-list">
        ${records.map((record) => `
          <article class="cp-field-card" data-procurement-id="${escapeAttribute(record.id)}">
            <div class="cp-field-card-meta">
              <strong>${escapeHtml(record.id)}</strong>
              <span>${escapeHtml(record.type)}</span>
              <span>${escapeHtml(record.status)}</span>
            </div>
            ${record.supplierId ? `<div>${escapeHtml(t.supplier)}: ${escapeHtml(record.supplierId)}</div>` : ""}
            ${record.referenceId ? `<div>${escapeHtml(t.reference)}: ${escapeHtml(record.referenceId)}</div>` : ""}
            ${record.amount !== null ? `<div>${escapeHtml(t.amount)}: ${escapeHtml(record.amount)} ${escapeHtml(record.currency ?? "")}</div>` : ""}
            <div>${record.itemCount} ${escapeHtml(t.itemUnit)} · ${record.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${record.evidenceCount} ${escapeHtml(t.evidenceUnit)}</div>
            ${record.approvalRef ? `<div>${escapeHtml(t.approval)}: ${escapeHtml(record.approvalRef)}</div>` : ""}
            ${record.date ? `<div>${escapeHtml(t.date)}: ${escapeHtml(record.date)}</div>` : ""}
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderChangeClaimControl(
  notices: WorkspaceState["changeNotices"],
  changes: WorkspaceState["changeCases"],
  claims: WorkspaceState["claims"],
  impacts: WorkspaceState["changeClaimImpacts"],
  label: string,
  documents: WorkspaceState["documents"] = [],
  t: WorkspaceLabels,
): string {
  if (!notices.length && !changes.length && !claims.length && !impacts.length && !documents.length) return "";

  const documentSection = documents.length === 0
    ? ""
    : `<section id="cp-documents" class="control-room-section" data-section="documents" data-workspace-menu="documents">
      <h2>${escapeHtml(t.documents)}</h2>
      <div class="control-room-cards">
        ${documents.map((document) => `<article class="control-room-card">
          <strong>${escapeHtml(document.documentId)}</strong>
          <span>${escapeHtml(document.title)}</span>
          <span>${escapeHtml(document.resourceType)} · ${escapeHtml(document.status)} · Rev ${document.revision}</span>
          <small>${document.linkedEntityRefs.length} ${escapeHtml(t.linkedReferenceUnit)} · ${escapeHtml(document.hasStorageRef ? t.stored : t.noStorage)}</small>
        </article>`).join("")}
      </div>
    </section>`;

  const renderRefs = (values: readonly string[]) =>
    values.length ? values.map((value) => `<span class="cp-ref">${escapeHtml(value)}</span>`).join(" ") : "—";

  return `
    <section id="cp-change-claim" class="cp-panel cp-change-claim" aria-label="${escapeAttribute(label)}" data-workspace-menu="control cost documents">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-change-claim-grid">
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.notices)}</h3>
          ${notices.length ? notices.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.noticeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.costLabel)}: ${renderRefs(item.costRefs)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.changeCases)}</h3>
          ${changes.length ? changes.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.changeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.noticeLabel)}: ${escapeHtml(item.originatingNoticeId ?? "—")}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.impactLinkLabel)}: ${item.impactLinkIds.length} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.claims)}</h3>
          ${claims.length ? claims.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.claimType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.changeLabel)}: ${escapeHtml(item.changeId ?? "—")}</span>
              <span>${escapeHtml(t.entitlement)}: ${escapeHtml(item.entitlementReference ?? "—")}</span>
              <span>${escapeHtml(t.decision)}: ${escapeHtml(item.decisionReference ?? "—")}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div data-workspace-menu="control cost">
          <h3>${escapeHtml(t.impactLinks)}</h3>
          ${impacts.length ? impacts.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.recordType)} · ${escapeHtml(item.recordId)}</strong>
              <span>${escapeHtml(item.impactedDomain)} / ${escapeHtml(item.impactedEntityType)} / ${escapeHtml(item.impactedEntityId)}</span>
              <span>${escapeHtml(item.impactType)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${escapeHtml(item.scheduleReference ?? "—")}</span>
              <span>${escapeHtml(t.costLabel)}: ${escapeHtml(item.costReference ?? "—")}</span>
              <span>${escapeHtml(t.approval)}: ${item.requiresApplicationApproval ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderActivityFilterSort(
  state: WorkspaceState,
  visibleCount: number,
  t: WorkspaceLabels,
): string {
  const sort = state.activitySort;
  const direction = sort?.direction ?? "asc";
  const options = [
    `<option value="wbs"${sort?.columnId === "wbs" ? " selected" : ""}>${escapeHtml(t.activityWbs)}</option>`,
    ...state.columns
      .filter((column) => column.id !== "wbs")
      .map((column) => {
        const selected = sort?.columnId === column.id ? " selected" : "";
        return `<option value="${escapeAttribute(column.id)}"${selected}>${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}</option>`;
      }),
  ].join("");
  return `<div class="cp-activity-toolbar" role="search">
    <label class="cp-activity-filter">
      <span>${escapeHtml(t.activityFilter)}</span>
      <input type="search" data-activity-filter value="${escapeAttribute(state.activityFilter)}" placeholder="${escapeAttribute(t.activityFilterPlaceholder)}" autocomplete="off" spellcheck="false">
    </label>
    <label class="cp-activity-group">
      <span>${escapeHtml(t.groupBy)}</span>
      <select data-activity-group aria-label="${escapeAttribute(t.groupBy)}">
        <option value="wbs"${state.activityGroupBy === "wbs" ? " selected" : ""}>${escapeHtml(t.activityWbs)}</option>
        <option value="none"${state.activityGroupBy === "none" ? " selected" : ""}>${escapeHtml(t.groupNone)}</option>
      </select>
    </label>
    <label class="cp-activity-sort">
      <span>${escapeHtml(t.activitySort)}</span>
      <select data-activity-sort aria-label="${escapeAttribute(t.activitySort)}">
        <option value=""${sort ? "" : " selected"}>${escapeHtml(t.sortNone)}</option>
        ${options}
      </select>
    </label>
    <button type="button" data-activity-sort-direction title="${escapeAttribute(direction === "asc" ? t.sortAscending : t.sortDescending)}" aria-label="${escapeAttribute(direction === "asc" ? t.sortAscending : t.sortDescending)}" ${sort ? "" : "disabled"}>${direction === "asc" ? "↑" : "↓"}</button>
    <output data-activity-count aria-live="polite">${visibleCount} / ${state.activities.length} ${escapeHtml(t.matchingActivities)}</output>
  </div>`;
}

function renderP6FieldChooser(
  state: WorkspaceState,
  history?: WorkspaceRendererOptions["layoutHistory"],
): string {
  const t = getWorkspaceLabels(state.locale);
  const registry = state.p6FieldRegistry;
  const layout = state.p6Layout;
  if (!registry || !layout) return "";
  const inLayout = new Set(layout.columns.map((column) => column.field_id));
  const available = registry.fields.filter((field) => !inLayout.has(field.field_id));
  const orderedColumns = layout.columns.slice().sort((a, b) => a.order - b.order);
  const visibleColumns = orderedColumns.filter((column) => column.visible);
  const hiddenColumns = orderedColumns.filter((column) => !column.visible);
  const noticeText = history?.noticeKey
    ? {
        undone: t.layoutUndone,
        redone: t.layoutRedone,
        restored: t.layoutRestored,
        empty: t.layoutHistoryEmpty,
        failed: t.layoutSaveFailed,
        conflict: t.layoutConflict,
      }[history.noticeKey]
    : null;
  const notice = noticeText
    ? `<output class="cp-p6-history-notice" role="status" aria-live="polite">${escapeHtml(noticeText)}</output>`
    : "";
  const restorable = (history?.revisions ?? []).filter((item) => item.revision < layout.revision);
  const restoreOptions = restorable
    .map((item) => `<option value="${item.revision}">R${item.revision} · ${item.columnCount} ${escapeHtml(t.columnUnit)}</option>`)
    .join("");
  const restoreControl = history
    ? `<span class="cp-p6-history-restore"><label>${escapeHtml(t.revisionOption)} <select data-p6-layout-revision-select aria-label="${escapeAttribute(t.restore)}" title="${escapeAttribute(t.layoutHistory)}" ${restoreOptions ? "" : "disabled"}>${restoreOptions || `<option value="">${escapeHtml(t.layoutHistoryEmpty)}</option>`}</select></label><button type="button" data-p6-layout-restore title="${escapeAttribute(t.restore)}" aria-label="${escapeAttribute(t.restore)}" ${restoreOptions ? "" : "disabled"}>${escapeHtml(t.restore)}</button></span>`
    : "";
  return `<section class="cp-p6-field-chooser" aria-label="${escapeAttribute(t.fieldChooser)}">
    <div class="cp-p6-field-chooser-heading">
      <strong>${escapeHtml(t.fields)}</strong><span>Field Registry · ${layout.scope} · R${layout.revision}</span>
    </div>
    <div class="cp-p6-history-bar" aria-label="${escapeAttribute(t.layoutHistory)}">
      <button type="button" data-p6-layout-undo title="${escapeAttribute(t.undo)}" ${history?.canUndo ? "" : "disabled"}>↶ ${escapeHtml(t.undo)}</button>
      <button type="button" data-p6-layout-redo title="${escapeAttribute(t.redo)}" ${history?.canRedo ? "" : "disabled"}>↷ ${escapeHtml(t.redo)}</button>
      ${restoreControl}
      ${notice}
    </div>
    <div class="cp-p6-field-list">
      ${visibleColumns.map((column, index) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item"><input type="text" data-p6-field-rename="${escapeAttribute(field.field_id)}" value="${escapeAttribute(column.label ?? field.display_name)}" aria-label="${escapeAttribute(t.rename)}" title="${escapeAttribute(t.rename)}"><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}">◌</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="up" title="${escapeAttribute(t.moveUp)}" aria-label="${escapeAttribute(t.moveUp)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="down" title="${escapeAttribute(t.moveDown)}" aria-label="${escapeAttribute(t.moveDown)}" ${index === visibleColumns.length - 1 ? "disabled" : ""}>↓</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="decrease" title="${escapeAttribute(t.narrower)}" aria-label="${escapeAttribute(t.narrower)}">−</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="increase" title="${escapeAttribute(t.wider)}" aria-label="${escapeAttribute(t.wider)}">+</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="start" title="${escapeAttribute(t.alignStart)}" aria-label="${escapeAttribute(t.alignStart)}" aria-pressed="${column.alignment === "start" ? "true" : "false"}">L</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="center" title="${escapeAttribute(t.alignCenter)}" aria-label="${escapeAttribute(t.alignCenter)}" aria-pressed="${column.alignment === "center" ? "true" : "false"}">C</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="end" title="${escapeAttribute(t.alignEnd)}" aria-label="${escapeAttribute(t.alignEnd)}" aria-pressed="${column.alignment === "end" ? "true" : "false"}">R</button><button type="button" data-p6-field-pin="${escapeAttribute(field.field_id)}" data-p6-field-pinned="${column.pinned ? "true" : "false"}" title="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-label="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-pressed="${column.pinned ? "true" : "false"}">📌</button><button type="button" data-p6-field-freeze="${escapeAttribute(field.field_id)}" data-p6-field-frozen="${column.frozen ? "true" : "false"}" title="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-label="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-pressed="${column.frozen ? "true" : "false"}">❄</button></span>`;
      }).join("")}
      ${hiddenColumns.map((column) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item is-hidden"><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" data-p6-field-visible="true" title="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}">${escapeHtml(column.label ?? field.display_name)}</button><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button></span>`;
      }).join("")}
      ${available.map((field) => `<button type="button" data-p6-field-add="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.add)}">${escapeHtml(field.display_name)}</button>`).join("")}
    </div>
  </section>`;
}

function renderActivityRow(activity: WorkspaceActivityRow, state: WorkspaceState, stickyOffsets: ReadonlyMap<string, number>): string {
  const selected = activity.id === state.selectedActivityId;
  const predecessors = predecessorSummary(activity.id, state);
  return `<tr role="row" data-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-selected="${selected ? "true" : "false"}" aria-label="${escapeAttribute(activity.id)}" class="${selected ? "is-selected" : ""}">${state.columns.map((column) => `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${renderCell(column, activity, state.calendarMode)}</td>`).join("")}<td class="cp-logic-column" data-predecessors="${escapeAttribute(activity.id)}">${predecessors ? escapeHtml(predecessors) : "—"}</td><td class="cp-actions-column"><button type="button" data-activity-edit="${escapeAttribute(activity.id)}">${escapeHtml(getWorkspaceLabels(state.locale).activityEdit)}</button></td></tr>`;
}

function renderCell(column: WorkspaceColumn, activity: WorkspaceActivityRow, calendarMode: WorkspaceState["calendarMode"]): string {
  if (column.id === "activity_id") return escapeHtml(activity.id);
  if (column.id === "activity_code") return escapeHtml(activity.code);
  if (column.id === "activity_name") return escapeHtml(activity.name);
  return renderCellValue(column, activity.cells?.[column.id] ?? null, calendarMode);
}

function renderCellValue(column: WorkspaceColumn, value: WorkspaceCellValue, calendarMode: WorkspaceState["calendarMode"]): string {
  if (value === null || value === undefined) return "—";
  if (column.id === "progress" && typeof value === "number") return `${value}%`;
  if (typeof value === "boolean") return value ? "✓" : "—";
  if (column.dataType === "date" && typeof value === "string") {
    return escapeHtml(formatWorkspaceCalendarDate(value, calendarMode));
  }
  return escapeHtml(String(value));
}

function renderGantt(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  ganttScale: WorkspaceGanttScale,
  calendarMode: WorkspaceCalendarMode,
  scale: ReturnType<typeof createGanttScale>,
  t: WorkspaceLabels,
  selectedActivityId: string | null,
  showRelationships: boolean,
): string {
  if (!scale) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const bars = activities
    .map((activity) => createGanttBarGeometry(activity, scale))
    .filter((bar): bar is GanttBarGeometry => bar !== null);
  if (!bars.length) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;

  const ticks = createGanttAxisTicks(scale, ganttScale);
  const links = createGanttLinkGeometry(relationships, bars);
  const scaleModeLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const toolbar = `<div class="cp-gantt-toolbar" aria-label="${escapeAttribute(t.ganttScaleLabel)}"><div class="cp-gantt-scale-controls" role="group" aria-label="${escapeAttribute(t.ganttScaleLabel)}">${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<button type="button" class="cp-gantt-scale-button${mode === ganttScale ? " is-active" : ""}" data-gantt-scale="${mode}" aria-pressed="${mode === ganttScale ? "true" : "false"}">${escapeHtml(scaleModeLabels[mode])}</button>`).join("")}</div><button type="button" class="cp-gantt-relationships-toggle${showRelationships ? " is-active" : ""}" data-gantt-relationships-toggle="${showRelationships ? "false" : "true"}" aria-pressed="${showRelationships ? "true" : "false"}" title="${escapeAttribute(t.ganttLinksToggle)}"><span>${escapeHtml(t.ganttLinksToggle)}</span><strong>${escapeHtml(showRelationships ? t.ganttLinksOn : t.ganttLinksOff)}</strong></button></div>`;
  const axis = `<div class="cp-gantt-axis" aria-hidden="true"><span class="cp-gantt-axis-label"></span><div class="cp-gantt-axis-track">${ticks.map((tick, index) => {
    const fullLabel = formatWorkspaceCalendarDate(tick.date, calendarMode);
    // At day resolution daily ticks are too close together for the full date,
    // so the DOM keeps the complete label (and tooltip) while CSS renders only
    // the day number through data-gantt-day.
    const dayLabel = fullLabel.split(/[\/\-]/).filter(Boolean).pop() ?? fullLabel;
    const dayClass = ganttScale === "day" ? " is-day" : "";
    const dayAttribute = ganttScale === "day" ? ` data-gantt-day="${escapeAttribute(dayLabel)}"` : "";
    return `<span class="cp-gantt-axis-tick${index === 0 ? " is-first" : tick.leftPercent > 88 ? " is-last" : ""}${dayClass}" data-gantt-tick="${escapeAttribute(tick.date)}"${dayAttribute} title="${escapeAttribute(fullLabel)}" style="left:${tick.leftPercent}%">${escapeHtml(fullLabel)}</span>`;
  }).join("")}</div></div>`;
  const linkSvg = showRelationships && links.length
    ? `<svg class="cp-gantt-links" viewBox="0 0 100 ${bars.length * 100}" preserveAspectRatio="none" role="img" aria-label="${escapeAttribute(t.ganttLinks)}"><defs><marker id="cp-gantt-arrow" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head" d="M 0 0 L 6 3 L 0 6 z"></path></marker><marker id="cp-gantt-arrow-critical" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head is-critical" d="M 0 0 L 6 3 L 0 6 z"></path></marker></defs>${links.map((link) => `<path class="cp-gantt-link${link.critical ? " is-critical" : ""}" data-gantt-link="${escapeAttribute(link.relationshipId)}" data-link-type="${link.type}" data-link-from="${escapeAttribute(link.predecessorId)}" data-link-to="${escapeAttribute(link.successorId)}" d="${escapeAttribute(link.path)}" marker-end="url(#cp-gantt-arrow${link.critical ? "-critical" : ""})" vector-effect="non-scaling-stroke"></path>`).join("")}</svg>`
    : "";
  const rows = bars.map((bar) => `<div class="cp-gantt-row${bar.activityId === selectedActivityId ? " is-selected" : ""}" role="button" data-gantt-activity-id="${escapeAttribute(bar.activityId)}" tabindex="0" aria-pressed="${bar.activityId === selectedActivityId ? "true" : "false"}" aria-label="${escapeAttribute(bar.activityId)}"><span class="cp-gantt-label">${escapeHtml(bar.activityId)}</span><div class="cp-gantt-track"><div class="cp-gantt-bar${bar.critical ? " is-critical" : ""}${bar.milestone ? " is-milestone" : ""}" style="left:${bar.leftPercent}%;width:${bar.widthPercent}%" title="${escapeAttribute(bar.activityId + (bar.milestone ? " — " + t.milestone : "") + " — " + bar.progressPercent + "%" + (bar.critical ? " — " + t.critical : ""))}"><span class="cp-gantt-progress" style="width:${bar.progressPercent}%"></span></div></div></div>`).join("");

  return `<div class="cp-gantt-board" role="region" aria-label="${escapeAttribute(t.gantt)}" data-gantt-scale-mode="${ganttScale}">${toolbar}${axis}<div class="cp-gantt-chart" style="--cp-gantt-rows:${bars.length}">${rows}${linkSvg}</div></div>`;
}





const WBS_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["notebook", "Notebook", "دفترچه"],
  ["budget-log", "Budget Log", "دفتر ثبت بودجه"],
  ["spending-plan", "Spending Plan", "برنامه هزینه"],
  ["budget-summary", "Budget Summary", "خلاصه بودجه"],
  ["milestones", "WBS Milestones", "نقاط عطف ساختار شکست"],
  ["documents", "WPs & Docs", "محصولات کاری و اسناد"],
  ["earned-value", "Earned Value", "ارزش کسب‌شده"],
  ["planning-resources", "Planning Resources", "منابع برنامه‌ریزی"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderWbsDetails(state: WorkspaceState, activeTab: string): string {
  const node = state.wbsNodes.find((item) => item.id === state.selectedWbsId);
  const panel = (tab: string): string => {
    if (!node) return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a WBS element to display its details.", "برای نمایش جزئیات، یک عنصر ساختار شکست انتخاب کنید."))}</p>`;
    if (tab === "general") {
      const parent = node.parentWbsId ? state.wbsNodes.find((item) => item.id === node.parentWbsId)?.name ?? node.parentWbsId : uiText(state.locale, "Project root", "ریشه پروژه");
      const fields = [
        [uiText(state.locale, "WBS ID", "شناسه WBS"), node.id],
        [uiText(state.locale, "WBS Code", "کد WBS"), node.localCode],
        [uiText(state.locale, "WBS Name", "نام WBS"), node.name],
        [uiText(state.locale, "Parent", "والد"), parent],
        [uiText(state.locale, "Sequence", "ترتیب"), String(node.sequenceNumber)],
        [uiText(state.locale, "Record revision", "ویرایش رکورد"), String(node.recordRevision)],
      ];
      return `<div class="cp-activity-detail-fields">${fields.map(([label, value]) => `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
    }
    const tabInfo = WBS_DETAIL_TABS.find(([key]) => key === tab);
    return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, `No authoritative ${tabInfo?.[1] ?? "WBS"} records are loaded for this element.`, `اطلاعات مرجع بخش «${tabInfo?.[2] ?? "جزئیات WBS"}» برای این عنصر بارگذاری نشده است.`))}</p>`;
  };
  return `<section class="cp-wbs-details">
    <header class="cp-wbs-details-heading"><strong>${escapeHtml(uiText(state.locale, "WBS Details", "جزئیات ساختار شکست"))}</strong><span>${escapeHtml(node?.localCode ?? "—")}</span></header>
    <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "WBS detail tabs", "زبانه‌های جزئیات WBS"))}">
      ${WBS_DETAIL_TABS.map(([key, en, fa]) => `<button type="button" role="tab" data-wbs-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-wbs-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
    </nav>
    ${WBS_DETAIL_TABS.map(([key]) => `<div id="cp-wbs-detail-panel-${key}" role="tabpanel" data-wbs-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${panel(key)}</div>`).join("")}
  </section>`;
}

const PROJECT_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["dates", "Dates", "تاریخ‌ها"],
  ["notebook", "Notebook", "دفترچه"],
  ["budget-log", "Budget Log", "دفتر ثبت بودجه"],
  ["spending-plan", "Spending Plan", "برنامه هزینه"],
  ["budget-summary", "Budget Summary", "خلاصه بودجه"],
  ["funding", "Funding", "تأمین مالی"],
  ["codes", "Codes", "کدها"],
  ["defaults", "Defaults", "پیش‌فرض‌ها"],
  ["resources", "Resources", "منابع"],
  ["settings", "Settings", "تنظیمات"],
  ["calculations", "Calculations", "محاسبات"],
  ["planning-resources", "Planning Resources", "منابع برنامه‌ریزی"],
  ["contract-management", "Contract Management", "مدیریت قرارداد"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderWindowDetailsPanel(state: WorkspaceState, t: WorkspaceLabels, container: HTMLElement): string {
  if (state.activeMenu === "schedule") {
    return renderActivityDetailsPanel(state, t, activityDetailsTabByContainer.get(container) ?? "general", getActivityDetailsVisibleTabs(container));
  }
  if (state.activeMenu === "project") {
    const activeTab = projectDetailsTabByContainer.get(container) ?? "general";
    const projectContent = (tab: string): string => {
      if (tab === "general") return `<div class="cp-activity-detail-fields">
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Project ID", "شناسه پروژه"))}</span><strong>${escapeHtml(state.context.project_id)}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Workspace revision", "ویرایش محیط کار"))}</span><strong>R${state.context.revision}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "WBS elements", "عناصر ساختار شکست"))}</span><strong>${state.wbsNodes.length}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Activities", "فعالیت‌ها"))}</span><strong>${state.activities.length}</strong></div>
        <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Relationships", "روابط"))}</span><strong>${state.relationships.length}</strong></div>
      </div>`;
      const tabInfo = PROJECT_DETAIL_TABS.find(([key]) => key === tab);
      return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, `No authoritative ${tabInfo?.[1] ?? "project"} detail fields are loaded for this project.`, `اطلاعات مرجع بخش «${tabInfo?.[2] ?? "جزئیات پروژه"}» برای این پروژه بارگذاری نشده است.`))}</p>`;
    };
    return `<div class="cp-activity-details cp-project-details">
      <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(uiText(state.locale, "Project Details", "جزئیات پروژه"))}</h2><span>${escapeHtml(state.context.project_id)}</span></div><small>${escapeHtml(uiText(state.locale, "Selected project", "پروژه انتخاب‌شده"))}</small></header>
      <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Project detail tabs", "زبانه‌های جزئیات پروژه"))}">
        ${PROJECT_DETAIL_TABS.map(([key, en, fa]) => `<button type="button" role="tab" data-project-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-project-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
      </nav>
      ${PROJECT_DETAIL_TABS.map(([key]) => `<section id="cp-project-detail-panel-${key}" class="cp-activity-detail-panel" role="tabpanel" data-project-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${projectContent(key)}</section>`).join("")}
    </div>`;
  }
  const title = getWorkspaceNavigationLabel(getWorkspaceNavigation(state.activeMenu), state.locale);
  return `<div class="cp-activity-details"><header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(uiText(state.locale, "Details", "جزئیات"))}</h2><span>${escapeHtml(title)}</span></div></header><p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a record in this window to display its details. This window's detail tabs are not implemented yet.", "برای نمایش جزئیات، یک رکورد در این پنجره انتخاب کنید. زبانه‌های اختصاصی این پنجره هنوز پیاده‌سازی نشده‌اند."))}</p></div>`;
}

const ACTIVITY_DETAIL_TABS = [
  ["general", "General", "عمومی"],
  ["status", "Status", "وضعیت"],
  ["resources", "Resources", "منابع"],
  ["predecessors", "Predecessors", "پیش‌نیازها"],
  ["successors", "Successors", "پس‌نیازها"],
  ["codes", "Codes", "کدها"],
  ["tasks", "Tasks", "وظایف"],
  ["discussion", "Discussion", "گفت‌وگو"],
  ["notebook", "Notebook", "دفترچه"],
  ["steps", "Steps", "گام‌ها"],
  ["feedback", "Feedback", "بازخورد"],
  ["documents", "WPs & Docs", "محصولات کاری و اسناد"],
  ["expenses", "Expenses", "هزینه‌ها"],
  ["summary", "Summary", "خلاصه"],
  ["relationships", "Relationships", "روابط"],
  ["risks", "Risks", "ریسک‌ها"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
] as const;

function renderActivityDetailsPanel(state: WorkspaceState, t: WorkspaceLabels, activeTab: string, visibleTabs: ReadonlySet<string>): string {
  const activity = state.activities.find((item) => item.id === state.selectedActivityId);
  const value = (key: string): string => {
    if (!activity) return "—";
    const raw = activity.cells?.[key];
    if (raw !== undefined && raw !== null && raw !== "") return String(raw);
    if (key === "activity_id" || key === "id") return activity.id;
    if (key === "activity_name" || key === "name") return activity.name;
    if (key === "wbs_id" || key === "wbs") return activity.wbsId;
    return "—";
  };
  const field = (label: string, content: string): string =>
    `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`;
  const empty = (message: string): string => `<p class="cp-activity-detail-empty">${escapeHtml(message)}</p>`;
  const relationshipRows = (kind: "predecessors" | "successors" | "relationships"): string => {
    if (!activity) return empty(uiText(state.locale, "Select an activity to view its relationships.", "برای مشاهده روابط، یک فعالیت انتخاب کنید."));
    const rows = state.relationships.filter((item) => kind === "predecessors"
      ? item.successorId === activity.id
      : kind === "successors" ? item.predecessorId === activity.id
        : item.predecessorId === activity.id || item.successorId === activity.id);
    if (!rows.length) return empty(uiText(state.locale, "No relationship records are available for this activity.", "برای این فعالیت رابطه‌ای ثبت نشده است."));
    return `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table"><thead><tr><th>${escapeHtml(uiText(state.locale, "Predecessor", "پیش‌نیاز"))}</th><th>${escapeHtml(uiText(state.locale, "Successor", "پس‌نیاز"))}</th><th>${escapeHtml(uiText(state.locale, "Type", "نوع"))}</th><th>${escapeHtml(uiText(state.locale, "Lag", "وقفه"))}</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHtml(row.predecessorId)}</td><td>${escapeHtml(row.successorId)}</td><td>${row.type}</td><td>${escapeHtml(formatRelationshipLag(row.lagValue, row.lagUnit, t))}</td></tr>`).join("")}</tbody></table></div>`;
  };
  const contentFor = (tab: string): string => {
    if (!activity) return empty(uiText(state.locale, "Select an activity in the table or Gantt chart to display its details.", "برای نمایش جزئیات، یک فعالیت را در جدول یا نمودار گانت انتخاب کنید."));
    if (tab === "general") {
      const coreFields = [
        field(uiText(state.locale, "Activity ID", "شناسه فعالیت"), activity.id),
        field(uiText(state.locale, "Activity Name", "نام فعالیت"), activity.name),
        field(uiText(state.locale, "WBS", "ساختار شکست"), activity.wbsId),
      ];
      const mapped = state.columns.map((column) => {
        const raw = activity.cells?.[column.id];
        return raw === undefined || raw === null || raw === "" ? "" : field(localizeWorkspaceLabel(state.locale, column.label), String(raw));
      }).filter(Boolean);
      return `<div class="cp-activity-detail-fields">${coreFields.join("")}${mapped.join("")}</div>`;
    }
    if (tab === "status") {
      const keys = ["status", "percent_complete", "duration", "remaining_duration", "actual_duration", "actual_start", "actual_finish", "early_start", "early_finish", "late_start", "late_finish", "total_float", "free_float"];
      return `<div class="cp-activity-detail-fields">${keys.map((key) => field(key.replaceAll("_", " "), value(key))).join("")}</div>`;
    }
    if (tab === "predecessors" || tab === "successors" || tab === "relationships") return relationshipRows(tab);
    if (tab === "summary") {
      const facts = activity.gantt;
      return facts ? `<div class="cp-activity-detail-fields">${field(uiText(state.locale, "Start", "شروع"), String(facts.start ?? "—"))}${field(uiText(state.locale, "Finish", "پایان"), String(facts.finish ?? "—"))}${field(uiText(state.locale, "Critical", "بحرانی"), facts.critical ? uiText(state.locale, "Yes", "بله") : uiText(state.locale, "No", "خیر"))}</div>` : empty(uiText(state.locale, "No authoritative schedule summary is available for this activity.", "خلاصه زمان‌بندی مرجع برای این فعالیت موجود نیست."));
    }
    const tabLabel = ACTIVITY_DETAIL_TABS.find(([key]) => key === tab);
    return empty(uiText(state.locale, `No ${tabLabel?.[1] ?? "detail"} records are loaded for this activity.`, `برای این فعالیت هنوز سابقه‌ای در بخش «${tabLabel?.[2] ?? "جزئیات"}» بارگذاری نشده است.`));
  };
  return `<div class="cp-activity-details">
    <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(t.details)}</h2><span>${escapeHtml(activity ? `${activity.id} — ${activity.name}` : state.selectedActivityId ?? "—")}</span></div><div class="cp-activity-details-heading-actions"><small>${escapeHtml(uiText(state.locale, "Activity Details", "جزئیات فعالیت"))}</small><button type="button" data-activity-details-options-open>${escapeHtml(uiText(state.locale, "Customize Tabs", "تنظیم زبانه‌ها"))}</button></div></header>
    <nav class="cp-activity-detail-tabs" role="tablist" aria-label="${escapeAttribute(uiText(state.locale, "Activity detail tabs", "زبانه‌های جزئیات فعالیت"))}">
      ${ACTIVITY_DETAIL_TABS.filter(([key]) => visibleTabs.has(key)).map(([key, en, fa]) => `<button type="button" role="tab" data-activity-detail-tab="${key}" aria-selected="${activeTab === key}" class="${activeTab === key ? "is-active" : ""}" aria-controls="cp-activity-detail-panel-${key}">${escapeHtml(uiText(state.locale, en, fa))}</button>`).join("")}
    </nav>
    ${ACTIVITY_DETAIL_TABS.filter(([key]) => visibleTabs.has(key)).map(([key]) => `<section id="cp-activity-detail-panel-${key}" class="cp-activity-detail-panel" role="tabpanel" data-activity-detail-panel="${key}"${activeTab === key ? "" : " hidden"}>${contentFor(key)}</section>`).join("")}
  </div>${renderActivityDetailsOptionsDialog(state, visibleTabs)}`;
}

function renderActivityDetailsOptionsDialog(state: WorkspaceState, visibleTabs: ReadonlySet<string>): string {
  return `<dialog class="cp-activity-details-options" data-activity-details-options-dialog aria-labelledby="cp-activity-details-options-title"><div class="cp-activity-details-options-head"><h3 id="cp-activity-details-options-title">${escapeHtml(uiText(state.locale, "Customize Activity Details", "تنظیم جزئیات فعالیت"))}</h3><button type="button" data-activity-details-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></div><p>${escapeHtml(uiText(state.locale, "Choose which detail tabs are visible in the bottom layout.", "زبانه‌هایی را که در چیدمان پایین نمایش داده می‌شوند انتخاب کنید."))}</p><div class="cp-activity-details-options-list">${ACTIVITY_DETAIL_TABS.map(([key, en, fa]) => `<label><input type="checkbox" data-activity-detail-visible="${key}"${visibleTabs.has(key) ? " checked" : ""}> ${escapeHtml(uiText(state.locale, en, fa))}</label>`).join("")}</div><footer><button type="button" data-activity-details-options-close>${escapeHtml(uiText(state.locale, "Cancel", "انصراف"))}</button><button type="button" data-activity-details-apply>${escapeHtml(uiText(state.locale, "Apply", "اعمال"))}</button></footer></dialog>`;
}

function getActivityDetailsVisibleTabs(container: HTMLElement): Set<string> {
  const existing = activityDetailsVisibleTabsByContainer.get(container);
  if (existing) return existing;
  const defaults = new Set<string>(ACTIVITY_DETAIL_TABS.map(([key]) => key));
  try {
    const raw = window.localStorage.getItem(ACTIVITY_DETAILS_TABS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as unknown;
      if (Array.isArray(parsed)) {
        const valid = new Set(parsed.filter((value): value is string => typeof value === "string" && defaults.has(value)));
        if (valid.size) { activityDetailsVisibleTabsByContainer.set(container, valid); return valid; }
      }
    }
  } catch { /* use defaults when local storage is unavailable or malformed */ }
  activityDetailsVisibleTabsByContainer.set(container, defaults);
  return defaults;
}

function renderLayoutOptionsDialog(state: WorkspaceState, t: WorkspaceLabels): string {
  const scaleLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  return `<dialog class="cp-layout-options-dialog" data-layout-options-dialog aria-labelledby="cp-layout-options-title">
    <form method="dialog" class="cp-layout-options-form">
      <header><div><small>${escapeHtml(uiText(state.locale, "Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-layout-options-title">${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</h2></div><button type="button" data-layout-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Timescale", "مقیاس زمانی"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Display interval", "بازه نمایش"))}
          <select data-layout-timescale>${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<option value="${mode}"${state.ganttScale === mode ? " selected" : ""}>${escapeHtml(scaleLabels[mode])}</option>`).join("")}</select>
        </label>
      </section>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Gantt display", "نمایش گانت"))}</h3>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-links${state.showGanttRelationships ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
        <p>${escapeHtml(uiText(state.locale, "Changes apply to the current Activities view. Other chart and layout controls will appear when their corresponding view is implemented.", "تغییرات روی نمای فعلی فعالیت‌ها اعمال می‌شود. گزینه‌های سایر نمودارها و چیدمان‌ها پس از پیاده‌سازی نمای مربوط نمایش داده خواهند شد."))}</p>
      </section>
      <footer><button type="button" data-layout-options-close>${escapeHtml(uiText(state.locale, "Close", "بستن"))}</button></footer>
    </form>
  </dialog>`;
}

function formatRelationshipLag(value: string, unit: string, t: WorkspaceLabels): string {
  return `${value} ${unit === "working-hour" ? t.workingHour : t.workingDay}`;
}

function predecessorSummary(activityId: string, state: WorkspaceState): string {
  return state.relationships
    .filter((relationship) => relationship.successorId === activityId)
    .map((relationship) => {
      const lag = Number(relationship.lagValue);
      const lagText = lag === 0 ? "" : `${lag > 0 ? "+" : ""}${relationship.lagValue}${relationship.lagUnit === "working-hour" ? "h" : "d"}`;
      return `${relationship.predecessorId} ${relationship.type}${lagText}`;
    })
    .join(", ");
}

function renderRelationships(state: WorkspaceState, t: WorkspaceLabels): string {
  const activityOptionsFor = (selectedId?: string): string =>
    state.activities
      .map((activity) => `<option value="${escapeAttribute(activity.id)}"${activity.id === selectedId ? " selected" : ""}>${escapeHtml(activity.id)} — ${escapeHtml(activity.name)}</option>`)
      .join("");
  const typeOptions = (selected: string): string =>
    (["FS", "SS", "FF", "SF"] as const)
      .map((type) => `<option value="${type}"${type === selected ? " selected" : ""}>${type}</option>`)
      .join("");
  const unitOptions = (selected: string): string =>
    [["working-day", t.workingDay], ["working-hour", t.workingHour]]
      .map(([value, label]) => `<option value="${value}"${value === selected ? " selected" : ""}>${escapeHtml(label)}</option>`)
      .join("");
  const editForm = (relationship: WorkspaceRelationshipRow): string => `<details class="cp-logic-edit" data-relationship-edit-box="${escapeAttribute(relationship.id)}">
      <summary>${escapeHtml(t.relationshipEdit)}</summary>
      <form class="cp-logic-editor" data-relationship-edit-form="${escapeAttribute(relationship.id)}" data-relationship-revision="${relationship.recordRevision}">
        <label>${escapeHtml(t.predecessor)} <select name="predecessor_id" required>${activityOptionsFor(relationship.predecessorId)}</select></label>
        <label>${escapeHtml(t.successor)} <select name="successor_id" required>${activityOptionsFor(relationship.successorId)}</select></label>
        <label>${escapeHtml(t.relationshipType)} <select name="relationship_type">${typeOptions(relationship.type)}</select></label>
        <label>${escapeHtml(t.relationshipLag)} <input name="lag_value" type="number" step="any" value="${escapeAttribute(relationship.lagValue)}" required></label>
        <label>${escapeHtml(t.relationshipLagUnit)} <select name="lag_unit">${unitOptions(relationship.lagUnit)}</select></label>
        <button type="submit">${escapeHtml(t.relationshipSave)}</button>
      </form>
    </details>`;
  const rows = state.relationships.map((relationship: WorkspaceRelationshipRow) => `<li class="cp-logic-item" data-relationship-id="${escapeAttribute(relationship.id)}">
      <span class="cp-logic-pair">${escapeHtml(relationship.predecessorId)} → ${escapeHtml(relationship.successorId)}</span>
      <span class="cp-logic-type">${escapeHtml(relationship.type)}</span>
      <span class="cp-logic-lag">${escapeHtml(formatRelationshipLag(relationship.lagValue, relationship.lagUnit, t))}</span>
      <button type="button" data-relationship-delete="${escapeAttribute(relationship.id)}" data-relationship-revision="${relationship.recordRevision}">${escapeHtml(t.relationshipDelete)}</button>
      ${editForm(relationship)}
    </li>`).join("");
  const activityOptions = activityOptionsFor();
  const canCreate = state.activities.length >= 2;
  return `<div class="cp-logic-list-wrap">
    ${state.relationships.length ? `<ul class="cp-logic-list">${rows}</ul>` : `<p class="cp-empty">${escapeHtml(t.noRelationships)}</p>`}
    <form class="cp-logic-editor" data-relationship-create-form>
      <h3>${escapeHtml(t.relationshipCreate)}</h3>
      <label>${escapeHtml(t.predecessor)} <select name="predecessor_id" required ${canCreate ? "" : "disabled"}>${activityOptions}</select></label>
      <label>${escapeHtml(t.successor)} <select name="successor_id" required ${canCreate ? "" : "disabled"}>${activityOptions}</select></label>
      <label>${escapeHtml(t.relationshipType)} <select name="relationship_type">${typeOptions("FS")}</select></label>
      <label>${escapeHtml(t.relationshipLag)} <input name="lag_value" type="number" step="any" value="0" required></label>
      <label>${escapeHtml(t.relationshipLagUnit)} <select name="lag_unit">${unitOptions("working-day")}</select></label>
      <button type="submit" ${canCreate ? "" : "disabled"}>${escapeHtml(t.relationshipCreate)}</button>
    </form>
  </div>`;
}

function menuButton(key: WorkspaceState["activeMenu"], label: string, state: WorkspaceState, icon: string): string {
  const active = key === state.activeMenu;
  return `<button type="button" class="cp-rail-button" data-menu="${key}" aria-current="${active ? "page" : "false"}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

function railActionButton(action: string, label: string, icon: string): string {
  return `<button type="button" class="cp-rail-button" data-rail-action="${escapeAttribute(action)}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value); }
