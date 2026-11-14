import type { WorkspaceActivityGroupLevel, WorkspaceActivityRow, WorkspaceCalendarMode, WorkspaceCellValue, WorkspaceColumn, WorkspaceGanttScale, WorkspaceProjectCalendar, WorkspaceRelationshipRow, WorkspaceRelationshipType, WorkspaceState, WorkspaceWbsMilestone } from "./workspace-model.js";
import { computeNextActivityId } from "./activity-id.js";
import { selectedActivityIdList } from "./workspace-model.js";
import type { ProjectSummary } from "./session-api.js";
import { GANTT_CONTENT_WIDTH, createGanttAxisTicks, createGanttBarGeometry, createGanttLinkGeometry, createGanttNonWorkingBands, createGanttPeriodGroups, createGanttScale, ganttDisplayMetrics, ganttRowPitch, isoWeekNumber, ordinalNumberAt, progressPointRelation, relationshipTypeFromEdges, resolveGanttLabelPosition, timescaleMajorUnit, type GanttBarGeometry, type GanttLinkEdge, type GanttPeriodGroup, type GanttRowMetric, type GanttScale } from "./workspace-gantt.js";
import { filterAndSortActivities } from "./workspace-filter-sort.js";
import {
  ACTIVITY_EXPORT_SCOPES,
  activitiesForExport,
  activitiesToCsv,
  activityExportFileName,
  activityExportScopeCount,
  computeActivityCounts,
  type ActivityCounts,
  type ActivityExportScope,
} from "./workspace-activity-scope.js";
import {
  applyActivityFilterState,
  createActivityFilterDateContext,
  describeActivityFilter,
  type ActivityFilterApplication,
} from "./workspace-activity-filters.js";
import {
  buildWbsTreeGuides,
  buildWorkspaceDisplayRows,
  collapseAllWbsIds,
  collapseToWbsIds,
  collectWbsGroupIds,
  getCollapsedWbsIds,
  isWorkspaceBandRow,
  setCollapsedWbsIds,
  toggleCollapsedWbs,
  wbsNodeDepths,
  type WbsTreeGuide,
  type WorkspaceDisplayRow,
  type WorkspaceFieldGroupRow,
  type WorkspaceWbsGroupRow,
} from "./workspace-wbs-display.js";
import {
  WORKSPACE_GROUP_FIELDS,
  groupFieldLabel,
  isWorkspaceGroupFieldId,
  type WorkspaceGroupField,
} from "./workspace-grouping.js";
import { formatWorkspaceCalendarDate } from "./workspace-calendar-display.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel, getWorkspaceNavigationSubmenuLabel } from "./workspace-navigation.js";
import { localizeWorkspaceLabel, translateWorkspaceText, translateWorkspaceUiText } from "./workspace-localization.js";
import { SCHEDULING_REFERENCE_CATALOG } from "./scheduling-reference-catalog.generated.js";
import { cubiPlatformLogoUrl } from "./cubi-brand-assets.js";
import { workspaceIcon, type WorkspaceIconName } from "./workspace-icons.js";
import { WORKSPACE_WINDOW_ICONS } from "./workspace-command-icons.js";
import { contextAddCommands, type ContextAddItem } from "./workspace-context-add.js";
import type { DesktopCommand } from "./workspace-desktop-shell.js";
import { defaultToolbarConfig, type ToolbarWorkspaceConfig } from "./workspace-toolbar-config.js";
import { renderToolbarRails, closeToolbarSurfaces, type ToolbarRailSession } from "./workspace-toolbar-view.js";
import { buildWbsHierarchy, wbsActivityCounts } from "./workspace-wbs-hierarchy.js";
import { weightedPercentComplete, wbsStatusLabel, wbsTechniqueLabel } from "./workspace-wbs-milestones.js";
import {
  nextWbsCopyCode,
  wbsClipboardLabels,
  wbsClipboardText,
  type WorkspaceWbsClipboardEntry,
} from "./workspace-wbs-clipboard.js";
import { anchorPoint, openContextMenu, type ContextMenuItem } from "./workspace-context-menu.js";
import { clampNetworkZoom, NETWORK_ZOOM_MAX, NETWORK_ZOOM_MIN, readNetworkZoom, renderActivityNetwork, storeNetworkZoom } from "./workspace-network.js";
import { readTraceLogicDepths, renderTraceLogic, storeTraceLogicDepths } from "./workspace-trace-logic.js";
import {
  ACTIVITY_USAGE_DEFAULT_PREFS,
  readActivityUsagePrefs,
  renderActivityUsage,
  storeActivityUsagePrefs,
  type ActivityUsageSource,
} from "./workspace-activity-usage.js";
import {
  DEFAULT_PRESENTATION,
  GANTT_BAR_KINDS,
  activityBarFacts,
  barKindMatchesFilter,
  barLabelText,
  ganttFinishIdName,
  hasActualDates,
  hasBaselineDates,
  presentationFontFamily,
  selectPrimaryBarKind,
  wbsBandInk,
  wbsLevelColor,
  type GanttBarKind,
  type GanttBarStyle,
  type GanttLabelFormat,
  type WorkspacePresentation,
} from "./workspace-presentation.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings", mainMenu: "Main Menu", currentSurface: "Current workspace surface", submenu: "submenu", formulaColumn: "formula column", fieldChooser: "Field Chooser", fields: "Fields", undo: "Undo", redo: "Redo", layoutHistory: "Layout history", layoutUndone: "Last layout change undone.", layoutRedone: "Layout change reapplied.", layoutRestored: "Layout revision restored.", layoutHistoryEmpty: "No earlier layout revision is available.", layoutSaveFailed: "Layout change was not saved.", layoutConflict: "Another session changed this layout. The latest saved revision was reloaded.", restore: "Restore", revisionOption: "revision", columnUnit: "column(s)", add: "Add", addAll: "Add all", remove: "Remove", moveUp: "Move up", moveDown: "Move down", narrower: "Narrower", wider: "Wider", alignStart: "Align left", alignCenter: "Align center", alignEnd: "Align right", pin: "Pin", unpin: "Unpin", freeze: "Freeze", unfreeze: "Unfreeze", hide: "Hide", show: "Show", rename: "Rename", findings: "Findings", proposedActions: "Proposed Actions", traceability: "Traceability", sources: "Sources", approvalRequired: "Approval Required", humanApprovalRequired: "Human approval required", noApprovalFlag: "No approval flag", sourceUnit: "source(s)", activityLinkUnit: "activity link(s)", evidenceUnit: "evidence", inspections: "Inspections", qualityNcr: "Quality / NCR", safety: "Safety", punchCloseout: "Punch / Closeout", due: "Due", supplier: "Supplier", reference: "Ref", amount: "Amount", itemUnit: "item(s)", linkedReferenceUnit: "linked reference(s)", stored: "stored", noStorage: "no storage", approval: "Approval", date: "Date", notices: "Notices", changeCases: "Change Cases", claims: "Claims", impactLinks: "Impact Links", scheduleLabel: "Schedule", costLabel: "Cost", noticeLabel: "Notice", changeLabel: "Change", entitlement: "Entitlement", decision: "Decision", impactLinkLabel: "Impact links",
    referenceTitle: "Scheduling logic & implementation reference", referenceDescription: "Browse scheduling requirements, calculation contracts and review evidence. A listed requirement is not proof of implementation; status is evidence-based.", referenceSearch: "Search the reference", referenceSearchPlaceholder: "Search by ID, rule, option, or status…", referenceNoMatches: "No matching entries.", referenceVersion: "Reference version", referenceAsOf: "Catalog date", referenceRequirementCount: "requirements", referenceFormulaCount: "calculation contracts", referenceDocumentationCount: "documentation review tracks", referenceMappedStatus: "Mapped; parity not yet proven", referenceGapStatus: "Known implementation gap", referenceInventoryStatus: "Inventory / acceptance evidence required", referenceFormulaStatus: "Formula contract; parity not yet proven", referenceRuleLabel: "Required behavior", referenceOptionsLabel: "Options", referenceGapLabel: "Known gap / remaining work", referenceInputsLabel: "Inputs", referenceCalendarRulesLabel: "Units & calendar rules", referenceEdgeCasesLabel: "Edge cases", referenceReviewLabel: "Review status", referenceRemainingLabel: "Remaining review work", referenceLinkedReqLabel: "Related requirement IDs", referenceRelationshipsGroupLabel: "Relationships & lag", referenceCalendarsGroupLabel: "Calendars & work time", referenceOptionsGroupLabel: "Schedule options & Data Date", referenceResourcesGroupLabel: "Resources & leveling", referenceProgressGroupLabel: "Progress & baselines", referenceOtherGroupLabel: "Other project-control areas", referenceFormulaGroupLabel: "Calculation formula contracts", referenceDocumentationGroupLabel: "Documentation review register", referenceCatalogGroupLabel: "Requirement catalogue", referenceDocReviewedLabel: "Core behavior extracted", referenceDocPartialLabel: "Partially reviewed", referenceDocPendingLabel: "Review not complete", referenceReviewNotice: "This catalogue is for traceability. Editing controls, persistent schedule updates and execution must be wired to the shared scheduling core and acceptance-tested separately.",
    wbs: "Project / WBS", wbsCreate: "Add WBS", wbsEdit: "Edit selected WBS", wbsCode: "Code", wbsName: "Name", wbsParent: "Parent WBS", wbsProjectRoot: "Project root", wbsSequence: "Sequence", wbsSave: "Save WBS", wbsDelete: "Delete selected", wbsSelectPrompt: "Select a WBS node to edit.", wbsMutationFailed: "WBS change failed.", wbsDeleteConfirm: "Delete this WBS node?", activities: "Activity Grid", activityCreate: "Add activity", activityEdit: "Edit activity", activityId: "Activity ID", activityName: "Activity name", activityDuration: "Duration", activityDurationUnit: "Duration unit", activityWbs: "WBS", activityCreateFailed: "Activity could not be saved.", activityFilter: "Filter activities", activityFilterPlaceholder: "ID, name, WBS, status…", activitySort: "Sort by", groupBy: "Group by", groupNone: "No grouping", sortNone: "Original order", sortAscending: "Ascending", sortDescending: "Descending", matchingActivities: "activities shown", noMatchingActivities: "No activities match the current filter.", gantt: "Gantt Chart", details: "Details", interchange: "Import / Export", resourceCapacity: "Resource Max Units / Time", scheduleOptions: "Schedule Options", runSchedule: "Run Schedule", formulaEditor: "Formula editor", scheduleReference: "Scheduling Code Reference", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noWbs: "No WBS elements loaded", noSchedule: "No scheduled activities", revision: "Revision", projectSettings: "Project settings", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
    logic: "Logic / Relationships", predecessorsColumn: "Predecessors", relationshipCreate: "Add relationship", predecessor: "Predecessor", successor: "Successor", relationshipType: "Type", relationshipLag: "Lag", relationshipLagUnit: "Lag unit", relationshipDelete: "Delete", relationshipDeleteConfirm: "Delete this relationship? Dates are recalculated after the change.", relationshipEdit: "Edit", relationshipSave: "Save relationship", noRelationships: "No relationships defined yet.", relationshipCreateFailed: "Relationship could not be saved.", relationshipDeleteFailed: "Relationship could not be deleted.", relationshipConflict: "The relationship changed in another session. Reload and try again.", workingDay: "Working day", workingHour: "Working hour",
    ganttScaleLabel: "Timeline scale", scaleDay: "Day", scaleWeek: "Week", scaleMonth: "Month", scaleQuarter: "Quarter", scaleYear: "Year", ganttLinks: "Dependency links", ganttLinksToggle: "Dependency links", ganttLinksOn: "Shown", ganttLinksOff: "Hidden", milestone: "Milestone",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات", mainMenu: "منوی اصلی", currentSurface: "سطح فعلی محیط کار", submenu: "زیرمنو", formulaColumn: "ستون فرمول", fieldChooser: "انتخاب‌گر فیلد", fields: "فیلدها", undo: "بازگردانی", redo: "تکرار", layoutHistory: "تاریخچهٔ چیدمان", layoutUndone: "آخرین تغییر چیدمان بازگردانی شد.", layoutRedone: "تغییر چیدمان دوباره اعمال شد.", layoutRestored: "نسخهٔ چیدمان بازگردانی شد.", layoutHistoryEmpty: "نسخهٔ قدیمی‌تری از چیدمان در دسترس نیست.", layoutSaveFailed: "تغییر چیدمان ذخیره نشد.", layoutConflict: "نشست دیگری این چیدمان را تغییر داد. آخرین نسخهٔ ذخیره‌شده دوباره بارگذاری شد.", restore: "بازگردانی نسخه", revisionOption: "نسخه", columnUnit: "ستون", add: "افزودن", addAll: "افزودن همه", remove: "حذف", moveUp: "جابجایی به بالا", moveDown: "جابجایی به پایین", narrower: "باریک‌تر", wider: "عریض‌تر", alignStart: "تراز چپ", alignCenter: "تراز وسط", alignEnd: "تراز راست", pin: "سنجاق کردن", unpin: "برداشتن سنجاق", freeze: "ثابت کردن", unfreeze: "لغو ثابت‌سازی", hide: "پنهان کردن", show: "نمایش", rename: "تغییر نام", findings: "یافته‌ها", proposedActions: "اقدامات پیشنهادی", traceability: "ردیابی", sources: "منابع", approvalRequired: "نیازمند تأیید", humanApprovalRequired: "نیازمند تأیید انسانی", noApprovalFlag: "بدون پرچم تأیید", sourceUnit: "منبع", activityLinkUnit: "پیوند فعالیت", evidenceUnit: "مستند", inspections: "بازرسی‌ها", qualityNcr: "کیفیت / NCR", safety: "ایمنی", punchCloseout: "پانچ / بستن موارد", due: "سررسید", supplier: "تأمین‌کننده", reference: "مرجع", amount: "مبلغ", itemUnit: "مورد", linkedReferenceUnit: "مرجع پیوندشده", stored: "ذخیره‌شده", noStorage: "بدون ذخیره‌سازی", approval: "تأیید", date: "تاریخ", notices: "اعلان‌ها", changeCases: "موارد تغییر", claims: "ادعاها", impactLinks: "پیوندهای اثر", scheduleLabel: "زمان‌بندی", costLabel: "هزینه", noticeLabel: "اعلان", changeLabel: "تغییر", entitlement: "استحقاق", decision: "تصمیم", impactLinkLabel: "پیوندهای اثر",
    referenceTitle: "مرجع منطق و پیاده‌سازی زمان‌بندی", referenceDescription: "الزامات زمان‌بندی، قراردادهای محاسباتی و شواهد بازبینی را مرور کنید. ثبت یک الزام به‌معنای اثبات پیاده‌سازی نیست؛ وضعیت بر پایهٔ شواهد است.", referenceSearch: "جست‌وجو در مرجع", referenceSearchPlaceholder: "جست‌وجو بر اساس شناسه، قاعده، گزینه یا وضعیت…", referenceNoMatches: "موردی با این جست‌وجو یافت نشد.", referenceVersion: "نسخه مرجع", referenceAsOf: "تاریخ کاتالوگ", referenceRequirementCount: "الزام", referenceFormulaCount: "قرارداد محاسباتی", referenceDocumentationCount: "مسیر بازبینی مستندات", referenceMappedStatus: "مسیر کد شناسایی شده؛ تطبیق هنوز اثبات نشده", referenceGapStatus: "شکاف اجرایی شناخته‌شده", referenceInventoryStatus: "تکمیل فهرست و شواهد پذیرش لازم است", referenceFormulaStatus: "قرارداد فرمول؛ تطبیق هنوز اثبات نشده", referenceRuleLabel: "رفتار الزامی", referenceOptionsLabel: "گزینه‌ها", referenceGapLabel: "شکاف شناخته‌شده / کار باقیمانده", referenceInputsLabel: "ورودی‌ها", referenceCalendarRulesLabel: "واحدها و قواعد تقویم", referenceEdgeCasesLabel: "حالت‌های مرزی", referenceReviewLabel: "وضعیت بازبینی", referenceRemainingLabel: "کار باقیمانده در بازبینی", referenceLinkedReqLabel: "شناسه‌های الزامات مرتبط", referenceRelationshipsGroupLabel: "روابط و وقفه‌ها", referenceCalendarsGroupLabel: "تقویم‌ها و ساعات کاری", referenceOptionsGroupLabel: "گزینه‌های زمان‌بندی و تاریخ داده", referenceResourcesGroupLabel: "منابع و تسطیح", referenceProgressGroupLabel: "پیشرفت و مبناها", referenceOtherGroupLabel: "سایر حوزه‌های کنترل پروژه", referenceFormulaGroupLabel: "قرارداد فرمول‌های محاسباتی", referenceDocumentationGroupLabel: "دفتر ثبت بازبینی مستندات", referenceCatalogGroupLabel: "فهرست الزامات", referenceDocReviewedLabel: "رفتار اصلی استخراج شده", referenceDocPartialLabel: "بازبینی جزئی", referenceDocPendingLabel: "بازبینی کامل نشده", referenceReviewNotice: "این فهرست برای ردیابی الزامات است. کنترل‌های ویرایش، به‌روزرسانی پایدار زمان‌بندی و اجرای محاسبه باید جداگانه به هستهٔ مشترک متصل و با آزمون پذیرش تأیید شوند.",
    wbs: "پروژه / WBS", wbsCreate: "افزودن ساختار شکست", wbsEdit: "ویرایش ساختار انتخاب‌شده", wbsCode: "کد", wbsName: "نام", wbsParent: "والد", wbsProjectRoot: "ریشهٔ پروژه", wbsSequence: "ترتیب", wbsSave: "ذخیره", wbsDelete: "حذف مورد انتخاب‌شده", wbsSelectPrompt: "برای ویرایش یک ردیف را انتخاب کنید.", wbsMutationFailed: "تغییر ساختار شکست ناموفق بود.", wbsDeleteConfirm: "این ردیف ساختار شکست حذف شود؟", activities: "جدول فعالیت‌ها", activityCreate: "افزودن فعالیت", activityEdit: "ویرایش فعالیت", activityId: "شناسه فعالیت", activityName: "نام فعالیت", activityDuration: "مدت", activityDurationUnit: "واحد مدت", activityWbs: "ساختار شکست", activityCreateFailed: "ذخیره فعالیت انجام نشد.", activityFilter: "پالایش فعالیت‌ها", activityFilterPlaceholder: "شناسه، نام، WBS، وضعیت…", activitySort: "ترتیب بر اساس", groupBy: "گروه‌بندی بر اساس", groupNone: "بدون گروه‌بندی", sortNone: "ترتیب اصلی", sortAscending: "صعودی", sortDescending: "نزولی", matchingActivities: "فعالیت نمایش‌داده‌شده", noMatchingActivities: "هیچ فعالیتی با پالایهٔ فعلی مطابقت ندارد.", gantt: "گانت", details: "جزئیات", interchange: "ورود / خروجی", resourceCapacity: "حداکثر واحد / زمان منبع", scheduleOptions: "تنظیمات زمان‌بندی", runSchedule: "اجرای زمان‌بندی", formulaEditor: "ویرایشگر فرمول", scheduleReference: "مرجع کد زمان‌بندی", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noWbs: "ساختار شکست کار بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", projectSettings: "تنظیمات پروژه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
    logic: "منطق / روابط", predecessorsColumn: "پیش‌نیازها", relationshipCreate: "افزودن رابطه", predecessor: "پیش‌نیاز", successor: "پس‌نیاز", relationshipType: "نوع", relationshipLag: "وقفه", relationshipLagUnit: "واحد وقفه", relationshipDelete: "حذف", relationshipDeleteConfirm: "این رابطه حذف شود؟ تاریخ‌ها پس از تغییر دوباره محاسبه می‌شوند.", relationshipEdit: "ویرایش", relationshipSave: "ذخیرهٔ رابطه", noRelationships: "هنوز رابطه‌ای تعریف نشده است.", relationshipCreateFailed: "ذخیره رابطه انجام نشد.", relationshipDeleteFailed: "حذف رابطه انجام نشد.", relationshipConflict: "رابطه در نشست دیگری تغییر کرده است. صفحه را دوباره بارگذاری کنید.", workingDay: "روز کاری", workingHour: "ساعت کاری",
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

function renderActivityCreateOptions(
  locale: string,
  field: ActivityCreateChoiceField,
  selectedValue?: string,
): string {
  const config = ACTIVITY_CREATE_FIELDS[field];
  const selected = selectedValue || config.defaultValue;
  return config.options.map((option) =>
    `<option value="${escapeAttribute(option.value)}" ${option.value === selected ? "selected" : ""}>${escapeHtml(translateWorkspaceUiText(locale, option.en, option.fa))}</option>`
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
const wbsViewByContainer = new WeakMap<HTMLElement, "table" | "chart">();
// The Cut/Copy clipboard is page-local, one entry per WBS surface container.
const wbsClipboardByContainer = new WeakMap<HTMLElement, WorkspaceWbsClipboardEntry>();
const ACTIVITY_DETAILS_TABS_STORAGE_KEY = "cubi:activity-details-visible-tabs:v2";
const workspaceEventDelegation = new WeakSet<HTMLElement>();
const workspaceStickyOffsetsCache = new WeakMap<readonly WorkspaceColumn[], ReadonlyMap<string, number>>();
const WORKSPACE_SPLIT_STORAGE_KEY = "cubi:workspace:split";
const WORKSPACE_TOP_LAYOUT_STORAGE_KEY = "cubi:workspace:top-layout";
const WORKSPACE_BOTTOM_LAYOUT_STORAGE_KEY = "cubi:workspace:bottom-layout";
// The reference splits the workbench evenly: the activity table and the Gantt
// each own half of the work area, with the table filler ending at the divider.
const DEFAULT_TABLE_SPLIT = 50;
const DEFAULT_DETAILS_SPLIT = 70;
const MIN_TABLE_SPLIT = 25;
const MAX_TABLE_SPLIT = 75;
const MIN_DETAILS_SPLIT = 40;
const MAX_DETAILS_SPLIT = 80;
const MIN_COLUMN_WIDTH = 48;
const MAX_COLUMN_WIDTH = 640;

function splitStorageKey(kind: "table-gantt" | "details", state: WorkspaceState): string {
  // Presentation-only preference: scoped to tenant, project, workspace window
  // and pane, so two windows never overwrite each other's split.
  return [
    WORKSPACE_SPLIT_STORAGE_KEY,
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
    kind,
  ].join(":");
}

export type WorkspaceTopLayout = "table-only" | "table-gantt" | "activity-network";
export type WorkspaceBottomLayout = "details" | "trace-logic" | "usage-profile" | "usage-spreadsheet" | "none";

function topLayoutStorageKey(state: WorkspaceState): string {
  // Presentation-only preference scoped like the pane splits, so a second
  // project or window never inherits another plan's chosen layout.
  return [
    WORKSPACE_TOP_LAYOUT_STORAGE_KEY,
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
  ].join(":");
}

function bottomLayoutStorageKey(state: WorkspaceState): string {
  return [
    WORKSPACE_BOTTOM_LAYOUT_STORAGE_KEY,
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
  ].join(":");
}

function networkZoomStorageKey(state: WorkspaceState): string {
  return [
    "cubi:workspace:network-zoom",
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
  ].join(":");
}

/** The network needs persisted activities and relationships; the table does not. */
export function isWorkspaceTopLayoutAvailable(layout: WorkspaceTopLayout, state: WorkspaceState): boolean {
  if (layout === "activity-network") return state.activities.length > 0 && state.relationships.length > 0;
  return true;
}

export function isWorkspaceTraceLogicAvailable(state: WorkspaceState): boolean {
  // Trace Logic is a projection of the persisted relationships; without a
  // selected activity or any relationship it stays unavailable instead of
  // showing a fabricated chain.
  return Boolean(state.selectedActivityId) && state.relationships.length > 0;
}

/**
 * The Activity Usage views only exist when the project actually stores
 * assignment periods; an empty read keeps them disabled instead of drawing a
 * fabricated zero profile.
 */
export function isWorkspaceUsageAvailable(
  layout: WorkspaceBottomLayout,
  source: ActivityUsageSource | undefined,
): boolean {
  if (layout !== "usage-profile" && layout !== "usage-spreadsheet") return true;
  return usageSourceAvailable(source);
}

function usageSourceAvailable(source: ActivityUsageSource | undefined): boolean {
  return source !== undefined && source.status === "loaded" && source.periods.length > 0;
}

export function readWorkspaceTopLayout(state: WorkspaceState): WorkspaceTopLayout {
  try {
    const raw = window.localStorage.getItem(topLayoutStorageKey(state));
    if ((raw === "table-only" || raw === "table-gantt" || raw === "activity-network") && isWorkspaceTopLayoutAvailable(raw, state)) {
      return raw;
    }
  } catch {
    // Preference storage is optional; fall back to the table + Gantt layout.
  }
  return "table-gantt";
}

export function storeWorkspaceTopLayout(state: WorkspaceState, layout: WorkspaceTopLayout): void {
  try {
    window.localStorage.setItem(topLayoutStorageKey(state), layout);
  } catch {
    // Preference storage is optional; the choice still applies to this render.
  }
}

export function readWorkspaceBottomLayout(
  state: WorkspaceState,
  usageSource?: ActivityUsageSource,
): WorkspaceBottomLayout {
  try {
    const raw = window.localStorage.getItem(bottomLayoutStorageKey(state));
    if (raw === "none") return "none";
    if (raw === "trace-logic" && isWorkspaceTraceLogicAvailable(state)) return "trace-logic";
    if ((raw === "usage-profile" || raw === "usage-spreadsheet") && usageSourceAvailable(usageSource)) return raw;
    if (raw === "details") return "details";
  } catch {
    // Preference storage is optional; the details pane is the default.
  }
  return "details";
}

export function storeWorkspaceBottomLayout(state: WorkspaceState, layout: WorkspaceBottomLayout): void {
  try {
    window.localStorage.setItem(bottomLayoutStorageKey(state), layout);
  } catch {
    // Preference storage is optional; the choice still applies to this render.
  }
}

function readStoredSplit(key: string, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw === null ? Number.NaN : Number.parseFloat(raw);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(100, Math.max(0, parsed));
  } catch {
    return fallback;
  }
}

function storeSplit(key: string, value: number): void {
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // Preference storage is optional; the resize still applies for this session.
  }
}

function clearStoredSplit(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Preference storage is optional.
  }
}

function isRtlElement(element: Element | null): boolean {
  const direction = element?.closest?.("[dir]")?.getAttribute("dir");
  return direction === "rtl";
}

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

/** Open the real Layout Options / Timescale dialog from any toolbar or menu. */
function openLayoutOptionsDialog(container: HTMLElement): void {
  const dialog = container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]");
  if (dialog && typeof dialog.showModal === "function") dialog.showModal();
  else dialog?.setAttribute("open", "");
}

function resetTableSplit(container: HTMLElement): void {
  const split = container.querySelector<HTMLElement>("[data-panel-split]");
  if (!split) return;
  if (split.dataset.splitKey) clearStoredSplit(split.dataset.splitKey);
  split.style.setProperty("--cp-split-table", `${DEFAULT_TABLE_SPLIT}%`);
  split.querySelector<HTMLElement>("[data-panel-splitter]")?.setAttribute("aria-valuenow", String(DEFAULT_TABLE_SPLIT));
}

function resetDetailsSplit(container: HTMLElement): void {
  const main = container.querySelector<HTMLElement>(".cp-main");
  const splitter = container.querySelector<HTMLElement>("[data-details-splitter]");
  if (!main) return;
  if (splitter?.dataset.splitKey) clearStoredSplit(splitter.dataset.splitKey);
  main.style.setProperty("--cp-split-primary", `${DEFAULT_DETAILS_SPLIT}%`);
  main.style.setProperty("--cp-split-details", `${DEFAULT_DETAILS_SPLIT}%`);
  splitter?.setAttribute("aria-valuenow", String(DEFAULT_DETAILS_SPLIT));
}

function resetColumnWidths(container: HTMLElement): void {
  const record = workspaceRenderRecords.get(container);
  const widths: Record<string, number> = {};
  for (const column of record?.state.columns ?? []) {
    if (record?.state.p6Layout?.columns.some((entry) => entry.field_id === column.id)) {
      widths[column.id] = defaultActivityColumnWidth(column);
    }
  }
  if (record?.options.onP6ColumnWidthsReset && Object.keys(widths).length > 0) {
    record.options.onP6ColumnWidthsReset(widths);
    return;
  }
  for (const [columnId, width] of Object.entries(widths)) {
    applyActivityColumnWidth(container, columnId, width, false);
  }
}

/** Open the activity create form with the clicked WBS element preselected. */
function openActivityCreateForWbs(container: HTMLElement, wbsId: string | null): void {
  openToolsDrawer(container);
  const form = container.querySelector<HTMLFormElement>("[data-activity-create-form]");
  if (!form) return;
  if (wbsId) {
    const select = form.querySelector<HTMLSelectElement>('select[name="wbs_id"]');
    if (select && Array.from(select.options).some((option) => option.value === wbsId)) select.value = wbsId;
  }
  form.querySelector<HTMLInputElement>('input[name="activity_id"]')?.focus({ preventScroll: true });
}

function startTableGanttResize(splitter: HTMLElement, event: PointerEvent): void {
  const split = splitter.closest<HTMLElement>("[data-panel-split]");
  if (!split) return;
  event.preventDefault();
  const rect = split.getBoundingClientRect();
  if (rect.width <= 0) return;
  const rtl = isRtlElement(split);
  const key = split.dataset.splitKey ?? "";
  try { splitter.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const offset = rtl ? rect.right - moveEvent.clientX : moveEvent.clientX - rect.left;
    const percent = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, (offset / rect.width) * 100));
    split.style.setProperty("--cp-split-table", `${percent.toFixed(2)}%`);
    splitter.setAttribute("aria-valuenow", percent.toFixed(0));
  };
  const stop = (): void => {
    splitter.removeEventListener("pointermove", move);
    splitter.removeEventListener("pointerup", stop);
    splitter.removeEventListener("pointercancel", stop);
    const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table"));
    if (key && Number.isFinite(current)) storeSplit(key, current);
  };
  splitter.addEventListener("pointermove", move);
  splitter.addEventListener("pointerup", stop);
  splitter.addEventListener("pointercancel", stop);
}

function startDetailsResize(splitter: HTMLElement, event: PointerEvent): void {
  const main = splitter.closest<HTMLElement>(".cp-main");
  if (!main) return;
  event.preventDefault();
  const rect = main.getBoundingClientRect();
  if (rect.height <= 0) return;
  const key = splitter.dataset.splitKey ?? "";
  try { splitter.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const percent = Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, ((moveEvent.clientY - rect.top) / rect.height) * 100));
    main.style.setProperty("--cp-split-primary", `${percent.toFixed(2)}%`);
    main.style.setProperty("--cp-split-details", `${percent.toFixed(2)}%`);
    splitter.setAttribute("aria-valuenow", percent.toFixed(0));
  };
  const stop = (): void => {
    splitter.removeEventListener("pointermove", move);
    splitter.removeEventListener("pointerup", stop);
    splitter.removeEventListener("pointercancel", stop);
    const current = Number.parseFloat(main.style.getPropertyValue("--cp-split-primary"));
    if (key && Number.isFinite(current)) storeSplit(key, current);
  };
  splitter.addEventListener("pointermove", move);
  splitter.addEventListener("pointerup", stop);
  splitter.addEventListener("pointercancel", stop);
}

function defaultActivityColumnWidth(column: { id: string; label: string; dataType: string }): number {
  // Keep the reset widths aligned with the persisted P6 layout seed so a reset
  // restores the compact professional table rather than an inflated one.
  const canonical: Record<string, number> = {
    "activity.id": 56,
    "activity.name": 172,
    "activity.wbs": 100,
    "activity.planned_duration": 58,
    "activity.remaining_duration": 58,
    "activity.duration_percent_complete": 58,
    "activity.early_start": 64,
    "activity.early_finish": 64,
    "activity.status": 70,
    "activity.total_float": 56,
    "activity.is_critical": 55,
  };
  if (canonical[column.id] !== undefined) return canonical[column.id];
  const key = `${column.id} ${column.label}`.toLowerCase();
  if (/name|title|نام/.test(key)) return 130;
  if (/wbs|ساختار/.test(key)) return 100;
  if (/float|شناور/.test(key)) return 50;
  if (/status|وضعیت/.test(key)) return 70;
  if (/%|percent|progress|پیشرفت|درصد/.test(key)) return 50;
  if (/start|finish|date|شروع|پایان|تاریخ/.test(key)) return 68;
  if (/duration|مدت/.test(key)) return 50;
  if (/id|code|شناسه|کد/.test(key)) return 48;
  return 70;
}

function activityColumnCells(container: HTMLElement, columnId: string): HTMLElement[] {
  const grid = container.querySelector<HTMLElement>("#cp-activity-grid");
  if (!grid) return [];
  return Array.from(grid.querySelectorAll<HTMLElement>("[data-column-id]")).filter((element) => element.dataset.columnId === columnId);
}

function applyActivityColumnWidth(container: HTMLElement, columnId: string, width: number, persist: boolean): number {
  const cells = activityColumnCells(container, columnId);
  const header = cells.find((element) => element.tagName === "TH");
  if (!header) return 0;
  const current = Number.parseFloat(header.style.width) || header.getBoundingClientRect?.().width || MIN_COLUMN_WIDTH;
  const next = Math.round(Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, width)));
  const table = header.closest("table");
  if (table) {
    const base = Number.parseFloat(table.style.width) || table.getBoundingClientRect?.().width || 0;
    table.style.width = `${Math.max(320, Math.round(base + next - current))}px`;
  }
  for (const cell of cells) cell.style.width = `${next}px`;
  header.querySelector<HTMLElement>("[data-column-resize]")?.setAttribute("aria-valuenow", String(next));
  if (persist) {
    const record = workspaceRenderRecords.get(container);
    if (record?.state.p6Layout?.columns.some((column) => column.field_id === columnId)) {
      record.options.onP6FieldWidthChange?.(columnId, next);
    }
  }
  return next;
}

function startColumnResize(container: HTMLElement, handle: HTMLElement, event: PointerEvent): void {
  const columnId = handle.dataset.columnResize;
  if (!columnId) return;
  event.preventDefault();
  event.stopPropagation();
  const rtl = isRtlElement(container);
  const startX = event.clientX;
  const startWidth = Number.parseFloat(handle.closest<HTMLElement>("th")?.style.width ?? "") || handle.closest<HTMLElement>("th")?.getBoundingClientRect?.().width || MIN_COLUMN_WIDTH;
  let next = startWidth;
  try { handle.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  const move = (moveEvent: PointerEvent): void => {
    const delta = (moveEvent.clientX - startX) * (rtl ? -1 : 1);
    next = applyActivityColumnWidth(container, columnId, startWidth + delta, false);
  };
  const stop = (): void => {
    handle.removeEventListener("pointermove", move);
    handle.removeEventListener("pointerup", stop);
    handle.removeEventListener("pointercancel", stop);
    if (next) applyActivityColumnWidth(container, columnId, next, true);
  };
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", stop);
  handle.addEventListener("pointercancel", stop);
}

/** Which of a bar's two authoritative edges sits under the pointer. */
function ganttLinkEdgeAt(bar: HTMLElement, clientX: number): GanttLinkEdge | null {
  const rect = bar.getBoundingClientRect?.();
  if (!rect || rect.width <= 0) return null;
  // A narrow bar (including a milestone) still needs a usable middle zone, so
  // the edge band never exceeds a quarter of the bar on each side.
  const zone = Math.min(6, Math.max(3, rect.width * 0.25));
  if (clientX <= rect.left + zone) return "start";
  if (clientX >= rect.right - zone) return "finish";
  return null;
}

function ganttLinkTypeLabel(locale: string, type: WorkspaceRelationshipType): string {
  const names: Record<WorkspaceRelationshipType, readonly [string, string]> = {
    FS: ["Finish to Start", "پایان به شروع"],
    SS: ["Start to Start", "شروع به شروع"],
    FF: ["Finish to Finish", "پایان به پایان"],
    SF: ["Start to Finish", "شروع به پایان"],
  };
  const [en, fa] = names[type];
  return `${type} — ${uiText(locale, en, fa)}`;
}

type GanttLinkTarget = { activityId: string; edge: GanttLinkEdge; type: WorkspaceRelationshipType; row: HTMLElement };

type GanttLinkDrag = {
  pointerId: number;
  predecessorId: string;
  fromEdge: GanttLinkEdge;
  body: HTMLElement;
  path: SVGPathElement;
  overlay: SVGSVGElement;
  hint: HTMLElement;
  startPercent: number;
  startY: number;
  startClientX: number;
  startClientY: number;
  moved: boolean;
  target: GanttLinkTarget | null;
  move: (event: PointerEvent) => void;
  finish: (event: PointerEvent) => void;
  cancel: () => void;
  onKey: (event: KeyboardEvent) => void;
};

const ganttLinkDrags = new WeakMap<HTMLElement, GanttLinkDrag>();

function ganttLinkPercent(body: HTMLElement, clientX: number): number {
  const rect = body.getBoundingClientRect?.();
  if (!rect || rect.width <= 0) return 0;
  return Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
}

/**
 * Draws a relationship between two persisted bars, as the V26 Help describes:
 * the source edge decides the start, the edge released over decides the end.
 * The gesture only proposes a relationship; persistence stays with the caller.
 */
function beginGanttLinkDrag(container: HTMLElement, event: PointerEvent, barEl: HTMLElement, rowEl: HTMLElement, edge: GanttLinkEdge): void {
  const record = workspaceRenderRecords.get(container);
  const body = rowEl.closest?.(".cp-gantt-body") as HTMLElement | null;
  if (!record || !body) return;
  if (ganttLinkDrags.has(container)) return;
  const barRect = barEl.getBoundingClientRect();
  const startClientX = edge === "start" ? barRect.left : barRect.right;
  const startY = rowEl.offsetTop + rowEl.offsetHeight / 2;
  const namespace = "http://www.w3.org/2000/svg";
  const overlay = document.createElementNS(namespace, "svg");
  overlay.setAttribute("class", "cp-gantt-link-preview-layer");
  overlay.setAttribute("viewBox", `0 0 1000 ${Math.max(1, body.offsetHeight)}`);
  overlay.setAttribute("preserveAspectRatio", "none");
  overlay.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(namespace, "path");
  path.setAttribute("class", "cp-gantt-link-preview");
  path.setAttribute("data-gantt-link-preview", "");
  overlay.append(path);
  const hint = document.createElement("div");
  hint.className = "cp-gantt-link-hint";
  hint.dataset.ganttLinkHint = "";
  hint.setAttribute("role", "status");
  hint.hidden = true;
  body.append(overlay, hint);
  container.dataset.ganttLinkDragging = "true";

  const drag: GanttLinkDrag = {
    pointerId: event.pointerId,
    predecessorId: (rowEl.dataset.ganttActivityId ?? "").trim(),
    fromEdge: edge,
    body,
    path,
    overlay,
    hint,
    startPercent: ganttLinkPercent(body, startClientX),
    startY,
    startClientX,
    startClientY: event.clientY,
    moved: false,
    target: null,
    move: () => undefined,
    finish: () => undefined,
    cancel: () => undefined,
    onKey: () => undefined,
  };  const clearTargetHighlight = (): void => {
    body.querySelectorAll<HTMLElement>("[data-gantt-activity-id].is-link-target").forEach((row) => row.classList.remove("is-link-target"));
  };
  drag.move = (moveEvent: PointerEvent): void => {
    if (moveEvent.pointerId !== drag.pointerId) return;
    const distance = Math.hypot(moveEvent.clientX - drag.startClientX, moveEvent.clientY - drag.startClientY);
    if (distance > 3) drag.moved = true;
    const bodyRect = body.getBoundingClientRect();
    const pointerX = ganttLinkPercent(body, moveEvent.clientX);
    const pointerY = Math.min(body.offsetHeight, Math.max(0, moveEvent.clientY - bodyRect.top));
    // The target is resolved against row geometry for the same reason as the
    // source: shaped bars are clipped and the link layer is transparent to the
    // eye but present in hit testing.
    let target: GanttLinkTarget | null = null;
    let targetEndPercent = pointerX;
    for (const targetRow of body.querySelectorAll<HTMLElement>("[data-gantt-activity-id]")) {
      const rowRect = targetRow.getBoundingClientRect();
      if (moveEvent.clientY < rowRect.top || moveEvent.clientY > rowRect.bottom) continue;
      const activityId = (targetRow.dataset.ganttActivityId ?? "").trim();
      if (!activityId || activityId === drag.predecessorId) continue;
      const targetBar = targetRow.querySelector<HTMLElement>(".cp-gantt-bar[data-gantt-bar-primary='true']");
      if (!targetBar) continue;
      const targetRect = targetBar.getBoundingClientRect();
      const targetEdge = ganttLinkEdgeAt(targetBar, moveEvent.clientX)
        ?? (moveEvent.clientX <= targetRect.left + targetRect.width / 2 ? "start" : "finish");
      const endX = ganttLinkPercent(body, targetEdge === "start" ? targetRect.left : targetRect.right);
      // Releasing over the bar, or within a short reach of either edge, targets
      // that activity; empty track space stays an uncommitted drag.
      const reach = Math.max(12, targetRect.width * 0.25);
      if (moveEvent.clientX < targetRect.left - reach || moveEvent.clientX > targetRect.right + reach) continue;
      target = { activityId, edge: targetEdge, type: relationshipTypeFromEdges(drag.fromEdge, targetEdge), row: targetRow };
      targetEndPercent = endX;
      break;
    }
    drag.target = target;
    clearTargetHighlight();
    if (target) target.row.classList.add("is-link-target");
    // Route like the persisted links: a horizontal run from the source edge to
    // just beside the target edge, then vertically to the target row.
    let endX = targetEndPercent;
    let endY = pointerY;
    if (target) {
      endY = target.row.offsetTop + target.row.offsetHeight / 2;
    }
    const startX = drag.startPercent;
    const laneX = Math.max(0.2, Math.min(99.8, endX + (endX >= startX ? 1.2 : -1.2)));
    drag.path.setAttribute(
      "d",
      `M ${ganttRound(startX * 10)} ${ganttRound(drag.startY)} H ${ganttRound(laneX * 10)} V ${ganttRound(endY)} H ${ganttRound(endX * 10)}`,
    );
    drag.overlay.dataset.ganttLinkPreview = target ? target.type : "";
    if (target) {
      drag.hint.hidden = false;
      drag.hint.dataset.ganttLinkType = target.type;
      drag.hint.textContent = ganttLinkTypeLabel(record.state.locale, target.type);
      drag.hint.style.left = `${Math.round(moveEvent.clientX - bodyRect.left + 12)}px`;
      drag.hint.style.top = `${Math.round(pointerY + 10)}px`;
    } else {
      drag.hint.hidden = true;
      drag.hint.textContent = "";
      drag.hint.removeAttribute("data-gantt-link-type");
    }
  };
  const teardown = (): void => {
    clearTargetHighlight();
    drag.overlay.remove();
    drag.hint.remove();
    delete container.dataset.ganttLinkDragging;
    container.removeEventListener("pointermove", drag.move);
    container.removeEventListener("pointerup", drag.finish);
    container.removeEventListener("pointercancel", drag.cancel);
    document.removeEventListener("keydown", drag.onKey, true);
    try { barEl.releasePointerCapture?.(drag.pointerId); } catch { /* optional pointer capture */ }
    ganttLinkDrags.delete(container);
  };
  drag.onKey = (keyEvent: KeyboardEvent): void => {
    if (keyEvent.key !== "Escape") return;
    keyEvent.preventDefault();
    keyEvent.stopPropagation();
    drag.cancel();
  };
  drag.finish = (finishEvent: PointerEvent): void => {
    if (finishEvent.pointerId !== drag.pointerId) return;
    const committed = drag.moved ? drag.target : null;
    teardown();
    if (!committed) return;
    record.options.onRelationshipCreate?.({
      predecessorId: drag.predecessorId,
      successorId: committed.activityId,
      type: committed.type,
      lagValue: "0",
      lagUnit: "working-day",
    });
  };
  drag.cancel = (): void => teardown();
  ganttLinkDrags.set(container, drag);
  try { barEl.setPointerCapture?.(event.pointerId); } catch { /* optional pointer capture */ }
  container.addEventListener("pointermove", drag.move);
  container.addEventListener("pointerup", drag.finish);
  container.addEventListener("pointercancel", drag.cancel);
  document.addEventListener("keydown", drag.onKey, true);
  drag.path.setAttribute("d", `M ${ganttRound(drag.startPercent * 10)} ${ganttRound(startY)} L ${ganttRound(drag.startPercent * 10)} ${ganttRound(startY)}`);
}

/** Applies the presentation-only network zoom to the rendered SVG. */
function applyNetworkZoom(section: HTMLElement, nextZoom: number): void {
  const svg = section.querySelector<SVGSVGElement>(".cp-network-svg");
  if (!svg) return;
  const baseWidth = Number(section.dataset.networkBaseWidth);
  const baseHeight = Number(section.dataset.networkBaseHeight);
  if (!Number.isFinite(baseWidth) || !Number.isFinite(baseHeight) || baseWidth <= 0 || baseHeight <= 0) return;
  const zoom = clampNetworkZoom(nextZoom);
  svg.setAttribute("width", String(Math.round(baseWidth * zoom)));
  svg.setAttribute("height", String(Math.round(baseHeight * zoom)));
  section.dataset.networkZoom = String(zoom);
  const label = section.querySelector<HTMLElement>("[data-network-zoom-label]");
  if (label) label.textContent = `${Math.round(zoom * 100)}%`;
  section.querySelectorAll<HTMLButtonElement>("[data-network-zoom]").forEach((button) => {
    if (button.dataset.networkZoom === "in") button.disabled = zoom >= NETWORK_ZOOM_MAX;
    else if (button.dataset.networkZoom === "out") button.disabled = zoom <= NETWORK_ZOOM_MIN;
  });
  const storageKey = section.dataset.networkStorageKey ?? "";
  if (storageKey) storeNetworkZoom(storageKey, zoom);
}

function fitNetworkZoom(section: HTMLElement): number {
  const scroll = section.querySelector<HTMLElement>(".cp-network-scroll");
  if (!scroll) return 1;
  const baseWidth = Number(section.dataset.networkBaseWidth);
  const baseHeight = Number(section.dataset.networkBaseHeight);
  if (!Number.isFinite(baseWidth) || !Number.isFinite(baseHeight) || baseWidth <= 0 || baseHeight <= 0) return 1;
  const availableWidth = (scroll.clientWidth || 0) - 8;
  const availableHeight = (scroll.clientHeight || 0) - 8;
  if (availableWidth <= 0 || availableHeight <= 0) return 1;
  return clampNetworkZoom(Math.min(availableWidth / baseWidth, availableHeight / baseHeight, 1));
}

function bindWorkspaceEvents(container: HTMLElement): void {
  if (typeof container.addEventListener !== "function" || workspaceEventDelegation.has(container)) return;
  workspaceEventDelegation.add(container);
  // The activity table and the chart are one vertical surface: scrolling
  // either pane keeps every bar on the row it belongs to.
  container.addEventListener("scroll", (event) => {
    const target = event.target as HTMLElement | null;
    const table = container.querySelector<HTMLElement>("#cp-activity-grid .cp-table-wrap");
    const chart = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-chart");
    if (!table || !chart || !target || (target !== table && target !== chart)) return;
    const other = target === table ? chart : table;
    // The table keeps its header and the chart keeps its timescale axis while
    // scrolling. Their heights differ, so a one-to-one scrollTop copy would
    // shift every bar by that difference; compensate for the header delta.
    const axisHeight = chart.querySelector<HTMLElement>(".cp-gantt-axis")?.getBoundingClientRect().height ?? 0;
    const headerHeight = table.querySelector<HTMLElement>("thead")?.getBoundingClientRect().height ?? 0;
    const delta = target === table ? axisHeight - headerHeight : headerHeight - axisHeight;
    const maxScroll = Math.max(0, other.scrollHeight - other.clientHeight);
    const desired = Math.max(0, Math.min(maxScroll, target.scrollTop + delta));
    if (Math.abs(other.scrollTop - desired) > 0.5) other.scrollTop = desired;
  }, true);
  // A contextual Add menu closes on any click that lands outside it and when
  // focus leaves its own subtree, so it can never sit stale over the table.
  if (typeof document !== "undefined") {
    document.addEventListener("click", (event) => {
      if (!container.isConnected) return;
      const node = event.target as Node | null;
      container.querySelectorAll<HTMLDetailsElement>("[data-context-add][open]").forEach((menu) => {
        if (!node || !menu.contains(node)) menu.open = false;
      });
    });
  }
  container.addEventListener("focusout", (event) => {
    const menu = (event.target as HTMLElement | null)?.closest?.<HTMLDetailsElement>("[data-context-add]");
    if (!menu) return;
    const next = event.relatedTarget as Node | null;
    if (!next || !menu.contains(next)) menu.open = false;
  });
  container.addEventListener("toggle", (event) => {
    const menu = event.target as HTMLDetailsElement | null;
    if (!menu?.matches?.("[data-context-add]")) return;
    const summary = menu.querySelector<HTMLElement>("summary");
    summary?.setAttribute("aria-expanded", String(menu.open));
    summary?.toggleAttribute("data-open", menu.open);
  }, true);
  container.addEventListener("pointerdown", (event) => {
    const target = event.target as HTMLElement | null;
    const columnHandle = target?.closest?.<HTMLElement>("[data-column-resize]");
    if (columnHandle) {
      startColumnResize(container, columnHandle, event);
      return;
    }
    const tableSplitter = target?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (tableSplitter) {
      startTableGanttResize(tableSplitter, event);
      return;
    }
    const detailsSplitter = target?.closest?.<HTMLElement>("[data-details-splitter]");
    if (detailsSplitter) {
      startDetailsResize(detailsSplitter, event);
      return;
    }
    // Drawing a relationship starts on an authoritative bar edge, and only
    // while relationship lines are shown, as the V26 Help documents. The link
    // layer sits above the rows and shaped bars are clipped, so the pointer is
    // resolved geometrically against the row's primary duration bar. Secondary
    // buttons keep their context-menu behaviour.
    if (event.button !== 0) return;
    const gantt = target?.closest?.<HTMLElement>("#cp-gantt");
    let primaryBar: HTMLElement | null = null;
    let activityRow: HTMLElement | null = null;
    if (gantt) {
      for (const row of gantt.querySelectorAll<HTMLElement>("[data-gantt-activity-id]")) {
        const rowRect = row.getBoundingClientRect();
        if (event.clientY < rowRect.top || event.clientY > rowRect.bottom) continue;
        const bar = row.querySelector<HTMLElement>(".cp-gantt-bar[data-gantt-bar-primary='true']");
        if (!bar) continue;
        const barRect = bar.getBoundingClientRect();
        if (event.clientY < barRect.top || event.clientY > barRect.bottom) continue;
        primaryBar = bar;
        activityRow = row;
        break;
      }
    }
    if (primaryBar && activityRow) {
      const record = workspaceRenderRecords.get(container);
      if (record?.state.showGanttRelationships) {
        const handle = target?.closest?.<HTMLElement>("[data-gantt-link-edge]")?.dataset.ganttLinkEdge;
        const edge = handle === "start" || handle === "finish" ? handle : ganttLinkEdgeAt(primaryBar, event.clientX);
        if (edge) {
          event.preventDefault();
          beginGanttLinkDrag(container, event, primaryBar, activityRow, edge);
        }
      }
    }
  });
  container.addEventListener("input", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!target) return;
    const milestoneForm = target.closest<HTMLFormElement>("[data-wbs-milestones-form]");
    if (milestoneForm) {
      updateWbsMilestoneRollup(milestoneForm);
      return;
    }
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
    const projectSearch = target.closest<HTMLInputElement>("[data-project-search]");
    if (projectSearch) {
      projectRegisterStateFor(container).query = projectSearch.value;
      refreshProjectRegister(container);
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
    // A rejected submit must say why; silently doing nothing looks like a lost
    // click. The server stays the authority for cross-activity rules.
    const relationshipInputNotice = (text: string): void => {
      const panel = container.querySelector<HTMLElement>("#cp-logic");
      if (!panel) return;
      let notice = panel.querySelector<HTMLElement>("[data-relationship-error]");
      if (!notice) {
        notice = document.createElement("p");
        notice.dataset.relationshipError = "true";
        notice.setAttribute("role", "alert");
        panel.prepend(notice);
      }
      notice.textContent = text;
    };
    if (form.matches("[data-wbs-status-form]")) {
      event.preventDefault();
      const wbsId = form.dataset.wbsStatusForm ?? "";
      const node = record.state.wbsNodes.find((item) => item.id === wbsId);
      if (!node) return;
      const status = form.querySelector<HTMLSelectElement>('[name="status"]')?.value;
      const technique = form.querySelector<HTMLSelectElement>('[name="percent_complete_technique"]')?.value;
      void record.options.onWbsUpdate?.(wbsId, {
        code: node.localCode,
        name: node.name,
        sequenceNumber: node.sequenceNumber,
        ...(status === "planned" || status === "active" || status === "inactive" || status === "what_if" ? { status } : {}),
        ...(technique === "activities" || technique === "milestones" ? { percentCompleteTechnique: technique } : {}),
      });
      return;
    }
    if (form.matches("[data-wbs-milestones-form]")) {
      event.preventDefault();
      const wbsId = form.dataset.wbsMilestonesForm ?? "";
      const expectedRevision = Number(form.dataset.wbsRevision ?? "");
      const rows = [...form.querySelectorAll<HTMLElement>("[data-wbs-milestone-row]")];
      const milestones: WorkspaceWbsMilestone[] = rows.map((row, index) => {
        const field = (name: string): HTMLInputElement | null => row.querySelector<HTMLInputElement>(`[name="${name}"]`);
        return {
          id: field("milestone_id")?.value.trim() ?? "",
          name: field("milestone_name")?.value.trim() ?? "",
          weight: Number(field("milestone_weight")?.value ?? ""),
          completed: field("milestone_completed")?.checked ?? false,
          sequenceNumber: index,
        };
      });
      const ids = new Set(milestones.map((item) => item.id));
      const invalid =
        !wbsId ||
        !Number.isInteger(expectedRevision) ||
        expectedRevision < 1 ||
        milestones.length === 0 ||
        ids.size !== milestones.length ||
        milestones.some(
          (item) =>
            !item.id ||
            !item.name ||
            !Number.isFinite(item.weight) ||
            item.weight <= 0,
        );
      const panel = form.closest<HTMLElement>(".cp-wbs-milestones");
      if (invalid) {
        if (panel) {
          let notice = panel.querySelector<HTMLElement>("[data-wbs-milestone-error]");
          if (!notice) {
            notice = document.createElement("p");
            notice.dataset.wbsMilestoneError = "true";
            notice.setAttribute("role", "alert");
            notice.className = "cp-activity-detail-note";
            panel.prepend(notice);
          }
          notice.textContent = uiText(
            record.state.locale,
            "Each milestone needs a unique ID and a name, with a weight greater than zero.",
            "هر نقطه عطف به شناسهٔ یکتا، نام و وزنی بزرگ‌تر از صفر نیاز دارد.",
          );
        }
        return;
      }
      void record.options.onWbsMilestonesUpdate?.(wbsId, milestones, expectedRevision);
      return;
    }
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
      if (predecessorId && successorId && predecessorId === successorId) {
        relationshipInputNotice(uiText(record.state.locale, "A relationship needs two different activities.", "یک رابطه به دو فعالیت متفاوت نیاز دارد."));
        return;
      }
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
      if (predecessorId && successorId && predecessorId === successorId) {
        relationshipInputNotice(uiText(record.state.locale, "A relationship needs two different activities.", "یک رابطه به دو فعالیت متفاوت نیاز دارد."));
        return;
      }
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
      const status = form.querySelector<HTMLSelectElement>('[name="status"]')?.value;
      const technique = form.querySelector<HTMLSelectElement>('[name="percent_complete_technique"]')?.value;
      if (wbsId) {
        void record.options.onWbsUpdate?.(wbsId, {
          code: readText("code"),
          name: readText("name"),
          sequenceNumber,
          ...(status === "planned" || status === "active" || status === "inactive" || status === "what_if" ? { status } : {}),
          ...(technique === "activities" || technique === "milestones" ? { percentCompleteTechnique: technique } : {}),
        });
      }
    }
  });
  container.addEventListener("click", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-project-settings],[data-desktop-command],[data-context-add] summary,[data-register-tab],[data-calendar-editor-tab],[data-wbs-detail-tab],[data-project-detail-tab],[data-activity-details-options-open],[data-activity-details-options-close],[data-activity-details-apply],[data-activity-detail-tab],[data-window-close],[data-shell-command],[data-layout-options-open],[data-layout-options-close],[data-menu],[data-rail-action],[data-tools-open],[data-tools-close],[data-wbs-drawer-close],[data-wbs-view],[data-wbs-id],[data-wbs-cut],[data-wbs-copy],[data-wbs-paste],[data-wbs-delete],[data-wbs-milestone-add],[data-wbs-milestone-remove],[data-document-row],[data-document-detail-tab],[data-relationship-delete],[data-p6-field-add],[data-p6-field-add-all],[data-p6-field-remove],[data-p6-field-visibility],[data-p6-field-width],[data-p6-field-alignment],[data-p6-field-pin],[data-p6-field-freeze],[data-p6-field-move],[data-p6-layout-undo],[data-p6-layout-redo],[data-p6-layout-restore],[data-gantt-scale],[data-network-zoom],[data-gantt-relationships-toggle],[data-gantt-activity-id],[data-band-toggle],[data-wbs-toggle],[data-wbs-expand-all],[data-wbs-collapse-all],[data-wbs-collapse-to],[data-collapse-to-apply],[data-collapse-to-cancel],[data-wbs-row],[data-trace-goto],[data-usage-refresh],[data-activity-id],[data-activity-edit],[data-activity-sort-direction],[data-reset-table-split],[data-reset-details-split],[data-reset-column-widths],[data-activity-create-open],[data-columns-open],[data-project-open],[data-project-row],[data-project-select],[data-project-domain-toggle],[data-project-filter-reset],[data-activity-select-all],[data-activity-export-open],[data-activity-export-cancel],[data-activity-export-scope],[data-activity-export-download]") : null;
    if (!target) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const { state, options } = record;
    if (target.dataset.activitySelectAll !== undefined) {
      // The scope contract lives in the main shell so the menu command and the
      // toolbar button take exactly the same state transition.
      options.onSelectAll?.();
      return;
    }
    if (target.dataset.activityExportOpen !== undefined) {
      openActivityExportDialog(container);
      return;
    }
    if (target.dataset.activityExportCancel !== undefined) {
      target.closest<HTMLDialogElement>("[data-activity-export-dialog]")?.close();
      return;
    }
    if (target.dataset.activityExportScope !== undefined) {
      selectActivityExportScope(container, target.dataset.activityExportScope as ActivityExportScope);
      return;
    }
    if (target.dataset.activityExportDownload !== undefined) {
      downloadActivityExport(container);
      return;
    }
    if (target.dataset.registerTab) {
      const tab = target.dataset.registerTab;
      container.querySelectorAll<HTMLElement>("[data-register-tab]").forEach((button) => {
        const active = button.dataset.registerTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-register-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.registerPanel !== tab;
      });
      return;
    }
    if (target.dataset.usageRefresh !== undefined) {
      // Re-reads the authoritative stored periods; the renderer shows its own
      // loading state until the read returns.
      options.onActivityUsageRefresh?.();
      return;
    }
    if (target.dataset.calendarEditorTab) {
      const tab = target.dataset.calendarEditorTab;
      container.querySelectorAll<HTMLElement>("[data-calendar-editor-tab]").forEach((button) => {
        const active = button.dataset.calendarEditorTab === tab;
        button.setAttribute("aria-selected", String(active));
        button.classList.toggle("is-active", active);
      });
      container.querySelectorAll<HTMLElement>("[data-calendar-editor-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.calendarEditorPanel !== tab;
      });
      return;
    }
    if (target.dataset.wbsView) {
      const view = target.dataset.wbsView === "chart" ? "chart" : "table";
      wbsViewByContainer.set(container, view);
      container.querySelectorAll<HTMLElement>("[data-wbs-view]").forEach((button) => {
        const active = button.dataset.wbsView === view;
        button.setAttribute("aria-pressed", String(active));
        button.classList.toggle("is-active", active);
      });
      const hierarchy = container.querySelector<HTMLElement>("[data-wbs-hierarchy]");
      if (hierarchy) {
        const labels = getWorkspaceLabels(state.locale);
        hierarchy.innerHTML = view === "chart"
          ? renderWbsChart(state.wbsNodes, state.selectedWbsId, state.locale, labels)
          : renderWbsTable(state.wbsNodes, state.activities, state.selectedWbsId, state.locale, labels);
      }
      return;
    }
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
    if (target.dataset.projectOpen !== undefined) {
      const projectId = target.dataset.projectOpen;
      if (projectId && projectId !== state.context.project_id) options.onProjectOpen?.(projectId);
      return;
    }
    if (target.dataset.projectFilterReset !== undefined) {
      const register = projectRegisterStateFor(container);
      register.query = "";
      register.domain = PROJECT_DOMAIN_FILTER_ALL;
      register.status = PROJECT_STATUS_FILTER_ALL;
      refreshProjectRegister(container);
      container.querySelector<HTMLInputElement>("[data-project-search]")?.focus();
      return;
    }
    if (target.dataset.projectDomainToggle !== undefined) {
      const register = projectRegisterStateFor(container);
      const key = target.dataset.projectDomainToggle;
      if (register.collapsed.has(key)) register.collapsed.delete(key);
      else register.collapsed.add(key);
      refreshProjectRegister(container);
      return;
    }
    if (target.dataset.projectSelect !== undefined || target.dataset.projectRow !== undefined) {
      const projectId = target.dataset.projectSelect ?? target.dataset.projectRow;
      if (!projectId) return;
      projectRegisterStateFor(container).selectedId = projectId;
      refreshProjectRegister(container);
      return;
    }
    if (target.dataset.resetTableSplit !== undefined) { resetTableSplit(container); return; }
    if (target.dataset.resetDetailsSplit !== undefined) { resetDetailsSplit(container); return; }
    if (target.dataset.resetColumnWidths !== undefined) { resetColumnWidths(container); return; }
    if (target.dataset.activityCreateOpen !== undefined) { options.onActivityContextCommand?.("add", state.selectedActivityId ?? ""); return; }
    if (target.dataset.columnsOpen !== undefined) { options.onActivityContextCommand?.("columns", state.selectedActivityId ?? ""); return; }
    if (target.dataset.toolsOpen !== undefined) { openToolsDrawer(container); return; }
    if (target.dataset.toolsClose !== undefined) { closeDrawer(container, "[data-tools-drawer]"); return; }
    if (target.dataset.wbsDrawerClose !== undefined) { closeDrawer(container, "[data-wbs-drawer]"); return; }
    if (typeof target.matches === "function" && target.matches("[data-context-add] > summary")) {
      const menu = target.parentElement as HTMLDetailsElement | null;
      // Focus the first enabled command after the native toggle so keyboard
      // users can continue without pressing Tab through the rail again.
      window.setTimeout(() => {
        if (!menu?.open) return;
        menu.querySelector<HTMLButtonElement>("[role='menuitem']:not([disabled])")?.focus({ preventScroll: true });
      }, 0);
      return;
    }
    if (target.dataset.desktopCommand) {
      const menu = target.closest<HTMLDetailsElement>("[data-context-add]");
      if (menu) {
        menu.open = false;
        menu.querySelector<HTMLElement>("summary")?.focus({ preventScroll: true });
      }
      options.onDesktopCommand?.(target.dataset.desktopCommand as DesktopCommand);
      return;
    }
    if (target.dataset.railAction) {
      const action = target.dataset.railAction;
      if (action === "navigation") {
        toggleDrawer(container, "[data-nav-flyout]");
        const flyout = container.querySelector<HTMLElement>("[data-nav-flyout]");
        container.querySelectorAll<HTMLElement>("[data-nav-flyout-toggle]").forEach((button) => button.setAttribute("aria-expanded", String(Boolean(flyout && !flyout.hidden))));
        return;
      }
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
    if ("wbsCut" in target.dataset || "wbsCopy" in target.dataset) {
      const selected = state.wbsNodes.find((node) => node.id === state.selectedWbsId);
      if (!selected) return;
      const entry: WorkspaceWbsClipboardEntry = {
        mode: "wbsCut" in target.dataset ? "cut" : "copy",
        wbsId: selected.id,
        code: selected.localCode,
        name: selected.name,
      };
      wbsClipboardByContainer.set(container, entry);
      const clipboard = container.querySelector<HTMLElement>("[data-wbs-clipboard]");
      if (clipboard) clipboard.textContent = wbsClipboardText(state.locale, entry);
      const paste = container.querySelector<HTMLButtonElement>("[data-wbs-paste]");
      if (paste) paste.disabled = false;
      const clipboardError = container.querySelector<HTMLElement>("[data-wbs-clipboard-error]");
      if (clipboardError) { clipboardError.hidden = true; clipboardError.textContent = ""; }
      return;
    }
    if ("wbsPaste" in target.dataset) {
      const clip = wbsClipboardLabels(state.locale);
      const entry = wbsClipboardByContainer.get(container);
      const targetNode = state.wbsNodes.find((node) => node.id === state.selectedWbsId);
      const clipboardError = container.querySelector<HTMLElement>("[data-wbs-clipboard-error]");
      const showClipboardError = (message: string): void => {
        if (!clipboardError) return;
        clipboardError.hidden = false;
        clipboardError.textContent = message;
      };
      if (!entry) { showClipboardError(clip.selectTarget); return; }
      if (!targetNode) { showClipboardError(clip.selectTarget); return; }
      if (entry.mode === "cut") {
        const source = state.wbsNodes.find((node) => node.id === entry.wbsId);
        if (!source) {
          wbsClipboardByContainer.delete(container);
          const clipboard = container.querySelector<HTMLElement>("[data-wbs-clipboard]");
          if (clipboard) clipboard.textContent = wbsClipboardText(state.locale, null);
          const paste = container.querySelector<HTMLButtonElement>("[data-wbs-paste]");
          if (paste) paste.disabled = true;
          showClipboardError(clip.selectTarget);
          return;
        }
        if (source.id === targetNode.id) { showClipboardError(clip.cannotPasteIntoSelf); return; }
        // A cut paste moves the existing record, so its activity assignments
        // stay attached to the same WBS identity (V26 cut-and-paste topic).
        wbsClipboardByContainer.delete(container);
        const clipboard = container.querySelector<HTMLElement>("[data-wbs-clipboard]");
        if (clipboard) clipboard.textContent = wbsClipboardText(state.locale, null);
        const paste = container.querySelector<HTMLButtonElement>("[data-wbs-paste]");
        if (paste) paste.disabled = true;
        void options.onWbsUpdate?.(source.id, {
          code: source.localCode,
          name: source.name,
          sequenceNumber: source.sequenceNumber,
          ...(source.status ? { status: source.status } : {}),
          ...(source.percentCompleteTechnique ? { percentCompleteTechnique: source.percentCompleteTechnique } : {}),
          parentKind: "wbs",
          parentWbsId: targetNode.id,
        });
        return;
      }
      // A copy paste asks the server to duplicate the whole subtree.
      const rootCode = nextWbsCopyCode(state.wbsNodes, targetNode.id, entry.code);
      void options.onWbsCopy?.(entry.wbsId, targetNode.id, rootCode);
      return;
    }
    if ("wbsMilestoneAdd" in target.dataset) {
      const form = target.closest<HTMLFormElement>("[data-wbs-milestones-form]");
      const body = form?.querySelector<HTMLElement>("[data-wbs-milestone-rows]");
      if (form && body) {
        body.insertAdjacentHTML("beforeend", wbsMilestoneRowMarkup(state.locale, { id: "", name: "", weight: "1", completed: false }));
        const added = body.querySelector<HTMLElement>("[data-wbs-milestone-row]:last-child input");
        added?.focus();
        updateWbsMilestoneRollup(form);
      }
      return;
    }
    if ("wbsMilestoneRemove" in target.dataset) {
      const form = target.closest<HTMLFormElement>("[data-wbs-milestones-form]");
      target.closest<HTMLElement>("[data-wbs-milestone-row]")?.remove();
      if (form) updateWbsMilestoneRollup(form);
      return;
    }
    if (target.dataset.relationshipDelete) {
      const revision = Number.parseInt(target.dataset.relationshipRevision ?? "", 10);
      if (!Number.isInteger(revision) || revision < 1) return;
      // Deleting a dependency silently would remove a scheduling constraint, so
      // the Logic panel asks first like the Gantt arrow menu already does.
      if (typeof window !== "undefined" && typeof window.confirm === "function" && !window.confirm(getWorkspaceLabels(state.locale).relationshipDeleteConfirm)) {
        target.focus?.();
        return;
      }
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
    if (target.dataset.p6FieldAddAll !== undefined) {
      // "Add all" means every registry field that is not in the layout yet. It
      // never re-adds a visible column, so one click cannot duplicate fields.
      const registry = state.p6FieldRegistry;
      const layout = state.p6Layout;
      if (!registry || !layout) return;
      const inLayout = new Set(layout.columns.map((column) => column.field_id));
      const fieldIds = registry.fields.filter((field) => !inLayout.has(field.field_id)).map((field) => field.field_id);
      if (fieldIds.length) options.onP6FieldAddMany?.(fieldIds);
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
      openLayoutOptionsDialog(container);
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
    if (target.dataset.networkZoom) {
      const section = target.closest<HTMLElement>("[data-network-view]");
      if (!section) return;
      const mode = target.dataset.networkZoom;
      const current = Number(section.dataset.networkZoom) || 1;
      const next = mode === "fit" ? fitNetworkZoom(section) : mode === "in" ? current + 0.1 : mode === "out" ? current - 0.1 : current;
      applyNetworkZoom(section, next);
      return;
    }
    if (target.dataset.ganttRelationshipsToggle !== undefined) {
      options.onGanttRelationshipsChange?.(target.dataset.ganttRelationshipsToggle === "true");
      return;
    }
    if (target.dataset.ganttActivityId) {
      const activityId = target.dataset.ganttActivityId;
      return void options.onGanttActivitySelect?.(
        activityId,
        activitySelectionRequest(container, event, "[data-gantt-activity-id]", "ganttActivityId"),
      );
    }
    if (target.dataset.wbsToggle) {
      const projectId = state.context.project_id;
      toggleCollapsedWbs(projectId, target.dataset.wbsToggle);
      rerenderWorkspaceRows(container);
      return;
    }
    if (target.dataset.bandToggle) {
      const projectId = state.context.project_id;
      toggleCollapsedWbs(projectId, target.dataset.bandToggle);
      rerenderWorkspaceRows(container);
      return;
    }
    if (target.dataset.wbsExpandAll !== undefined) {
      setCollapsedWbsIds(state.context.project_id, []);
      rerenderWorkspaceRows(container);
      return;
    }
    if (target.dataset.wbsCollapseAll !== undefined) {
      setCollapsedWbsIds(state.context.project_id, collapseAllWbsIds(state.activities, state.wbsNodes));
      rerenderWorkspaceRows(container);
      return;
    }
    if (target.dataset.wbsCollapseTo !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-collapse-to-dialog]");
      const select = dialog?.querySelector<HTMLSelectElement>("[data-collapse-to-select]");
      if (select && state.selectedWbsId && state.wbsNodes.some((node) => node.id === state.selectedWbsId)) {
        select.value = state.selectedWbsId;
      }
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    if (target.dataset.collapseToApply !== undefined) {
      const dialog = container.querySelector<HTMLElement>("[data-collapse-to-dialog]");
      const targetWbsId = dialog?.querySelector<HTMLSelectElement>("[data-collapse-to-select]")?.value ?? "";
      if (targetWbsId && state.wbsNodes.some((node) => node.id === targetWbsId)) {
        setCollapsedWbsIds(state.context.project_id, collapseToWbsIds(state.activities, state.wbsNodes, targetWbsId));
        rerenderWorkspaceRows(container);
      }
      const native = dialog as HTMLDialogElement | null;
      if (native && typeof native.close === "function") native.close();
      else native?.removeAttribute("open");
      return;
    }
    if (target.dataset.collapseToCancel !== undefined) {
      const dialog = container.querySelector<HTMLDialogElement>("[data-collapse-to-dialog]");
      if (dialog && typeof dialog.close === "function") dialog.close();
      else dialog?.removeAttribute("open");
      return;
    }
    if (target.dataset.wbsRow) {
      options.onWbsSelect?.(target.dataset.wbsRow);
      return;
    }
    if (target.dataset.traceGoto) {
      options.onActivitySelect?.(target.dataset.traceGoto);
      return;
    }
    if (target.dataset.activityId) {
      options.onActivitySelect?.(
        target.dataset.activityId,
        activitySelectionRequest(container, event, "#cp-activity-grid tbody tr[data-activity-id]", "activityId"),
      );
    }
  });
  container.addEventListener("contextmenu", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    // The details pane is a separate surface with its own Customize menu.
    if (target.closest("#cp-details")) return;
    const context = workspaceContextAt(target);
    if (!context) return;
    event.preventDefault();
    if (context.kind === "table-activity" || context.kind === "gantt-activity") {
      const activityId = context.activityId;
      if (activityId) workspaceRenderRecords.get(container)?.options.onActivitySelect?.(activityId);
    }
    const point = event as MouseEvent;
    const fallback = anchorPoint(context.anchor);
    openWorkspaceContextMenu(
      container,
      context,
      Number.isFinite(point.clientX) ? point.clientX : fallback.x,
      Number.isFinite(point.clientY) ? point.clientY : fallback.y,
      context.anchor,
      false,
    );
  });
  container.addEventListener("dblclick", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const networkEdge = target.closest<SVGGraphicsElement>("[data-network-relationship-id]");
    if (networkEdge) {
      const relationshipId = networkEdge.getAttribute("data-network-relationship-id") ?? "";
      if (!relationshipId) return;
      event.preventDefault();
      openRelationshipEditor(container, relationshipId);
      return;
    }
    const wbsRow = target.closest<HTMLElement>("[data-wbs-row]");
    if (!wbsRow?.dataset.wbsRow) return;
    event.preventDefault();
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    toggleCollapsedWbs(record.state.context.project_id, wbsRow.dataset.wbsRow);
    rerenderWorkspaceRows(container);
  });
  container.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeToolbarSurfaces();
    const keyTarget = event.target as HTMLElement | null;
    const addMenu = keyTarget?.closest?.<HTMLElement>("[data-context-add]") ?? null;
    if (addMenu && typeof addMenu.querySelector === "function") {
      const details = addMenu as HTMLDetailsElement;
      const summary = addMenu.querySelector<HTMLElement>("summary");
      const commands = () => Array.from(addMenu.querySelectorAll<HTMLButtonElement>("[role='menuitem']:not([disabled])"));
      if (event.key === "Escape" && details.open) {
        event.preventDefault();
        event.stopPropagation();
        details.open = false;
        summary?.focus({ preventScroll: true });
        return;
      }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        const items = commands();
        if (items.length) {
          event.preventDefault();
          const current = items.indexOf(document.activeElement as HTMLButtonElement);
          const last = items.length - 1;
          let next = current;
          if (event.key === "ArrowDown") next = current >= last ? 0 : current + 1;
          else if (event.key === "ArrowUp") next = current <= 0 ? last : current - 1;
          else if (event.key === "Home") next = 0;
          else next = last;
          if (!details.open) details.open = true;
          items[next].focus({ preventScroll: true });
          return;
        }
      }
    }
    if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
      if (!keyTarget || typeof keyTarget.closest !== "function") return;
      if (keyTarget.closest("#cp-details")) return;
      const context = workspaceContextAt(keyTarget);
      if (!context) return;
      event.preventDefault();
      const point = anchorPoint(context.anchor);
      openWorkspaceContextMenu(container, context, point.x, point.y, context.anchor);
      return;
    }
    const gridRow = keyTarget?.closest?.<HTMLElement>("#cp-activity-grid tbody tr[tabindex]") ?? null;
    if (gridRow && ["ArrowDown", "ArrowUp", "Home", "End", "PageDown", "PageUp"].includes(event.key)) {
      const rows = Array.from(container.querySelectorAll<HTMLElement>("#cp-activity-grid tbody tr[tabindex]"));
      const index = rows.indexOf(gridRow);
      if (index >= 0) {
        event.preventDefault();
        const page = 10;
        let next = index;
        if (event.key === "ArrowDown") next = Math.min(rows.length - 1, index + 1);
        else if (event.key === "ArrowUp") next = Math.max(0, index - 1);
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = rows.length - 1;
        else if (event.key === "PageDown") next = Math.min(rows.length - 1, index + page);
        else if (event.key === "PageUp") next = Math.max(0, index - page);
        const targetRow = rows[next];
        if (!targetRow) return;
        const record = workspaceRenderRecords.get(container);
        const activityId = targetRow.dataset.activityId;
        // Band rows stay selectable only with Enter; moving onto them keeps the
        // current activity selection so a band never becomes a primary record.
        if (activityId && record?.options.onActivitySelect && !event.ctrlKey && !event.metaKey) {
          const orderedIds = rows.flatMap((row) => (row.dataset.activityId ? [row.dataset.activityId] : []));
          record.options.onActivitySelect(activityId, event.shiftKey ? { range: true, orderedIds } : undefined);
        } else {
          targetRow.focus();
        }
      }
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      const projectRow = keyTarget?.closest?.<HTMLElement>("[data-project-row]") ?? null;
      // A focusable table row selects the project; a nested button keeps its
      // native activation (Open or select), so only handle the row itself.
      if (projectRow && !keyTarget?.closest?.("button")) {
        event.preventDefault();
        projectRegisterStateFor(container).selectedId = projectRow.dataset.projectRow ?? null;
        refreshProjectRegister(container);
        return;
      }
      const activationTarget = keyTarget && typeof keyTarget.closest === "function"
        ? keyTarget.closest<HTMLElement>("[data-network-relationship-id],[data-gantt-activity-id],[data-activity-id],[data-document-row],[data-wbs-row]")
        : null;
      if (!activationTarget) return;
      // The toggle is a real button: let its native click handle Enter/Space
      // rather than toggling twice. Anywhere else on the focused band row
      // expands or collapses the branch.
      if (activationTarget.dataset.wbsRow && !keyTarget?.closest?.("[data-wbs-toggle]")) {
        event.preventDefault();
        const record = workspaceRenderRecords.get(container);
        if (!record) return;
        toggleCollapsedWbs(record.state.context.project_id, activationTarget.dataset.wbsRow);
        rerenderWorkspaceRows(container);
        return;
      }
      if (activationTarget.dataset.wbsRow) return;
      event.preventDefault();
      if (activationTarget.dataset.networkRelationshipId) {
        openRelationshipEditor(container, activationTarget.dataset.networkRelationshipId);
        return;
      }
      if (activationTarget.dataset.documentRow) {
        activationTarget.click();
        return;
      }
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      if (activationTarget.dataset.ganttActivityId) record.options.onGanttActivitySelect?.(activationTarget.dataset.ganttActivityId);
      else if (activationTarget.dataset.activityId) record.options.onActivitySelect?.(activationTarget.dataset.activityId);
      return;
    }
    const columnHandle = keyTarget?.closest?.<HTMLElement>("[data-column-resize]");
    if (columnHandle) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const columnId = columnHandle.dataset.columnResize;
      if (!columnId) return;
      event.preventDefault();
      const header = columnHandle.closest<HTMLElement>("th");
      const current = Number.parseFloat(header?.style.width ?? "") || MIN_COLUMN_WIDTH;
      const step = event.shiftKey ? 40 : 10;
      const delta = (event.key === "ArrowRight" ? step : -step) * (isRtlElement(container) ? -1 : 1);
      applyActivityColumnWidth(container, columnId, current + delta, true);
      return;
    }
    const tableSplitter = keyTarget?.closest?.<HTMLElement>("[data-panel-splitter]");
    if (tableSplitter) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      const split = tableSplitter.closest<HTMLElement>("[data-panel-split]");
      if (!split) return;
      event.preventDefault();
      const current = Number.parseFloat(split.style.getPropertyValue("--cp-split-table")) || DEFAULT_TABLE_SPLIT;
      const logical = (event.key === "ArrowRight" ? 2 : -2) * (isRtlElement(split) ? -1 : 1);
      const next = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, current + logical));
      split.style.setProperty("--cp-split-table", `${next}%`);
      tableSplitter.setAttribute("aria-valuenow", next.toFixed(0));
      if (split.dataset.splitKey) storeSplit(split.dataset.splitKey, next);
      return;
    }
    const detailsSplitter = keyTarget?.closest?.<HTMLElement>("[data-details-splitter]");
    if (detailsSplitter) {
      if (event.key !== "ArrowUp" && event.key !== "ArrowDown" && event.key !== "Home" && event.key !== "End") return;
      const main = detailsSplitter.closest<HTMLElement>(".cp-main");
      if (!main) return;
      event.preventDefault();
      const current = Number.parseFloat(main.style.getPropertyValue("--cp-split-primary")) || DEFAULT_DETAILS_SPLIT;
      const next = event.key === "Home"
        ? DEFAULT_DETAILS_SPLIT
        : event.key === "End"
          ? MAX_DETAILS_SPLIT
          : Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, current + (event.key === "ArrowDown" ? 2 : -2)));
      main.style.setProperty("--cp-split-primary", `${next}%`);
      main.style.setProperty("--cp-split-details", `${next}%`);
      detailsSplitter.setAttribute("aria-valuenow", next.toFixed(0));
      if (detailsSplitter.dataset.splitKey) storeSplit(detailsSplitter.dataset.splitKey, next);
    }
  });
  container.addEventListener("change", (event) => {
    const element = event.target && typeof (event.target as { closest?: unknown }).closest === "function"
      ? event.target as HTMLElement
      : null;
    if (!element) return;
    if (Object.prototype.hasOwnProperty.call(element.dataset, "projectDomainFilter")) {
      const value = (element as HTMLSelectElement).value;
      projectRegisterStateFor(container).domain = value || PROJECT_DOMAIN_FILTER_ALL;
      refreshProjectRegister(container);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "projectStatusFilter")) {
      const value = (element as HTMLSelectElement).value;
      projectRegisterStateFor(container).status = value || PROJECT_STATUS_FILTER_ALL;
      refreshProjectRegister(container);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "projectSort")) {
      const value = (element as HTMLSelectElement).value;
      if (value !== "name" && value !== "start_date" && value !== "status") return;
      projectRegisterStateFor(container).sort = value;
      refreshProjectRegister(container);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "topLayout")) {
      const value = (element as HTMLSelectElement).value;
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      if (value !== "table-only" && value !== "table-gantt" && value !== "activity-network") return;
      if (!isWorkspaceTopLayoutAvailable(value, record.state)) return;
      storeWorkspaceTopLayout(record.state, value);
      // Presentation-only switch: the workspace state, revision and schedule
      // result are untouched. A full render swaps the primary view and closes
      // the options dialog while the details pane and selection survive.
      renderMainWorkspace(container, record.state, record.options);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "bottomLayout")) {
      const value = (element as HTMLSelectElement).value;
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      if (value !== "details" && value !== "trace-logic" && value !== "usage-profile" && value !== "usage-spreadsheet" && value !== "none") return;
      if (value === "trace-logic" && !isWorkspaceTraceLogicAvailable(record.state)) return;
      if (!isWorkspaceUsageAvailable(value, record.options.activityUsage)) return;
      storeWorkspaceBottomLayout(record.state, value);
      // Presentation-only switch, same contract as the top layout: the
      // selection, filters and splits survive because only the bottom surface
      // is re-rendered.
      renderBottomSurface(container, record.state, record.options);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "traceDepth")) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const direction = element.dataset.traceDepth;
      if (direction !== "predecessors" && direction !== "successors") return;
      // Bottom Layout Options sets the predecessor and successor levels
      // independently; both persist as one local preference pair.
      const depth = Number.parseInt((element as HTMLSelectElement).value, 10);
      storeTraceLogicDepths({ ...readTraceLogicDepths(), [direction]: depth });
      renderBottomSurface(container, record.state, record.options);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "usageMetric")) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value;
      if (value !== "units" && value !== "cost") return;
      try {
        storeActivityUsagePrefs(window.localStorage, record.state.context, { ...usagePrefs(record.state), metric: value });
      } catch {
        // Presentation-only preference; the choice still applies to this render.
      }
      renderBottomSurface(container, record.state, record.options);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "usageScope")) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value;
      if (value !== "all" && value !== "selected") return;
      try {
        storeActivityUsagePrefs(window.localStorage, record.state.context, { ...usagePrefs(record.state), scope: value });
      } catch {
        // Presentation-only preference; the choice still applies to this render.
      }
      renderBottomSurface(container, record.state, record.options);
      return;
    }
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
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutBaseline")) {
      workspaceRenderRecords.get(container)?.options.onGanttDisplayToggle?.("baseline", (element as HTMLInputElement).checked);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutProgressLine")) {
      workspaceRenderRecords.get(container)?.options.onGanttDisplayToggle?.("progress-line", (element as HTMLInputElement).checked);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(element.dataset, "layoutDataDateLine")) {
      workspaceRenderRecords.get(container)?.options.onGanttDisplayToggle?.("data-date-line", (element as HTMLInputElement).checked);
      return;
    }
    const isGroupSelect = Object.prototype.hasOwnProperty.call(element.dataset, "activityGroup");
    if (isGroupSelect) {
      const record = workspaceRenderRecords.get(container);
      if (!record) return;
      const value = (element as HTMLSelectElement).value;
      const direction = record.state.activityGroupLevels[0]?.direction ?? "asc";
      // The toolbar is the single-level shortcut; the Group and Sort dialog
      // owns multi-level plans and persists them with the layout.
      if (value === "none") record.options.onActivityGroupLevelsChange?.([]);
      else if (value === "wbs") record.options.onActivityGroupLevelsChange?.([{ fieldId: "wbs", direction }]);
      else if (isWorkspaceGroupFieldId(value)) record.options.onActivityGroupLevelsChange?.([{ fieldId: value, direction }]);
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

export type WorkspaceContextKind =
  | "table-activity"
  | "table-header"
  | "table-empty"
  | "table-wbs"
  | "gantt-activity"
  | "gantt-link"
  | "gantt-wbs"
  | "gantt-empty"
  | "gantt-timescale"
  | "network-activity"
  | "network-link";

export type WorkspaceContextTarget = {
  kind: WorkspaceContextKind;
  anchor: HTMLElement;
  activityId?: string;
  wbsId?: string;
  relationshipId?: string;
  columnId?: string;
};

/** Classify the object under the pointer. Each Gantt object owns its menu. */
function workspaceContextAt(target: HTMLElement): WorkspaceContextTarget | null {
  const closest = <T extends Element>(selector: string): T | null => {
    try {
      return target.closest<T>(selector);
    } catch {
      return null;
    }
  };
  const network = closest<HTMLElement>("[data-network-view]");
  if (network) {
    const edge = closest<SVGGraphicsElement>("[data-network-relationship-id]");
    const relationshipId = edge?.getAttribute("data-network-relationship-id") ?? "";
    if (relationshipId) {
      return { kind: "network-link", relationshipId, anchor: edge as unknown as HTMLElement };
    }
    const node = closest<HTMLElement>("[data-network-view] [data-gantt-activity-id]");
    const activityId = node?.dataset.ganttActivityId ?? "";
    if (activityId) return { kind: "network-activity", activityId, anchor: node as HTMLElement };
    return null;
  }
  const link = closest<SVGPathElement>("[data-gantt-link],[data-gantt-link-hit]");
  const relationshipId = link?.dataset.ganttLink ?? link?.dataset.ganttLinkHit;
  if (relationshipId) {
    // Focus restore needs a focusable owner. A relationship belongs to the
    // successor row, so Escape returns to that row (falling back to the chart)
    // rather than to an SVG path that cannot take focus.
    const successorId = link?.getAttribute("data-link-to") ?? "";
    const rows = successorId && target.ownerDocument
      ? Array.from(target.ownerDocument.querySelectorAll<HTMLElement>("#cp-gantt [data-gantt-activity-id]"))
      : [];
    const successor = rows.find((row) => row.getAttribute("data-gantt-activity-id") === successorId) ?? null;
    const chart = closest<HTMLElement>("#cp-gantt");
    return { kind: "gantt-link", relationshipId, anchor: successor ?? chart ?? (link as unknown as HTMLElement) };
  }
  const header = closest<HTMLElement>("#cp-activity-grid thead th");
  if (header) {
    return { kind: "table-header", columnId: header.dataset.columnId ?? "", anchor: header };
  }
  const activityRow = closest<HTMLElement>("#cp-activity-grid tbody tr[data-activity-id]");
  if (activityRow?.dataset.activityId) {
    return { kind: "table-activity", activityId: activityRow.dataset.activityId, anchor: activityRow };
  }
  const tableWbs = closest<HTMLElement>("#cp-activity-grid tr[data-wbs-row]");
  if (tableWbs?.dataset.wbsRow) {
    return { kind: "table-wbs", wbsId: tableWbs.dataset.wbsRow, anchor: tableWbs };
  }
  const ganttRow = closest<HTMLElement>("#cp-gantt [data-gantt-activity-id]");
  if (ganttRow) {
    const activityId = ganttRow.dataset.ganttActivityId;
    if (activityId) return { kind: "gantt-activity", activityId, anchor: ganttRow };
  }
  if (closest("#cp-gantt")) {
    const summary = closest<HTMLElement>("[data-gantt-summary]");
    const group = closest<HTMLElement>(".cp-gantt-group-row[data-gantt-wbs-id]");
    // The group row carries the focusable identity; the summary bar inside it
    // is decorative, so anchor to the row when the pointer lands on the bar.
    const wbsTarget = group ?? summary;
    if (wbsTarget) {
      const wbsId = wbsTarget.getAttribute("data-gantt-wbs-id")
        ?? wbsTarget.closest<HTMLElement>("[data-gantt-wbs-id]")?.getAttribute("data-gantt-wbs-id")
        ?? "";
      if (wbsId) return { kind: "gantt-wbs", wbsId, anchor: wbsTarget };
    }
  }
  const axis = closest<HTMLElement>("#cp-gantt .cp-gantt-axis");
  if (axis) return { kind: "gantt-timescale", anchor: axis };
  const gantt = closest<HTMLElement>("#cp-gantt");
  if (gantt) return { kind: "gantt-empty", anchor: gantt };
  const grid = closest<HTMLElement>("#cp-activity-grid");
  if (grid) return { kind: "table-empty", anchor: grid };
  return null;
}

type ContextItemOptions = {
  shortcut?: string;
  disabled?: boolean;
  reason?: { en: string; fa: string };
  checked?: boolean;
  separator?: boolean;
};

function contextItem(
  state: WorkspaceState,
  command: string,
  label: { en: string; fa: string },
  icon: WorkspaceIconName,
  options: ContextItemOptions = {},
): ContextMenuItem {
  return {
    command,
    label: uiText(state.locale, label.en, label.fa),
    icon,
    shortcut: options.shortcut,
    disabled: options.disabled,
    reason: options.reason ? uiText(state.locale, options.reason.en, options.reason.fa) : undefined,
    checked: options.checked,
    separatorBefore: options.separator,
  };
}

function activityMenuItems(
  state: WorkspaceState,
  activityId: string | undefined,
  gantt: boolean,
  lineNumbers: boolean,
): ContextMenuItem[] {
  const hasActivity = Boolean(activityId);
  const hasWbsGroups = state.activityGroupBy === "wbs" && state.wbsNodes.length > 0;
  const wbsActions: ContextMenuItem[] = [
    contextItem(state, "expand-all", ACTIVITY_CONTEXT_LABELS.expandAll, "expand", { shortcut: "Ctrl+Num +", disabled: !hasWbsGroups, separator: true }),
    contextItem(state, "collapse-all", ACTIVITY_CONTEXT_LABELS.collapseAll, "collapse", { shortcut: "Ctrl+Num -", disabled: !hasWbsGroups }),
    contextItem(state, "collapse-to", ACTIVITY_CONTEXT_LABELS.collapseTo, "collapseTo", { disabled: !hasWbsGroups }),
  ];
  if (gantt) {
    return [
      contextItem(state, "details", ACTIVITY_CONTEXT_LABELS.details, "activity", { disabled: !hasActivity }),
      contextItem(state, "add", ACTIVITY_CONTEXT_LABELS.add, "plus", { shortcut: "Ins", disabled: !state.wbsNodes.length, separator: true }),
      contextItem(state, "link", ACTIVITY_CONTEXT_LABELS.link, "link", { disabled: !hasActivity }),
      contextItem(state, "bars", { en: "Bar Styles…", fa: "سبک میله‌ها…" }, "bars", { separator: true }),
      contextItem(state, "font-row", ACTIVITY_CONTEXT_LABELS.fontRow, "font"),
      contextItem(state, "filters", ACTIVITY_CONTEXT_LABELS.filters, "filter", { separator: true }),
      contextItem(state, "group-sort", ACTIVITY_CONTEXT_LABELS.groupSort, "group"),
      contextItem(state, "relationships", { en: "Show Relationships", fa: "نمایش روابط" }, "link", { checked: state.showGanttRelationships, separator: true }),
      ...wbsActions,
    ];
  }
  return [
    contextItem(state, "details", ACTIVITY_CONTEXT_LABELS.details, "activity", { disabled: !hasActivity }),
    contextItem(state, "cut", ACTIVITY_CONTEXT_LABELS.cut, "cut", { shortcut: "Ctrl+X", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.cut, separator: true }),
    contextItem(state, "copy", ACTIVITY_CONTEXT_LABELS.copy, "copy", { shortcut: "Ctrl+C", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.copy }),
    contextItem(state, "paste", ACTIVITY_CONTEXT_LABELS.paste, "paste", { shortcut: "Ctrl+V", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.paste }),
    contextItem(state, "fill-down", ACTIVITY_CONTEXT_LABELS.fillDown, "fill", { shortcut: "Ctrl+E", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.fillDown }),
    contextItem(state, "add", ACTIVITY_CONTEXT_LABELS.add, "plus", { shortcut: "Ins", disabled: !state.wbsNodes.length }),
    contextItem(state, "delete", ACTIVITY_CONTEXT_LABELS.delete, "delete", { shortcut: "Del", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.delete }),
    contextItem(state, "dissolve", ACTIVITY_CONTEXT_LABELS.dissolve, "dissolve", { disabled: true, reason: ACTIVITY_CONTEXT_REASONS.dissolve }),
    contextItem(state, "renumber", ACTIVITY_CONTEXT_LABELS.renumber, "renumber", { disabled: true, reason: ACTIVITY_CONTEXT_REASONS.renumber }),
    contextItem(state, "export-excel", ACTIVITY_CONTEXT_LABELS.exportExcel, "excel", { disabled: true, reason: ACTIVITY_CONTEXT_REASONS.exportExcel }),
    contextItem(state, "assign", ACTIVITY_CONTEXT_LABELS.assign, "assignment", { disabled: true, reason: ACTIVITY_CONTEXT_REASONS.assign }),
    contextItem(state, "link", ACTIVITY_CONTEXT_LABELS.link, "link", { disabled: !hasActivity }),
    contextItem(state, "columns", ACTIVITY_CONTEXT_LABELS.columns, "columns", { disabled: !hasActivity, separator: true }),
    contextItem(state, "line-numbers", ACTIVITY_CONTEXT_LABELS.lineNumbers, "lineNumbers", { checked: lineNumbers }),
    contextItem(state, "font-row", ACTIVITY_CONTEXT_LABELS.fontRow, "font", { disabled: !hasActivity }),
    contextItem(state, "filters", ACTIVITY_CONTEXT_LABELS.filters, "filter", { separator: true }),
    contextItem(state, "group-sort", ACTIVITY_CONTEXT_LABELS.groupSort, "group"),
    ...wbsActions,
  ];
}

function headerMenuItems(state: WorkspaceState, columnId: string, lineNumbers: boolean): ContextMenuItem[] {
  const sort = state.activitySort;
  const isColumn = Boolean(columnId);
  const ascending = isColumn && sort?.columnId === columnId && (sort?.direction ?? "asc") === "asc";
  const descending = isColumn && sort?.columnId === columnId && sort?.direction === "desc";
  const layoutColumn = state.p6Layout?.columns.some((entry) => entry.field_id === columnId) ?? false;
  const canHide = layoutColumn && state.columns.length > 1;
  return [
    contextItem(state, "columns", ACTIVITY_CONTEXT_LABELS.columns, "columns"),
    contextItem(state, "sort-asc", { en: "Sort Ascending", fa: "ترتیب صعودی" }, "sort", { disabled: !isColumn, checked: ascending, separator: true }),
    contextItem(state, "sort-desc", { en: "Sort Descending", fa: "ترتیب نزولی" }, "sort", { disabled: !isColumn, checked: descending }),
    contextItem(state, "hide-column", { en: "Hide Column", fa: "پنهان کردن ستون" }, "close", {
      disabled: !canHide,
      reason: layoutColumn
        ? { en: "At least one column must stay visible.", fa: "دست‌کم یک ستون باید نمایان بماند." }
        : { en: "This column is not part of the persisted layout.", fa: "این ستون بخشی از چیدمان ذخیره‌شده نیست." },
    }),
    contextItem(state, "line-numbers", ACTIVITY_CONTEXT_LABELS.lineNumbers, "lineNumbers", { checked: lineNumbers, separator: true }),
    contextItem(state, "font-row", ACTIVITY_CONTEXT_LABELS.fontRow, "font"),
    contextItem(state, "reset-column-widths", { en: "Reset Column Widths", fa: "بازنشانی عرض ستون‌ها" }, "columns"),
    contextItem(state, "filters", ACTIVITY_CONTEXT_LABELS.filters, "filter", { separator: true }),
    contextItem(state, "group-sort", ACTIVITY_CONTEXT_LABELS.groupSort, "group"),
  ];
}

function tableEmptyMenuItems(state: WorkspaceState, lineNumbers: boolean): ContextMenuItem[] {
  const hasWbsGroups = state.activityGroupBy === "wbs" && state.wbsNodes.length > 0;
  return [
    contextItem(state, "add", ACTIVITY_CONTEXT_LABELS.add, "plus", { disabled: !state.wbsNodes.length }),
    contextItem(state, "paste", ACTIVITY_CONTEXT_LABELS.paste, "paste", { shortcut: "Ctrl+V", disabled: true, reason: ACTIVITY_CONTEXT_REASONS.paste }),
    contextItem(state, "columns", ACTIVITY_CONTEXT_LABELS.columns, "columns", { separator: true }),
    contextItem(state, "line-numbers", ACTIVITY_CONTEXT_LABELS.lineNumbers, "lineNumbers", { checked: lineNumbers }),
    contextItem(state, "font-row", ACTIVITY_CONTEXT_LABELS.fontRow, "font"),
    contextItem(state, "filters", ACTIVITY_CONTEXT_LABELS.filters, "filter", { separator: true }),
    contextItem(state, "group-sort", ACTIVITY_CONTEXT_LABELS.groupSort, "group"),
    contextItem(state, "expand-all", ACTIVITY_CONTEXT_LABELS.expandAll, "expand", { disabled: !hasWbsGroups, separator: true }),
    contextItem(state, "collapse-all", ACTIVITY_CONTEXT_LABELS.collapseAll, "collapse", { disabled: !hasWbsGroups }),
    contextItem(state, "collapse-to", ACTIVITY_CONTEXT_LABELS.collapseTo, "collapseTo", { disabled: !hasWbsGroups }),
    contextItem(state, "layout-options", { en: "Layout Options…", fa: "گزینه‌های چیدمان…" }, "settings", { separator: true }),
    contextItem(state, "reset-table-split", { en: "Reset Table Split", fa: "بازنشانی تقسیم جدول" }, "table"),
    contextItem(state, "reset-details-split", { en: "Reset Details Split", fa: "بازنشانی تقسیم جزئیات" }, "table"),
    contextItem(state, "reset-column-widths", { en: "Reset Column Widths", fa: "بازنشانی عرض ستون‌ها" }, "columns"),
  ];
}

function wbsMenuItems(state: WorkspaceState, wbsId: string | undefined, collapsed: boolean): ContextMenuItem[] {
  return [
    contextItem(state, collapsed ? "expand-wbs" : "collapse-wbs", collapsed
      ? { en: "Expand This Branch", fa: "بازکردن این شاخه" }
      : { en: "Collapse This Branch", fa: "بستن این شاخه" }, collapsed ? "expand" : "collapse", { disabled: !wbsId }),
    contextItem(state, "collapse-to", ACTIVITY_CONTEXT_LABELS.collapseTo, "collapseTo", { disabled: !state.wbsNodes.length }),
    contextItem(state, "wbs-add-activity", { en: "Add Activity in This WBS", fa: "افزودن فعالیت در این ساختار شکست" }, "plus", { disabled: !wbsId || !state.wbsNodes.length, separator: true }),
    contextItem(state, "wbs-details", { en: "WBS Details", fa: "جزئیات ساختار شکست" }, "wbs", { disabled: !wbsId }),
    contextItem(state, "group-wbs", { en: "Group by WBS", fa: "گروه‌بندی بر اساس ساختار شکست" }, "group", { checked: state.activityGroupBy === "wbs", separator: true }),
    contextItem(state, "layout-options", { en: "Layout Options…", fa: "گزینه‌های چیدمان…" }, "settings", { separator: true }),
  ];
}

function ganttScaleItems(state: WorkspaceState): ContextMenuItem[] {
  const labels: Record<WorkspaceGanttScale, { en: string; fa: string }> = {
    day: { en: "Day", fa: "روز" },
    week: { en: "Week", fa: "هفته" },
    month: { en: "Month", fa: "ماه" },
    quarter: { en: "Quarter", fa: "فصل" },
    year: { en: "Year", fa: "سال" },
  };
  return (["day", "week", "month", "quarter", "year"] as const).map((mode, index) =>
    contextItem(state, `scale-${mode}`, labels[mode], "calendar", {
      checked: state.ganttScale === mode,
      separator: index === 0,
    }));
}

function ganttEmptyMenuItems(state: WorkspaceState): ContextMenuItem[] {
  return [
    ...ganttScaleItems(state),
    contextItem(state, "layout-options", { en: "Timescale…", fa: "مقیاس زمانی…" }, "calendar", { separator: true }),
    contextItem(state, "bars", { en: "Bar Styles…", fa: "سبک میله‌ها…" }, "bars"),
    contextItem(state, "font-row", ACTIVITY_CONTEXT_LABELS.fontRow, "font"),
    contextItem(state, "user-preferences", { en: "User Preferences…", fa: "ترجیحات کاربر…" }, "settings"),
    contextItem(state, "relationships", { en: "Show Relationships", fa: "نمایش روابط" }, "link", { checked: state.showGanttRelationships, separator: true }),
    contextItem(state, "reset-table-split", { en: "Reset Table Split", fa: "بازنشانی تقسیم جدول" }, "table", { separator: true }),
    contextItem(state, "reset-details-split", { en: "Reset Details Split", fa: "بازنشانی تقسیم جزئیات" }, "table"),
    contextItem(state, "reset-column-widths", { en: "Reset Column Widths", fa: "بازنشانی عرض ستون‌ها" }, "columns"),
  ];
}

function ganttTimescaleMenuItems(state: WorkspaceState): ContextMenuItem[] {
  return [
    contextItem(state, "layout-options", { en: "Timescale…", fa: "مقیاس زمانی…" }, "calendar"),
    ...ganttScaleItems(state),
    contextItem(state, "relationships", { en: "Show Relationships", fa: "نمایش روابط" }, "link", { checked: state.showGanttRelationships, separator: true }),
  ];
}

function ganttLinkMenuItems(state: WorkspaceState, relationshipId: string | undefined): ContextMenuItem[] {
  const relationship = state.relationships.find((entry) => entry.id === relationshipId);
  return [
    contextItem(state, "relationship-edit", { en: "Edit Relationship…", fa: "ویرایش رابطه…" }, "edit", { disabled: !relationship }),
    contextItem(state, "relationship-delete", { en: "Delete Relationship", fa: "حذف رابطه" }, "delete", {
      disabled: !relationship,
      reason: { en: "The relationship was not found in the current schedule.", fa: "رابطه در زمان‌بندی جاری یافت نشد." },
    }),
    contextItem(state, "relationship-predecessor", { en: "Go to Predecessor", fa: "رفتن به پیش‌نیاز" }, "activity", { disabled: !relationship, separator: true }),
    contextItem(state, "relationship-successor", { en: "Go to Successor", fa: "رفتن به پس‌نیاز" }, "activity", { disabled: !relationship }),
  ];
}

export function workspaceMenuItems(record: WorkspaceRenderRecord, context: WorkspaceContextTarget): ContextMenuItem[] {
  const { state } = record;
  const lineNumbers = (record.options.presentation ?? DEFAULT_PRESENTATION).table.lineNumbers;
  switch (context.kind) {
    case "table-activity": return activityMenuItems(state, context.activityId, false, lineNumbers);
    case "table-header": return headerMenuItems(state, context.columnId ?? "", lineNumbers);
    case "table-empty": return tableEmptyMenuItems(state, lineNumbers);
    case "table-wbs": {
      const collapsed = getCollapsedWbsIds(state.context.project_id).has(context.wbsId ?? "");
      return wbsMenuItems(state, context.wbsId, collapsed);
    }
    case "gantt-activity": return activityMenuItems(state, context.activityId, true, lineNumbers);
    case "gantt-link": return ganttLinkMenuItems(state, context.relationshipId);
    case "network-activity": return activityMenuItems(state, context.activityId, true, lineNumbers);
    case "network-link": return ganttLinkMenuItems(state, context.relationshipId);
    case "gantt-wbs": {
      const collapsed = getCollapsedWbsIds(state.context.project_id).has(context.wbsId ?? "");
      return wbsMenuItems(state, context.wbsId, collapsed);
    }
    case "gantt-timescale": return ganttTimescaleMenuItems(state);
    case "gantt-empty": return ganttEmptyMenuItems(state);
  }
}

const CONTEXT_MENU_LABELS: Record<WorkspaceContextKind, { en: string; fa: string }> = {
  "table-activity": { en: "Activity", fa: "فعالیت" },
  "table-header": { en: "Column", fa: "ستون" },
  "table-empty": { en: "Activity Table", fa: "جدول فعالیت‌ها" },
  "table-wbs": { en: "WBS Element", fa: "عنصر ساختار شکست" },
  "gantt-activity": { en: "Gantt Activity", fa: "فعالیت گانت" },
  "gantt-link": { en: "Relationship", fa: "رابطه" },
  "gantt-wbs": { en: "Gantt WBS Summary", fa: "خلاصهٔ ساختار شکست در گانت" },
  "gantt-empty": { en: "Gantt Chart", fa: "نمودار گانت" },
  "gantt-timescale": { en: "Timescale", fa: "مقیاس زمانی" },
  "network-activity": { en: "Network Activity", fa: "فعالیت شبکه" },
  "network-link": { en: "Relationship", fa: "رابطه" },
};

function openWorkspaceContextMenu(
  container: HTMLElement,
  context: WorkspaceContextTarget,
  x: number,
  y: number,
  anchor: HTMLElement | null,
  focusFirst = true,
): void {
  const record = workspaceRenderRecords.get(container);
  if (!record) return;
  const items = workspaceMenuItems(record, context);
  if (!items.length) return;
  const label = CONTEXT_MENU_LABELS[context.kind];
  openContextMenu({
    x,
    y,
    anchor,
    focusFirst,
    kind: context.kind,
    label: uiText(record.state.locale, label.en, label.fa),
    direction: record.state.direction === "rtl" ? "rtl" : "ltr",
    items,
    onCommand: (command) => runWorkspaceMenuCommand(container, context, command),
  });
}

function openRelationshipEditor(container: HTMLElement, relationshipId: string): void {
  openToolsDrawer(container);
  const escaped = relationshipId.replace(/["\\]/g, "\\$&");
  const box = container.querySelector<HTMLDetailsElement>(`[data-relationship-edit-box="${escaped}"]`);
  if (!box) return;
  box.open = true;
  if (typeof box.scrollIntoView === "function") box.scrollIntoView({ block: "center" });
  box.querySelector<HTMLElement>("select, input, button")?.focus({ preventScroll: true });
}

function runWorkspaceMenuCommand(
  container: HTMLElement,
  context: WorkspaceContextTarget,
  command: string,
): void {
  const record = workspaceRenderRecords.get(container);
  if (!record) return;
  const { state, options } = record;
  const projectId = state.context.project_id;
  const activityId = context.activityId ?? state.selectedActivityId ?? "";
  const wbsId = context.wbsId ?? "";
  const relationship = context.relationshipId
    ? state.relationships.find((entry) => entry.id === context.relationshipId)
    : undefined;
  switch (command) {
    case "details":
    case "add":
    case "link":
    case "columns":
    case "line-numbers":
    case "font-row":
    case "group-sort":
      options.onActivityContextCommand?.(command, activityId);
      return;
    case "filters":
      container.querySelector<HTMLInputElement>("[data-activity-filter]")?.focus();
      return;
    case "expand-all":
      setCollapsedWbsIds(projectId, []);
      rerenderWorkspaceRows(container);
      return;
    case "collapse-all":
      setCollapsedWbsIds(projectId, collapseAllWbsIds(state.activities, state.wbsNodes));
      rerenderWorkspaceRows(container);
      return;
    case "collapse-to": {
      const dialog = container.querySelector<HTMLDialogElement>("[data-collapse-to-dialog]");
      const select = dialog?.querySelector<HTMLSelectElement>("[data-collapse-to-select]");
      if (select && wbsId && state.wbsNodes.some((node) => node.id === wbsId)) select.value = wbsId;
      if (dialog && typeof dialog.showModal === "function") dialog.showModal();
      else dialog?.setAttribute("open", "");
      return;
    }
    case "expand-wbs":
    case "collapse-wbs":
      if (wbsId) {
        toggleCollapsedWbs(projectId, wbsId);
        rerenderWorkspaceRows(container);
      }
      return;
    case "wbs-add-activity":
      openActivityCreateForWbs(container, wbsId || null);
      return;
    case "wbs-details":
      if (wbsId) {
        options.onWbsSelect?.(wbsId);
        openWbsDrawer(container);
      }
      return;
    case "group-wbs":
      options.onActivityGroupByChange?.("wbs");
      return;
    case "bars":
      options.onGanttCommand?.("bars");
      return;
    case "user-preferences":
      options.onGanttCommand?.("user-preferences");
      return;
    case "relationships":
      options.onGanttRelationshipsChange?.(!state.showGanttRelationships);
      return;
    case "layout-options":
      openLayoutOptionsDialog(container);
      return;
    case "reset-table-split":
      resetTableSplit(container);
      return;
    case "reset-details-split":
      resetDetailsSplit(container);
      return;
    case "reset-column-widths":
      resetColumnWidths(container);
      return;
    case "sort-asc":
    case "sort-desc":
      if (context.columnId) options.onActivitySortSet?.(context.columnId, command === "sort-asc" ? "asc" : "desc");
      return;
    case "hide-column":
      if (context.columnId) options.onP6FieldVisibilityChange?.(context.columnId, false);
      return;
    case "relationship-edit":
      if (relationship) openRelationshipEditor(container, relationship.id);
      return;
    case "relationship-delete": {
      if (!relationship || !options.onRelationshipDelete) return;
      const message = uiText(state.locale, "Delete this relationship?", "این رابطه حذف شود؟");
      if (typeof window.confirm === "function" && !window.confirm(message)) return;
      void options.onRelationshipDelete(relationship.id, relationship.recordRevision);
      return;
    }
    case "relationship-predecessor":
      if (relationship) options.onActivitySelect?.(relationship.predecessorId);
      return;
    case "relationship-successor":
      if (relationship) options.onActivitySelect?.(relationship.successorId);
      return;
    default:
      if (command.startsWith("scale-")) {
        const mode = command.slice("scale-".length);
        if (mode === "day" || mode === "week" || mode === "month" || mode === "quarter" || mode === "year") {
          options.onGanttScaleChange?.(mode);
        }
      }
  }
}

function renderWbsTable(
  nodes: WorkspaceState["wbsNodes"],
  activities: WorkspaceState["activities"],
  selectedWbsId: string | null,
  locale: WorkspaceState["locale"],
  labels: WorkspaceLabels,
): string {
  if (!nodes.length) return `<div class="cp-empty">${escapeHtml(labels.noWbs)}</div>`;
  const rows = buildWbsHierarchy(nodes);
  const counts = wbsActivityCounts(activities);
  const indent = (depth: number): string => `style="padding-inline-start:${(depth - 1) * 18}px"`;
  const body = rows.map(({ node, depth, orphan }) => {
    const selected = selectedWbsId === node.id;
    const activityCount = counts.get(node.id) ?? 0;
    return `<tr class="cp-wbs-row${selected ? " is-selected" : ""}${orphan ? " is-orphan" : ""}" data-wbs-id="${escapeAttribute(node.id)}" data-wbs-depth="${depth}" aria-level="${depth}" aria-selected="${selected}">
      <td class="cp-wbs-code-cell"><span class="cp-wbs-indent" ${indent(depth)}>${escapeHtml(node.localCode)}</span></td>
      <td class="cp-wbs-name-cell"><button type="button" class="cp-wbs-node${selected ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(node.id)}" aria-current="${selected ? "true" : "false"}">${escapeHtml(node.name)}</button>${orphan ? `<small class="cp-wbs-orphan-note">${escapeHtml(uiText(locale, "Parent not loaded", "والد بارگذاری نشده"))}</small>` : ""}</td>
      <td class="cp-wbs-count-cell">${activityCount}</td>
      <td class="cp-wbs-sequence-cell">${node.sequenceNumber}</td>
      <td class="cp-wbs-revision-cell">R${node.recordRevision}</td>
    </tr>`;
  }).join("");
  return `<div class="cp-wbs-table-wrap"><table class="cp-wbs-table" data-wbs-table role="treegrid" aria-label="${escapeAttribute(labels.wbs)}">
    <thead><tr>
      <th scope="col">${escapeHtml(uiText(locale, "WBS Code", "کد WBS"))}</th>
      <th scope="col">${escapeHtml(uiText(locale, "WBS Name", "نام WBS"))}</th>
      <th scope="col">${escapeHtml(uiText(locale, "Activities", "فعالیت‌ها"))}</th>
      <th scope="col">${escapeHtml(uiText(locale, "Sequence", "ترتیب"))}</th>
      <th scope="col">${escapeHtml(uiText(locale, "Rev", "ویرایش"))}</th>
    </tr></thead>
    <tbody>${body}</tbody>
  </table></div>`;
}

function renderWbsChart(
  nodes: WorkspaceState["wbsNodes"],
  selectedWbsId: string | null,
  locale: WorkspaceState["locale"],
  labels: WorkspaceLabels,
): string {
  if (!nodes.length) return `<div class="cp-empty">${escapeHtml(labels.noWbs)}</div>`;
  const rows = buildWbsHierarchy(nodes);
  const cards = rows.map(({ node, depth, hasChildren, orphan }) => {
    const selected = selectedWbsId === node.id;
    return `<li class="cp-wbs-chart-item" role="treeitem" aria-level="${depth}" aria-selected="${selected}"${hasChildren ? ' aria-expanded="true"' : ""}>
      <button type="button" class="cp-wbs-chart-node${selected ? " is-selected" : ""}${orphan ? " is-orphan" : ""}" data-wbs-id="${escapeAttribute(node.id)}" data-wbs-depth="${depth}" aria-current="${selected ? "true" : "false"}" style="margin-inline-start:${(depth - 1) * 22}px">
        <span class="cp-wbs-chart-code">${escapeHtml(node.localCode)}</span>
        <strong>${escapeHtml(node.name)}</strong>
        <small>R${node.recordRevision} · #${node.sequenceNumber}</small>
      </button>
    </li>`;
  }).join("");
  return `<div class="cp-wbs-chart" data-wbs-chart><ul class="cp-wbs-chart-list" role="tree" aria-label="${escapeAttribute(uiText(locale, "WBS chart", "نمودار WBS"))}">${cards}</ul></div>`;
}

function canIncrementallyUpdate(previous: WorkspaceState, next: WorkspaceState): boolean {
  return previous.context === next.context && previous.locale === next.locale && previous.direction === next.direction && previous.calendarMode === next.calendarMode && previous.ganttScale === next.ganttScale && previous.showGanttRelationships === next.showGanttRelationships && previous.visiblePanels === next.visiblePanels && previous.columns === next.columns && previous.activities === next.activities && previous.wbsNodes === next.wbsNodes && previous.relationships === next.relationships && previous.activityFilter === next.activityFilter && previous.activityGroupBy === next.activityGroupBy && previous.activityGroupLevels === next.activityGroupLevels && previous.activitySort === next.activitySort && previous.activitySortLevels === next.activitySortLevels && previous.controlSummary === next.controlSummary && previous.smartGuide === next.smartGuide && previous.siteDailyLogs === next.siteDailyLogs && previous.timecards === next.timecards && previous.equipmentReports === next.equipmentReports && previous.fieldIssues === next.fieldIssues && previous.changeNotices === next.changeNotices && previous.changeCases === next.changeCases && previous.claims === next.claims && previous.changeClaimImpacts === next.changeClaimImpacts && previous.documents === next.documents && previous.procurementRecords === next.procurementRecords && previous.inspections === next.inspections && previous.qualityRecords === next.qualityRecords && previous.safetyObservations === next.safetyObservations && previous.punchItems === next.punchItems && previous.p6FieldRegistry === next.p6FieldRegistry && previous.p6Layout === next.p6Layout;
}

function usagePrefs(state: WorkspaceState) {
  try {
    return readActivityUsagePrefs(window.localStorage, state.context);
  } catch {
    return { ...ACTIVITY_USAGE_DEFAULT_PREFS };
  }
}

function bottomLayoutHeading(layout: WorkspaceBottomLayout): string {
  if (layout === "trace-logic") return "cp-trace-heading";
  if (layout === "usage-profile" || layout === "usage-spreadsheet") return "cp-usage-heading";
  return "cp-details-heading";
}

/**
 * Content of the bottom pane for the current window. The Activities window can
 * swap the Activity Details for Trace Logic, the Activity Usage views, or hide
 * the pane entirely; every other window keeps its own details panel.
 */
function renderBottomPaneContent(state: WorkspaceState, t: WorkspaceLabels, container: HTMLElement, options: WorkspaceRendererOptions = {}): string {
  // The Roles window renders its own detail tabs, so the shared pane stays
  // empty instead of carrying the generic "detail tabs are not implemented"
  // fallback, which would be false for this window even while hidden.
  if (state.activeMenu === "roles" || state.activeMenu === "calendars") return "";
  const layout: WorkspaceBottomLayout = state.activeMenu === "schedule" ? readWorkspaceBottomLayout(state, options.activityUsage) : "details";
  if (layout === "trace-logic") {
    return renderTraceLogic(state.activities, state.relationships, state.locale, state.selectedActivityId, readTraceLogicDepths());
  }
  if (layout === "usage-profile" || layout === "usage-spreadsheet") {
    return renderActivityUsage({
      view: layout === "usage-profile" ? "profile" : "spreadsheet",
      source: options.activityUsage ?? { status: "loading", errorCode: null, periods: [] },
      activities: state.activities.map((activity) => ({ id: activity.id, code: activity.code, name: activity.name })),
      selectedIds: selectedActivityIdList(state),
      locale: state.locale,
      prefs: usagePrefs(state),
    });
  }
  return renderWindowDetailsPanel(state, t, container, options);
}

/**
 * Whether the shared bottom pane should occupy layout space. The Roles window
 * owns its own General / Resources / Units & Prices detail tabs inside the
 * window, and the shared surface has no role reader, so it would only repeat
 * facts or claim those tabs do not exist. The initial render, the layout-only
 * re-render and the incremental window switch all call this helper so they
 * cannot disagree and resurrect the pane after a menu change.
 */
function bottomDetailsVisible(state: WorkspaceState, layout: WorkspaceBottomLayout): boolean {
  // Roles, Calendars, Issues and Documents render a complete detail surface
  // inside their own window; the shared pane has no reader for them and would
  // only show the generic "tabs are not implemented" fallback.
  return (
    state.visiblePanels.details &&
    layout !== "none" &&
    state.activeMenu !== "roles" &&
    state.activeMenu !== "calendars" &&
    state.activeMenu !== "issues" &&
    state.activeMenu !== "documents"
  );
}

/**
 * Re-renders only the bottom surface after a Show on Bottom switch. The grid,
 * Gantt, filters and selection are untouched, so the pane keeps the exact
 * height and horizontal position the user had.
 */
function renderBottomSurface(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions): void {
  const layout: WorkspaceBottomLayout = state.activeMenu === "schedule" ? readWorkspaceBottomLayout(state, options.activityUsage) : "details";
  const main = container.querySelector<HTMLElement>(".cp-main[data-details-split]");
  const aside = container.querySelector<HTMLElement>("#cp-details");
  if (!main || !aside) return;
  const visible = bottomDetailsVisible(state, layout);
  main.dataset.detailsCollapsed = visible ? "false" : "true";
  main.dataset.bottomLayout = layout;
  aside.hidden = !visible;
  aside.dataset.bottomSurface = layout;
  aside.setAttribute("aria-labelledby", bottomLayoutHeading(layout));
  aside.innerHTML = renderBottomPaneContent(state, getWorkspaceLabels(state.locale), container, options);
  if (layout === "details") options.enhanceActivityDetails?.(aside, state);
  container.querySelector<HTMLDialogElement>("[data-layout-options-dialog]")?.close();
  workspaceRenderRecords.set(container, { state, options });
}

function applyIncrementalWorkspaceUpdate(container: HTMLElement, previous: WorkspaceState, next: WorkspaceState, options: WorkspaceRendererOptions): boolean {
  if (!canIncrementallyUpdate(previous, next)) return false;
  const menuChanged = previous.activeMenu !== next.activeMenu;
  const wbsChanged = previous.selectedWbsId !== next.selectedWbsId;
  const previousSelection = selectedActivityIdList(previous);
  const nextSelection = selectedActivityIdList(next);
  const activityChanged = previous.selectedActivityId !== next.selectedActivityId ||
    previousSelection.length !== nextSelection.length ||
    previousSelection.some((id, index) => id !== nextSelection[index]);
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
    if (stage) stage.outerHTML = renderP6ModuleStage(container, next, labels, options);
    refreshContextAddMenu(container, next, options);
    container.querySelector<HTMLElement>("[data-nav-flyout]")?.setAttribute("hidden", "");
    const schedulingReference = container.querySelector<HTMLElement>("#cp-scheduling-reference");
    if (schedulingReference) schedulingReference.hidden = next.activeMenu !== "schedule";
    const details = container.querySelector<HTMLElement>("#cp-details");
    if (details) {
      const nextLayout: WorkspaceBottomLayout = next.activeMenu === "schedule" ? readWorkspaceBottomLayout(next, options.activityUsage) : "details";
      const nextMain = container.querySelector<HTMLElement>(".cp-main[data-details-split]");
      const nextVisible = bottomDetailsVisible(next, nextLayout);
      details.hidden = !nextVisible;
      details.dataset.bottomSurface = nextLayout;
      details.setAttribute("aria-labelledby", bottomLayoutHeading(nextLayout));
      if (nextMain) {
        nextMain.dataset.detailsCollapsed = nextVisible ? "false" : "true";
        nextMain.dataset.bottomLayout = nextLayout;
      }
      details.innerHTML = renderBottomPaneContent(next, labels, container, options);
      if (nextLayout === "details") options.enhanceActivityDetails?.(details, next);
    }
    return true;
  }
  if (wbsChanged) {
    container.querySelectorAll<HTMLElement>("[data-wbs-id]").forEach((button) => {
      const selected = button.dataset.wbsId === next.selectedWbsId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", selected ? "true" : "false");
    });
    // Selection is incremental here, so the table row state must be refreshed
    // too; otherwise the row keeps the aria-selected value it was rendered with.
    container.querySelectorAll<HTMLElement>(".cp-wbs-row[data-wbs-id]").forEach((row) => {
      row.setAttribute("aria-selected", String(row.dataset.wbsId === next.selectedWbsId));
    });
    const wbsDetails = container.querySelector<HTMLElement>(".cp-wbs-details");
    if (wbsDetails) wbsDetails.outerHTML = renderWbsDetails(next, wbsDetailsTabByContainer.get(container) ?? "general");
    // The WBS window commands depend on the selected element, so the
    // incremental selection path must update them too instead of leaving the
    // disabled state from the initial paint.
    const hasSelection = Boolean(next.selectedWbsId);
    container.querySelectorAll<HTMLButtonElement>(".cp-wbs-window [data-wbs-cut], .cp-wbs-window [data-wbs-copy], .cp-wbs-window [data-wbs-delete]").forEach((button) => {
      button.disabled = !hasSelection;
    });
    const pasteButton = container.querySelector<HTMLButtonElement>(".cp-wbs-window [data-wbs-paste]");
    if (pasteButton) pasteButton.disabled = !hasSelection || !wbsClipboardByContainer.get(container);
    return true;
  }
  const nextSelectionSet = new Set(nextSelection);
  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const selected = nextSelectionSet.has(row.dataset.activityId ?? "");
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
    if (row.tagName === "TR" && next.selectedActivityId) {
      // Move the grid's single tab stop with the primary row so Tab and the
      // arrow keys agree after an incremental selection update.
      row.setAttribute("tabindex", row.dataset.activityId === next.selectedActivityId ? "0" : "-1");
    }
  });
  container.querySelectorAll<HTMLElement>("[data-gantt-activity-id]").forEach((row) => {
    const selected = nextSelectionSet.has(row.dataset.ganttActivityId ?? "");
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-pressed", selected ? "true" : "false");
  });
  updateActivityScopeCounts(container, next, options, nextSelection);
  // Add Relationship depends on the selected activity, so the rail follows the
  // incremental selection instead of keeping its first-paint disabled state.
  refreshContextAddMenu(container, next, options);
  const details = container.querySelector<HTMLElement>("#cp-details");
  if (details) {
    const t = getWorkspaceLabels(next.locale);
    details.innerHTML = renderBottomPaneContent(next, t, container, options);
    options.enhanceActivityDetails?.(details, next);
  }
  return true;
}


export type ActivityContextCommand =
  | "details"
  | "add"
  | "link"
  | "columns"
  | "line-numbers"
  | "font-row"
  | "group-sort";

export type WorkspaceActivitySelection = {
  /** Ctrl/Cmd-click: toggle this row without clearing the others. */
  additive?: boolean;
  /** Shift-click: extend from the fixed anchor to this row. */
  range?: boolean;
  /** Displayed row order used to resolve a Shift-click range. */
  orderedIds?: readonly string[];
};

function activitySelectionRequest(
  container: HTMLElement,
  event: MouseEvent,
  selector: string,
  key: "activityId" | "ganttActivityId",
): WorkspaceActivitySelection | undefined {
  if (!event.ctrlKey && !event.metaKey && !event.shiftKey) return undefined;
  const orderedIds = [...container.querySelectorAll<HTMLElement>(selector)]
    .map((row) => row.dataset[key] ?? "")
    .filter((id) => id.length > 0);
  return { additive: event.ctrlKey || event.metaKey, range: event.shiftKey, orderedIds };
}

export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  openWindows?: readonly WorkspaceState["activeMenu"][];
  onWindowClose?: (menu: WorkspaceState["activeMenu"]) => void;
  onWbsSelect?: (wbsId: string) => void;
  onWbsCreate?: (input: { code: string; name: string; sequenceNumber: number; parentWbsId: string | null }) => void | Promise<void>;
  onWbsUpdate?: (wbsId: string, input: { code: string; name: string; sequenceNumber: number; status?: "planned" | "active" | "inactive" | "what_if"; percentCompleteTechnique?: "activities" | "milestones"; parentKind?: "project" | "wbs"; parentWbsId?: string | null }) => void | Promise<void>;
  onWbsCopy?: (wbsId: string, targetParentWbsId: string, rootCode: string) => void | Promise<void>;
  onWbsMilestonesUpdate?: (wbsId: string, milestones: readonly WorkspaceWbsMilestone[], expectedRevision: number) => void | Promise<void>;
  onWbsDelete?: (wbsId: string) => void | Promise<void>;
  onActivityCreate?: (input: { activityId: string; name: string; durationValue: number; durationUnit: string; wbsId: string; activityType: string; status: string; statusCode: string; percentCompleteType: string; levelingPriority: string }) => void | Promise<void>;
  onActivityEdit?: (activityId: string) => void | Promise<void>;
  onRelationshipCreate?: (input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipUpdate?: (relationshipId: string, recordRevision: number, input: { predecessorId: string; successorId: string; type: WorkspaceRelationshipType; lagValue: string; lagUnit: string }) => void | Promise<void>;
  onRelationshipDelete?: (relationshipId: string, recordRevision: number) => void | Promise<void>;
  onActivitySelect?: (activityId: string, selection?: WorkspaceActivitySelection) => void;
  onGanttActivitySelect?: (activityId: string, selection?: WorkspaceActivitySelection) => void;
  /**
   * Replaces the rendered Activity Details with the interactive Details
   * surface. Called only while the bottom pane actually shows Details, so the
   * enhancement can never overwrite Trace Logic or a hidden pane.
   */
  enhanceActivityDetails?: (host: HTMLElement, state: WorkspaceState) => void;
  /**
   * Persisted assignment periods the Activity Usage Profile/Spreadsheet
   * project. Missing means the authoritative read has not completed yet.
   */
  activityUsage?: ActivityUsageSource;
  /** Re-reads assignment periods from the resource read API. */
  onActivityUsageRefresh?: () => void;
  /** Activity right-click commands that belong to the desktop shell. */
  onActivityContextCommand?: (command: ActivityContextCommand, activityId: string) => void;
  onGanttScaleChange?: (ganttScale: WorkspaceGanttScale) => void;
  onGanttRelationshipsChange?: (visible: boolean) => void;
  /** Persists one Gantt display toggle through the same layout presentation. */
  onGanttDisplayToggle?: (kind: "baseline" | "progress-line" | "data-date-line", visible: boolean) => void;
  onGanttCommand?: (command: "bars" | "font-row" | "user-preferences") => void;
  onProjectSettings?: () => void;
  /** Authoritative metadata row of the open project, when the server returned it. */
  projectSummary?: ProjectSummary | null;
  /** Projects the session may open, exactly as the session service listed them. */
  projects?: readonly ProjectSummary[];
  /** Switches the open project from the Projects window. */
  onProjectOpen?: (projectId: string) => void;
  onActivityFilterChange?: (filterText: string) => void;
  /** Selects every activity in the current filter/search scope, not just painted rows. */
  onSelectAll?: () => void;
  onActivitySortChange?: (columnId: string | null) => void;
  /** Sets both the sort column and direction in one state transition. */
  onActivitySortSet?: (columnId: string, direction: "asc" | "desc") => void;
  onActivityGroupByChange?: (groupBy: "wbs" | "none") => void;
  /** Ordered group plan from the toolbar or the Group and Sort dialog. */
  onActivityGroupLevelsChange?: (levels: readonly WorkspaceActivityGroupLevel[]) => void;
  onActivitySortDirectionToggle?: () => void;
  onP6FieldAdd?: (fieldId: string) => void;
  /** Adds every available registry field in one layout transition. */
  onP6FieldAddMany?: (fieldIds: readonly string[]) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldWidthChange?: (fieldId: string, width: number) => void;
  onP6ColumnWidthsReset?: (widths: Readonly<Record<string, number>>) => void;
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
  /** Authenticated write capability for this project (planner/administrator). */
  canWrite?: boolean;
  /**
   * Dispatches a stable desktop command id. The contextual rail uses the same
   * ids as the toolbar and application menu, never a second action handler.
   */
  onDesktopCommand?: (command: DesktopCommand) => void;
  presentation?: WorkspacePresentation;
  /** Authoritative project Data Date; null when the read model exposes none. */
  dataDate?: string | null;
  /** Persisted dual-rail toolbar configuration for the signed-in user. */
  toolbarConfig?: ToolbarWorkspaceConfig;
  /** Persists a toolbar customization and repaints the workspace. */
  onToolbarConfigChange?: (next: ToolbarWorkspaceConfig) => void;
  /** True only when the signed-in session can use administrator commands. */
  canAdminister?: boolean;
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const previous = workspaceRenderRecords.get(container);
  if (previous && previous.options.presentation !== options.presentation) {
    // Presentation changes repaint table classes and bar layers, which the
    // incremental selection path does not touch.
    workspaceRenderRecords.delete(container);
  } else if (previous && applyIncrementalWorkspaceUpdate(container, previous.state, state, options)) {
    workspaceRenderRecords.set(container, { state, options });
    return;
  }
  const t = getWorkspaceLabels(state.locale);
  // V26 Defaults: the create form starts from the stored project values. The
  // ID is only a suggestion the user can edit; the server stores what is sent.
  const projectSummary = options.projectSummary;
  const projectDefaults = projectSummary && projectSummary.project_id === state.context.project_id
    ? {
        prefix: projectSummary.activity_id_prefix ?? "",
        suffix: projectSummary.activity_id_suffix ?? "",
        increment: projectSummary.activity_id_increment ?? 10,
        incrementActivityId: projectSummary.increment_activity_id === true,
      }
    : { prefix: "", suffix: "", increment: 10, incrementActivityId: false };
  const activityTypeValues = new Set(ACTIVITY_CREATE_FIELDS.activity_type.options.map((option) => option.value as string));
  const percentTypeValues = new Set(ACTIVITY_CREATE_FIELDS.percent_complete_type.options.map((option) => option.value as string));
  const storedActivityType = projectSummary?.default_activity_type ?? "";
  const storedPercentType = projectSummary?.default_percent_complete_type ?? "";
  const activityDefaults = {
    activityType: activityTypeValues.has(storedActivityType) ? storedActivityType : undefined,
    percentCompleteType: percentTypeValues.has(storedPercentType.toUpperCase()) ? storedPercentType.toUpperCase() : undefined,
  };
  const activityIdSuggestion = computeNextActivityId(
    state.activities.map((activity) => activity.id),
    projectDefaults,
    state.selectedActivityId,
  );
  const activityIdSuggestionHint = uiText(
    state.locale,
    "Suggested from the project defaults; edit it before saving.",
    "بر پایهٔ پیش‌فرض‌های پروژه پیشنهاد شده است؛ پیش از ذخیره می‌توانید آن را ویرایش کنید.",
  );
  const presentation = options.presentation ?? DEFAULT_PRESENTATION;
  const tablePresentation = presentation.table;
  const lineNumbers = tablePresentation.lineNumbers;
  const presentationVars = [
    `--cp-p6-font-family:${presentationFontFamily(tablePresentation.fontFamily)}`,
    `--cp-p6-font-size:${tablePresentation.fontSize}px`,
    `--cp-p6-text-color:${presentationColor(tablePresentation.textColor)}`,
    `--cp-p6-bg-color:${presentationColor(tablePresentation.backgroundColor)}`,
    `--cp-p6-row-height:${tablePresentation.rowHeight}px`,
  ].join(";");
  const filterApplication = applyActivityFilterState(
    state.activities,
    presentation.filters,
    state.wbsNodes,
    createActivityFilterDateContext(state.activities, options.dataDate ?? null),
  );
  const filteredActivities = filterAndSortActivities(
    filterApplication.activities,
    state.activityFilter,
    state.activitySort,
    state.activityGroupBy,
    state.wbsNodes,
    state.activitySortLevels,
    state.activityGroupLevels,
  );
  // An active filter always reveals matching descendants; collapse is a view
  // preference for browsing the unfiltered schedule, never a way to hide hits.
  const collapsedWbsIds = state.activityFilter.trim() || filterApplication.filters.length
    ? new Set<string>()
    : getCollapsedWbsIds(state.context.project_id);
  const displayRows = buildWorkspaceDisplayRows(
    filteredActivities,
    state.wbsNodes,
    state.activityGroupBy,
    collapsedWbsIds,
    state.activityGroupLevels,
    state.locale,
  );
  const visibleActivityIds = displayRows.flatMap((row) => (row.kind === "activity" ? [row.activity.id] : []));
  const activityCounts = computeActivityCounts({
    activities: state.activities,
    filterMatchedIds: filterApplication.matchedIds,
    scopeActivities: filteredActivities,
    visibleIds: visibleActivityIds,
    selectedIds: selectedActivityIdList(state),
  });
  const groupRows = displayRows.filter(isWorkspaceBandRow);
  const treeColumnId = state.columns.find((column) => column.id === "activity_id" || column.id === "activity.id")?.id
    ?? state.columns.find((column) => column.id === "activity_name" || column.id === "activity.name")?.id
    ?? state.columns[0]?.id
    ?? null;
  // The time axis is anchored to every filter-matched activity, so collapsing a
  // branch never rescales the bars that remain visible.
  const scale = createGanttScale(filteredActivities);
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
  // the table and pushing the required columns out of the initial view. The
  // predecessor and row-action helpers stay in the DOM but are hidden by the
  // reference stylesheet, so they must not widen the table either.
  const activityTableWidth =
    state.columns.reduce((total, column) => total + column.width, 0) + (lineNumbers ? 40 : 0);
  const treeGuides = buildWbsTreeGuides(displayRows);
  let activityLineNumber = 0;
  // Roving tabindex: the activity rows share one Tab stop, and the primary
  // row (or the first activity when nothing is selected yet) receives it.
  const tabbableRowId = state.selectedActivityId
    ?? displayRows.find((row) => row.kind === "activity")?.activity.id
    ?? null;
  const activityRowMarkup = displayRows.map((row, index) => {
    if (row.kind === "wbs") return renderWbsGroupRow(row, state, stickyOffsets, presentation, t, treeGuides[index]);
    if (row.kind === "fieldGroup") return renderFieldGroupRow(row, state, stickyOffsets, presentation, t, treeGuides[index]);
    activityLineNumber += 1;
    return renderActivityRow(row.activity, state, stickyOffsets, presentation, activityLineNumber, row.depth, treeColumnId, treeGuides[index], row.activity.id === tabbableRowId);
  }).join("");

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
  // One shared window→glyph table, so the rail, the flyout and the desktop
  // shell can never show two different shapes for the same destination.
  const railMenuIcons = WORKSPACE_WINDOW_ICONS;
  const appliedFilterName = filterApplication.filters.map((filter) => filter.name).join(" + ");
  const activeFilterName = appliedFilterName
    ? state.activityFilter.trim()
      ? `${appliedFilterName} · ${state.activityFilter.trim()}`
      : appliedFilterName
    : "";
  const highlightOnly = filterApplication.highlight;
  const activityFilterLabel = activeFilterName
    ? highlightOnly
      ? uiText(state.locale, `${activeFilterName} (highlighted)`, `${activeFilterName} (برجسته‌شده)`)
      : activeFilterName
    : uiText(state.locale, "All Activities", "همهٔ فعالیت‌ها");
  const activeFilterTitle = filterApplication.filters
    .map((filter) => describeActivityFilter(filter, state.locale))
    .join(" | ");
  const tableSplitKey = splitStorageKey("table-gantt", state);
  const detailsSplitKey = splitStorageKey("details", state);
  const tableSplit = Math.min(MAX_TABLE_SPLIT, Math.max(MIN_TABLE_SPLIT, readStoredSplit(tableSplitKey, DEFAULT_TABLE_SPLIT)));
  const detailsSplit = Math.min(MAX_DETAILS_SPLIT, Math.max(MIN_DETAILS_SPLIT, readStoredSplit(detailsSplitKey, DEFAULT_DETAILS_SPLIT)));
  const topLayout: WorkspaceTopLayout = state.activeMenu === "schedule" ? readWorkspaceTopLayout(state) : "table-gantt";
  const bottomLayout: WorkspaceBottomLayout = state.activeMenu === "schedule" ? readWorkspaceBottomLayout(state, options.activityUsage) : "details";
  const detailsVisible = bottomDetailsVisible(state, bottomLayout);
  // The session list already carries the authoritative name, so the title bar
  // keeps it on first paint instead of flashing the id until the record loads.
  const headerProject =
    options.projectSummary && options.projectSummary.project_id === state.context.project_id
      ? options.projectSummary
      : options.projects?.find((project) => project.project_id === state.context.project_id) ?? null;
  const headerProjectLabel = headerProject?.name || state.context.project_id;
  const addCommands = contextAddCommands(contextAddState(state, options));
  // Both rails are driven by one command registry and one persisted
  // configuration. The old hard-coded icon map is gone: every destination and
  // action below arrives through the registry, so customization can move,
  // hide, reorder and dock any of them.
  const toolbarSession: ToolbarRailSession = {
    config: options.toolbarConfig ?? defaultToolbarConfig(),
    context: {
      activeWindow: state.activeMenu,
      locale: state.locale,
      capabilities: {
        hasWbs: state.wbsNodes.length > 0,
        hasSelectedActivity: Boolean(state.selectedActivityId),
        hasMultiSelection: selectedActivityIdList(state).length > 1,
        hasActivities: state.activities.length > 0,
        hasRelationships: state.relationships.length > 0,
        hasLayout: Boolean(state.p6Layout),
        canUndoLayout: Boolean(options.layoutHistory?.canUndo),
        canRedoLayout: Boolean(options.layoutHistory?.canRedo),
        groupByWbs: state.activityGroupBy === "wbs",
        canAdminister: options.canAdminister === true,
        canOpenFieldChooser: Boolean(state.p6Layout && state.p6FieldRegistry),
      },
      detailsVisible,
      ganttVisible: state.visiblePanels.gantt,
      lineNumbers,
    },
    translate: (english, persian) => uiText(state.locale, english, persian),
    onChange: options.onToolbarConfigChange ?? (() => undefined),
    direction: state.direction,
  };
  const toolbarRails = renderToolbarRails(container, toolbarSession);


  container.innerHTML = `
    <section class="cp-workspace cp-p6-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}" data-active-menu="${state.activeMenu}" data-table-row-mode="${tablePresentation.rowHeightMode}" data-show-icons="${tablePresentation.showIcons}" data-line-numbers="${lineNumbers}" style="${escapeAttribute(presentationVars)}">
      <header class="cp-header">
        <div class="cp-brand"><img class="cp-brand-logo" src="${escapeAttribute(cubiPlatformLogoUrl())}" width="1536" height="664" alt="CUBI Platform" /></div>
        <div class="cp-project" data-project-id="${escapeAttribute(state.context.project_id)}" title="${escapeAttribute(state.context.project_id)}">${escapeHtml(headerProjectLabel)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
        <button type="button" id="cp-project-settings-open" class="cp-project-settings-open" data-project-settings aria-label="${escapeAttribute(t.projectSettings)}">${escapeHtml(t.projectSettings)}</button>
      </header>
      <div class="cp-p6-shell" data-left-tools="${toolbarRails.leftWide ? "wide" : "icon"}" data-right-tools="${toolbarRails.rightWide ? "wide" : "icon"}">
        <nav class="cp-menu cp-p6-rail cp-navigation-tree cp-tool-rail" data-tool-rail="left" aria-label="${escapeAttribute(uiText(state.locale, "Left tool rail", "ریل ابزار چپ"))}">
          ${toolbarRails.left}
        </nav>
        <div class="cp-p6-body">
          ${state.activeMenu === "schedule" ? renderLayoutOptionsDialog(state, t, options) : ""}
          <main class="cp-main" data-details-split data-bottom-layout="${bottomLayout}" data-details-collapsed="${detailsVisible ? "false" : "true"}" style="--cp-split-primary:${detailsSplit.toFixed(2)}%;--cp-split-details:${detailsSplit.toFixed(2)}%">
            <div class="cp-p6-primary">
              ${toolbarRails.floating}
              <div class="cp-layout-selector-host" data-layout-selector-host data-workspace-menu="schedule" role="region" aria-label="${escapeAttribute(uiText(state.locale, "Activities layout", "چیدمان فعالیت‌ها"))}"></div>
              <section class="cp-p6-split" data-panel-split data-top-layout="${topLayout}" data-split-key="${escapeAttribute(tableSplitKey)}" data-workspace-menu="schedule" style="--cp-split-table:${tableSplit.toFixed(2)}%">
                <section id="cp-activity-grid" class="cp-panel cp-grid" ${!state.visiblePanels.activity_grid ? "hidden" : ""} data-workspace-menu="schedule" tabindex="-1">
                  <div class="cp-p6-grid-head">
                    <h2>${escapeHtml(t.activities)}</h2>
                    <div class="cp-p6-grid-actions" role="group" aria-label="${escapeAttribute(uiText(state.locale, "Activities toolbar", "نوار ابزار فعالیت‌ها"))}">
                      <button type="button" data-activity-create-open title="${escapeAttribute(t.activityCreate)}" aria-label="${escapeAttribute(t.activityCreate)}">${workspaceIcon("plus")}</button>
                      <button type="button" data-columns-open title="${escapeAttribute(ACTIVITY_CONTEXT_LABELS.columns.en)}" aria-label="${escapeAttribute(uiText(state.locale, "Columns", "ستون‌ها"))}">${workspaceIcon("columns")}</button>
                      <button type="button" data-rail-action="wbs" title="${escapeAttribute(uiText(state.locale, "WBS", "ساختار شکست"))}" aria-label="${escapeAttribute(uiText(state.locale, "WBS", "ساختار شکست"))}">${workspaceIcon("wbs")}</button>
                      <button type="button" data-layout-options-open title="${escapeAttribute(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}" aria-label="${escapeAttribute(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}">${workspaceIcon("settings")}</button>
                      <span class="cp-action-separator" role="separator" aria-orientation="vertical"></span>
                      <button type="button" data-reset-table-split title="${escapeAttribute(uiText(state.locale, "Restore the default table / Gantt width split", "بازگردانی تقسیم پیش‌فرض عرض جدول و گانت"))}" aria-label="${escapeAttribute(uiText(state.locale, "Reset table split", "بازنشانی تقسیم جدول"))}">${workspaceIcon("resetTableSplit")}</button>
                      <button type="button" data-reset-details-split title="${escapeAttribute(uiText(state.locale, "Restore the default 70/30 activity / details height split", "بازگردانی تقسیم ارتفاع پیش‌فرض ۷۰/۳۰ فعالیت و جزئیات"))}" aria-label="${escapeAttribute(uiText(state.locale, "Reset details split", "بازنشانی تقسیم جزئیات"))}">${workspaceIcon("resetDetailsSplit")}</button>
                      <button type="button" data-reset-column-widths title="${escapeAttribute(uiText(state.locale, "Restore the saved column widths", "بازگردانی عرض‌های ذخیره‌شدهٔ ستون‌ها"))}" aria-label="${escapeAttribute(uiText(state.locale, "Reset column widths", "بازنشانی عرض ستون‌ها"))}">${workspaceIcon("resetColumns")}</button>
                    </div>
                  </div>
                  ${renderActivityFilterSort(state, activityCounts, t, groupRows.length, {
                    filterIds: filterApplication.filters.map((filter) => filter.id).join(","),
                    mode: filterApplication.highlight ? "highlight" : "replace",
                    title: activeFilterTitle,
                    stateLabel: activityFilterLabel,
                  })}
                  ${renderActivityExportDialog(activityCounts, t, state)}
                  <div class="cp-table-wrap">
                    <table role="grid" aria-label="${escapeAttribute(t.activities)}" aria-multiselectable="true" style="width:${activityTableWidth}px">
                      <thead><tr role="row">${lineNumbers ? `<th role="columnheader" scope="col" class="cp-p6-line-number">#</th>` : ""}${state.columns.map((column) => `<th role="columnheader" scope="col" tabindex="-1" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="width:${column.width}px;text-align:${column.alignment}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}"><span class="cp-p6-column-label">${escapeHtml(localizeWorkspaceLabel(state.locale, column.label))}${column.formula ? `<span aria-label="${escapeAttribute(t.formulaColumn)}">ƒx</span>` : ""}</span><span class="cp-p6-column-resize" data-column-resize="${escapeAttribute(column.id)}" role="separator" aria-orientation="vertical" aria-label="${escapeAttribute(uiText(state.locale, `Resize ${localizeWorkspaceLabel(state.locale, column.label)} column`, `تغییر عرض ستون ${localizeWorkspaceLabel(state.locale, column.label)}`))}" aria-valuemin="${MIN_COLUMN_WIDTH}" aria-valuemax="${MAX_COLUMN_WIDTH}" aria-valuenow="${column.width}" tabindex="0" data-resize-handle="column"></span></th>`).join("")}<th role="columnheader" scope="col" class="cp-logic-column">${escapeHtml(t.predecessorsColumn)}</th><th role="columnheader" scope="col" class="cp-actions-column"></th></tr></thead>
                      <tbody>${displayRows.length ? activityRowMarkup : `<tr role="row"><td role="gridcell" colspan="${Math.max(1, state.columns.length + 2 + (lineNumbers ? 1 : 0))}">${escapeHtml(state.activities.length ? t.noMatchingActivities : t.noActivities)}</td></tr>`}</tbody>
                    </table>
                  </div>
                </section>
                ${topLayout === "table-only" ? "" : `<div class="cp-p6-splitter" data-panel-splitter role="separator" aria-orientation="vertical" tabindex="0" aria-label="${escapeAttribute(topLayout === "activity-network" ? uiText(state.locale, "Resize table and Activity Network", "تغییر اندازهٔ جدول و شبکهٔ فعالیت‌ها") : uiText(state.locale, "Resize table and Gantt", "تغییر اندازهٔ جدول و گانت"))}" aria-valuemin="${MIN_TABLE_SPLIT}" aria-valuemax="${MAX_TABLE_SPLIT}" aria-valuenow="${tableSplit.toFixed(0)}" data-resize-handle="table-gantt"><span></span></div>
                ${topLayout === "activity-network"
                  ? renderActivityNetwork(state.activities, state.relationships, state.locale, state.selectedActivityId, readNetworkZoom(networkZoomStorageKey(state)), networkZoomStorageKey(state))
                  : `<section id="cp-gantt" class="cp-panel cp-gantt" ${!state.visiblePanels.gantt ? "hidden" : ""} data-workspace-menu="schedule" tabindex="-1">
                  <div class="cp-p6-gantt-head">
                    <h2>${escapeHtml(t.gantt)}</h2>
                  </div>
                  ${renderGantt(displayRows, state.relationships, state.ganttScale, state.calendarMode, scale, t, state.selectedActivityId, state.showGanttRelationships, presentation, state.locale, options.dataDate ?? null, state.projectCalendar, selectedActivityIdList(state))}
                </section>`}`}
              </section>
              ${renderP6ModuleStage(container, state, t, options)}
            </div>
            <div class="cp-details-splitter" data-details-splitter data-split-key="${escapeAttribute(detailsSplitKey)}" role="separator" aria-orientation="horizontal" tabindex="0" aria-label="${escapeAttribute(uiText(state.locale, "Resize activity area and details", "تغییر اندازهٔ ناحیهٔ فعالیت و جزئیات"))}" aria-valuemin="${MIN_DETAILS_SPLIT}" aria-valuemax="${MAX_DETAILS_SPLIT}" aria-valuenow="${detailsSplit.toFixed(0)}" data-resize-handle="details"><span></span></div>
            <aside id="cp-details" class="cp-panel cp-details" ${detailsVisible ? "" : "hidden"} data-bottom-surface="${bottomLayout}" data-workspace-menu="project schedule progress resources cost documents reports control settings" aria-labelledby="${bottomLayoutHeading(bottomLayout)}">${renderBottomPaneContent(state, t, container, options)}</aside>
          </main>
          <div class="cp-p6-drawer cp-p6-wbs-drawer" data-wbs-drawer hidden aria-label="${escapeAttribute(t.wbs)}">
            <div class="cp-p6-drawer-head"><strong>${escapeHtml(t.wbs)}</strong><button type="button" data-wbs-drawer-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
            <aside id="cp-project-wbs" class="cp-panel cp-wbs" ${!state.visiblePanels.project_wbs ? "hidden" : ""} data-workspace-menu="project schedule" aria-label="${escapeAttribute(t.wbs)}">
              <h2>${escapeHtml(t.wbs)}</h2>
              ${renderWbsTable(state.wbsNodes, state.activities, state.selectedWbsId, state.locale, t)}
              ${renderWbsDetails(state, "general")}
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
                  <label>${escapeHtml(uiText(state.locale, "Status", "وضعیت"))}
                    <select name="status">
                      ${(["planned", "active", "inactive", "what_if"] as const).map((status) => `<option value="${status}" ${(selected.status ?? "planned") === status ? "selected" : ""}>${escapeHtml(wbsStatusLabel(state.locale, status))}</option>`).join("")}
                    </select>
                  </label>
                  <label>${escapeHtml(uiText(state.locale, "Percent complete technique", "روش درصد تکمیل"))}
                    <select name="percent_complete_technique">
                      ${(["activities", "milestones"] as const).map((technique) => `<option value="${technique}" ${(selected.percentCompleteTechnique ?? "activities") === technique ? "selected" : ""}>${escapeHtml(wbsTechniqueLabel(state.locale, technique))}</option>`).join("")}
                    </select>
                  </label>
                  <label>${escapeHtml(t.wbsSequence)} <input name="sequence_number" type="number" min="0" step="1" value="${selected.sequenceNumber}" required></label>
                  <button type="submit">${escapeHtml(t.wbsSave)}</button>
                  <button type="button" data-wbs-delete>${escapeHtml(t.wbsDelete)}</button>
                </form>`;
              })() : `<p class="cp-empty">${escapeHtml(t.wbsSelectPrompt)}</p>`}
              <p class="cp-wbs-delete-guidance" data-wbs-delete-guidance role="note" hidden></p>
            </aside>
          </div>
        </div>
        <aside class="cp-comments-dock-rail cp-context-command-rail cp-tool-rail" data-tool-rail="right" aria-label="${escapeAttribute(uiText(state.locale, "Right tool rail", "ریل ابزار راست"))}">
          ${renderContextAddMenu(addCommands, state)}
          ${toolbarRails.right}
        </aside>
      </div>
      <div class="cp-p6-flyout" data-nav-flyout hidden>${renderFullNavigationMenu(state, railMenuIcons)}${renderNavigationSurface(state)}</div>
      <div class="cp-p6-drawer cp-p6-tools-drawer" data-tools-drawer hidden aria-label="${escapeAttribute(rail.tools)}">
        <div class="cp-p6-drawer-head"><strong>${escapeHtml(rail.tools)}</strong><button type="button" data-tools-close title="${escapeAttribute(rail.close)}" aria-label="${escapeAttribute(rail.close)}">${workspaceIcon("close")}</button></div>
        <div class="cp-p6-tool-scroll">
          ${renderP6FieldChooser(state, options.layoutHistory)}
          <section class="cp-panel cp-p6-tool-panel" aria-label="${escapeAttribute(t.activityCreate)}">
            <h2>${escapeHtml(t.activityCreate)}</h2>
            <form class="cp-activity-editor" data-activity-create-form>
              <h3>${escapeHtml(t.activityCreate)}</h3>
              <label>${escapeHtml(t.activityId)} <input name="activity_id" required maxlength="80" autocomplete="off" value="${escapeAttribute(activityIdSuggestion)}"><small class="cp-form-hint" data-activity-id-suggestion>${escapeHtml(activityIdSuggestionHint)}</small></label>
              <label>${escapeHtml(t.activityName)} <input name="name" required maxlength="180" autocomplete="off"></label>
              <label>${escapeHtml(t.activityDuration)} <input name="duration_value" type="number" min="0" step="any" value="1" required></label>
              <label>${escapeHtml(t.activityDurationUnit)} <select name="duration_unit"><option value="working-day">${escapeHtml(t.workingDay)}</option><option value="working-hour">${escapeHtml(t.workingHour)}</option></select></label>
              <label>${escapeHtml(t.activityWbs)} <select name="wbs_id" required ${state.wbsNodes.length ? "" : "disabled"}>${state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}" ${node.id === state.selectedWbsId ? "selected" : ""}>${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "activity_type"))} <select name="activity_type">${renderActivityCreateOptions(state.locale, "activity_type", activityDefaults.activityType)}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status"))} <select name="status">${renderActivityCreateOptions(state.locale, "status")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "status_code"))} <select name="status_code">${renderActivityCreateOptions(state.locale, "status_code")}</select></label>
              <label>${escapeHtml(getActivityCreateFieldLabel(state.locale, "percent_complete_type"))} <select name="percent_complete_type">${renderActivityCreateOptions(state.locale, "percent_complete_type", activityDefaults.percentCompleteType)}</select></label>
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
      ${state.wbsNodes.length ? renderCollapseToDialog(state) : ""}
    </section>
  `;

  workspaceRenderRecords.set(container, { state, options });
  if (!workspaceEventDelegation.has(container)) bindWorkspaceEvents(container);
  const detailsSurface = container.querySelector?.<HTMLElement>("#cp-details");
  if (detailsSurface && bottomLayout === "details") options.enhanceActivityDetails?.(detailsSurface, state);
  markFilterHighlights(container, filterApplication);
  alignGanttRows(container);
}

/**
 * The table header and the chart axis must end on the same pixel so every bar
 * lands on its activity row. Both panes are independent flex children, so the
 * offset between the 34px table header (and the filter row above it) and the
 * chart axis is measured once after layout instead of guessed in CSS.
 */
function alignGanttRows(container: HTMLElement): void {
  if (typeof container.querySelector !== "function") return;
  const header = container.querySelector<HTMLElement>("#cp-activity-grid thead");
  const axis = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-axis");
  const board = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-board");
  if (!header || !axis || !board) return;
  const headerBottom = header.getBoundingClientRect().bottom;
  const axisBottom = axis.getBoundingClientRect().bottom;
  if (!headerBottom || !axisBottom) return;
  const applied = Number.parseFloat(board.style.getPropertyValue("--cp-gantt-top-offset")) || 0;
  // The axis is already shifted by the offset currently in force; subtract it
  // before comparing so repeated renders stay stable instead of collapsing.
  const offset = Math.max(0, Math.min(80, Math.round(headerBottom - (axisBottom - applied))));
  board.style.setProperty("--cp-gantt-top-offset", `${offset}px`);
}


function renderRegisterWindow(
  state: WorkspaceState,
  title: string,
  columns: readonly [string, string][],
  tabs: readonly [string, string, string][],
): string {
  const empty = uiText(state.locale, "No records are loaded for this project.", "هیچ رکوردی برای این پروژه بارگذاری نشده است.");
  return `<div class="cp-register-window">
    <div class="cp-register-toolbar"><strong>${escapeHtml(title)}</strong><div><button type="button" disabled>${escapeHtml(uiText(state.locale, "New", "جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Filter", "فیلتر"))}</button></div></div>
    <div class="cp-register-table-wrap"><table><thead><tr>${columns.map(([en,fa])=>`<th>${escapeHtml(uiText(state.locale,en,fa))}</th>`).join("")}</tr></thead><tbody><tr><td colspan="${columns.length}">${escapeHtml(empty)}</td></tr></tbody></table></div>
    <section class="cp-register-details"><header><strong>${escapeHtml(uiText(state.locale, "Details", "جزئیات"))}</strong><span>${escapeHtml(uiText(state.locale, "No selection", "بدون انتخاب"))}</span></header><nav class="cp-register-detail-tabs" role="tablist">${tabs.map(([key,en,fa],index)=>`<button type="button" role="tab" data-register-tab="${state.activeMenu}:${key}" aria-selected="${index===0}" class="${index===0?"is-active":""}">${escapeHtml(uiText(state.locale,en,fa))}</button>`).join("")}</nav><div class="cp-register-detail-content">${tabs.map(([key,en,fa],index)=>`<section data-register-panel="${state.activeMenu}:${key}"${index===0?"":" hidden"}><p>${escapeHtml(uiText(state.locale, `Select a record to view its ${en.toLowerCase()} details. No records are fabricated.`, `برای مشاهده جزئیات «${fa}» یک رکورد انتخاب کنید. هیچ رکوردی ساخته نشده است.`))}</p></section>`).join("")}</div></section>
    <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "This is the visual register shell. Create, edit, delete and persistence actions remain disabled until the authoritative module service is connected.", "این پوسته بصری فهرست است. عملیات ایجاد، ویرایش، حذف و ذخیره تا اتصال سرویس مرجع ماژول غیرفعال هستند."))}</p>
  </div>`;
}

function renderCalendarCatalog(state: WorkspaceState): string {
  const catalog = state.calendarCatalog;
  if (catalog.status === "unavailable") {
    const message = uiText(state.locale, "Calendar catalogue unavailable", "فهرست تقویم‌ها در دسترس نیست");
    return '<div class="cp-calendar-empty">' + escapeHtml(message) + ' (' + escapeHtml(catalog.errorCode ?? "unknown") + ')</div>';
  }
  if (catalog.status !== "loaded") {
    return '<div class="cp-calendar-empty">' + escapeHtml(uiText(state.locale, "Calendar catalogue has not been loaded.", "فهرست تقویم‌ها هنوز بارگذاری نشده است.")) + '</div>';
  }
  if (!catalog.calendars.length) {
    return '<div class="cp-calendar-empty">' + escapeHtml(uiText(state.locale, "No calendar records exist for this project.", "برای این پروژه رکورد تقویمی وجود ندارد.")) + '</div>';
  }
  const headings = [
    ["Calendar ID", "شناسه تقویم"], ["Name", "نام"], ["Type", "نوع"],
    ["Kind", "ماهیت"], ["Version", "نسخه"], ["Revision", "ویرایش"],
  ];
  const head = headings.map(([en, fa]) => '<th>' + escapeHtml(uiText(state.locale, en, fa)) + '</th>').join("");
  const rows = catalog.calendars.map((calendar) => '<tr><td>' +
    escapeHtml(calendar.calendarId) + '</td><td>' + escapeHtml(calendar.name) +
    '</td><td>' + escapeHtml(calendar.calendarType) + '</td><td>' +
    escapeHtml(calendar.kind) + '</td><td>' + escapeHtml(calendar.calendarVersion) +
    '</td><td>' + escapeHtml(String(calendar.recordRevision)) + '</td></tr>').join("");
  return '<div class="cp-register-table-wrap"><table><thead><tr>' + head +
    '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}


type ProjectRegisterSort = "name" | "start_date" | "status";
type ProjectRegisterState = {
  query: string;
  domain: string;
  status: string;
  sort: ProjectRegisterSort;
  selectedId: string | null;
  collapsed: Set<string>;
};
const projectRegisterStates = new WeakMap<HTMLElement, ProjectRegisterState>();
const PROJECT_DOMAIN_FILTER_ALL = "__all__";
const PROJECT_DOMAIN_FILTER_UNCLASSIFIED = "__unclassified__";
const PROJECT_STATUS_FILTER_ALL = "__all__";
const PROJECT_STATUS_VALUES = ["active", "inactive", "planned", "what_if"] as const;
const PROJECT_DOMAIN_ORDER = [
  "construction",
  "oil_gas",
  "infrastructure",
  "industrial",
  "energy",
  "other",
] as const;

function businessDomainLabel(locale: string, domain: string | undefined): string {
  switch (domain) {
    case "construction": return uiText(locale, "Construction", "ساخت‌وساز");
    case "oil_gas": return uiText(locale, "Oil & Gas", "نفت و گاز");
    case "infrastructure": return uiText(locale, "Infrastructure", "زیرساخت");
    case "industrial": return uiText(locale, "Industrial", "صنعتی");
    case "energy": return uiText(locale, "Energy", "انرژی");
    case "other": return uiText(locale, "Other", "سایر");
    default: return uiText(locale, "Not classified", "طبقه‌بندی‌نشده");
  }
}

function projectStatusLabel(locale: string, status: string | undefined): string {
  switch (status) {
    case "inactive": return uiText(locale, "Inactive", "غیرفعال");
    case "planned": return uiText(locale, "Planned", "برنامه‌ریزی‌شده");
    case "what_if": return uiText(locale, "What-If", "فرضی");
    default: return uiText(locale, "Active", "فعال");
  }
}

function projectRegisterStateFor(container: HTMLElement): ProjectRegisterState {
  let register = projectRegisterStates.get(container);
  if (!register) {
    register = { query: "", domain: PROJECT_DOMAIN_FILTER_ALL, status: PROJECT_STATUS_FILTER_ALL, sort: "name", selectedId: null, collapsed: new Set() };
    projectRegisterStates.set(container, register);
  }
  return register;
}

function sortProjectRows(rows: readonly ProjectSummary[], sort: ProjectRegisterSort, locale: string): ProjectSummary[] {
  const byName = (a: ProjectSummary, b: ProjectSummary): number =>
    (a.name || a.project_id).localeCompare(b.name || b.project_id, locale);
  return [...rows].sort((a, b) => {
    if (sort === "start_date") {
      const left = a.start_date ?? "";
      const right = b.start_date ?? "";
      if (!left && !right) return byName(a, b);
      if (!left) return 1;
      if (!right) return -1;
      return left.localeCompare(right) || byName(a, b);
    }
    if (sort === "status") {
      return (a.status ?? "active").localeCompare(b.status ?? "active") || byName(a, b);
    }
    return byName(a, b);
  });
}

function renderProjectRegister(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions): string {
  const locale = state.locale;
  const currentId = state.context.project_id;
  const listed = options.projects;
  if (!listed) {
    return `<section class="cp-project-register" data-project-register aria-busy="true"><p class="cp-project-register-empty">${escapeHtml(uiText(locale, "Loading the session-authorized project list…", "در حال بارگذاری فهرست پروژه‌های مجاز نشست…"))}</p></section>`;
  }
  const register = projectRegisterStateFor(container);
  const summary = options.projectSummary ?? null;
  // The session list is authoritative for which projects exist; the freshly
  // read summary replaces the list's row for the open project so a renamed
  // project never shows a stale name.
  const rows: ProjectSummary[] = listed.map((row) => (row.project_id === currentId && summary ? summary : row));
  if (summary && !rows.some((row) => row.project_id === currentId)) rows.unshift(summary);

  const query = register.query.trim().toLocaleLowerCase(locale);
  const matches = (row: ProjectSummary): boolean => {
    const domain = row.business_domain ?? "";
    const domainOk = register.domain === PROJECT_DOMAIN_FILTER_ALL
      || (register.domain === PROJECT_DOMAIN_FILTER_UNCLASSIFIED ? !domain : domain === register.domain);
    if (!domainOk) return false;
    const status = row.status ?? "active";
    if (register.status !== PROJECT_STATUS_FILTER_ALL && status !== register.status) return false;
    if (!query) return true;
    const haystack = [row.project_id, row.name, row.description ?? "", businessDomainLabel(locale, domain), projectStatusLabel(locale, status)]
      .join(" ")
      .toLocaleLowerCase(locale);
    return haystack.includes(query);
  };
  const visibleRows = sortProjectRows(rows.filter(matches), register.sort, locale);
  const selected = rows.find((row) => row.project_id === register.selectedId)
    ?? rows.find((row) => row.project_id === currentId)
    ?? null;
  const selectedId = selected?.project_id ?? null;

  const presentDomains = [...new Set(rows.map((row) => row.business_domain ?? ""))]
    .sort((a, b) => {
      const left = a ? PROJECT_DOMAIN_ORDER.indexOf(a as typeof PROJECT_DOMAIN_ORDER[number]) : PROJECT_DOMAIN_ORDER.length;
      const right = b ? PROJECT_DOMAIN_ORDER.indexOf(b as typeof PROJECT_DOMAIN_ORDER[number]) : PROJECT_DOMAIN_ORDER.length;
      return left - right;
    });
  const domainOptions = [
    `<option value="${PROJECT_DOMAIN_FILTER_ALL}"${register.domain === PROJECT_DOMAIN_FILTER_ALL ? " selected" : ""}>${escapeHtml(uiText(locale, "All business domains", "همهٔ حوزه‌های کاری"))}</option>`,
    ...presentDomains.map((domain) => {
      const value = domain || PROJECT_DOMAIN_FILTER_UNCLASSIFIED;
      return `<option value="${escapeAttribute(value)}"${register.domain === value ? " selected" : ""}>${escapeHtml(businessDomainLabel(locale, domain))} (${rows.filter((row) => (row.business_domain ?? "") === domain).length})</option>`;
    }),
  ].join("");

  const presentStatuses = PROJECT_STATUS_VALUES.filter((status) =>
    rows.some((row) => (row.status ?? "active") === status));
  const statusOptions = [
    `<option value="${PROJECT_STATUS_FILTER_ALL}"${register.status === PROJECT_STATUS_FILTER_ALL ? " selected" : ""}>${escapeHtml(uiText(locale, "All project statuses", "همهٔ وضعیت‌های پروژه"))}</option>`,
    ...presentStatuses.map((status) =>
      `<option value="${status}"${register.status === status ? " selected" : ""}>${escapeHtml(projectStatusLabel(locale, status))} (${rows.filter((row) => (row.status ?? "active") === status).length})</option>`),
  ].join("");

  const groups = new Map<string, ProjectSummary[]>();
  for (const row of visibleRows) {
    const key = row.business_domain ?? "";
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  const orderedGroups = [...groups.entries()].sort((a, b) => {
    const left = a[0] ? PROJECT_DOMAIN_ORDER.indexOf(a[0] as typeof PROJECT_DOMAIN_ORDER[number]) : PROJECT_DOMAIN_ORDER.length;
    const right = b[0] ? PROJECT_DOMAIN_ORDER.indexOf(b[0] as typeof PROJECT_DOMAIN_ORDER[number]) : PROJECT_DOMAIN_ORDER.length;
    return left - right;
  });

  const tree = orderedGroups.length
    ? `<ul class="cp-project-domain-groups">${orderedGroups.map(([domain, groupRows]) => {
      const key = domain || PROJECT_DOMAIN_FILTER_UNCLASSIFIED;
      const collapsed = register.collapsed.has(key);
      const projects = groupRows.map((row) => {
        const active = row.project_id === selectedId;
        return `<li><button type="button" class="cp-project-tree-project${active ? " is-selected" : ""}" data-project-select="${escapeAttribute(row.project_id)}" aria-pressed="${active}" title="${escapeAttribute(`${row.project_id} · ${projectStatusLabel(locale, row.status)}`)}"><strong>${escapeHtml(row.name || row.project_id)}</strong><small>${escapeHtml(row.project_id)}</small>${row.project_id === currentId ? `<span class="cp-project-current">${escapeHtml(uiText(locale, "Open", "باز"))}</span>` : ""}</button></li>`;
      }).join("");
      return `<li class="cp-project-domain-group${collapsed ? " is-collapsed" : ""}" data-project-domain-group="${escapeAttribute(key)}"><button type="button" class="cp-project-domain-toggle" data-project-domain-toggle="${escapeAttribute(key)}" aria-expanded="${!collapsed}"><span class="cp-project-domain-name">${escapeHtml(businessDomainLabel(locale, domain))}</span><span class="cp-project-domain-count">${groupRows.length}</span></button>${collapsed ? "" : `<ul class="cp-project-domain-projects">${projects}</ul>`}</li>`;
    }).join("")}</ul>`
    : `<p class="cp-project-register-empty" data-project-no-matches>${rows.length ? escapeHtml(uiText(locale, "No projects match the current search, business domain or project status filter.", "هیچ پروژه‌ای با جست‌وجو، حوزهٔ کاری یا فیلتر وضعیت پروژهٔ فعلی مطابقت ندارد.")) : escapeHtml(uiText(locale, "The session service returned no projects.", "سرویس نشست هیچ پروژه‌ای برنگرداند."))}</p>`;

  const dateSystemLabel = (row: ProjectSummary): string => row.date_system === "jalali"
    ? uiText(locale, "Jalali", "شمسی")
    : row.date_system === "gregorian" ? uiText(locale, "Gregorian", "میلادی") : "—";
  const tableRows = visibleRows.length
    ? visibleRows.map((row) => {
      const current = row.project_id === currentId;
      const active = row.project_id === selectedId;
      return `<tr data-project-row="${escapeAttribute(row.project_id)}"${current ? ' aria-current="true"' : ""} data-project-domain="${escapeAttribute(row.business_domain ?? "")}" data-project-selected="${active}" tabindex="0" aria-selected="${active}"><td><code>${escapeHtml(row.project_id)}</code></td><td>${escapeHtml(row.name || row.project_id)}</td><td>${escapeHtml(businessDomainLabel(locale, row.business_domain))}</td><td>${escapeHtml(row.start_date || "—")}</td><td>${escapeHtml(dateSystemLabel(row))}</td><td>${escapeHtml(row.primary_calendar_id || "—")}</td><td>${escapeHtml(projectStatusLabel(locale, row.status))}</td><td>${current ? `<span class="cp-project-current">${escapeHtml(uiText(locale, "Open", "باز"))}</span>` : `<button type="button" data-project-open="${escapeAttribute(row.project_id)}">${escapeHtml(uiText(locale, "Open", "بازکردن"))}</button>`}</td></tr>`;
    }).join("")
    : `<tr><td colspan="8">${escapeHtml(rows.length ? uiText(locale, "No projects match the current search, business domain or project status filter.", "هیچ پروژه‌ای با جست‌وجو، حوزهٔ کاری یا فیلتر وضعیت پروژهٔ فعلی مطابقت ندارد.") : uiText(locale, "The session service returned no projects.", "سرویس نشست هیچ پروژه‌ای برنگرداند."))}</td></tr>`;

  const selection = selected
    ? `<section class="cp-project-selection" data-project-selection aria-live="polite" aria-label="${escapeAttribute(uiText(locale, "Selected project", "پروژهٔ انتخاب‌شده"))}">
        <header><h3>${escapeHtml(uiText(locale, "Selected project", "پروژهٔ انتخاب‌شده"))}</h3><span>${selected.project_id === currentId ? escapeHtml(uiText(locale, "Currently open", "اکنون باز است")) : escapeHtml(uiText(locale, "Not open", "باز نیست"))}</span></header>
        <div class="cp-project-selection-fields">
          <div><span>${escapeHtml(uiText(locale, "Project ID", "شناسه پروژه"))}</span><strong>${escapeHtml(selected.project_id)}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Project Name", "نام پروژه"))}</span><strong>${escapeHtml(selected.name || selected.project_id)}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Business Domain", "حوزهٔ کاری"))}</span><strong>${escapeHtml(businessDomainLabel(locale, selected.business_domain))}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Status", "وضعیت"))}</span><strong>${escapeHtml(projectStatusLabel(locale, selected.status))}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Start Date", "تاریخ شروع"))}</span><strong>${escapeHtml(selected.start_date || "—")}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Date System", "تقویم"))}</span><strong>${escapeHtml(dateSystemLabel(selected))}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Primary Calendar", "تقویم اصلی"))}</span><strong>${escapeHtml(selected.primary_calendar_id || "—")}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Organization", "سازمان"))}</span><strong>${escapeHtml(selected.tenant_id)}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Data revision", "ویرایش داده"))}</span><strong>R${selected.revision}</strong></div>
          <div><span>${escapeHtml(uiText(locale, "Configuration revision", "ویرایش تنظیمات"))}</span><strong>R${selected.settings_revision ?? 0}</strong></div>
        </div>
        ${selected.description?.trim() ? `<p class="cp-project-selection-description">${escapeHtml(selected.description.trim())}</p>` : ""}
        <div class="cp-project-selection-actions">
          ${selected.project_id === currentId
            ? `<button type="button" data-project-settings>${escapeHtml(uiText(locale, "Edit project properties", "ویرایش مشخصات پروژه"))}</button>`
            : `<button type="button" data-project-open="${escapeAttribute(selected.project_id)}">${escapeHtml(uiText(locale, "Open project", "بازکردن پروژه"))}</button>`}
        </div>
      </section>`
    : `<p class="cp-project-register-empty">${escapeHtml(uiText(locale, "Select a project in the business domain tree or the table to see its record.", "برای دیدن رکورد پروژه، آن را در درخت حوزهٔ کاری یا جدول انتخاب کنید."))}</p>`;

  return `<section class="cp-project-register" data-project-register aria-label="${escapeAttribute(uiText(locale, "Project Table", "جدول پروژه‌ها"))}">
    <div class="cp-project-register-toolbar">
      <label class="cp-project-register-field"><span>${escapeHtml(uiText(locale, "Search projects", "جست‌وجوی پروژه‌ها"))}</span><input type="search" data-project-search value="${escapeAttribute(register.query)}" autocomplete="off" placeholder="${escapeAttribute(uiText(locale, "Project ID, name or description", "شناسه، نام یا توضیح پروژه"))}"></label>
      <label class="cp-project-register-field"><span>${escapeHtml(uiText(locale, "Business Domain", "حوزهٔ کاری"))}</span><select data-project-domain-filter>${domainOptions}</select></label>
      <label class="cp-project-register-field"><span>${escapeHtml(uiText(locale, "Project status", "وضعیت پروژه"))}</span><select data-project-status-filter>${statusOptions}</select></label>
      <label class="cp-project-register-field"><span>${escapeHtml(uiText(locale, "Sort by", "ترتیب بر اساس"))}</span><select data-project-sort><option value="name"${register.sort === "name" ? " selected" : ""}>${escapeHtml(uiText(locale, "Name", "نام"))}</option><option value="start_date"${register.sort === "start_date" ? " selected" : ""}>${escapeHtml(uiText(locale, "Start date", "تاریخ شروع"))}</option><option value="status"${register.sort === "status" ? " selected" : ""}>${escapeHtml(uiText(locale, "Status", "وضعیت"))}</option></select></label>
      <span class="cp-project-register-count" data-project-register-count role="status" aria-live="polite">${escapeHtml(uiText(locale, `${visibleRows.length} of ${rows.length} projects`, `${visibleRows.length} از ${rows.length} پروژه`))}</span>
      ${query || register.domain !== PROJECT_DOMAIN_FILTER_ALL || register.status !== PROJECT_STATUS_FILTER_ALL ? `<button type="button" class="cp-project-filter-reset" data-project-filter-reset>${escapeHtml(uiText(locale, "Clear filters", "پاک‌کردن فیلترها"))}</button>` : ""}
    </div>
    <div class="cp-project-register-layout">
      <nav class="cp-project-domain-tree" aria-label="${escapeAttribute(uiText(locale, "Business Domain hierarchy", "سلسله‌مراتب حوزهٔ کاری"))}">
        <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(locale, "Business Domains", "حوزه‌های کاری"))}</h3><span>${escapeHtml(uiText(locale, "EPS-level classification", "طبقه‌بندی سطح سازمانی"))}</span></div>
        ${tree}
      </nav>
      <div class="cp-project-register-main">
        <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(locale, "Project Table", "جدول پروژه‌ها"))}</h3><span>${escapeHtml(uiText(locale, "Server project list", "فهرست پروژه‌های سرور"))}</span></div>
        <div class="cp-project-table-wrap">
          <table class="cp-project-register-table cp-project-table">
            <thead><tr><th>${escapeHtml(uiText(locale, "Project ID", "شناسه پروژه"))}</th><th>${escapeHtml(uiText(locale, "Project Name", "نام پروژه"))}</th><th>${escapeHtml(uiText(locale, "Business Domain", "حوزهٔ کاری"))}</th><th>${escapeHtml(uiText(locale, "Start Date", "تاریخ شروع"))}</th><th>${escapeHtml(uiText(locale, "Date System", "تقویم"))}</th><th>${escapeHtml(uiText(locale, "Primary Calendar", "تقویم اصلی"))}</th><th>${escapeHtml(uiText(locale, "Status", "وضعیت"))}</th><th>${escapeHtml(uiText(locale, "Open", "بازکردن"))}</th></tr></thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
        ${selection}
      </div>
    </div>
  </section>`;
}

function refreshProjectRegister(container: HTMLElement): void {
  const record = workspaceRenderRecords.get(container);
  const section = container.querySelector<HTMLElement>("[data-project-register]");
  if (!record || !section) return;
  const active = document.activeElement as HTMLElement | null;
  const focusKind = active?.dataset.projectSearch !== undefined ? "search"
    : active?.dataset.projectDomainFilter !== undefined ? "domain"
    : active?.dataset.projectStatusFilter !== undefined ? "status"
    : active?.dataset.projectSort !== undefined ? "sort"
    : active?.dataset.projectDomainToggle !== undefined ? `domain:${active.dataset.projectDomainToggle}`
    : active?.dataset.projectSelect !== undefined ? `project:${active.dataset.projectSelect}`
    : null;
  const caret = active instanceof HTMLInputElement && focusKind === "search" ? active.selectionStart : null;
  section.outerHTML = renderProjectRegister(container, record.state, record.options);
  if (!focusKind) return;
  const selector = focusKind === "search" ? "[data-project-search]"
    : focusKind === "domain" ? "[data-project-domain-filter]"
    : focusKind === "status" ? "[data-project-status-filter]"
    : focusKind === "sort" ? "[data-project-sort]"
    : focusKind.startsWith("domain:") ? `[data-project-domain-toggle="${CSS.escape(focusKind.slice(7))}"]`
    : `[data-project-select="${CSS.escape(focusKind.slice(8))}"]`;
  const next = container.querySelector<HTMLElement>(selector);
  next?.focus({ preventScroll: true });
  if (next instanceof HTMLInputElement && caret !== null) {
    next.setSelectionRange(caret, caret);
  }
}

function renderP6ModuleStage(container: HTMLElement, state: WorkspaceState, t: WorkspaceLabels, options: WorkspaceRendererOptions): string {
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
      const summary = options.projectSummary ?? null;
      body = `
        <div class="cp-project-window-toolbar">
          ${controls(`${moduleButton("wbs", "wbs", uiText(state.locale, "Open WBS structure", "بازکردن ساختار WBS"))}${moduleButton("tools", "tools", uiText(state.locale, "Import / Export", "ورود / خروجی"))}${projectSettingsButton(state, t)}`)}
          <span class="cp-project-window-scope">${escapeHtml(uiText(state.locale, "Session-authorized projects", "پروژه‌های مجاز نشست"))}</span>
        </div>
        ${renderProjectRegister(container, state, options)}
        <section class="cp-project-structure-summary" aria-label="${escapeAttribute(uiText(state.locale, "Project structure summary", "خلاصه ساختار پروژه"))}">
          <div class="cp-project-register-heading"><h3>${escapeHtml(uiText(state.locale, "Project Structure", "ساختار پروژه"))}</h3><span>${escapeHtml(uiText(state.locale, "Loaded WBS hierarchy", "سلسله‌مراتب WBS بارگذاری‌شده"))}</span></div>
          ${state.wbsNodes.length ? `<div class="cp-project-wbs-list">${state.wbsNodes.map((node) => `<div class="cp-project-wbs-row"><span>${escapeHtml(node.localCode)}</span><strong>${escapeHtml(node.name)}</strong><small>R${node.recordRevision}</small></div>`).join("")}</div>` : `<p class="cp-empty">${escapeHtml(uiText(state.locale, "No WBS elements are loaded for this project.", "هیچ عنصر WBS برای این پروژه بارگذاری نشده است."))}</p>`}
        </section>
        <p class="cp-project-window-note">${escapeHtml(uiText(state.locale, "The register lists exactly the projects the session service returned, grouped by the Business Domain stored on each project. Opening a project re-reads that project's workspace from the server; nothing outside the session's membership is invented.", "این فهرست دقیقاً همان پروژه‌هایی را نشان می‌دهد که سرویس نشست برگردانده و بر اساس حوزهٔ کاری ذخیره‌شده در هر پروژه گروه‌بندی شده است. بازکردن هر پروژه، محیط کار آن را از سرور دوباره می‌خواند و هیچ پروژه‌ای بیرون از عضویت نشست ساخته نمی‌شود."))}</p>
        ${summary ? "" : `<p class="cp-project-window-note" data-project-metadata-pending="true">${escapeHtml(uiText(state.locale, "The authoritative project record has not been read yet, so schedule fields stay blank instead of showing placeholder values.", "رکورد مرجع پروژه هنوز خوانده نشده است؛ بنابراین فیلدهای زمان‌بندی به‌جای نمایش مقدار جایگزین، خالی می‌مانند."))}</p>`}`;
      break;
    }
    case "wbs": {
      const wbsView = wbsViewByContainer.get(container) ?? "table";
      const clip = wbsClipboardLabels(state.locale);
      const clipEntry = wbsClipboardByContainer.get(container) ?? null;
      const hasSelection = Boolean(state.selectedWbsId);
      body = `<div class="cp-wbs-window"><div class="cp-register-toolbar"><strong>${escapeHtml(uiText(state.locale, "Work Breakdown Structure", "ساختار شکست کار"))}</strong><div><button type="button" data-rail-action="wbs">${escapeHtml(uiText(state.locale, "Add WBS", "افزودن WBS"))}</button><button type="button" data-wbs-cut ${hasSelection ? "" : "disabled"}>${escapeHtml(clip.cut)}</button><button type="button" data-wbs-copy ${hasSelection ? "" : "disabled"}>${escapeHtml(clip.copy)}</button><button type="button" data-wbs-paste ${hasSelection && clipEntry ? "" : "disabled"}>${escapeHtml(clip.paste)}</button><button type="button" data-wbs-delete ${hasSelection ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button><span data-wbs-clipboard class="cp-wbs-clipboard">${escapeHtml(wbsClipboardText(state.locale, clipEntry))}</span><p class="cp-wbs-clipboard-error" data-wbs-clipboard-error role="alert" hidden></p><span class="cp-wbs-view-toggle" role="group" aria-label="${escapeAttribute(uiText(state.locale, "WBS view", "نمای WBS"))}"><button type="button" data-wbs-view="table" aria-pressed="${wbsView === "table"}" class="${wbsView === "table" ? "is-active" : ""}">${escapeHtml(uiText(state.locale, "Table View", "نمای جدولی"))}</button><button type="button" data-wbs-view="chart" aria-pressed="${wbsView === "chart"}" class="${wbsView === "chart" ? "is-active" : ""}">${escapeHtml(uiText(state.locale, "Chart View", "نمای نمودار"))}</button></span></div></div><div class="cp-wbs-window-layout"><section><h3>${escapeHtml(uiText(state.locale, "WBS Hierarchy", "سلسله‌مراتب WBS"))}</h3><div data-wbs-hierarchy>${wbsView === "chart" ? renderWbsChart(state.wbsNodes, state.selectedWbsId, state.locale, t) : renderWbsTable(state.wbsNodes, state.activities, state.selectedWbsId, state.locale, t)}</div></section><section>${renderWbsDetails(state, wbsDetailsTabByContainer.get(container) ?? "general")}</section></div><p class="cp-wbs-delete-guidance" data-wbs-delete-guidance role="note" hidden></p><p class="cp-register-notice">${escapeHtml(uiText(state.locale, "The table and chart are generated from one ordered projection of the loaded WBS hierarchy, so both show the same persisted nodes in the same order. Selecting a row or card reads the same authoritative WBS record; detail tabs show only fields the WBS core returns.", "جدول و نمودار از یک نمای مرتب واحد از سلسله‌مراتب WBS بارگذاری‌شده ساخته می‌شوند؛ بنابراین هر دو همان گره‌های ذخیره‌شده را با همان ترتیب نشان می‌دهند. انتخاب هر سطر یا کارت همان رکورد مرجع WBS را می‌خواند و زبانه‌های جزئیات فقط فیلدهای برگشتی هستهٔ WBS را نمایش می‌دهند."))}</p></div>`;
      break;
    }
    case "calendars":
      body = `
        <div class="cp-calendar-window" data-calendar-page>
          <div class="cp-calendar-window-toolbar">
            <strong>${escapeHtml(uiText(state.locale, "Calendar Register", "فهرست تقویم‌ها"))}</strong>
            <div><button type="button" disabled title="${escapeAttribute(uiText(state.locale, "Calendar persistence is not connected yet.", "ذخیره‌سازی تقویم هنوز متصل نشده است."))}">${escapeHtml(uiText(state.locale, "New Calendar", "تقویم جدید"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Edit", "ویرایش"))}</button><button type="button" disabled>${escapeHtml(uiText(state.locale, "Delete", "حذف"))}</button></div>
          </div>
          <div class="cp-calendar-window-layout">
            <section class="cp-calendar-register">
              <div class="cp-calendar-section-head"><strong>${escapeHtml(uiText(state.locale, "Available Calendars", "تقویم‌های موجود"))}</strong></div>
              ${renderCalendarCatalog(state)}
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
    case "assignments":
      body = `<div class="cp-register-window" data-assignments-page></div>`;
      break;
    case "roles":
      body = `<div class="cp-register-window cp-roles-window" data-roles-page></div>`;
      break;
    case "resources":
      body = `<div class="cp-register-window cp-resources-window" data-resources-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Resource Register", "فهرست منابع"))}"></div>`;
      break;
    case "expenses":
      body = `<div class="cp-register-window" data-expenses-page role="region" aria-label="${escapeHtml(uiText(state.locale, "Project Expenses", "هزینه‌های پروژه"))}"></div>`;
      break;
    case "documents":
      body = `<div class="cp-register-window cp-documents-window" data-documents-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Documents", "اسناد پروژه"))}"></div>`;
      break;
    case "cost":
      body = `<div class="cp-register-window" data-cost-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Cost Overview", "نمای کلی هزینه"))}"></div>`;
      break;
    case "progress":
      body = `<div class="cp-register-window" data-progress-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Activity Progress", "پیشرفت فعالیت‌ها"))}"></div>`;
      break;
    case "control":
      body = `
        <div class="cp-control-window">
          <div class="cp-p6-module-metrics">
            ${metric(state.inspections.length + state.qualityRecords.length, t.assurance)}
            ${metric(state.safetyObservations.length, t.safety)}
            ${metric(state.fieldIssues.length, t.issues)}
            ${metric(state.punchItems.length, t.punchCloseout)}
          </div>
          ${controls(`${moduleButton("forms", "forms", uiText(state.locale, "Forms & Workflows", "فرم‌ها و گردش‌کار"))}${moduleButton("tools", "warning", uiText(state.locale, "Open control records", "بازکردن سوابق کنترل"))}`)}
          ${renderControlStage(state, t)}
        </div>`;
      break;
    case "reports":
      body = `<div class="cp-register-window cp-reports-window" data-reports-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Reports", "گزارش‌های پروژه"))}"></div>`;
      break;
    case "administration":
      body = `<div class="cp-register-window cp-administration-window" data-administration-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Administration", "مدیریت پروژه"))}"></div>`;
      break;
    case "exchange":
      body = `<div class="cp-register-window cp-exchange-window" data-exchange-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Import and Export", "ورود و خروجی پروژه"))}"></div>`;
      break;
    case "backup":
      body = `<div class="cp-register-window cp-backup-window" data-backup-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Backup and Recovery", "پشتیبان‌گیری و بازیابی پروژه"))}"></div>`;
      break;
    case "issues":
      body = `<div class="cp-register-window cp-issues-window" data-issues-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Issues", "مسائل پروژه"))}"></div>`;
      break;
    case "risks":
      body = `<div class="cp-register-window cp-risks-window" data-risks-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Risks", "ریسک‌های پروژه"))}"></div>`;
      break;
    case "thresholds":
      body = `<div class="cp-register-window cp-thresholds-window" data-thresholds-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Thresholds", "آستانه‌های پروژه"))}"></div>`;
      break;
    case "tracking":
      body = `<div class="cp-register-window cp-tracking-window" data-tracking-page role="region" aria-label="${escapeAttribute(uiText(state.locale, "Project Tracking", "رهگیری پروژه"))}"></div>`;
      break;
    case "settings":
      body = `
        <p>${escapeHtml(uiText(state.locale, "Project settings are edited through the existing authoritative project service.", "تنظیمات پروژه از طریق سرویس مرجع موجود پروژه ویرایش می‌شود."))}</p>
        ${controls(projectSettingsButton(state, t))}
        ${renderSettingsLayoutAdministration(state, options)}`;
      break;
    default:
      body = "";
  }
  return `<section id="cp-p6-module-stage" class="cp-p6-module-stage" data-p6-module="${escapeAttribute(state.activeMenu)}" data-workspace-menu="${escapeAttribute(state.activeMenu)}">
    <header class="cp-p6-module-head"><div><h2>${escapeHtml(title)}</h2><span>${escapeHtml(status)}</span></div><span class="cp-p6-module-surface">${escapeHtml(uiText(state.locale, "Workspace page", "صفحهٔ محیط کار"))}</span></header>
    <div class="cp-p6-module-body">${body}</div>
  </section>`;
}

function moduleButton(action: string, icon: WorkspaceIconName, label: string): string {
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

  if (state.activeMenu === "progress") {
    copy = locale === "fa"
      ? { title: "نمای پیشرفت پروژه", message: "پیشرفت هر فعالیت از سرویس مشترک فعالیت خوانده و ویرایش می‌شود. برای ثبت یا تغییر فعالیت‌ها از جدول فعالیت‌ها و برای بازمحاسبهٔ تاریخ‌ها از اجرای زمان‌بندی استفاده کنید؛ در این صفحه درصد یا تاریخ ساختگی نمایش داده نمی‌شود." }
      : { title: "Project progress", message: "Activity progress is read from and edited through the shared activity service. Use the activity grid to add activities and Run Schedule to recalculate dates; this page does not invent percentages or dates." };
  } else if (state.activeMenu === "cost") {
    copy = locale === "fa"
      ? { title: "هزینه و جریان مالی", message: "نمای هزینه از هزینه‌ها، حساب‌های هزینه، دوره‌های مالی، مبناها و مدل خواندن مشترک ارزش کسب‌شده خوانده می‌شود. نمودارهای مالی تکمیلی هنوز در این پیش‌نمایش وجود ندارند و هیچ محاسبه‌ای در مرورگر انجام نمی‌شود." }
      : { title: "Cost & financial control", message: "The cost overview reads stored expenses, cost accounts, financial periods, baselines and the shared earned-value read model. Additional financial charts are not available in this preview, and no calculation is performed in the browser." };
  } else if (state.activeMenu === "control" && !hasControlRecords) {
    copy = locale === "fa"
      ? { title: "کنترل پروژه", message: "هنوز سابقه‌ای برای خلاصه کنترل، گزارش روزانه، بازرسی، مسئله، تغییر یا ادعا در دسترس نیست. با ثبت داده‌های معتبر، این بخش پر می‌شود." }
      : { title: "Project controls", message: "No control summary, daily log, inspection, issue, change or claim records are available yet. This area will populate when authoritative records are saved." };
  }

  if (!copy) return "";
  return `<section class="cp-panel cp-module-empty-state" data-workspace-menu="${state.activeMenu}" aria-live="polite"><h2>${escapeHtml(copy.title)}</h2><p>${escapeHtml(copy.message)}</p></section>`;
}

function renderFullNavigationMenu(state: WorkspaceState, icons: Record<WorkspaceState["activeMenu"], WorkspaceIconName>): string {
  const t = getWorkspaceLabels(state.locale);
  return `<nav class="cp-p6-flyout-tree" aria-label="${escapeAttribute(t.mainMenu)}">
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Project workspace", "محیط پروژه"))}</span>
      ${menuButton("project", t.project, state, icons.project)}
      ${menuButton("wbs", uiText(state.locale, "WBS", "ساختار شکست"), state, icons.wbs)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Planning & execution", "برنامه‌ریزی و اجرا"))}</span>
      ${menuButton("schedule", t.schedule, state, icons.schedule)}
      ${menuButton("progress", t.progress, state, icons.progress)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Resources & cost", "منابع و هزینه"))}</span>
      ${menuButton("resources", t.resources, state, icons.resources)}
      ${menuButton("assignments", uiText(state.locale, "Assignments", "تخصیص‌ها"), state, icons.assignments)}
      ${menuButton("calendars", uiText(state.locale, "Calendars", "تقویم‌ها"), state, icons.calendars)}
      ${menuButton("roles", uiText(state.locale, "Roles", "نقش‌ها"), state, icons.roles)}
      ${menuButton("cost", t.cost, state, icons.cost)}
      ${menuButton("expenses", uiText(state.locale, "Expenses", "هزینه‌ها"), state, icons.expenses)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "Project information", "اطلاعات پروژه"))}</span>
      ${menuButton("documents", t.documents, state, icons.documents)}
      ${menuButton("reports", t.reports, state, icons.reports)}
      ${menuButton("tracking", uiText(state.locale, "Tracking", "رهگیری"), state, icons.tracking)}
      ${menuButton("control", t.control, state, icons.control)}
      ${menuButton("thresholds", uiText(state.locale, "Thresholds", "آستانه‌ها"), state, icons.thresholds)}
      ${menuButton("risks", uiText(state.locale, "Risks", "ریسک‌ها"), state, icons.risks)}
      ${menuButton("issues", uiText(state.locale, "Issues", "مسائل"), state, icons.issues)}
    </div>
    <div class="cp-p6-flyout-group"><span>${escapeHtml(uiText(state.locale, "CUBI tools & administration", "ابزارها و مدیریت CUBI"))}</span>
      ${railActionButton("forms", uiText(state.locale, "Form Builder", "فرم‌ساز"), "forms")}
      ${menuButton("settings", t.settings, state, icons.settings)}
      ${menuButton("administration", uiText(state.locale, "Administration", "مدیریت"), state, icons.administration)}
      ${menuButton("exchange", uiText(state.locale, "Import / Export", "ورود / خروجی"), state, icons.exchange)}
      ${menuButton("backup", uiText(state.locale, "Backup / Recovery", "پشتیبان‌گیری / بازیابی"), state, icons.backup)}
      ${railActionButton("tools", uiText(state.locale, "Tools", "ابزارها"), "tools")}
    </div>
  </nav>`;
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
    case "wbs":
    case "assignments":
    case "expenses":
    case "issues":
    case "documents":
    case "risks":
    case "thresholds":
    case "calendars":
    case "roles":
    case "tracking":
      return [];
    case "cost":
      return ["#cp-cost-overview", "#cp-cost-registers"];
    case "reports":
      return [];
    case "administration":
    case "exchange":
    case "backup":
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

function renderControlStage(state: WorkspaceState, t: WorkspaceLabels): string {
  const locale = state.locale;
  const summary = state.controlSummary;
  if (!summary) {
    return `<section class="cp-control-stage-summary" aria-label="${escapeAttribute(t.controlSummary)}">
      <div class="cp-control-summary-empty">${escapeHtml(uiText(locale, "No control-intelligence snapshot is loaded for this project revision. The record counts above come only from the workspace read model; no analysis is calculated in the browser.", "هیچ تصویر لحظه‌ای از هوش کنترل برای این ویرایش پروژه بارگذاری نشده است. شمارش‌های بالا فقط از مدل خواندن محیط کار می‌آیند و هیچ تحلیلی در مرورگر محاسبه نمی‌شود."))}</div>
    </section>`;
  }
  const metrics = Object.entries(summary.metrics)
    .map(([key, value]) => `<div class="cp-control-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");
  const findings = summary.findings.length
    ? summary.findings.map((finding) => `<article class="cp-control-finding is-${escapeHtml(finding.severity)}">
        <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
        <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
        <div class="cp-control-finding-meta">${escapeHtml(finding.domain)} · ${escapeHtml(finding.severity)} · ${finding.source_refs.length} ${escapeHtml(t.sourceUnit)}</div>
      </article>`).join("")
    : `<div class="cp-empty">—</div>`;
  const actions = summary.proposedActions.length
    ? `<div class="cp-control-actions">${summary.proposedActions.map((action) => `<article class="cp-control-action">
        <strong>${escapeHtml(action.title_key)}</strong>
        <span>${escapeHtml(action.action_type)} · ${action.requires_approval ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
      </article>`).join("")}</div>`
    : `<div class="cp-empty">—</div>`;
  return `<section class="cp-control-stage-summary" aria-label="${escapeAttribute(t.controlSummary)}">
    <div class="cp-control-heading">
      <div><h3>${escapeHtml(t.controlSummary)}</h3><div class="cp-control-result">${escapeHtml(summary.resultId)}</div></div>
      <time datetime="${escapeAttribute(summary.generatedAt)}">${escapeHtml(summary.generatedAt)}</time>
    </div>
    <div class="cp-control-section"><h4>${escapeHtml(t.metrics)}</h4><div class="cp-control-metrics">${metrics || '<div class="cp-empty">—</div>'}</div></div>
    <div class="cp-control-section"><h4>${escapeHtml(t.findings)}</h4><div class="cp-control-findings">${findings}</div></div>
    <div class="cp-control-section"><h4>${escapeHtml(t.proposedActions)}</h4>${actions}</div>
    <p class="cp-register-notice">${escapeHtml(uiText(locale, "Metrics, findings and proposed actions are rendered from the control-room read model for this project revision. This page performs no client-side analysis and invents no finding.", "شاخص‌ها، یافته‌ها و اقدامات پیشنهادی از مدل خواندن اتاق کنترل برای این ویرایش پروژه نمایش داده می‌شوند. این صفحه هیچ تحلیلی در مرورگر انجام نمی‌دهد و هیچ یافته‌ای نمی‌سازد."))}</p>
  </section>`;
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
  counts: ActivityCounts,
  t: WorkspaceLabels,
  groupCount: number,
  filterState?: { filterIds: string; mode: string; title: string; stateLabel: string },
): string {
  const sort = state.activitySort;
  const treeActions = state.activityGroupBy === "wbs" && state.wbsNodes.length > 0
    ? `<span class="cp-activity-tree-actions" role="group" aria-label="${escapeAttribute(uiText(state.locale, "WBS hierarchy", "سلسله‌مراتب ساختار شکست"))}">
      <button type="button" data-wbs-expand-all title="${escapeAttribute(uiText(state.locale, "Expand all WBS branches", "بازکردن همهٔ شاخه‌های ساختار شکست"))}" aria-label="${escapeAttribute(uiText(state.locale, "Expand all", "بازکردن همه"))}">${workspaceIcon("expand")}</button>
      <button type="button" data-wbs-collapse-all title="${escapeAttribute(uiText(state.locale, "Collapse all WBS branches", "بستن همهٔ شاخه‌های ساختار شکست"))}" aria-label="${escapeAttribute(uiText(state.locale, "Collapse all", "بستن همه"))}" ${groupCount ? "" : "disabled"}>${workspaceIcon("collapse")}</button>
      <button type="button" data-wbs-collapse-to title="${escapeAttribute(uiText(state.locale, "Collapse To…", "بستن تا…"))}" aria-label="${escapeAttribute(uiText(state.locale, "Collapse To", "بستن تا"))}" ${groupCount ? "" : "disabled"}>${workspaceIcon("collapseTo")}</button>
    </span>`
    : "";
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
  // Select All covers the whole current scope, including branches that are
  // collapsed, so a filtered or grouped table cannot silently select only the
  // rows the DOM happens to paint.
  const selectAllTitle = uiText(
    state.locale,
    `Select all ${counts.searchMatched} activities in the current filter and search scope; collapsed rows are included`,
    `انتخاب همهٔ ${counts.searchMatched} فعالیت در محدودهٔ فیلتر و جست‌وجوی فعلی؛ ردیف‌های جمع‌شده نیز شامل می‌شوند`,
  );
  return `<div class="cp-activity-toolbar" role="search">
    <label class="cp-activity-filter">
      <span>${escapeHtml(t.activityFilter)}</span>
      <input type="search" data-activity-filter value="${escapeAttribute(state.activityFilter)}" placeholder="${escapeAttribute(t.activityFilterPlaceholder)}" autocomplete="off" spellcheck="false">
    </label>
    <label class="cp-activity-group">
      <span>${escapeHtml(t.groupBy)}</span>
      <select data-activity-group aria-label="${escapeAttribute(t.groupBy)}">
        <option value="none"${state.activityGroupLevels.length === 0 ? " selected" : ""}>${escapeHtml(t.groupNone)}</option>
        <option value="wbs"${state.activityGroupLevels[0]?.fieldId === "wbs" ? " selected" : ""}>${escapeHtml(t.activityWbs)}</option>
        ${WORKSPACE_GROUP_FIELDS.filter((field) => field.id !== "wbs").map((field) =>
          `<option value="${escapeAttribute(field.id)}"${state.activityGroupLevels[0]?.fieldId === field.id ? " selected" : ""}>${escapeHtml(groupFieldLabel(field.id, state.locale))}</option>`).join("")}
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
    ${treeActions}
    ${filterState ? `<output class="cp-activity-filter-state" data-active-filter="${escapeAttribute(filterState.filterIds)}" data-filter-mode="${escapeAttribute(filterState.mode)}" title="${escapeAttribute(filterState.title)}">${escapeHtml(t.activityFilter)}: ${escapeHtml(filterState.stateLabel)}</output>` : ""}
    <span class="cp-activity-scope-actions" role="group" aria-label="${escapeAttribute(uiText(state.locale, "Selection and export", "انتخاب و خروجی"))}">
      <button type="button" class="cp-activity-select-all" data-activity-select-all title="${escapeAttribute(selectAllTitle)}" aria-label="${escapeAttribute(uiText(state.locale, "Select all activities in scope", "انتخاب همهٔ فعالیت‌های محدوده"))}" ${counts.searchMatched ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Select All", "انتخاب همه"))}</button>
      <button type="button" data-activity-export-open title="${escapeAttribute(uiText(state.locale, "Export all, filtered or selected activities", "خروجی همه، فیلترشده یا انتخاب‌شده"))}" aria-label="${escapeAttribute(uiText(state.locale, "Export activities", "خروجی فعالیت‌ها"))}" ${counts.total ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Export…", "خروجی…"))}</button>
    </span>
    <span class="cp-activity-counts" data-activity-counts
      data-count-total="${counts.total}" data-count-filter="${counts.filterMatched}"
      data-count-search="${counts.searchMatched}" data-count-visible="${counts.visible}"
      data-count-selected="${counts.selected}" data-count-selected-scope="${counts.selectedInScope}" aria-live="polite">
      <output data-activity-count title="${escapeAttribute(uiText(state.locale, "Painted rows / project activities", "ردیف‌های نمایش‌داده‌شده / فعالیت‌های پروژه"))}">${counts.visible} / ${counts.total} ${escapeHtml(t.matchingActivities)}</output>
      <span data-count-item="total" title="${escapeAttribute(uiText(state.locale, "Activities in the allowed project read model", "فعالیت‌های مدل خواندنی مجاز پروژه"))}">${escapeHtml(uiText(state.locale, "Total", "کل"))} <strong>${counts.total}</strong></span>
      <span data-count-item="filter" title="${escapeAttribute(uiText(state.locale, "Activities matching the checked Activity Filters", "فعالیت‌های منطبق با فیلترهای فعال"))}">${escapeHtml(uiText(state.locale, "Filter", "فیلتر"))} <strong>${counts.filterMatched}</strong></span>
      <span data-count-item="search" title="${escapeAttribute(uiText(state.locale, "Activities matching the filter and the quick search", "فعالیت‌های منطبق با فیلتر و جست‌وجوی سریع"))}">${escapeHtml(uiText(state.locale, "Search", "جست‌وجو"))} <strong>${counts.searchMatched}</strong></span>
      <span data-count-item="visible" title="${escapeAttribute(uiText(state.locale, "Activity rows painted after grouping and collapse", "ردیف‌های فعالیت پس از گروه‌بندی و جمع‌شدن"))}">${escapeHtml(uiText(state.locale, "Visible", "قابل مشاهده"))} <strong>${counts.visible}</strong></span>
      <span data-count-item="selected" title="${escapeAttribute(uiText(state.locale, "Selected activities in the project", "فعالیت‌های انتخاب‌شده در پروژه"))}">${escapeHtml(uiText(state.locale, "Selected", "انتخاب‌شده"))} <strong>${counts.selected}</strong></span>
      <span data-count-item="selected-scope" title="${escapeAttribute(uiText(state.locale, "Selected activities inside the current scope", "فعالیت‌های انتخاب‌شده در محدودهٔ فعلی"))}">${escapeHtml(uiText(state.locale, "In scope", "در محدوده"))} <strong>${counts.selectedInScope}</strong></span>
    </span>
  </div>`;
}

/**
 * Scope confirmation before any file is produced. Every number comes from the
 * same read model the table and Gantt consume; choosing a scope never adds a
 * row outside it and zero-row scopes stay disabled.
 */
function renderActivityExportDialog(
  counts: ActivityCounts,
  t: WorkspaceLabels,
  state: WorkspaceState,
): string {
  const scopeCopy: Record<ActivityExportScope, { en: string; fa: string }> = {
    all: { en: "All activities", fa: "همهٔ فعالیت‌ها" },
    filtered: { en: "Filtered activities", fa: "فعالیت‌های فیلترشده" },
    selected: { en: "Selected activities", fa: "فعالیت‌های انتخاب‌شده" },
  };
  const rows = ACTIVITY_EXPORT_SCOPES.map((scope) => {
    const count = activityExportScopeCount(scope, counts);
    const active = scope === "all";
    return `<button type="button" class="cp-activity-export-scope${active ? " is-active" : ""}" role="radio" aria-checked="${active ? "true" : "false"}" data-activity-export-scope="${scope}" ${count ? "" : "disabled"}>
      <span>${escapeHtml(uiText(state.locale, scopeCopy[scope].en, scopeCopy[scope].fa))}</span>
      <strong data-export-scope-count>${count}</strong>
    </button>`;
  }).join("");
  return `<dialog class="cp-activity-export-dialog" data-activity-export-dialog data-activity-export-active="all" data-export-total="${counts.total}" data-export-filter="${counts.filterMatched}" data-export-search="${counts.searchMatched}" data-export-selected="${counts.selected}" aria-labelledby="cp-activity-export-title">
    <h3 id="cp-activity-export-title">${escapeHtml(uiText(state.locale, "Export activities", "خروجی فعالیت‌ها"))}</h3>
    <p>${escapeHtml(uiText(state.locale, "Counts come from the authoritative project read model before any file is produced. Collapsed rows stay part of the filtered and all scopes.", "شمارش‌ها پیش از تولید فایل از مدل خواندنی مرجع پروژه گرفته می‌شوند. ردیف‌های جمع‌شده در محدودهٔ همه و فیلترشده باقی می‌مانند."))}</p>
    <div class="cp-activity-export-scopes" role="radiogroup" aria-label="${escapeAttribute(uiText(state.locale, "Export scope", "محدودهٔ خروجی"))}">${rows}</div>
    <p class="cp-activity-export-summary" data-activity-export-summary aria-live="polite">${escapeHtml(uiText(state.locale, `All activities: ${counts.total} rows · ${counts.selected} selected`, `همهٔ فعالیت‌ها: ${counts.total} ردیف · ${counts.selected} انتخاب‌شده`))}</p>
    <footer>
      <button type="button" data-activity-export-cancel>${escapeHtml(uiText(state.locale, "Cancel", "انصراف"))}</button>
      <button type="button" class="cp-dialog-primary" data-activity-export-download ${counts.total ? "" : "disabled"}>${escapeHtml(uiText(state.locale, "Download CSV", "دریافت CSV"))}</button>
    </footer>
  </dialog>`;
}

/** The filter and search scope the table, Gantt, counts and exports all share. */
function activityScopeForState(
  state: WorkspaceState,
  options: WorkspaceRendererOptions,
): { filterApplication: ActivityFilterApplication; filtered: readonly WorkspaceActivityRow[] } {
  const presentation = options.presentation ?? DEFAULT_PRESENTATION;
  const filterApplication = applyActivityFilterState(
    state.activities,
    presentation.filters,
    state.wbsNodes,
    createActivityFilterDateContext(state.activities, options.dataDate ?? null),
  );
  const filtered = filterAndSortActivities(
    filterApplication.activities,
    state.activityFilter,
    state.activitySort,
    state.activityGroupBy,
    state.wbsNodes,
    state.activitySortLevels,
    state.activityGroupLevels,
  );
  return { filterApplication, filtered };
}

function activityExportSummaryText(scope: ActivityExportScope, count: number, locale: string): string {
  const labels: Record<ActivityExportScope, { en: string; fa: string }> = {
    all: { en: "All activities", fa: "همهٔ فعالیت‌ها" },
    filtered: { en: "Filtered activities", fa: "فعالیت‌های فیلترشده" },
    selected: { en: "Selected activities", fa: "فعالیت‌های انتخاب‌شده" },
  };
  return uiText(
    locale,
    `${labels[scope].en}: ${count} rows will be exported from the authoritative read model`,
    `${labels[scope].fa}: ${count} ردیف از مدل خواندنی مرجع خروجی گرفته می‌شود`,
  );
}

/**
 * Recomputes the dialog counts when it opens. Selection changes take the
 * incremental render path, which repaints toolbar counters but not a closed
 * dialog; without this refresh, "Export selected" could name the selection
 * from an older render.
 */
function refreshActivityExportDialog(container: HTMLElement): void {
  const record = workspaceRenderRecords.get(container);
  const dialog = container.querySelector<HTMLElement>("[data-activity-export-dialog]");
  if (!record || !dialog) return;
  const { filterApplication, filtered } = activityScopeForState(record.state, record.options);
  const visibleIds = [...container.querySelectorAll<HTMLElement>("#cp-activity-grid tbody tr[data-activity-id]")]
    .flatMap((row) => (row.dataset.activityId ? [row.dataset.activityId] : []));
  const counts = computeActivityCounts({
    activities: record.state.activities,
    filterMatchedIds: filterApplication.matchedIds,
    scopeActivities: filtered,
    visibleIds,
    selectedIds: selectedActivityIdList(record.state),
  });
  dialog.dataset.exportTotal = String(counts.total);
  dialog.dataset.exportFilter = String(counts.filterMatched);
  dialog.dataset.exportSearch = String(counts.searchMatched);
  dialog.dataset.exportSelected = String(counts.selected);
  for (const button of dialog.querySelectorAll<HTMLElement>("[data-activity-export-scope]")) {
    const scope = button.dataset.activityExportScope as ActivityExportScope | undefined;
    if (!scope || !ACTIVITY_EXPORT_SCOPES.includes(scope)) continue;
    const count = activityExportScopeCount(scope, counts);
    const counter = button.querySelector<HTMLElement>("[data-export-scope-count]");
    if (counter) counter.textContent = String(count);
    button.toggleAttribute("disabled", count === 0);
  }
  let active = (dialog.dataset.activityExportActive ?? "all") as ActivityExportScope;
  if (!ACTIVITY_EXPORT_SCOPES.includes(active) || activityExportScopeCount(active, counts) === 0) {
    active = "all";
  }
  dialog.dataset.activityExportActive = active;
  dialog.querySelectorAll<HTMLElement>("[data-activity-export-scope]").forEach((entry) => {
    const selected = entry.dataset.activityExportScope === active;
    entry.classList.toggle("is-active", selected);
    entry.setAttribute("aria-checked", selected ? "true" : "false");
  });
  const summary = dialog.querySelector<HTMLElement>("[data-activity-export-summary]");
  if (summary) summary.textContent = activityExportSummaryText(active, activityExportScopeCount(active, counts), record.state.locale);
  const download = dialog.querySelector<HTMLButtonElement>("[data-activity-export-download]");
  if (download) download.disabled = counts.total === 0;
}

function openActivityExportDialog(container: HTMLElement): void {
  const dialog = container.querySelector<HTMLDialogElement>("[data-activity-export-dialog]");
  if (!dialog) return;
  refreshActivityExportDialog(container);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function selectActivityExportScope(container: HTMLElement, scope: ActivityExportScope): void {
  const dialog = container.querySelector<HTMLElement>("[data-activity-export-dialog]");
  if (!dialog) return;
  const button = dialog.querySelector<HTMLElement>(`[data-activity-export-scope="${scope}"]`);
  if (!button || button.hasAttribute("disabled")) return;
  dialog.dataset.activityExportActive = scope;
  dialog.querySelectorAll<HTMLElement>("[data-activity-export-scope]").forEach((entry) => {
    const active = entry.dataset.activityExportScope === scope;
    entry.classList.toggle("is-active", active);
    entry.setAttribute("aria-checked", active ? "true" : "false");
  });
  const counts: Record<ActivityExportScope, number> = {
    all: Number(dialog.dataset.exportTotal ?? 0),
    filtered: Number(dialog.dataset.exportSearch ?? 0),
    selected: Number(dialog.dataset.exportSelected ?? 0),
  };
  const summary = dialog.querySelector<HTMLElement>("[data-activity-export-summary]");
  if (summary) {
    const locale = workspaceRenderRecords.get(container)?.state.locale ?? "en";
    summary.textContent = activityExportSummaryText(scope, counts[scope], locale);
  }
}

/**
 * Keeps the toolbar counts truthful when only the in-memory selection changed
 * and the renderer took the incremental path instead of repainting the toolbar.
 */
function updateActivityScopeCounts(
  container: HTMLElement,
  state: WorkspaceState,
  options: WorkspaceRendererOptions,
  selectedIds: readonly string[],
): void {
  const host = container.querySelector<HTMLElement>("[data-activity-counts]");
  if (!host) return;
  const { filterApplication, filtered } = activityScopeForState(state, options);
  const visibleIds = [...container.querySelectorAll<HTMLElement>("#cp-activity-grid tbody tr[data-activity-id]")]
    .flatMap((row) => (row.dataset.activityId ? [row.dataset.activityId] : []));
  const counts = computeActivityCounts({
    activities: state.activities,
    filterMatchedIds: filterApplication.matchedIds,
    scopeActivities: filtered,
    visibleIds,
    selectedIds,
  });
  host.dataset.countTotal = String(counts.total);
  host.dataset.countFilter = String(counts.filterMatched);
  host.dataset.countSearch = String(counts.searchMatched);
  host.dataset.countVisible = String(counts.visible);
  host.dataset.countSelected = String(counts.selected);
  host.dataset.countSelectedScope = String(counts.selectedInScope);
  const values: Record<string, number> = {
    total: counts.total,
    filter: counts.filterMatched,
    search: counts.searchMatched,
    visible: counts.visible,
    selected: counts.selected,
    "selected-scope": counts.selectedInScope,
  };
  for (const [key, value] of Object.entries(values)) {
    const target = host.querySelector<HTMLElement>(`[data-count-item="${key}"] strong`);
    if (target) target.textContent = String(value);
  }
  const visibleOutput = host.querySelector<HTMLElement>("[data-activity-count]");
  if (visibleOutput) {
    const labels = getWorkspaceLabels(state.locale);
    visibleOutput.textContent = `${counts.visible} / ${counts.total} ${labels.matchingActivities}`;
  }
  const selectAll = container.querySelector<HTMLButtonElement>("[data-activity-select-all]");
  if (selectAll) selectAll.disabled = counts.searchMatched === 0;
}

function downloadActivityExport(container: HTMLElement): void {  const record = workspaceRenderRecords.get(container);
  const dialog = container.querySelector<HTMLDialogElement>("[data-activity-export-dialog]");
  if (!record || !dialog) return;
  const scope = (dialog.dataset.activityExportActive ?? "all") as ActivityExportScope;
  if (!ACTIVITY_EXPORT_SCOPES.includes(scope)) return;
  const { state, options } = record;
  const { filtered } = activityScopeForState(state, options);
  const sources = {
    activities: state.activities,
    filtered,
    selectedIds: selectedActivityIdList(state),
  };
  const rows = activitiesForExport(scope, sources);
  // A zero-row scope never produces a file or a success message.
  if (rows.length === 0) return;
  const csv = activitiesToCsv(rows, state.columns);
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = activityExportFileName(scope, state.context.project_id);
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  dialog.close();
}

function renderSettingsLayoutAdministration(state: WorkspaceState, options: WorkspaceRendererOptions): string {
  const heading = `<div class="cp-settings-layout-heading"><h3>${escapeHtml(uiText(state.locale, "Layout Administration", "مدیریت چیدمان"))}</h3><span>${escapeHtml(uiText(state.locale, "Activity grid · persisted layout", "شبکه فعالیت · چیدمان ذخیره‌شده"))}</span></div>`;
  const layout = state.p6Layout;
  if (!layout) {
    return `<section class="cp-settings-layout" data-settings-layout aria-label="${escapeAttribute(uiText(state.locale, "Layout administration", "مدیریت چیدمان"))}">${heading}<p class="cp-settings-layout-empty">${escapeHtml(uiText(state.locale, "No saved activity-grid layout is loaded for this project revision. The project service did not return a layout, so this page shows no field list and invents no layout.", "هیچ چیدمان ذخیره‌شدهٔ شبکهٔ فعالیت برای این ویرایش پروژه بارگذاری نشده است. سرویس پروژه چیدمانی برنگردانده؛ بنابراین این صفحه فهرست فیلدی نمایش نمی‌دهد و چیدمانی نمی‌سازد."))}</p></section>`;
  }
  const visibleColumns = layout.columns.filter((column) => column.visible).length;
  const facts: ReadonlyArray<readonly [string, string]> = [
    [uiText(state.locale, "Scope", "دامنه"), layout.scope],
    [uiText(state.locale, "View", "نما"), layout.view_id],
    [uiText(state.locale, "Revision", "ویرایش"), `R${layout.revision}`],
    [uiText(state.locale, "Columns", "ستون‌ها"), `${visibleColumns} / ${layout.columns.length}`],
  ];
  const revisionsPending = Boolean(options.layoutHistory) && !options.layoutHistory?.revisions;
  return `<section class="cp-settings-layout" data-settings-layout aria-label="${escapeAttribute(uiText(state.locale, "Layout administration", "مدیریت چیدمان"))}">
    ${heading}
    <dl class="cp-settings-layout-facts">${facts.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}</dl>
    ${renderP6FieldChooser(state, options.layoutHistory)}
    ${revisionsPending ? `<p class="cp-settings-layout-note" role="status">${escapeHtml(uiText(state.locale, "Saved revisions are loaded when layout history is requested; no revision list is shown before the server responds.", "نسخه‌های ذخیره‌شده هنگام درخواست تاریخچهٔ چیدمان بارگذاری می‌شوند؛ پیش از پاسخ سرور هیچ فهرست نسخه‌ای نمایش داده نمی‌شود."))}</p>` : ""}
    <p class="cp-register-notice">${escapeHtml(uiText(state.locale, "Layout changes persist through the shared layout contract with optimistic revision checks. Only the activity-grid layout is exposed; other surfaces keep the shared contract until their own layouts are stored.", "تغییرات چیدمان از طریق قرارداد مشترک چیدمان با بررسی خوش‌بینانهٔ ویرایش ذخیره می‌شود. فقط چیدمان شبکهٔ فعالیت در دسترس است؛ سایر سطوح تا ذخیرهٔ چیدمان خود از همان قرارداد مشترک استفاده می‌کنند."))}</p>
  </section>`;
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
      ${available.length ? `<button type="button" class="cp-p6-field-add-all" data-p6-field-add-all title="${escapeAttribute(t.addAll)}" aria-label="${escapeAttribute(t.addAll)}">${escapeHtml(t.addAll)}</button>` : ""}
      ${available.map((field) => `<button type="button" data-p6-field-add="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.add)}">${escapeHtml(field.display_name)}</button>`).join("")}
    </div>
  </section>`;
}

const ACTIVITY_CONTEXT_LABELS = {
  details: { en: "Activity Details", fa: "جزئیات فعالیت" },
  cut: { en: "Cut", fa: "برش" },
  copy: { en: "Copy", fa: "رونوشت" },
  paste: { en: "Paste", fa: "چسباندن" },
  fillDown: { en: "Fill Down", fa: "پرکردن به پایین" },
  add: { en: "Add", fa: "افزودن" },
  delete: { en: "Delete", fa: "حذف" },
  dissolve: { en: "Dissolve", fa: "انحلال" },
  renumber: { en: "Renumber Activity IDs", fa: "شماره‌گذاری دوبارهٔ شناسه‌ها" },
  exportExcel: { en: "Export to Excel", fa: "خروجی اکسل" },
  assign: { en: "Assign", fa: "تخصیص" },
  link: { en: "Link Activities", fa: "پیوند فعالیت‌ها" },
  columns: { en: "Columns…", fa: "ستون‌ها…" },
  lineNumbers: { en: "Line Numbers", fa: "شمارهٔ ردیف" },
  fontRow: { en: "Table Font and Row…", fa: "قلم و ردیف جدول…" },
  filters: { en: "Filters…", fa: "پالایه‌ها…" },
  groupSort: { en: "Group and Sort…", fa: "گروه‌بندی و ترتیب…" },
  expandAll: { en: "Expand All", fa: "بازکردن همه" },
  collapseAll: { en: "Collapse All", fa: "بستن همه" },
  collapseTo: { en: "Collapse To…", fa: "بستن تا…" },
} as const;

const ACTIVITY_CONTEXT_REASONS = {
  cut: { en: "Cut needs the activity delete route, which this runtime does not expose.", fa: "برش به مسیر حذف فعالیت نیاز دارد که این محیط اجرا ارائه نمی‌کند." },
  copy: { en: "Activity duplication is not implemented by the project service.", fa: "تکثیر فعالیت در سرویس پروژه پیاده‌سازی نشده است." },
  paste: { en: "There is no activity clipboard or bulk-create route.", fa: "کلیپ‌بورد فعالیت یا مسیر ساخت گروهی وجود ندارد." },
  fillDown: { en: "Bulk cell updates are not exposed by the activity API.", fa: "به‌روزرسانی گروهی سلول‌ها در API فعالیت ارائه نشده است." },
  delete: { en: "The activity delete route is not exposed by this runtime.", fa: "مسیر حذف فعالیت در این محیط اجرا ارائه نشده است." },
  dissolve: { en: "Dissolving a group has no server-side contract.", fa: "انحلال گروه قرارداد سمت سرور ندارد." },
  renumber: { en: "Activity ID renumbering is not implemented.", fa: "شماره‌گذاری دوبارهٔ شناسهٔ فعالیت پیاده‌سازی نشده است." },
  exportExcel: { en: "Only XML interchange is available; no XLSX export route exists.", fa: "تنها تبادل XML در دسترس است؛ مسیر خروجی XLSX وجود ندارد." },
  assign: { en: "Resource assignment write is not available; capacity is read-only.", fa: "نوشتن تخصیص منبع در دسترس نیست؛ ظرفیت فقط خواندنی است." },
} as const;

function contextMenuText(label: { en: string; fa: string }, locale: string): string {
  return uiText(locale, label.en, label.fa);
}

function renderCollapseToDialog(state: WorkspaceState): string {
  const locale = state.locale;
  const depths = wbsNodeDepths(state.wbsNodes);
  const options = state.wbsNodes.map((node) => `<option value="${escapeAttribute(node.id)}">L${(depths.get(node.id) ?? 0) + 1} · ${escapeHtml(node.localCode)} — ${escapeHtml(node.name)}</option>`).join("");
  return `<dialog class="cp-desktop-dialog cp-collapse-to-dialog" data-collapse-to-dialog aria-label="${escapeAttribute(uiText(locale, "Collapse To", "بستن تا"))}">
    <form method="dialog">
      <header class="cp-dialog-head"><strong>${escapeHtml(uiText(locale, "Collapse To…", "بستن تا…"))}</strong></header>
      <div class="cp-dialog-body">
        <label>${escapeHtml(uiText(locale, "WBS element to keep open", "عنصر ساختار شکست که باز بماند"))}
          <select data-collapse-to-select>${options}</select>
        </label>
        <p class="cp-dialog-note">${escapeHtml(uiText(locale, "Every branch outside the selected WBS path collapses. Activities keep their persisted schedule values.", "همهٔ شاخه‌های بیرون از مسیر انتخاب‌شده بسته می‌شوند. مقادیر زمان‌بندی فعالیت‌ها تغییر نمی‌کند."))}</p>
      </div>
      <div class="cp-dialog-buttons"><button type="button" data-collapse-to-cancel>${escapeHtml(uiText(locale, "Cancel", "انصراف"))}</button><button type="button" class="cp-dialog-primary" data-collapse-to-apply>${escapeHtml(uiText(locale, "Apply", "اعمال"))}</button></div>
    </form>
  </dialog>`;
}

/** Forces the next render to rebuild rows (collapse changes live outside state). */
export function invalidateWorkspaceRender(container: HTMLElement): void {
  workspaceRenderRecords.delete(container);
}

function rerenderWorkspaceRows(container: HTMLElement): void {
  const record = workspaceRenderRecords.get(container);
  if (!record) return;
  const table = container.querySelector<HTMLElement>("#cp-activity-grid .cp-table-wrap");
  const chart = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-chart");
  const tableTop = table?.scrollTop ?? 0;
  const tableLeft = table?.scrollLeft ?? 0;
  const chartTop = chart?.scrollTop ?? 0;
  workspaceRenderRecords.delete(container);
  renderMainWorkspace(container, record.state, record.options);
  const nextTable = container.querySelector<HTMLElement>("#cp-activity-grid .cp-table-wrap");
  const nextChart = container.querySelector<HTMLElement>("#cp-gantt .cp-gantt-chart");
  if (nextTable) {
    nextTable.scrollTop = tableTop;
    nextTable.scrollLeft = tableLeft;
  }
  if (nextChart) nextChart.scrollTop = chartTop;
}

function treeCellMarkup(
  guide: WbsTreeGuide,
  wbs: WorkspacePresentation["wbs"],
  content: string,
  levelDepth: number,
): string {
  // The reference draws the hierarchy as a staircase of solid level-coloured
  // spines in front of the first column: one 14px spine for every ancestor,
  // ending exactly where the branch ends. No thin guide lines are used.
  const spines = Array.from({ length: Math.max(0, Math.round(guide.depth)) }, (_, level) =>
    `<span class="cp-p6-wbs-spine" data-spine-level="${level + 1}" style="--cp-spine:${wbsLevelColor(wbs, level)}" aria-hidden="true"></span>`,
  ).join("");
  return `<span class="cp-p6-tree-guides" data-tree-depth="${guide.depth}" style="--cp-wbs-level:${wbsLevelColor(wbs, levelDepth)}">${spines}${content}</span>`;
}

/** Highlight mode keeps every row on screen and tints the matching ones. */
function markFilterHighlights(container: HTMLElement, application: ActivityFilterApplication): void {
  if (!application.highlight) return;
  const mark = (element: HTMLElement, id: string | undefined): void => {
    element.classList.toggle("is-filter-match", Boolean(id && application.matchedIds.has(id)));
  };
  container.querySelectorAll<HTMLElement>("tr[data-activity-id]").forEach((row) => mark(row, row.dataset.activityId));
  container.querySelectorAll<HTMLElement>("[data-gantt-activity-id]").forEach((row) => mark(row, row.dataset.ganttActivityId));
}

function renderActivityRow(
  activity: WorkspaceActivityRow,
  state: WorkspaceState,
  stickyOffsets: ReadonlyMap<string, number>,
  presentation: WorkspacePresentation,
  rowNumber: number,
  indentDepth = 0,
  treeColumnId: string | null = null,
  guide: WbsTreeGuide = { depth: indentDepth, rails: [], lastChild: true, hasChildren: false, collapsed: false },
  tabbable = true,
): string {
  const selected = selectedActivityIdList(state).includes(activity.id);
  const predecessors = predecessorSummary(activity.id, state);
  const showIcons = presentation.table.showIcons;
  const iconColumnId = showIcons
    ? state.columns.find((column) => column.id === "activity_id" || column.id === "activity.id")?.id ?? null
    : null;
  const rowIcon = showIcons ? activityTypeIcon(activity) : "";
  const cells = state.columns.map((column) => {
    const value = renderCell(column, activity, state.calendarMode);
    const isTree = column.id === treeColumnId;
    const content = isTree
      ? treeCellMarkup(
        guide,
        presentation.wbs,
        iconColumnId !== null && column.id === iconColumnId
          ? `<span class="cp-p6-activity-cell">${rowIcon}${value}</span>`
          : value,
        branchLevel(guide),
      )
      : value;
    const treeColor = isTree ? `;--cp-wbs-level:${wbsLevelColor(presentation.wbs, branchLevel(guide))}` : "";
    return `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${isTree ? " cp-p6-tree-cell" : ""}${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${treeColor}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${content}</td>`;
  }).join("");
  const lineNumberCell = presentation.table.lineNumbers
    ? `<td role="gridcell" class="cp-p6-line-number">${rowNumber}</td>`
    : "";
  return `<tr role="row" data-activity-id="${escapeAttribute(activity.id)}" data-activity-kind="${activityTypeKind(activity)}" tabindex="${tabbable ? "0" : "-1"}" aria-selected="${selected ? "true" : "false"}" aria-label="${escapeAttribute(activity.id)}" data-wbs-depth="${indentDepth}" data-wbs-level="${Math.min(6, guide.depth + 1)}" class="${selected ? "is-selected" : ""}">${lineNumberCell}${cells}<td class="cp-logic-column" data-predecessors="${escapeAttribute(activity.id)}">${predecessors ? escapeHtml(predecessors) : "—"}</td><td class="cp-actions-column"><button type="button" data-activity-edit="${escapeAttribute(activity.id)}">${escapeHtml(getWorkspaceLabels(state.locale).activityEdit)}</button></td></tr>`;
}

/**
 * A band produced by a non-WBS group level (for example Activity Status). It
 * carries the same derived rollups as a WBS band and its own collapse toggle;
 * the band never changes the activity rows it contains.
 */
function renderFieldGroupRow(
  row: WorkspaceFieldGroupRow,
  state: WorkspaceState,
  stickyOffsets: ReadonlyMap<string, number>,
  presentation: WorkspacePresentation,
  t: WorkspaceLabels,
  guide: WbsTreeGuide,
): string {
  const nameColumnId = state.columns.find((column) => column.id === "activity_name" || column.id === "activity.name")?.id ?? null;
  const treeColumnId = state.columns.find((column) => column.id === "activity_id" || column.id === "activity.id")?.id
    ?? nameColumnId
    ?? state.columns[0]?.id
    ?? null;
  const formatMs = (ms: number): string =>
    formatWorkspaceCalendarDate(new Date(ms).toISOString().slice(0, 10), state.calendarMode);
  const rollupTitle = uiText(
    state.locale,
    `Derived for display from ${row.summary.activityCount} persisted child activities`,
    `برای نمایش از ${row.summary.activityCount} فعالیت فرزند ذخیره‌شده محاسبه شده است`,
  );
  const fieldLabel = groupFieldLabel(row.fieldId, state.locale);
  const count = row.summary.activityCount;
  const toggleTitle = row.collapsed
    ? uiText(state.locale, "Expand group", "بازکردن گروه")
    : uiText(state.locale, "Collapse group", "بستن گروه");
  // The toggle stays in the tree column so it lines up with the hierarchy
  // spine; the value and its count sit in the name column, where the band has
  // room to show a long status or code without clipping.
  const toggleMarkup = `<button type="button" class="cp-p6-wbs-toggle" data-band-toggle="${escapeAttribute(row.bandKey)}" aria-expanded="${row.collapsed ? "false" : "true"}" title="${escapeAttribute(toggleTitle)}">${row.collapsed ? "+" : "−"}</button>`;
  const labelMarkup = `<span class="cp-p6-group-cell"><span class="cp-p6-group-label" data-group-field="${escapeAttribute(row.fieldId)}">${escapeHtml(row.label)}</span><span class="cp-p6-group-count" title="${escapeAttribute(uiText(state.locale, `${count} activities`, `${count} فعالیت`))}">(${count})</span></span>`;
  const cells = state.columns.map((column) => {
    const last = column.id.split(".").pop() ?? column.id;
    const isStart = last === "start";
    const isFinish = last === "finish";
    const isDuration = last === "duration";
    const isProgress = last === "progress" || last === "percent_complete" || last === "percentcomplete";
    let content = "";
    let derived = false;
    const isTree = column.id === treeColumnId;
    if (isTree) {
      const inline = nameColumnId === column.id ? `${toggleMarkup}${labelMarkup}` : toggleMarkup;
      content = treeCellMarkup(guide, presentation.wbs, inline, guide.depth);
    } else if (column.id === nameColumnId) {
      content = labelMarkup;
    } else if (isStart && row.summary.startMs !== null) {
      content = escapeHtml(formatMs(row.summary.startMs));
      derived = true;
    } else if (isFinish && row.summary.finishMs !== null) {
      content = escapeHtml(formatMs(row.summary.finishMs));
      derived = true;
    } else if (isDuration && row.summary.duration !== null) {
      content = escapeHtml(String(row.summary.duration));
      derived = true;
    } else if (isProgress && row.summary.progressPercent !== null) {
      content = `${row.summary.progressPercent}%`;
      derived = true;
    }
    return `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}"${derived ? ` data-rollup="display" title="${escapeAttribute(rollupTitle)}"` : ""} class="cp-p6-column cp-p6-wbs-cell-td${isTree ? " cp-p6-tree-cell" : ""}${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${content}</td>`;
  }).join("");
  const lineNumberCell = presentation.table.lineNumbers ? `<td role="gridcell" class="cp-p6-line-number"></td>` : "";
  const levelColor = wbsLevelColor(presentation.wbs, row.depth);
  const levelInk = wbsBandInk(presentation.wbs, row.depth);
  const bandStyle = [
    `--cp-wbs-level:${levelColor}`,
    `--cp-wbs-ink:${levelInk}`,
    `--cp-wbs-font-family:${presentationFontFamily(presentation.wbs.fontFamily)}`,
    `--cp-wbs-font-size:${presentation.wbs.fontSize}px`,
    `--cp-wbs-row-height:${presentation.wbs.rowHeight}px`,
  ].join(";");
  return `<tr role="row" data-field-group-row="${escapeAttribute(row.bandKey)}" data-group-field="${escapeAttribute(row.fieldId)}" data-group-level="${row.level}" data-group-value="${escapeAttribute(row.valueKey)}" data-band-depth="${row.depth}" data-band-collapsed="${row.collapsed}" tabindex="0" aria-label="${escapeAttribute(`${fieldLabel}: ${row.label}`)}" aria-expanded="${row.collapsed ? "false" : "true"}" class="cp-p6-wbs-band cp-p6-tree-band cp-p6-field-band${row.collapsed ? " is-collapsed" : ""}" style="${escapeAttribute(bandStyle)}">${lineNumberCell}${cells}<td class="cp-logic-column"></td><td class="cp-actions-column"></td></tr>`;
}

/** A leaf activity belongs to the branch one level above its indent. */
function branchLevel(guide: WbsTreeGuide): number {
  return guide.depth > 0 ? guide.depth - 1 : 0;
}

function renderWbsGroupRow(
  row: WorkspaceWbsGroupRow,
  state: WorkspaceState,
  stickyOffsets: ReadonlyMap<string, number>,
  presentation: WorkspacePresentation,
  t: WorkspaceLabels,
  guide: WbsTreeGuide,
): string {
  const treeColumnId = state.columns.find((column) => column.id === "activity_id" || column.id === "activity.id")?.id
    ?? state.columns.find((column) => column.id === "activity_name" || column.id === "activity.name")?.id
    ?? state.columns[0]?.id
    ?? null;
  const formatMs = (ms: number): string =>
    formatWorkspaceCalendarDate(new Date(ms).toISOString().slice(0, 10), state.calendarMode);
  const rollupTitle = uiText(
    state.locale,
    `Derived for display from ${row.summary.activityCount} persisted child activities`,
    `برای نمایش از ${row.summary.activityCount} فعالیت فرزند ذخیره‌شده محاسبه شده است`,
  );
  const bandLabels = presentation.wbs.labels;
  const titleMarkup = bandLabels.title
    ? `<span class="cp-p6-wbs-title">${escapeHtml(uiText(state.locale, "WBS", "WBS"))}</span>`
    : "";
  const codeMarkup = bandLabels.code
    ? `<span class="cp-p6-wbs-code">${escapeHtml(row.node.localCode)}</span>`
    : "";
  const cells = state.columns.map((column) => {
    const last = column.id.split(".").pop() ?? column.id;
    const isStart = last === "start";
    const isFinish = last === "finish";
    const isDuration = last === "duration";
    const isProgress = last === "progress" || last === "percent_complete" || last === "percentcomplete";
    let content = "";
    let derived = false;
    const isTree = column.id === treeColumnId;
    if (isTree) {
      content = treeCellMarkup(
        guide,
        presentation.wbs,
        `<span class="cp-p6-wbs-cell"><button type="button" class="cp-p6-wbs-toggle" data-wbs-toggle="${escapeAttribute(row.bandKey)}" aria-expanded="${row.collapsed ? "false" : "true"}" title="${escapeAttribute(row.collapsed ? uiText(state.locale, "Expand WBS branch", "بازکردن شاخهٔ ساختار شکست") : uiText(state.locale, "Collapse WBS branch", "بستن شاخهٔ ساختار شکست"))}">${row.collapsed ? "+" : "−"}</button><span class="cp-p6-wbs-icon">${workspaceIcon("wbs")}</span>${titleMarkup}${codeMarkup}</span>`,
        guide.depth,
      );
    } else if (column.id === "activity_name" || column.id === "activity.name") {
      content = bandLabels.name ? `<span class="cp-p6-wbs-name">${escapeHtml(row.node.name)}</span>` : "";
    } else if (isStart && row.summary.startMs !== null) {
      content = escapeHtml(formatMs(row.summary.startMs));
      derived = true;
    } else if (isFinish && row.summary.finishMs !== null) {
      content = escapeHtml(formatMs(row.summary.finishMs));
      derived = true;
    } else if (isDuration && row.summary.duration !== null) {
      content = escapeHtml(String(row.summary.duration));
      derived = true;
    } else if (isProgress && row.summary.progressPercent !== null) {
      content = `${row.summary.progressPercent}%`;
      derived = true;
    }
    return `<td role="gridcell" data-column-id="${escapeAttribute(column.id)}" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}"${derived ? ` data-rollup="display" title="${escapeAttribute(rollupTitle)}"` : ""} class="cp-p6-column cp-p6-wbs-cell-td${isTree ? " cp-p6-tree-cell" : ""}${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${content}</td>`;
  }).join("");
  const lineNumberCell = presentation.table.lineNumbers ? `<td role="gridcell" class="cp-p6-line-number"></td>` : "";
  const levelColor = wbsLevelColor(presentation.wbs, row.depth);
  const levelInk = wbsBandInk(presentation.wbs, row.depth);
  const bandStyle = [
    `--cp-wbs-level:${levelColor}`,
    `--cp-wbs-ink:${levelInk}`,
    `--cp-wbs-font-family:${presentationFontFamily(presentation.wbs.fontFamily)}`,
    `--cp-wbs-font-size:${presentation.wbs.fontSize}px`,
    `--cp-wbs-row-height:${presentation.wbs.rowHeight}px`,
  ].join(";");
  return `<tr role="row" data-wbs-row="${escapeAttribute(row.wbsId)}" data-band-key="${escapeAttribute(row.bandKey)}" data-wbs-level="${Math.min(6, row.depth + 1)}" data-wbs-depth="${row.depth}" data-wbs-collapsed="${row.collapsed}" tabindex="0" aria-label="${escapeAttribute(`${row.node.localCode} ${row.node.name}`)}" aria-expanded="${row.collapsed ? "false" : "true"}" class="cp-p6-wbs-band cp-p6-tree-band${row.collapsed ? " is-collapsed" : ""}" style="${escapeAttribute(bandStyle)}">${lineNumberCell}${cells}<td class="cp-logic-column"></td><td class="cp-actions-column"></td></tr>`;
}

function activityTypeKind(activity: WorkspaceActivityRow): "milestone" | "summary" | "loe" | "task" {
  const type = String(activity.cells?.["activity.activity_type"] ?? activity.cells?.activity_type ?? "").toLowerCase();
  return type.includes("milestone") ? "milestone" : type.includes("summary") ? "summary" : type.includes("level of effort") ? "loe" : "task";
}

function activityTypeIcon(activity: WorkspaceActivityRow): string {
  const kind = activityTypeKind(activity);
  const icon: WorkspaceIconName = kind === "milestone" ? "milestone" : kind === "summary" ? "wbs" : "activity";
  return `<span class="cp-p6-activity-icon is-${kind}" aria-hidden="true">${workspaceIcon(icon)}</span>`;
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

const GANTT_KIND_LABELS: Record<GanttBarKind, readonly [string, string]> = {
  task: ["Task", "فعالیت"],
  critical: ["Critical", "بحرانی"],
  summary: ["Summary", "خلاصه"],
  milestone: ["Milestone", "نقطه عطف"],
  progress: ["Progress", "پیشرفت"],
  actual: ["Actual", "واقعی"],
  baseline: ["Baseline", "خط مبنا"],
};

type GanttBarLayer = {
  kind: GanttBarKind;
  style: GanttBarStyle;
  leftPercent: number;
  widthPercent: number;
  /** Zero-duration milestone marker: fixed marker size instead of duration width. */
  milestone: boolean;
};

function ganttPercent(startMs: number, endMs: number, scale: GanttScale): { leftPercent: number; widthPercent: number } {
  const leftPercent = Math.max(0, Math.min(100, ((startMs - scale.startMs) / scale.rangeMs) * 100));
  const rightPercent = Math.max(0, Math.min(100, ((endMs - scale.startMs) / scale.rangeMs) * 100));
  return { leftPercent, widthPercent: Math.max(1, rightPercent - leftPercent) };
}

/** Span of a persisted auxiliary date pair (actual/baseline), never derived. */
function ganttDateSpan(activity: WorkspaceActivityRow, scale: GanttScale, prefixes: readonly string[]): { leftPercent: number; widthPercent: number } | null {
  const cells = activity.cells ?? {};
  for (const prefix of prefixes) {
    const start = cells[`${prefix}start`];
    const finish = cells[`${prefix}finish`];
    if (typeof start !== "string" || start.trim() === "" || typeof finish !== "string" || finish.trim() === "") continue;
    const startMs = Date.parse(start);
    const finishMs = Date.parse(finish);
    if (!Number.isFinite(startMs) || !Number.isFinite(finishMs) || finishMs < startMs) continue;
    return ganttPercent(startMs, finishMs, scale);
  }
  return null;
}

function renderGanttBar(layer: GanttBarLayer, top: number, height: number, progressOverlay: string, activity: WorkspaceActivityRow | undefined, bar: GanttBarGeometry, t: WorkspaceLabels, locale: string, format: GanttLabelFormat, weekDividers: readonly number[] = [], primary = false, linkHandles = false): string {
  const style = layer.style;
  const kindLabel = translateWorkspaceUiText(locale, ...GANTT_KIND_LABELS[layer.kind]);
  const width = layer.milestone ? Math.max(10, height) : layer.widthPercent;
  const geometryStyle = layer.milestone
    ? `left:${ganttRound(layer.leftPercent)}%;margin-left:-${ganttRound(width / 2)}px;width:${width}px;top:${top}px;height:${height}px;`
    : `left:${ganttRound(layer.leftPercent)}%;width:${ganttRound(width)}%;top:${top}px;height:${height}px;`;
  const startMarker = style.startShape !== "none" && style.startShape !== "bar"
    ? `<span class="cp-gantt-endpoint is-start is-${style.startShape}" style="--cp-gantt-endpoint:${style.startColor}"></span>`
    : "";
  const finishMarker = style.finishShape !== "none" && style.finishShape !== "bar"
    ? `<span class="cp-gantt-endpoint is-finish is-${style.finishShape}" style="--cp-gantt-endpoint:${style.finishColor}"></span>`
    : "";
  const labelText = barLabelText(style.labelField, bar, activity, format);
  const labelPosition = resolveGanttLabelPosition(style.labelPosition, bar);
  const label = labelText
    ? `<span dir="ltr" class="cp-gantt-bar-label is-${labelPosition}" data-gantt-label-position="${labelPosition}">${escapeHtml(labelText)}</span>`
    : "";
  // Nonwork necking: a 1px black divider at every calendar week boundary that
  // falls inside the bar, as the desktop reference draws it.
  const dividers = style.bodyShape === "bar" && !layer.milestone
    ? weekDividers.map((percent) => `<span class="cp-gantt-bar-tick" style="left:${ganttRound(percent)}%" aria-hidden="true"></span>`).join("")
    : "";
  const title = `${bar.activityId} · ${kindLabel} · ${bar.progressPercent}%${bar.critical ? " · " + t.critical : ""}${bar.milestone ? " · " + t.milestone : ""}`;
  // Only the primary duration bar carries the relationship drag handles: its
  // edges are the authoritative start and finish, unlike a stacked overlay.
  const handles = primary && linkHandles
    ? `<span class="cp-gantt-link-edge is-start" data-gantt-link-edge="start" aria-hidden="true"></span><span class="cp-gantt-link-edge is-finish" data-gantt-link-edge="finish" aria-hidden="true"></span>`
    : "";
  return `<div class="cp-gantt-bar cp-gantt-bar-${layer.kind}${bar.critical ? " is-critical" : ""} is-body-${style.bodyShape} is-pattern-${style.pattern}"${primary ? ' data-gantt-bar-primary="true"' : ""} data-gantt-bar-kind="${layer.kind}" data-gantt-bar-row="${style.row}" data-gantt-bar-shape="${style.bodyShape}" data-gantt-bar-pattern="${style.pattern}" style="${geometryStyle}--cp-bar-body:${style.bodyColor};--cp-bar-border:${style.borderColor}" title="${escapeAttribute(title)}">${startMarker}${finishMarker}${progressOverlay}${dividers}${label}${handles}</div>`;
}

function ganttRound(value: number): number {
  return Math.round(value * 100) / 100;
}

// Zoom only changes the resolution of the shared timeline: finer scales make
// the same date range wider, which is what creates horizontal scrolling.
// GANTT_CONTENT_WIDTH lives with the scale helpers so "Fit" can reason about it.

const GANTT_LAG_UNITS: Record<string, string> = {
  "working-day": "d",
  day: "d",
  "working-week": "w",
  week: "w",
  "working-month": "mo",
  month: "mo",
  year: "y",
  hour: "h",
  minute: "m",
  percent: "%",
};

/** Compact, persisted lag/lead marker; the value is never recomputed. */
function ganttLagText(lag: { value: string; unit: string }): string {
  const trimmed = lag.value.trim();
  const sign = trimmed.startsWith("-") ? "−" : "+";
  return `${sign}${trimmed.replace(/^[+-]/, "")}${GANTT_LAG_UNITS[lag.unit] ?? ""}`;
}

function renderGantt(
  rows: readonly WorkspaceDisplayRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  ganttScale: WorkspaceGanttScale,
  calendarMode: WorkspaceCalendarMode,
  scale: ReturnType<typeof createGanttScale>,
  t: WorkspaceLabels,
  selectedActivityId: string | null,
  showRelationships: boolean,
  presentation: WorkspacePresentation,
  locale: string,
  dataDate: string | null = null,
  projectCalendar: WorkspaceProjectCalendar | null = null,
  selectedActivityIds?: readonly string[],
): string {
  if (!rows.length) {
    return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">${escapeHtml(t.noSchedule)}</div>`;
  }
  // A scope whose activities carry no schedule dates still has one Gantt row
  // per table row. There is no timeline to scale, so the rows keep empty tracks
  // under a neutral axis instead of being replaced by a "no schedule" claim.
  const hasTimeline = scale !== null;
  const viewScale: GanttScale = scale ?? { startMs: 0, endMs: 1, rangeMs: 1 };

  const activities = rows
    .filter((row): row is Extract<WorkspaceDisplayRow, { kind: "activity" }> => row.kind === "activity")
    .map((row) => row.activity);
  const bars = activities
    .map((activity) => createGanttBarGeometry(activity, viewScale))
    .filter((bar): bar is GanttBarGeometry => bar !== null);

  const gantt = presentation.gantt;
  const rowHeight = ganttRowPitch(presentation.table.rowHeight);
  // Bands and activity rows have different heights, so the chart uses one
  // cumulative row metric for bars, links, sight lines and the progress line.
  const { metrics: rowMetrics, total: rowsHeight } = ganttDisplayMetrics(rows, rowHeight, presentation.wbs.rowHeight);
  const rowCenters = rowMetrics.map((metric) => metric.center);
  const contentWidth = GANTT_CONTENT_WIDTH[ganttScale];
  const activityById = new Map(activities.map((activity) => [activity.id, activity]));
  const barById = new Map(bars.map((bar) => [bar.activityId, bar]));
  const rowIndexByActivity = new Map<string, number>();
  rows.forEach((row, index) => {
    if (row.kind === "activity") rowIndexByActivity.set(row.activity.id, index);
  });
  const ticks = hasTimeline ? createGanttAxisTicks(viewScale, ganttScale) : [];
  const links = createGanttLinkGeometry(relationships, bars, rowIndexByActivity, { rowHeight, rowCenters, xUnits: 10 });
  const scaleModeLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const toolbar = `<div class="cp-gantt-toolbar" aria-label="${escapeAttribute(uiText(locale, "Gantt chart controls", "کنترل‌های نمودار گانت"))}"><div class="cp-gantt-scale-controls" role="group" aria-label="${escapeAttribute(t.ganttScaleLabel)}">${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<button type="button" class="cp-gantt-scale-button${mode === ganttScale ? " is-active" : ""}" data-gantt-scale="${mode}" aria-pressed="${mode === ganttScale ? "true" : "false"}">${escapeHtml(scaleModeLabels[mode])}</button>`).join("")}</div><button type="button" class="cp-gantt-relationships-toggle${showRelationships ? " is-active" : ""}" data-gantt-relationships-toggle="${showRelationships ? "false" : "true"}" aria-pressed="${showRelationships ? "true" : "false"}" title="${escapeAttribute(t.ganttLinksToggle)}"><span>${escapeHtml(t.ganttLinksToggle)}</span><strong>${escapeHtml(showRelationships ? t.ganttLinksOn : t.ganttLinksOff)}</strong></button></div>`;
  const axis = hasTimeline ? (() => {
    const timescale = presentation.timescale;
    const ordinalStartMs = timescale.ordinalStart
      ? Date.parse(`${timescale.ordinalStart}T00:00:00Z`)
      : viewScale.startMs;
    const groupLabel = (unit: "year" | "quarter" | "month" | "week", group: GanttPeriodGroup): string => {
      if (unit === "year") {
        const formatted = formatWorkspaceCalendarDate(group.date, calendarMode);
        return formatted.split(/[\/\-]/)[0] ?? formatted;
      }
      if (unit === "quarter") {
        const year = formatWorkspaceCalendarDate(group.date, calendarMode).split(/[\/\-]/)[0] ?? "";
        const month = Number(group.date.slice(5, 7));
        return `Qtr ${Math.floor((month - 1) / 3) + 1}, ${year}`.trim();
      }
      if (unit === "month") {
        const calendar = calendarMode === "jalali" ? "-u-ca-persian" : "";
        const language = locale === "fa" ? "fa-IR" : "en-US";
        try {
          return new Intl.DateTimeFormat(`${language}${calendar}`, {
            timeZone: "UTC", month: "long", year: "numeric",
          }).format(new Date(`${group.date}T00:00:00Z`));
        } catch {
          return group.date.slice(0, 7);
        }
      }
      return `W${isoWeekNumber(group.startMs)}`;
    };
    const majorUnit = timescaleMajorUnit(timescale.interval);
    const groupUnits: ("year" | "quarter" | "month" | "week")[] = [];
    if (timescale.dateFormat === "primary") {
      if (timescale.lines === 3 && majorUnit !== "year") groupUnits.push("year");
      groupUnits.push(majorUnit);
    }
    // When the zoom already labels a unit, repeating it in a period row would
    // print the same text twice, so the duplicated row is omitted.
    const renderedGroupUnits = groupUnits.filter((unit) => unit !== ganttScale);
    const groupsByUnit = new Map(
      renderedGroupUnits.map((unit) => [unit, createGanttPeriodGroups(viewScale, unit)]),
    );
    const axisHeight = Math.max(20, 19 + renderedGroupUnits.length * 18);
    const groupRows = renderedGroupUnits.map((unit) => `<div class="cp-gantt-timescale-groups" data-timescale-group-unit="${unit}" style="height:18px">${
      (groupsByUnit.get(unit) ?? []).map((group) => `<span class="cp-gantt-timescale-group" data-timescale-group="${escapeAttribute(group.date)}" title="${escapeAttribute(groupLabel(unit, group))}" style="left:${group.leftPercent}%;width:${group.widthPercent}%">${escapeHtml(groupLabel(unit, group))}</span>`).join("")
    }</div>`).join("");
    const shortMonthLabel = (date: string): string => {
      const calendar = calendarMode === "jalali" ? "-u-ca-persian" : "";
      const language = locale === "fa" ? "fa-IR" : "en-US";
      try {
        return new Intl.DateTimeFormat(`${language}${calendar}`, {
          timeZone: "UTC", month: "short",
        }).format(new Date(`${date}T00:00:00Z`));
      } catch {
        return date.slice(5, 7);
      }
    };
    const tickMarkup = ticks.map((tick, index) => {
    const fullLabel = formatWorkspaceCalendarDate(tick.date, calendarMode);
    // At day resolution daily ticks are too close together for the full date,
    // so the DOM keeps the complete label (and tooltip) while CSS renders only
    // the day number through data-gantt-day.
    const dayLabel = fullLabel.split(/[\/\-]/).filter(Boolean).pop() ?? fullLabel;
    const compactDay = presentation.timescale.dateFormat === "primary" && presentation.timescale.type !== "week-of-year" && ganttScale === "day";
    const dayAttribute = compactDay ? ` data-gantt-day="${escapeAttribute(dayLabel)}"` : "";
    const primary = timescale.dateFormat === "primary";
    // A month timescale prints the month name over its period, as the desktop
    // reference does ("Aug", "Sep"). The first tick may be the range start
    // rather than the first day of a month, so it still names its month.
    const compactMonth = primary && ganttScale === "month";
    const label = !primary
      ? String(ordinalNumberAt(tick.atMs, ordinalStartMs, timescale.ordinalInterval))
      : timescale.type === "week-of-year"
        ? `W${isoWeekNumber(tick.atMs)}`
        : compactMonth
          ? shortMonthLabel(tick.date)
          : fullLabel;
    return `<span class="cp-gantt-axis-tick${index === 0 ? " is-first" : tick.leftPercent > 88 ? " is-last" : ""}${compactDay ? " is-day" : ""}${compactMonth ? " is-month" : ""}" data-gantt-tick="${escapeAttribute(tick.date)}"${dayAttribute} title="${escapeAttribute(fullLabel)}" style="left:${tick.leftPercent}%">${escapeHtml(label)}</span>`;
    }).join("");
    return `<div class="cp-gantt-axis" tabindex="-1" data-timescale-lines="${timescale.lines}" data-timescale-format="${timescale.dateFormat}" data-timescale-interval="${timescale.interval}" data-timescale-type="${timescale.type}" style="height:${axisHeight}px;--cp-timescale-height:${axisHeight}px;--cp-timescale-font-size:${timescale.fontSize}px;--cp-timescale-color:${timescale.textColor};--cp-timescale-bg:${timescale.backgroundColor}"><div class="cp-gantt-axis-track">${groupRows}<div class="cp-gantt-timescale-ticks">${tickMarkup}</div></div></div>`;
  })() : `<div class="cp-gantt-axis is-unscheduled" aria-hidden="true" style="height:20px;--cp-timescale-height:20px"></div>`;
  const linkSvg = showRelationships && links.length
    ? `<svg class="cp-gantt-links" viewBox="0 0 1000 ${rowsHeight}" preserveAspectRatio="none" role="img" aria-label="${escapeAttribute(t.ganttLinks)}" style="height:${rowsHeight}px"><defs><marker id="cp-gantt-arrow" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head" d="M 0 0 L 6 3 L 0 6 z"></path></marker><marker id="cp-gantt-arrow-critical" markerUnits="userSpaceOnUse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path class="cp-gantt-arrow-head is-critical" d="M 0 0 L 6 3 L 0 6 z"></path></marker></defs>${links.map((link) => `<path class="cp-gantt-link${link.critical ? " is-critical" : ""}" data-gantt-link="${escapeAttribute(link.relationshipId)}" data-link-type="${link.type}" data-link-from="${escapeAttribute(link.predecessorId)}" data-link-to="${escapeAttribute(link.successorId)}" data-link-from-x="${link.fromX}" data-link-to-x="${link.toX}" data-link-lane-x="${link.laneX}" data-link-from-y="${link.fromY}" data-link-to-y="${link.toY}" d="${escapeAttribute(link.path)}" marker-end="url(#cp-gantt-arrow${link.critical ? "-critical" : ""})" vector-effect="non-scaling-stroke"><title>${escapeHtml(`${link.type} ${link.predecessorId} → ${link.successorId}${link.lag ? ` (${ganttLagText(link.lag)}${link.lag.unit === "percent" ? "" : " " + link.lag.unit})` : ""}`)}</title></path><path class="cp-gantt-link-hit" data-gantt-link-hit="${escapeAttribute(link.relationshipId)}" d="${escapeAttribute(link.path)}" aria-hidden="true"></path>`).join("")}</svg>`
    : "";
  // Lag and lead badges sit on the routing lane in HTML space, so they stay
  // upright and unscaled while the SVG stretches with the pane width.
  const lagBadges = showRelationships && links.some((link) => link.lag)
    ? `<div class="cp-gantt-lag-layer">${links.filter((link) => link.lag).map((link) => `<span class="cp-gantt-link-lag${link.lag && link.lag.value.trim().startsWith("-") ? " is-lead" : ""}" data-gantt-lag-for="${escapeAttribute(link.relationshipId)}" style="left:${link.laneX}%;top:${ganttRound((link.fromY + link.toY) / 2)}px" title="${escapeAttribute(`${link.type} ${link.predecessorId} → ${link.successorId}: ${ganttLagText(link.lag!)} ${link.lag!.unit}`)}">${escapeHtml(ganttLagText(link.lag!))}</span>`).join("")}</div>`
    : "";
  // Grid lines come from the same tick list as the axis; a CSS gradient cannot
  // follow month lengths, so the DOM carries exact percentages.
  // The reference chart has no fine vertical grid: only the period boundaries
  // (month starts, or year starts at the year zoom) are drawn, as dashed lines.
  const gridLines = hasTimeline ? createGanttAxisTicks(viewScale, ganttScale === "year" ? "year" : "month")
    .map((tick) => `<span class="cp-gantt-grid-line" data-gantt-grid="${escapeAttribute(tick.date)}" style="left:${tick.leftPercent}%"></span>`)
    .join("") : "";
  // Sight Lines tab: minor vertical lines follow the visible tick resolution.
  const minorVertical = gantt.sightLines.minorVertical
    ? ticks
      .filter((tick) => tick.leftPercent > 0.2)
      .map((tick) => `<span class="cp-gantt-grid-line is-minor" data-gantt-grid-minor="${escapeAttribute(tick.date)}" style="left:${tick.leftPercent}%"></span>`)
      .join("")
    : "";
  // Non-working shading comes from the primary calendar's persisted snapshot.
  // It paints behind grid lines and rows and never changes a schedule date.
  const nonWorkingBands = hasTimeline && projectCalendar?.status === "loaded"
    ? createGanttNonWorkingBands(viewScale, {
      workingWeekdays: projectCalendar.workingWeekdays,
      holidays: projectCalendar.holidays,
    })
    : [];
  const nonWorkingLayer = nonWorkingBands.length
    ? `<div class="cp-gantt-nonworking" aria-hidden="true">${nonWorkingBands.map((band) => `<span class="cp-gantt-nonworking-band is-${band.kind}" data-gantt-nonworking="${band.kind}" data-nonworking-from="${band.fromDate}" data-nonworking-to="${band.toDate}" data-nonworking-days="${band.days}" style="left:${ganttRound(band.leftPercent)}%;width:${ganttRound(band.widthPercent)}%" title="${escapeAttribute(`${band.kind === "holiday" ? "Holiday" : "Non-working day"} ${band.fromDate}${band.toDate === band.fromDate ? "" : ` – ${band.toDate}`}`)}"></span>`).join("")}</div>`
    : "";
  // Horizontal sight lines: one before every summary band, plus the documented
  // row interval. They live in the body layer so they scroll with the chart.
  const horizontalSight: string[] = [];
  if (gantt.sightLines.beforeSummaries) {
    rows.forEach((row, index) => {
      if (row.kind === "wbs") horizontalSight.push(`<span class="cp-gantt-sight-line is-horizontal is-major" style="top:${rowMetrics[index]?.top ?? 0}px"></span>`);
    });
  }
  if (gantt.sightLines.rowInterval > 0) {
    for (let index = gantt.sightLines.rowInterval; index < rows.length; index += gantt.sightLines.rowInterval) {
      horizontalSight.push(`<span class="cp-gantt-sight-line is-horizontal is-minor" style="top:${rowMetrics[index]?.top ?? 0}px"></span>`);
    }
  }
  // Completion-percentage point line over the persisted progress of every bar.
  // The Data Date is computed first so each point can be read against it: left
  // of the date is behind schedule, on it is on schedule, right of it is ahead.
  const dataDateMs = dataDate ? Date.parse(`${dataDate.slice(0, 10)}T00:00:00Z`) : Number.NaN;
  const dataDatePercent = hasTimeline && Number.isFinite(dataDateMs)
    ? ((dataDateMs - viewScale.startMs) / viewScale.rangeMs) * 100
    : Number.NaN;
  const progressRelations = { behind: 0, on: 0, ahead: 0 };
  const progressPoints = gantt.progressLine.visible
    ? rows
      .map((row, index) => {
        if (row.kind !== "activity") return null;
        const bar = barById.get(row.activity.id);
        if (!bar) return null;
        const share = Math.min(100, Math.max(0, bar.progressPercent)) / 100;
        const x = bar.leftPercent + bar.widthPercent * share;
        const relation = progressPointRelation(x, dataDatePercent, viewScale.rangeMs);
        if (relation) progressRelations[relation] += 1;
        return { x, y: rowMetrics[index]?.center ?? 0 };
      })
      .filter((point): point is { x: number; y: number } => point !== null)
    : [];
  const progressDateAttributes = Number.isFinite(dataDatePercent)
    ? ` data-gantt-progress-data-date="${escapeAttribute(dataDate!.slice(0, 10))}" data-gantt-progress-behind="${progressRelations.behind}" data-gantt-progress-on="${progressRelations.on}" data-gantt-progress-ahead="${progressRelations.ahead}"`
    : "";
  const progressLine = progressPoints.length > 1
    ? `<svg class="cp-gantt-progress-line-layer" viewBox="0 0 1000 ${rowsHeight}" preserveAspectRatio="none" style="height:${rowsHeight}px;--cp-progress-color:${gantt.progressLine.color};--cp-progress-width:${gantt.progressLine.thickness}px" aria-hidden="true"${progressDateAttributes}><path class="cp-gantt-progress-line" data-gantt-progress-line="${progressPoints.length}" d="${progressPoints.map((point, index) => `${index === 0 ? "M" : "L"} ${ganttRound(point.x * 10)} ${ganttRound(point.y)}`).join(" ")}"/></svg>`
    : "";
  const dataDateLine = gantt.dataDateLine.visible && Number.isFinite(dataDatePercent) && dataDatePercent >= 0 && dataDatePercent <= 100
    ? `<span class="cp-gantt-data-date is-${gantt.dataDateLine.style}" data-gantt-data-date="${escapeAttribute(dataDate!.slice(0, 10))}" style="left:${ganttRound(dataDatePercent)}%;--cp-data-date-color:${gantt.dataDateLine.color};--cp-data-date-width:${gantt.dataDateLine.thickness}px"><span class="cp-gantt-data-date-label">${escapeHtml(uiText(locale, "Data Date", "تاریخ داده"))}</span></span>`
    : "";
  // Legend follows the General tab: only bar types that are actually displayed.
  const legendKinds = GANTT_BAR_KINDS.filter((kind) => presentation.bars[kind].visible);
  const legend = gantt.legend.visible && legendKinds.length
    ? `<div class="cp-gantt-legend is-${gantt.legend.position}" data-gantt-legend="${gantt.legend.position}" aria-label="${escapeAttribute(uiText(locale, "Gantt legend", "راهنمای گانت"))}">${legendKinds.map((kind) => {
      const style = presentation.bars[kind];
      return `<span class="cp-gantt-legend-item" data-gantt-legend-kind="${kind}"><span class="cp-gantt-legend-swatch is-${style.bodyShape} is-pattern-${style.pattern}" style="--cp-legend-color:${style.bodyColor};--cp-legend-border:${style.borderColor}"></span>${escapeHtml(translateWorkspaceUiText(locale, ...GANTT_KIND_LABELS[kind]))}</span>`;
    }).join("")}</div>`
    : "";
  const legendTop = gantt.legend.visible && gantt.legend.position === "top" ? legend : "";
  const legendBottom = gantt.legend.visible && gantt.legend.position === "bottom" ? legend : "";
  const rowsMarkup = renderGanttRows(rows, barById, activityById, presentation, rowHeight, rowMetrics, selectedActivityId, t, locale, viewScale, calendarMode, selectedActivityIds ? new Set(selectedActivityIds) : null, showRelationships);

  return `<div class="cp-gantt-board" role="region" aria-label="${escapeAttribute(t.gantt)}" data-gantt-scale-mode="${ganttScale}" data-bar-labels="${gantt.showBarLabels}" style="--cp-gantt-row-height:${rowHeight}px;--cp-gantt-rows-height:${rowsHeight}px;--cp-gantt-content-width:${contentWidth}px;--cp-bar-label-size:${gantt.labelFontSize}px;--cp-bar-label-color:${gantt.labelColor}">${toolbar}${legendTop}<div class="cp-gantt-chart" style="--cp-gantt-rows:${rows.length}" data-gantt-rows="${rows.length}">${axis}<div class="cp-gantt-body" data-gantt-body="${rows.length}" style="height:${rowsHeight}px">${nonWorkingLayer}${gridLines || minorVertical ? `<div class="cp-gantt-grid" aria-hidden="true">${gridLines}${minorVertical}</div>` : ""}${horizontalSight.length ? `<div class="cp-gantt-sight-lines" aria-hidden="true">${horizontalSight.join("")}</div>` : ""}${rowsMarkup}${progressLine}${dataDateLine}${linkSvg}${lagBadges}</div>${legendBottom}</div></div>`;
}

function renderGanttRows(
  rows: readonly WorkspaceDisplayRow[],
  barById: ReadonlyMap<string, GanttBarGeometry>,
  activityById: ReadonlyMap<string, WorkspaceActivityRow>,
  presentation: WorkspacePresentation,
  rowHeight: number,
  rowMetrics: readonly GanttRowMetric[],
  selectedActivityId: string | null,
  t: WorkspaceLabels,
  locale: string,
  scale: GanttScale,
  calendarMode: WorkspaceCalendarMode,
  selectedIds: ReadonlySet<string> | null = null,
  showRelationships = false,
): string {
  return rows.map((row, index) => {
    const next = rows[index + 1];
    // The reference rules a dashed line only where a group branch finishes, not
    // around every row, so branch extents read without a full row grid.
    const groupEnd = !next || next.depth < row.depth || (isWorkspaceBandRow(row) && next.depth <= row.depth);
    const metric = rowMetrics[index];
    if (row.kind === "wbs") {
      return renderGanttWbsRow(row, presentation, t, locale, scale, calendarMode, groupEnd, Math.max(14, (metric?.height ?? presentation.wbs.rowHeight) - 1));
    }
    if (row.kind === "fieldGroup") {
      return renderGanttFieldGroupRow(row, presentation, locale, scale, calendarMode, groupEnd, Math.max(14, (metric?.height ?? presentation.wbs.rowHeight) - 1));
    }
    return renderGanttActivityRow(row.activity, barById.get(row.activity.id), activityById, presentation, metric?.height ?? rowHeight, selectedActivityId, t, locale, scale, calendarMode, row.depth, groupEnd, selectedIds, showRelationships);
  }).join("");
}

function summaryLabelText(field: GanttBarStyle["labelField"], row: WorkspaceWbsGroupRow, format: { calendarMode?: WorkspaceCalendarMode; locale?: string } = {}): string {
  switch (field) {
    case "activity-id": return row.node.localCode;
    case "activity-name": return row.node.name;
    case "finish-id-name": {
      const finish = row.summary.finishMs === null ? "" : new Date(row.summary.finishMs).toISOString().slice(0, 10);
      return ganttFinishIdName(finish, row.node.localCode, row.node.name, format);
    }
    case "duration": return row.summary.duration === null ? "" : String(row.summary.duration);
    case "progress": return row.summary.progressPercent === null ? "" : `${Math.round(row.summary.progressPercent)}%`;
    default: return "";
  }
}

function renderGanttWbsRow(
  row: WorkspaceWbsGroupRow,
  presentation: WorkspacePresentation,
  t: WorkspaceLabels,
  locale: string,
  scale: GanttScale,
  calendarMode: WorkspaceCalendarMode,
  groupEnd: boolean,
  rowHeight: number,
): string {
  const style = presentation.bars.summary;
  const hasSpan = row.summary.startMs !== null && row.summary.finishMs !== null && row.summary.finishMs >= row.summary.startMs;
  const geometry = style.visible && hasSpan ? ganttPercent(row.summary.startMs as number, row.summary.finishMs as number, scale) : null;
  const title = uiText(
    locale,
    `WBS ${row.node.localCode}: summary derived from ${row.summary.activityCount} persisted activities`,
    `WBS ${row.node.localCode}: خلاصهٔ مشتق‌شده از ${row.summary.activityCount} فعالیت ذخیره‌شده`,
  );
  // The summary bar is configured by the same Bar Styles editor as task bars:
  // height, fill pattern, end shapes and label are read from the persisted style.
  const height = Math.max(3, Math.min(24, style.height));
  const endpoint = (shape: GanttBarStyle["startShape"], color: string, edge: "start" | "finish"): string =>
    shape !== "none" && shape !== "bar"
      ? `<span class="cp-gantt-endpoint is-${edge} is-${shape}" style="--cp-gantt-endpoint:${color}"></span>`
      : "";
  const caps = style.startShape === "bar" && style.finishShape === "bar"
    ? `<span class="cp-gantt-summary-cap is-start" aria-hidden="true"></span><span class="cp-gantt-summary-cap is-finish" aria-hidden="true"></span>`
    : `${endpoint(style.startShape, style.startColor, "start")}${endpoint(style.finishShape, style.finishColor, "finish")}`;
  const labelText = summaryLabelText(style.labelField, row, { calendarMode, locale });
  const labelPosition = resolveGanttLabelPosition(style.labelPosition, geometry ?? { leftPercent: 0, widthPercent: 0 });
  const label = labelText
    ? `<span dir="ltr" class="cp-gantt-bar-label is-${labelPosition}" data-gantt-label-position="${labelPosition}">${escapeHtml(labelText)}</span>`
    : "";
  const bar = geometry
    ? `<div class="cp-gantt-summary-bar is-body-${style.bodyShape} is-pattern-${style.pattern}" data-gantt-summary="derived" data-gantt-wbs-id="${escapeAttribute(row.wbsId)}" data-gantt-bar-shape="${style.bodyShape}" data-gantt-bar-pattern="${style.pattern}" style="left:${ganttRound(geometry.leftPercent)}%;width:${ganttRound(geometry.widthPercent)}%;height:${height}px;--cp-bar-body:${style.bodyColor};--cp-bar-border:${style.borderColor}" title="${escapeAttribute(title)}">${caps}${label}</div>`
    : "";
  const color = wbsLevelColor(presentation.wbs, row.depth);
  // The group row uses the band height, so it stays level with the table band
  // even when the band typography needs a taller row.
  return `<div class="cp-gantt-row cp-gantt-group-row${groupEnd ? " is-group-end" : ""}" data-gantt-wbs-id="${escapeAttribute(row.wbsId)}" data-gantt-depth="${row.depth}" tabindex="-1" data-wbs-level="${Math.min(6, row.depth + 1)}" style="--cp-wbs-level:${color};--cp-gantt-row-height:${rowHeight}px" aria-label="${escapeAttribute(title)}"><div class="cp-gantt-track">${bar}</div></div>`;
}

function fieldGroupSummaryLabelText(field: GanttBarStyle["labelField"], row: WorkspaceFieldGroupRow, format: { calendarMode?: WorkspaceCalendarMode; locale?: string } = {}): string {
  switch (field) {
    case "activity-id":
    case "activity-name": return row.label;
    case "finish-id-name": {
      const finish = row.summary.finishMs === null ? "" : new Date(row.summary.finishMs).toISOString().slice(0, 10);
      return ganttFinishIdName(finish, "", row.label, format);
    }
    case "duration": return row.summary.duration === null ? "" : String(row.summary.duration);
    case "progress": return row.summary.progressPercent === null ? "" : `${Math.round(row.summary.progressPercent)}%`;
    default: return "";
  }
}

/**
 * Gantt summary row for a field-group band. Geometry, style and label come
 * from the persisted Bar Styles summary style, exactly like a WBS band; only
 * the identity text differs.
 */
function renderGanttFieldGroupRow(
  row: WorkspaceFieldGroupRow,
  presentation: WorkspacePresentation,
  locale: string,
  scale: GanttScale,
  calendarMode: WorkspaceCalendarMode,
  groupEnd: boolean,
  rowHeight: number,
): string {
  const style = presentation.bars.summary;
  const hasSpan = row.summary.startMs !== null && row.summary.finishMs !== null && row.summary.finishMs >= row.summary.startMs;
  const geometry = style.visible && hasSpan ? ganttPercent(row.summary.startMs as number, row.summary.finishMs as number, scale) : null;
  const fieldLabel = groupFieldLabel(row.fieldId, locale);
  const title = `${fieldLabel}: ${row.label} — ` + (locale.toLowerCase().startsWith("fa")
    ? `خلاصهٔ مشتق‌شده از ${row.summary.activityCount} فعالیت ذخیره‌شده`
    : `summary derived from ${row.summary.activityCount} persisted activities`);
  const height = Math.max(3, Math.min(24, style.height));
  const endpoint = (shape: GanttBarStyle["startShape"], color: string, edge: "start" | "finish"): string =>
    shape !== "none" && shape !== "bar"
      ? `<span class="cp-gantt-endpoint is-${edge} is-${shape}" style="--cp-gantt-endpoint:${color}"></span>`
      : "";
  const caps = style.startShape === "bar" && style.finishShape === "bar"
    ? `<span class="cp-gantt-summary-cap is-start" aria-hidden="true"></span><span class="cp-gantt-summary-cap is-finish" aria-hidden="true"></span>`
    : `${endpoint(style.startShape, style.startColor, "start")}${endpoint(style.finishShape, style.finishColor, "finish")}`;
  const labelText = fieldGroupSummaryLabelText(style.labelField, row, { calendarMode, locale });
  const labelPosition = resolveGanttLabelPosition(style.labelPosition, geometry ?? { leftPercent: 0, widthPercent: 0 });
  const label = labelText
    ? `<span dir="ltr" class="cp-gantt-bar-label is-${labelPosition}" data-gantt-label-position="${labelPosition}">${escapeHtml(labelText)}</span>`
    : "";
  const bar = geometry
    ? `<div class="cp-gantt-summary-bar is-body-${style.bodyShape} is-pattern-${style.pattern}" data-gantt-summary="derived" data-gantt-field-band="${escapeAttribute(row.bandKey)}" data-gantt-bar-shape="${style.bodyShape}" data-gantt-bar-pattern="${style.pattern}" style="left:${ganttRound(geometry.leftPercent)}%;width:${ganttRound(geometry.widthPercent)}%;height:${height}px;--cp-bar-body:${style.bodyColor};--cp-bar-border:${style.borderColor}" title="${escapeAttribute(title)}">${caps}${label}</div>`
    : "";
  const color = wbsLevelColor(presentation.wbs, row.depth);
  return `<div class="cp-gantt-row cp-gantt-group-row cp-gantt-field-group-row${groupEnd ? " is-group-end" : ""}" data-gantt-field-group="${escapeAttribute(row.bandKey)}" data-group-field="${escapeAttribute(row.fieldId)}" data-gantt-depth="${row.depth}" tabindex="-1" data-wbs-level="${Math.min(6, row.depth + 1)}" style="--cp-wbs-level:${color};--cp-gantt-row-height:${rowHeight}px" aria-label="${escapeAttribute(title)}"><div class="cp-gantt-track">${bar}</div></div>`;
}

function renderGanttActivityRow(
  activity: WorkspaceActivityRow,
  bar: GanttBarGeometry | undefined,
  activityById: ReadonlyMap<string, WorkspaceActivityRow>,
  presentation: WorkspacePresentation,
  rowHeight: number,
  selectedActivityId: string | null,
  t: WorkspaceLabels,
  locale: string,
  scale: GanttScale,
  calendarMode: WorkspaceCalendarMode,
  depth: number,
  groupEnd: boolean,
  selectedIds: ReadonlySet<string> | null = null,
  showRelationships = false,
): string {
  const selected = selectedIds ? selectedIds.has(activity.id) : activity.id === selectedActivityId;
  const rowTitle = `${activity.id}${activity.name ? " — " + activity.name : ""}`;
  const rowClass = `cp-gantt-row${selected ? " is-selected" : ""}${groupEnd ? " is-group-end" : ""}`;
  if (!bar) {
    return `<div class="${rowClass} cp-gantt-row-empty" role="button" data-gantt-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-pressed="${selected ? "true" : "false"}" aria-label="${escapeAttribute(rowTitle)}" data-wbs-level="${Math.min(6, depth + 1)}"><div class="cp-gantt-track"></div></div>`;
  }
  const resolved = activityById.get(bar.activityId) ?? activity;
  const facts = activityBarFacts(resolved, bar);
  const primaryKind = selectPrimaryBarKind(presentation.bars, facts);
  const primaryStyle = primaryKind ? presentation.bars[primaryKind] : null;
  const layers: GanttBarLayer[] = [];
  if (primaryKind && primaryStyle) {
    layers.push({ kind: primaryKind, style: primaryStyle, leftPercent: bar.leftPercent, widthPercent: bar.widthPercent, milestone: bar.milestone });
  }
  const progressStyle = presentation.bars.progress;
  const showProgress = Boolean(primaryStyle) && progressStyle.visible && bar.progressPercent > 0 && barKindMatchesFilter(progressStyle.filter, facts);
  // A progress style assigned to the primary row is drawn as the completion
  // fill inside that bar; on another row it stays an independent bar layer.
  const progressSameRow = Boolean(primaryStyle) && progressStyle.row === primaryStyle?.row;
  if (showProgress && !progressSameRow) {
    layers.push({ kind: "progress", style: progressStyle, leftPercent: bar.leftPercent, widthPercent: Math.max(0.6, bar.widthPercent * (bar.progressPercent / 100)), milestone: false });
  }
  if (presentation.bars.actual.visible && hasActualDates(resolved)) {
    const span = ganttDateSpan(resolved, scale, ["activity.actual_", "actual_"]);
    if (span) layers.push({ kind: "actual", style: presentation.bars.actual, ...span, milestone: false });
  }
  if (presentation.bars.baseline.visible && hasBaselineDates(resolved)) {
    const span = ganttDateSpan(resolved, scale, ["activity.baseline_", "baseline_"]);
    if (span) layers.push({ kind: "baseline", style: presentation.bars.baseline, ...span, milestone: false });
  }
  layers.sort((a, b) => a.style.row - b.style.row);

  // Fit every stacked layer inside the activity row without overlap. When the
  // requested heights exceed the row, they scale down together so the bars
  // stay exactly one-per-row and aligned with the table.
  const gap = 1;
  const desired = layers.map((layer) => Math.min(24, Math.max(3, layer.style.height)));
  const available = Math.max(8, rowHeight - 2);
  const desiredTotal = desired.reduce((total, value) => total + value, 0) + Math.max(0, layers.length - 1) * gap;
  const heights = desiredTotal > available && desiredTotal > 0
    ? desired.map((value) => Math.max(2, Math.floor(value * (available / desiredTotal))))
    : desired;
  const total = heights.reduce((sum, value) => sum + value, 0) + Math.max(0, layers.length - 1) * gap;
  let top = Math.max(1, Math.round((rowHeight - total) / 2));

  let overlay = "";
  if (showProgress && progressSameRow && primaryKind) {
    const primaryIndex = layers.findIndex((layer) => layer.kind === primaryKind);
    const primaryHeight = primaryIndex >= 0 ? heights[primaryIndex] : 0;
    const overlayHeight = Math.max(2, Math.min(progressStyle.height, primaryHeight));
    overlay = `<span class="cp-gantt-progress" style="width:${ganttRound(Math.min(100, bar.progressPercent))}%;height:${overlayHeight}px;background:${progressStyle.bodyColor};top:${Math.round((primaryHeight - overlayHeight) / 2)}px"></span>`;
  }

  // Week boundaries are the shared axis ticks clipped to this bar, so necking
  // stays aligned with the timescale through every zoom and calendar change.
  const barEnd = bar.leftPercent + bar.widthPercent;
  const weekDividers = !bar.milestone && bar.widthPercent > 2
    ? createGanttAxisTicks(scale, "week")
      .filter((tick) => tick.leftPercent > bar.leftPercent + 0.2 && tick.leftPercent < barEnd - 0.2)
      .map((tick) => ((tick.leftPercent - bar.leftPercent) / bar.widthPercent) * 100)
    : [];

  const layerMarkup = layers.map((layer, index) => {
    const height = heights[index];
    const markup = renderGanttBar(layer, top, height, layer.kind === primaryKind ? overlay : "", resolved, bar, t, locale, { calendarMode, locale }, layer.kind === primaryKind && layer.style.necking ? weekDividers : [], layer.kind === primaryKind, showRelationships);
    top += height + gap;
    return markup;
  }).join("");

  // Total float is painted only from an authoritative numeric field. Its unit
  // follows the persisted scheduling setting, so the bar stays a duration
  // indicator and never invents a finish date.
  const floatDays = Number(resolved.cells?.total_float);
  const floatEndMs = Number.isFinite(floatDays) && floatDays > 0 && !bar.milestone && primaryStyle
    ? Date.parse(resolved.gantt?.finish ?? "") + floatDays * 86_400_000
    : Number.NaN;
  const floatMarkup = Number.isFinite(floatEndMs)
    ? (() => {
      const span = ganttPercent(Date.parse(resolved.gantt!.finish), floatEndMs, scale);
      const left = Math.min(100, bar.leftPercent + bar.widthPercent);
      const width = Math.max(0.4, span.leftPercent + span.widthPercent - left);
      return `<span class="cp-gantt-float" data-gantt-float="${escapeAttribute(bar.activityId)}" data-gantt-float-value="${escapeAttribute(String(resolved.cells?.total_float))}" title="${escapeAttribute(uiText(locale, `Total float ${resolved.cells?.total_float}`, `شناوری کل ${resolved.cells?.total_float}`))}" style="left:${ganttRound(left)}%;width:${ganttRound(width)}%"></span>`;
    })()
    : "";
  return `<div class="${rowClass}" role="button" data-gantt-activity-id="${escapeAttribute(bar.activityId)}" tabindex="0" aria-pressed="${selected ? "true" : "false"}" aria-label="${escapeAttribute(rowTitle)}" data-wbs-level="${Math.min(6, depth + 1)}"><div class="cp-gantt-track">${layerMarkup}${floatMarkup}</div></div>`;
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

function wbsMilestoneRowMarkup(
  locale: WorkspaceState["locale"],
  item: { id: string; name: string; weight: string; completed: boolean },
): string {
  return `<tr data-wbs-milestone-row>
    <td></td>
    <td><input name="milestone_id" maxlength="80" value="${escapeAttribute(item.id)}" required autocomplete="off"></td>
    <td><input name="milestone_name" maxlength="180" value="${escapeAttribute(item.name)}" required autocomplete="off"></td>
    <td><input name="milestone_weight" type="number" min="0.01" step="0.01" value="${escapeAttribute(item.weight)}" required></td>
    <td><input name="milestone_completed" type="checkbox"${item.completed ? " checked" : ""}></td>
    <td><button type="button" data-wbs-milestone-remove aria-label="${escapeAttribute(uiText(locale, "Remove milestone", "حذف نقطه عطف"))}">${workspaceIcon("close")}</button></td>
  </tr>`;
}

/** Mirrors the server's weighted roll-up from the editor's current values. */
function updateWbsMilestoneRollup(form: HTMLElement): void {
  const host = form.closest<HTMLElement>(".cp-wbs-milestones");
  if (!host) return;
  const rows = [...form.querySelectorAll<HTMLElement>("[data-wbs-milestone-row]")];
  const milestones: WorkspaceWbsMilestone[] = rows.map((row, index) => ({
    id: row.querySelector<HTMLInputElement>('[name="milestone_id"]')?.value.trim() ?? "",
    name: row.querySelector<HTMLInputElement>('[name="milestone_name"]')?.value.trim() ?? "",
    weight: Number(row.querySelector<HTMLInputElement>('[name="milestone_weight"]')?.value ?? "0"),
    completed: row.querySelector<HTMLInputElement>('[name="milestone_completed"]')?.checked ?? false,
    sequenceNumber: index,
  }));
  const total = milestones.reduce((sum, item) => sum + (Number.isFinite(item.weight) ? item.weight : 0), 0);
  const weighted = weightedPercentComplete(
    milestones.map((item) => ({ ...item, weight: Number.isFinite(item.weight) ? item.weight : 0 })),
  );
  const totalEl = host.querySelector<HTMLElement>("[data-wbs-milestone-total]");
  if (totalEl) totalEl.textContent = String(Math.round(total * 100) / 100);
  const rollupEl = host.querySelector<HTMLElement>("[data-wbs-milestone-rollup]");
  if (rollupEl) rollupEl.textContent = `${weighted.toFixed(2)}%`;
  rows.forEach((row, index) => {
    const indexCell = row.querySelector<HTMLElement>("td");
    if (indexCell) indexCell.textContent = String(index + 1);
  });
}

function renderWbsDetails(state: WorkspaceState, activeTab: string): string {
  const node = state.wbsNodes.find((item) => item.id === state.selectedWbsId);
  const panel = (tab: string): string => {
    if (!node) return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "Select a WBS element to display its details.", "برای نمایش جزئیات، یک عنصر ساختار شکست انتخاب کنید."))}</p>`;
    if (tab === "general") {
      const parentNode = node.parentWbsId ? state.wbsNodes.find((item) => item.id === node.parentWbsId) : null;
      const parent = node.parentKind === "project"
        ? uiText(state.locale, "Project root", "ریشه پروژه")
        : parentNode ? `${parentNode.localCode} — ${parentNode.name}` : node.parentWbsId ?? "—";
      const percent = node.percentComplete ?? null;
      const fields = [
        [uiText(state.locale, "WBS ID", "شناسه WBS"), node.id],
        [uiText(state.locale, "WBS Code", "کد WBS"), node.localCode],
        [uiText(state.locale, "WBS Name", "نام WBS"), node.name],
        [uiText(state.locale, "Status", "وضعیت"), wbsStatusLabel(state.locale, node.status)],
        [uiText(state.locale, "Percent complete technique", "روش درصد تکمیل"), wbsTechniqueLabel(state.locale, node.percentCompleteTechnique)],
        [uiText(state.locale, "Weighted percent complete", "درصد تکمیل وزنی"), percent === null ? "—" : `${percent.toFixed(2)}%`],
        [uiText(state.locale, "Parent kind", "نوع والد"), node.parentKind === "project" ? uiText(state.locale, "Project", "پروژه") : uiText(state.locale, "WBS element", "عنصر WBS")],
        [uiText(state.locale, "Parent", "والد"), parent],
        [uiText(state.locale, "Sequence", "ترتیب"), String(node.sequenceNumber)],
        [uiText(state.locale, "Record revision", "ویرایش رکورد"), String(node.recordRevision)],
      ];
      const fieldsHtml = `<div class="cp-activity-detail-fields">${fields.map(([label, value]) => `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
      const statusSelect = (["planned", "active", "inactive", "what_if"] as const)
        .map((status) => `<option value="${status}" ${(node.status ?? "planned") === status ? "selected" : ""}>${escapeHtml(wbsStatusLabel(state.locale, status))}</option>`)
        .join("");
      const techniqueSelect = (["activities", "milestones"] as const)
        .map((technique) => `<option value="${technique}" ${(node.percentCompleteTechnique ?? "activities") === technique ? "selected" : ""}>${escapeHtml(wbsTechniqueLabel(state.locale, technique))}</option>`)
        .join("");
      return `${fieldsHtml}
        <form class="cp-wbs-status-form" data-wbs-status-form="${escapeAttribute(node.id)}" data-wbs-revision="${node.recordRevision}">
          <label>${escapeHtml(uiText(state.locale, "Status", "وضعیت"))}<select name="status">${statusSelect}</select></label>
          <label>${escapeHtml(uiText(state.locale, "Percent complete technique", "روش درصد تکمیل"))}<select name="percent_complete_technique">${techniqueSelect}</select></label>
          <button type="submit">${escapeHtml(uiText(state.locale, "Save WBS settings", "ذخیره تنظیمات WBS"))}</button>
        </form>`;
    }
    if (tab === "milestones") {
      if (node.milestones === undefined) {
        return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "No authoritative WBS milestone records are loaded for this element.", "اطلاعات مرجع نقاط عطف WBS برای این عنصر بارگذاری نشده است."))}</p>`;
      }
      const milestones = node.milestones;
      const weighted = weightedPercentComplete(milestones);
      const totalWeight = milestones.reduce((sum, item) => sum + item.weight, 0);
      const rows = milestones.map((item, index) => `<tr data-wbs-milestone-row>
        <td>${index + 1}</td>
        <td><input name="milestone_id" maxlength="80" value="${escapeAttribute(item.id)}" required autocomplete="off"></td>
        <td><input name="milestone_name" maxlength="180" value="${escapeAttribute(item.name)}" required autocomplete="off"></td>
        <td><input name="milestone_weight" type="number" min="0.01" step="0.01" value="${item.weight}" required></td>
        <td><input name="milestone_completed" type="checkbox"${item.completed ? " checked" : ""}></td>
        <td><button type="button" data-wbs-milestone-remove aria-label="${escapeAttribute(uiText(state.locale, "Remove milestone", "حذف نقطه عطف"))}">${workspaceIcon("close")}</button></td>
      </tr>`).join("");
      return `<div class="cp-wbs-milestones">
        <div class="cp-activity-detail-fields">
          <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Technique", "روش"))}</span><strong>${escapeHtml(wbsTechniqueLabel(state.locale, node.percentCompleteTechnique))}</strong></div>
          <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Total weight", "وزن کل"))}</span><strong data-wbs-milestone-total>${escapeHtml(String(Math.round(totalWeight * 100) / 100))}</strong></div>
          <div class="cp-activity-detail-field"><span>${escapeHtml(uiText(state.locale, "Weighted percent complete", "درصد تکمیل وزنی"))}</span><strong data-wbs-milestone-rollup>${escapeHtml(`${weighted.toFixed(2)}%`)}</strong></div>
        </div>
        <form class="cp-wbs-milestones-form" data-wbs-milestones-form="${escapeAttribute(node.id)}" data-wbs-revision="${node.recordRevision}">
          <table class="cp-wbs-milestone-table">
            <thead><tr>
              <th scope="col">#</th>
              <th scope="col">${escapeHtml(uiText(state.locale, "Milestone ID", "شناسه نقطه عطف"))}</th>
              <th scope="col">${escapeHtml(uiText(state.locale, "Name", "نام"))}</th>
              <th scope="col">${escapeHtml(uiText(state.locale, "Weight", "وزن"))}</th>
              <th scope="col">${escapeHtml(uiText(state.locale, "Completed", "تکمیل‌شده"))}</th>
              <th scope="col"></th>
            </tr></thead>
            <tbody data-wbs-milestone-rows>${rows}</tbody>
          </table>
          <div class="cp-wbs-milestones-actions">
            <button type="button" data-wbs-milestone-add>${escapeHtml(uiText(state.locale, "Add milestone", "افزودن نقطه عطف"))}</button>
            <button type="submit">${escapeHtml(uiText(state.locale, "Save milestones", "ذخیره نقاط عطف"))}</button>
          </div>
          <p class="cp-activity-detail-note">${escapeHtml(uiText(state.locale, "The weighted percent complete is completed milestone weight divided by total weight. Saving replaces the element's milestone list and advances its record revision.", "درصد تکمیل وزنی برابر وزن نقاط عطف تکمیل‌شده تقسیم بر وزن کل است. ذخیره، فهرست نقاط عطف عنصر را جایگزین کرده و ویرایش رکورد آن را افزایش می‌دهد."))}</p>
        </form>
      </div>`;
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

function renderWindowDetailsPanel(state: WorkspaceState, t: WorkspaceLabels, container: HTMLElement, options: WorkspaceRendererOptions = {}): string {
  if (state.activeMenu === "schedule") {
    return renderActivityDetailsPanel(state, t, activityDetailsTabByContainer.get(container) ?? "general", getActivityDetailsVisibleTabs(container));
  }
  if (state.activeMenu === "project") {
    const activeTab = projectDetailsTabByContainer.get(container) ?? "general";
    const summary = options.projectSummary ?? null;
    const field = (label: string, content: string): string =>
      `<div class="cp-activity-detail-field"><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`;
    const dateSystemLabel = (row: ProjectSummary): string => row.date_system === "jalali"
      ? uiText(state.locale, "Jalali", "شمسی")
      : row.date_system === "gregorian" ? uiText(state.locale, "Gregorian", "میلادی") : "—";
    const notRead = (): string => `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, "The authoritative project record has not been read yet. Refresh the workspace to read it; no placeholder values are shown.", "رکورد مرجع پروژه هنوز خوانده نشده است. برای خواندن آن محیط کار را به‌روزرسانی کنید؛ هیچ مقدار جایگزینی نمایش داده نمی‌شود."))}</p>`;
    const projectContent = (tab: string): string => {
      if (tab === "general") {
        if (!summary) return notRead();
        return `<div class="cp-activity-detail-fields">
          ${field(uiText(state.locale, "Project Name", "نام پروژه"), summary.name || summary.project_id)}
          ${field(uiText(state.locale, "Project ID", "شناسه پروژه"), summary.project_id)}
          ${field(uiText(state.locale, "Business Domain", "حوزهٔ کاری"), businessDomainLabel(state.locale, summary.business_domain))}
          ${field(uiText(state.locale, "Status", "وضعیت"), projectStatusLabel(state.locale, summary.status))}
          ${field(uiText(state.locale, "Description", "توضیحات"), summary.description?.trim() || "—")}
          ${field(uiText(state.locale, "Start Date", "تاریخ شروع"), summary.start_date || "—")}
          ${field(uiText(state.locale, "Date System", "تقویم"), dateSystemLabel(summary))}
          ${field(uiText(state.locale, "Primary Calendar", "تقویم اصلی"), summary.primary_calendar_id || "—")}
          ${field(uiText(state.locale, "Settings revision", "ویرایش تنظیمات"), `R${summary.settings_revision ?? 0}`)}
        </div>`;
      }
      if (tab === "dates") {
        if (!summary) return notRead();
        return `<div class="cp-activity-detail-fields">
          ${field(uiText(state.locale, "Planned Start", "شروع برنامه‌ای"), summary.start_date || "—")}
          ${field(uiText(state.locale, "Date System", "تقویم"), dateSystemLabel(summary))}
        </div>
        <p class="cp-activity-detail-note">${escapeHtml(uiText(state.locale, "Forecast, actual and finish dates are produced by the scheduling core from the activity data; this project record stores only the planned start.", "تاریخ‌های پیش‌بینی، واقعی و پایان توسط هستهٔ زمان‌بندی از داده‌های فعالیت تولید می‌شوند؛ این رکورد پروژه فقط شروع برنامه‌ای را ذخیره می‌کند."))}</p>`;
      }
      if (tab === "defaults") {
        if (!summary) return notRead();
        const activityTypeLabel = (value: string): string => {
          if (value === "Resource Dependent") return uiText(state.locale, "Resource Dependent", "وابسته به منبع");
          if (value === "Level of Effort") return uiText(state.locale, "Level of Effort", "تلاش مستمر");
          if (value === "Start Milestone") return uiText(state.locale, "Start Milestone", "نقطه عطف آغاز");
          if (value === "Finish Milestone") return uiText(state.locale, "Finish Milestone", "نقطه عطف پایان");
          if (value === "WBS Summary") return uiText(state.locale, "WBS Summary", "خلاصهٔ WBS");
          return uiText(state.locale, "Task Dependent", "وابسته به وظیفه");
        };
        const percentTypeLabel = (value: string): string => {
          if (value === "UNITS") return uiText(state.locale, "Units", "واحدها");
          if (value === "PHYSICAL") return uiText(state.locale, "Physical", "فیزیکی");
          if (value === "SCOPE") return uiText(state.locale, "Scope", "دامنه");
          return uiText(state.locale, "Duration", "مدت");
        };
        return `<div class="cp-activity-detail-fields">
          ${field(uiText(state.locale, "Default activity type", "نوع پیش‌فرض فعالیت"), activityTypeLabel(summary.default_activity_type ?? "Task Dependent"))}
          ${field(uiText(state.locale, "Percent complete type", "نوع درصد تکمیل"), percentTypeLabel((summary.default_percent_complete_type ?? "DURATION").toUpperCase()))}
          ${field(uiText(state.locale, "Activity ID prefix", "پیشوند شناسهٔ فعالیت"), summary.activity_id_prefix || "—")}
          ${field(uiText(state.locale, "Activity ID suffix", "پسوند شناسهٔ فعالیت"), summary.activity_id_suffix || "—")}
          ${field(uiText(state.locale, "ID increment", "گام افزایش شناسه"), String(summary.activity_id_increment ?? 10))}
          ${field(uiText(state.locale, "Increment from selected activity", "افزایش بر پایهٔ فعالیت انتخاب‌شده"), summary.increment_activity_id ? uiText(state.locale, "Yes", "بله") : uiText(state.locale, "No", "خیر"))}
        </div>
        <p class="cp-activity-detail-note">${escapeHtml(uiText(state.locale, "Applied when a new activity is created. Changing a default never rewrites existing activities.", "هنگام ساخت فعالیت جدید اعمال می‌شود. تغییر پیش‌فرض، فعالیت‌های موجود را بازنویسی نمی‌کند."))}</p>`;
      }
      if (tab === "settings") {
        if (!summary) return notRead();
        return `<div class="cp-activity-detail-fields">
          ${field(uiText(state.locale, "Date System", "تقویم"), dateSystemLabel(summary))}
          ${field(uiText(state.locale, "Primary Calendar", "تقویم اصلی"), summary.primary_calendar_id || "—")}
          ${field(uiText(state.locale, "Business Domain", "حوزهٔ کاری"), businessDomainLabel(state.locale, summary.business_domain))}
          ${field(uiText(state.locale, "Settings revision", "ویرایش تنظیمات"), `R${summary.settings_revision ?? 0}`)}
        </div>
        <p class="cp-activity-detail-note">${escapeHtml(uiText(state.locale, "Fiscal year start and default price per unit are not stored on the project record this server exposes. Activity ID numbering is edited on the Defaults tab.", "شروع سال مالی و قیمت پیش‌فرض واحد در رکورد پروژه‌ای که این سرور ارائه می‌دهد ذخیره نمی‌شوند. شماره‌گذاری شناسهٔ فعالیت در زبانهٔ پیش‌فرض‌ها ویرایش می‌شود."))}</p>`;
      }
      const tabInfo = PROJECT_DETAIL_TABS.find(([key]) => key === tab);
      return `<p class="cp-activity-detail-empty">${escapeHtml(uiText(state.locale, `No authoritative ${tabInfo?.[1] ?? "project"} detail fields are loaded for this project.`, `اطلاعات مرجع بخش «${tabInfo?.[2] ?? "جزئیات پروژه"}» برای این پروژه بارگذاری نشده است.`))}</p>`;
    };
    return `<div class="cp-activity-details cp-project-details">
      <header class="cp-activity-details-heading"><div><h2 id="cp-details-heading">${escapeHtml(uiText(state.locale, "Project Details", "جزئیات پروژه"))}</h2><span>${escapeHtml(summary ? `${summary.name} — ${summary.project_id}` : state.context.project_id)}</span></div><div class="cp-activity-details-heading-actions"><small>${escapeHtml(uiText(state.locale, "Selected project", "پروژه انتخاب‌شده"))}</small><button type="button" data-project-settings>${escapeHtml(uiText(state.locale, "Edit Project", "ویرایش پروژه"))}</button></div></header>
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
  ["relationships", "Relationships", "روابط"],
  ["codes", "Codes", "کدها"],
  ["notebook", "Notebook", "دفترچه"],
  ["steps", "Steps", "گام‌ها"],
  ["wps-docs", "WPs & Docs", "محصولات کاری و اسناد"],
  ["expenses", "Expenses", "هزینه‌ها"],
  ["issues", "Issues", "مسائل"],
  ["risks", "Risks", "ریسک‌ها"],
  ["summary", "Summary", "خلاصه"],
  ["udfs", "UDFs", "فیلدهای کاربر"],
  ["update-history", "Update History", "تاریخچه تغییرات"],
  ["calendar", "Calendar (CUBI)", "تقویم (CUBI)"],
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

function renderLayoutOptionsDialog(state: WorkspaceState, t: WorkspaceLabels, options: WorkspaceRendererOptions): string {
  const scaleLabels: Record<WorkspaceGanttScale, string> = {
    day: t.scaleDay,
    week: t.scaleWeek,
    month: t.scaleMonth,
    quarter: t.scaleQuarter,
    year: t.scaleYear,
  };
  const topLayout = readWorkspaceTopLayout(state);
  const bottomLayout = readWorkspaceBottomLayout(state, options.activityUsage);
  const networkAvailable = isWorkspaceTopLayoutAvailable("activity-network", state);
  const traceAvailable = isWorkspaceTraceLogicAvailable(state);
  const usageAvailable = usageSourceAvailable(options.activityUsage);
  const presentation = options.presentation ?? DEFAULT_PRESENTATION;
  // Baseline bars are only offered when a stored baseline window is projected
  // onto the grid; otherwise the toggle would promise a date the project lacks.
  const baselineAvailable = state.activities.some(hasBaselineDates);
  return `<dialog class="cp-layout-options-dialog" data-layout-options-dialog aria-labelledby="cp-layout-options-title">
    <form method="dialog" class="cp-layout-options-form">
      <header><div><small>${escapeHtml(uiText(state.locale, "Activities window", "پنجره فعالیت‌ها"))}</small><h2 id="cp-layout-options-title">${escapeHtml(uiText(state.locale, "Layout Options", "گزینه‌های چیدمان"))}</h2></div><button type="button" data-layout-options-close aria-label="${escapeAttribute(uiText(state.locale, "Close", "بستن"))}">×</button></header>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Top Layout", "چیدمان بالا"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Primary view", "نمای اصلی"))}
          <select data-top-layout><option value="table-only"${topLayout === "table-only" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Table", "جدول فعالیت‌ها"))}</option><option value="table-gantt"${topLayout === "table-gantt" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Table + Gantt Chart", "جدول فعالیت‌ها + نمودار گانت"))}</option><option value="activity-network"${networkAvailable ? "" : " disabled"}${topLayout === "activity-network" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Network", "شبکهٔ فعالیت‌ها"))}</option><option value="activity-usage-spreadsheet" disabled>Activity Usage Spreadsheet</option><option value="activity-usage-profile" disabled>Activity Usage Profile</option><option value="resource-usage-spreadsheet" disabled>Resource Usage Spreadsheet</option><option value="resource-usage-profile" disabled>Resource Usage Profile</option></select>
        </label>
        ${networkAvailable ? "" : `<p>${escapeHtml(uiText(state.locale, "The Activity Network needs persisted activities and relationships. It stays disabled for this project instead of drawing placeholder nodes.", "شبکهٔ فعالیت‌ها به فعالیت‌ها و روابط ذخیره‌شده نیاز دارد. برای این پروژه غیرفعال می‌ماند تا گره‌های ساختگی ترسیم نشوند."))}</p>`}
        <p>${escapeHtml(uiText(state.locale, "The Activity Network and Trace Logic are drawn from the persisted activities and relationships already loaded in this workspace; the Activity Usage views project stored assignment periods and stay disabled until that read returns rows.", "شبکهٔ فعالیت‌ها و ردیابی منطق از فعالیت‌ها و روابط ذخیره‌شده و بارگذاری‌شده در این محیط کار ترسیم می‌شوند؛ نماهای مصرف، دوره‌های تخصیص ذخیره‌شده را نمایش می‌دهند و تا زمانی که این خواندن ردیفی برنگرداند غیرفعال می‌مانند."))}</p>
        <h3>${escapeHtml(uiText(state.locale, "Bottom Layout", "چیدمان پایین"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Details view", "نمای جزئیات"))}
          <select data-bottom-layout><option value="details"${bottomLayout === "details" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Details", "جزئیات فعالیت"))}</option><option value="trace-logic"${traceAvailable ? "" : " disabled"}${bottomLayout === "trace-logic" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Trace Logic", "ردیابی منطق"))}</option><option value="usage-spreadsheet"${usageAvailable ? "" : " disabled"}${bottomLayout === "usage-spreadsheet" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Usage Spreadsheet", "صفحه‌گستردهٔ مصرف فعالیت"))}</option><option value="usage-profile"${usageAvailable ? "" : " disabled"}${bottomLayout === "usage-profile" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "Activity Usage Profile", "نیم‌رخ مصرف فعالیت"))}</option><option value="none"${bottomLayout === "none" ? " selected" : ""}>${escapeHtml(uiText(state.locale, "None", "بدون نما"))}</option></select>
        </label>
        ${traceAvailable ? "" : `<p>${escapeHtml(uiText(state.locale, "Trace Logic needs a selected activity and persisted relationships. Select an activity with loaded logic to enable it.", "ردیابی منطق به یک فعالیت انتخاب‌شده و روابط ذخیره‌شده نیاز دارد. برای فعال‌شدن، فعالیتی با منطق بارگذاری‌شده انتخاب کنید."))}</p>`}
        ${usageAvailable ? "" : `<p>${escapeHtml(uiText(state.locale, "The Activity Usage views need stored assignment periods for this project. They stay disabled instead of drawing a fabricated zero profile.", "نماهای مصرف فعالیت به دوره‌های تخصیص ذخیره‌شده برای این پروژه نیاز دارند. برای پرهیز از رسم نیم‌رخ صفر ساختگی، غیرفعال می‌مانند."))}</p>`}
      </section>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Timescale", "مقیاس زمانی"))}</h3>
        <label>${escapeHtml(uiText(state.locale, "Display interval", "بازه نمایش"))}
          <select data-layout-timescale>${(["day", "week", "month", "quarter", "year"] as const).map((mode) => `<option value="${mode}"${state.ganttScale === mode ? " selected" : ""}>${escapeHtml(scaleLabels[mode])}</option>`).join("")}</select>
        </label>
      </section>
      <section class="cp-layout-options-section">
        <h3>${escapeHtml(uiText(state.locale, "Gantt display", "نمایش گانت"))}</h3>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-links${state.showGanttRelationships ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" disabled> ${escapeHtml(uiText(state.locale, "Show critical path", "نمایش مسیر بحرانی"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-progress-line${presentation.gantt.progressLine.visible ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show progress line", "نمایش خط پیشرفت"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-baseline${presentation.bars.baseline.visible ? " checked" : ""}${baselineAvailable ? "" : " disabled"}> ${escapeHtml(uiText(state.locale, "Show baseline bars", "نمایش میله‌های مبنا"))}</label>
        <label class="cp-layout-options-check"><input type="checkbox" data-layout-data-date-line${presentation.gantt.dataDateLine.visible ? " checked" : ""}> ${escapeHtml(uiText(state.locale, "Show Data Date line", "نمایش خط تاریخ داده"))}</label>
        <p>${escapeHtml(uiText(state.locale, "The progress line, baseline bars and Data Date line write the same saved layout presentation as the Bars dialog; they never change schedule data. The critical path is shown by the Critical bar style and the Critical filter, so this dialog does not add a second toggle.", "خط پیشرفت، میله‌های مبنا و خط تاریخ داده همان ارائهٔ چیدمان ذخیره‌شدهٔ کادر میله‌ها را می‌نویسند و هرگز دادهٔ زمان‌بندی را تغییر نمی‌دهند. مسیر بحرانی با سبک میلهٔ بحرانی و پالایهٔ بحرانی نمایش داده می‌شود؛ این کادر کلید دوم نمی‌سازد."))}</p>
        ${baselineAvailable ? "" : `<p data-layout-baseline-unavailable>${escapeHtml(uiText(state.locale, "No stored baseline window is loaded for this project, so the baseline bars stay disabled instead of drawing a derived window.", "برای این پروژه پنجرهٔ مبنای ذخیره‌شده‌ای بارگذاری نشده است؛ میله‌های مبنا غیرفعال می‌مانند تا پنجرهٔ ساختگی رسم نشود."))}</p>`}
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

function menuButton(key: WorkspaceState["activeMenu"], label: string, state: WorkspaceState, icon: WorkspaceIconName): string {
  const active = key === state.activeMenu;
  return `<button type="button" class="cp-rail-button" data-menu="${key}" aria-current="${active ? "page" : "false"}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

function railActionButton(action: string, label: string, icon: WorkspaceIconName): string {
  return `<button type="button" class="cp-rail-button" data-rail-action="${escapeAttribute(action)}" title="${escapeAttribute(label)}" aria-label="${escapeAttribute(label)}">${workspaceIcon(icon)}<span class="cp-rail-label">${escapeHtml(label)}</span></button>`;
}

/** One projection of the state facts the contextual Add menu depends on. */
function contextAddState(state: WorkspaceState, options: WorkspaceRendererOptions): Parameters<typeof contextAddCommands>[0] {
  return {
    activeMenu: state.activeMenu,
    canWrite: options.canWrite === true,
    hasWbs: state.wbsNodes.length > 0,
    hasSelectedActivity: Boolean(state.selectedActivityId),
    hasCalendarCatalog: state.calendarCatalog.calendars.length > 0,
  };
}

/**
 * The incremental menu/selection path must rebuild the rail commands from the
 * same projection as a full render; otherwise the previous window's commands
 * would stay clickable after switching windows.
 */
function refreshContextAddMenu(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions): void {
  const current = typeof container.querySelector === "function"
    ? container.querySelector<HTMLElement>("[data-context-add]")
    : null;
  if (!current) return;
  current.outerHTML = renderContextAddMenu(contextAddCommands(contextAddState(state, options)), state);
}

/**
 * The single "Add" entry at the top of the contextual rail. It opens a menu of
 * real desktop commands for the active window; unavailable commands stay with
 * their reason instead of disappearing behind a decorative button.
 */
function renderContextAddMenu(items: readonly ContextAddItem[], state: WorkspaceState): string {
  const localized = (value: { en: string; fa: string }): string =>
    state.locale.toLowerCase().startsWith("fa") ? value.fa : value.en;
  const label = uiText(state.locale, "Add", "افزودن");
  const entries = items.map((item) => {
    const disabled = item.disabledReason ? " disabled aria-disabled=\"true\"" : "";
    const reason = item.disabledReason
      ? `<small class="cp-context-add-reason">${escapeHtml(localized(item.disabledReason))}</small>`
      : "";
    const title = item.disabledReason ? `${localized(item.label)} — ${localized(item.disabledReason)}` : localized(item.label);
    return `<button type="button" role="menuitem" data-desktop-command="${escapeAttribute(item.command)}"${disabled} title="${escapeAttribute(title)}">${workspaceIcon(item.icon)}<span>${escapeHtml(localized(item.label))}</span>${reason}</button>`;
  });
  return `<details class="cp-context-add-menu" data-context-add>
    <summary role="button" aria-haspopup="menu" aria-expanded="false" aria-label="${escapeAttribute(label)}" title="${escapeAttribute(label)}">+</summary>
    <div class="cp-context-add-popup" data-context-add-popup role="menu" aria-label="${escapeAttribute(label)}">
      <strong>${escapeHtml(label)}</strong>
      ${entries.length
        ? entries.join("")
        : `<p class="cp-context-add-empty">${escapeHtml(uiText(state.locale, "This window has no create action.", "این پنجره فرمان ایجاد ندارد."))}</p>`}
    </div>
  </details>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value); }

/** Presentation colours are hex by contract; reject anything else before it reaches CSS. */
function presentationColor(value: string): string {
  return /^#[0-9a-f]{6}$/i.test(value) ? value : "#1f2933";
}
