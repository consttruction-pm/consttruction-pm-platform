/**
 * CUBI Form Builder workspace surface.
 *
 * This module is the operational client for the server-side form builder API:
 * it reads and writes real templates, versions, submissions and approvals; it
 * never evaluates formulas itself and never fabricates project values. The
 * server owns validation, the shared Formula Core, version immutability and
 * permission checks. Client rendering only reflects those contracts.
 */

export type FormBuilderContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
};

export type FormBuilderOptions = {
  host: HTMLElement;
  context: FormBuilderContext;
  locale: string;
  calendarMode: "gregorian" | "jalali";
  onClose?: () => void;
};

export type FormBuilderHandle = {
  close: () => void;
  isOpen: () => boolean;
};

type Locale = "en" | "fa" | "de" | "zh";
type Library = "organization" | "project";
type FormTab = "library" | "design" | "reports" | "print";
type DesignTab = "schema" | "tables" | "formulas" | "charts" | "workflow" | "page" | "versions";

type UnknownRecord = Record<string, any>;

type TemplateSummary = {
  template_id: string;
  library: Library;
  status: string;
  published_version: number | null;
  record_revision: number;
  title: string;
  title_text: string;
  category: string;
  tags: string[];
  default_locale: string;
  updated_at: string;
  updated_by: string;
  source_template_id: string | null;
  field_count: number;
  table_count: number;
  formula_count: number;
  chart_count: number;
  draft_dirty: boolean;
};

type TemplateDetail = TemplateSummary & {
  payload: UnknownRecord;
  published?: { version: number; payload: UnknownRecord } | null;
  issues: { code: string; path: string; message_key: string; severity: string }[];
  valid?: boolean;
};

type SubmissionSummary = {
  submission_id: string;
  template_id: string;
  template_version: number;
  status: string;
  title: string;
  author: string;
  assigned_to?: string | null;
  report_date?: string | null;
  record_revision: number;
  updated_at: string;
};

type SubmissionDetail = SubmissionSummary & {
  values: UnknownRecord;
  tables: UnknownRecord;
  calculated: UnknownRecord;
  bindings?: UnknownRecord;
  template?: UnknownRecord;
  approvals?: UnknownRecord[];
  revisions?: UnknownRecord[];
  validation?: { valid?: boolean; issues?: UnknownRecord[] };
  issues?: UnknownRecord[];
  editable?: boolean;
};

type Assignee = {
  user_id: string;
  label: string;
  label_fa?: string;
  roles: string[];
};

type BindingSource = {
  source: string;
  label: unknown;
  fields: { field: string; result_type: string }[];
  values: UnknownRecord;
  provenance: UnknownRecord;
};

type ModalState =
  | null
  | { kind: "new-template"; library: Library }
  | { kind: "new-report" }
  | { kind: "publish" }
  | { kind: "reason"; action: "return" | "reject" }
  | { kind: "add-component"; sectionId: string }
  | { kind: "diff" };

type UiState = {
  tab: FormTab;
  designTab: DesignTab;
  designLibrary: Library;
  selectedTemplateId: string | null;
  template: TemplateDetail | null;
  orgTemplates: TemplateSummary[];
  projectTemplates: TemplateSummary[];
  submissions: SubmissionSummary[];
  submission: SubmissionDetail | null;
  draftValues: UnknownRecord;
  draftTables: UnknownRecord;
  draftTitle: string;
  draftReportDate: string;
  draftAssignee: string;
  assignees: Assignee[];
  bindings: BindingSource[];
  permissions: Record<string, boolean>;
  viewer: string;
  versions: UnknownRecord[];
  diff: UnknownRecord | null;
  printHtml: string;
  selectedFieldId: string | null;
  selectedTableId: string | null;
  selectedFormulaId: string | null;
  selectedChartId: string | null;
  selectedSectionId: string | null;
  search: string;
  status: { kind: "info" | "ok" | "error"; message: string } | null;
  validationIssues: { code: string; path: string; message_key: string; severity: string }[];
  formulaTest: UnknownRecord | null;
  modal: ModalState;
  dirty: boolean;
  saving: boolean;
  loading: boolean;
  undo: string[];
  redo: string[];
  draggedSection: string | null;
  draggedComponent: string | null;
  reportFilter: "all" | "mine";
};

const TEXT: Record<string, readonly [string, string, string, string]> = {
  title: ["Form Builder", "سازندهٔ فرم", "Formular-Designer", "表单构建器"],
  subtitle: ["Organization and project form libraries with versioned publishing", "کتابخانهٔ فرم سازمانی و پروژه با انتشار نسخه‌دار", "Organisations- und Projektformularbibliothek mit versionierter Veröffentlichung", "组织与项目表单库，支持版本化发布"],
  close: ["Close", "بستن", "Schließen", "关闭"],
  library: ["Library", "کتابخانه", "Bibliothek", "表单库"],
  designer: ["Designer", "طراح", "Designer", "设计器"],
  reports: ["Reports & approvals", "گزارش‌ها و تأییدها", "Berichte & Freigaben", "报表与审批"],
  print: ["Print & export", "چاپ و خروجی", "Druck & Export", "打印与导出"],
  organization: ["Organization library", "کتابخانهٔ سازمان", "Organisationsbibliothek", "组织库"],
  project: ["Project library", "کتابخانهٔ پروژه", "Projektbibliothek", "项目库"],
  newTemplate: ["New template", "فرم جدید", "Neue Vorlage", "新建模板"],
  aiDraft: ["AI draft", "پیش‌نویس هوش مصنوعی", "KI-Entwurf", "AI 草稿"],
  search: ["Search templates", "جستجوی فرم‌ها", "Vorlagen suchen", "搜索模板"],
  open: ["Open", "بازکردن", "Öffnen", "打开"],
  copy: ["Copy to project", "کپی به پروژه", "In Projekt kopieren", "复制到项目"],
  promote: ["Promote to organization", "ارتقا به سازمان", "In Organisation übernehmen", "提升至组织"],
  deprecate: ["Deprecate", "بازنشسته کردن", "Zurückziehen", "弃用"],
  publish: ["Publish version", "انتشار نسخه", "Version veröffentlichen", "发布版本"],
  save: ["Save draft", "ذخیرهٔ پیش‌نویس", "Entwurf speichern", "保存草稿"],
  validate: ["Validate", "اعتبارسنجی", "Prüfen", "校验"],
  saving: ["Saving…", "در حال ذخیره…", "Speichern…", "正在保存…"],
  saved: ["Draft saved", "پیش‌نویس ذخیره شد", "Entwurf gespeichert", "草稿已保存"],
  unsaved: ["Unsaved changes", "تغییرات ذخیره‌نشده", "Nicht gespeicherte Änderungen", "未保存的更改"],
  revision: ["Revision", "نسخهٔ رکورد", "Revision", "修订"],
  version: ["Version", "نسخه", "Version", "版本"],
  status: ["Status", "وضعیت", "Status", "状态"],
  draft: ["Draft", "پیش‌نویس", "Entwurf", "草稿"],
  published: ["Published", "منتشرشده", "Veröffentlicht", "已发布"],
  deprecated: ["Deprecated", "بازنشسته", "Zurückgezogen", "已弃用"],
  fields: ["Fields", "فیلدها", "Felder", "字段"],
  tables: ["Tables", "جدول‌ها", "Tabellen", "表格"],
  formulas: ["Formulas", "فرمول‌ها", "Formeln", "公式"],
  charts: ["Charts", "نمودارها", "Diagramme", "图表"],
  sections: ["Sections", "بخش‌ها", "Abschnitte", "分区"],
  workflow: ["Workflow", "گردش‌کار", "Workflow", "工作流"],
  pageSetup: ["Page & print", "صفحه و چاپ", "Seite & Druck", "页面与打印"],
  versions: ["Version history", "تاریخچهٔ نسخه‌ها", "Versionsverlauf", "版本历史"],
  noTemplates: ["No templates in this library yet.", "هنوز فرمی در این کتابخانه نیست.", "Noch keine Vorlagen in dieser Bibliothek.", "此库中还没有模板。"],
  noReports: ["No reports have been recorded for this project yet.", "هنوز گزارشی برای این پروژه ثبت نشده است.", "Für dieses Projekt wurden noch keine Berichte erfasst.", "此项目尚无报表。"],
  create: ["Create", "ساخت", "Erstellen", "创建"],
  cancel: ["Cancel", "انصراف", "Abbrechen", "取消"],
  confirm: ["Confirm", "تأیید", "Bestätigen", "确认"],
  id: ["Template ID", "شناسهٔ فرم", "Vorlagen-ID", "模板 ID"],
  titleField: ["Title", "عنوان", "Titel", "标题"],
  category: ["Category", "دسته", "Kategorie", "类别"],
  tags: ["Tags", "برچسب‌ها", "Schlagwörter", "标签"],
  defaultLocale: ["Default locale", "زبان پیش‌فرض", "Standardsprache", "默认语言"],
  addField: ["Add field", "افزودن فیلد", "Feld hinzufügen", "添加字段"],
  addTable: ["Add table", "افزودن جدول", "Tabelle hinzufügen", "添加表格"],
  addFormula: ["Add formula", "افزودن فرمول", "Formel hinzufügen", "添加公式"],
  addChart: ["Add chart", "افزودن نمودار", "Diagramm hinzufügen", "添加图表"],
  addSection: ["Add section", "افزودن بخش", "Abschnitt hinzufügen", "添加分区"],
  properties: ["Properties", "ویژگی‌ها", "Eigenschaften", "属性"],
  type: ["Type", "نوع", "Typ", "类型"],
  required: ["Required", "الزامی", "Erforderlich", "必填"],
  unit: ["Unit", "واحد", "Einheit", "单位"],
  precision: ["Precision", "دقت", "Genauigkeit", "精度"],
  options: ["Options (comma separated)", "گزینه‌ها (با کاما)", "Optionen (kommagetrennt)", "选项（逗号分隔）"],
  min: ["Minimum", "حداقل", "Minimum", "最小值"],
  max: ["Maximum", "حداکثر", "Maximum", "最大值"],
  expression: ["Expression", "عبارت", "Ausdruck", "表达式"],
  resultType: ["Result type", "نوع نتیجه", "Ergebnistyp", "结果类型"],
  test: ["Test through Formula Core", "آزمایش با هستهٔ فرمول", "Mit Formelkern testen", "通过公式核心测试"],
  testResult: ["Formula result", "نتیجهٔ فرمول", "Formelergebnis", "公式结果"],
  samples: ["Sample values (field=value, comma separated)", "مقادیر نمونه (فیلد=مقدار، با کاما)", "Beispielwerte (feld=wert, kommagetrennt)", "示例值（字段=值，逗号分隔）"],
  chartType: ["Chart type", "نوع نمودار", "Diagrammtyp", "图表类型"],
  source: ["Source", "منبع", "Quelle", "数据源"],
  series: ["Series", "سری‌ها", "Datenreihen", "数据系列"],
  legend: ["Show legend", "نمایش راهنما", "Legende anzeigen", "显示图例"],
  approvalMode: ["Approval mode", "حالت تأیید", "Freigabemodus", "审批模式"],
  reviewers: ["Reviewer roles", "نقش‌های بازبین", "Prüferrollen", "审核角色"],
  approvers: ["Approver roles", "نقش‌های تأییدکننده", "Freigeberrollen", "批准角色"],
  allowSelf: ["Allow self-approval", "اجازهٔ تأیید توسط خود", "Selbstfreigabe erlauben", "允许自我审批"],
  paper: ["Paper", "کاغذ", "Papier", "纸张"],
  orientation: ["Orientation", "جهت", "Ausrichtung", "方向"],
  portrait: ["Portrait", "عمودی", "Hochformat", "纵向"],
  landscape: ["Landscape", "افقی", "Querformat", "横向"],
  margins: ["Margins (mm)", "حاشیه‌ها (میلی‌متر)", "Ränder (mm)", "页边距（毫米）"],
  scale: ["Scale %", "مقیاس ٪", "Skalierung %", "缩放 %"],
  customWidth: ["Custom width (mm)", "عرض سفارشی (میلی‌متر)", "Eigene Breite (mm)", "自定义宽度（毫米）"],
  customHeight: ["Custom height (mm)", "ارتفاع سفارشی (میلی‌متر)", "Eigene Höhe (mm)", "自定义高度（毫米）"],
  duplicate: ["Duplicate", "تکرار", "Duplizieren", "复制"],
  delete: ["Delete", "حذف", "Löschen", "删除"],
  moveUp: ["Move up", "بالا", "Nach oben", "上移"],
  moveDown: ["Move down", "پایین", "Nach unten", "下移"],
  addComponent: ["Add to section", "افزودن به بخش", "Zum Abschnitt", "添加到分区"],
  unplaced: ["Fields not placed in a section", "فیلدهای خارج از بخش", "Nicht platzierte Felder", "未放入分区的字段"],
  assignee: ["Assignee", "مسئول تکمیل", "Zugewiesen an", "负责人"],
  assignTo: ["Assign to", "واگذاری به", "Zuweisen an", "分配给"],
  createReport: ["New report", "گزارش جدید", "Neuer Bericht", "新建报表"],
  reportTitle: ["Report title", "عنوان گزارش", "Berichtstitel", "报表标题"],
  reportDate: ["Report date", "تاریخ گزارش", "Berichtsdatum", "报表日期"],
  periodStart: ["Period start", "شروع دوره", "Zeitraumbeginn", "周期开始"],
  periodEnd: ["Period end", "پایان دوره", "Zeitraumende", "周期结束"],
  submit: ["Submit", "ارسال", "Einreichen", "提交"],
  saveDraft: ["Save report", "ذخیرهٔ گزارش", "Bericht speichern", "保存报表"],
  evaluate: ["Evaluate", "محاسبه", "Berechnen", "计算"],
  calculated: ["Calculated values", "مقادیر محاسبه‌شده", "Berechnete Werte", "计算值"],
  approvalTrail: ["Approval trail", "روند تأیید", "Freigabeverlauf", "审批记录"],
  revisions: ["Revisions", "نسخه‌های ثبت", "Revisionen", "修订记录"],
  approve: ["Approve", "تأیید", "Freigeben", "批准"],
  reject: ["Reject", "رد", "Ablehnen", "驳回"],
  return: ["Return", "بازگشت", "Zurückweisen", "退回"],
  startReview: ["Start review", "شروع بازبینی", "Prüfung starten", "开始审核"],
  issue: ["Issue", "صدور", "Ausgeben", "签发"],
  archive: ["Archive", "بایگانی", "Archivieren", "归档"],
  printPdf: ["Print / Save as PDF", "چاپ / ذخیرهٔ PDF", "Drucken / Als PDF", "打印/另存为 PDF"],
  exportExcel: ["Export Excel", "خروجی اکسل", "Excel exportieren", "导出 Excel"],
  printPreview: ["Print preview", "پیش‌نمایش چاپ", "Druckvorschau", "打印预览"],
  loading: ["Loading…", "در حال بارگذاری…", "Laden…", "加载中…"],
  failed: ["The operation failed.", "عملیات ناموفق بود.", "Der Vorgang ist fehlgeschlagen.", "操作失败。"],
  conflict: ["Another session changed this item. Reload the latest revision.", "نشست دیگری این مورد را تغییر داد. آخرین نسخه را بارگذاری کنید.", "Eine andere Sitzung hat dieses Element geändert. Laden Sie die neueste Revision.", "另一会话更改了此项。请重新加载最新修订。"],
  reloadLatest: ["Reload latest", "بارگذاری آخرین", "Neueste laden", "重新加载最新"],
  validationOk: ["Template is valid.", "فرم معتبر است.", "Die Vorlage ist gültig.", "模板有效。"],
  validationIssues: ["Validation issues", "مسائل اعتبارسنجی", "Validierungsprobleme", "校验问题"],
  formulaOk: ["Formula evaluated by the shared core.", "فرمول با هستهٔ مشترک محاسبه شد.", "Formel durch den gemeinsamen Kern berechnet.", "公式已由共享核心计算。"],
  formulaFailed: ["Formula could not be evaluated.", "فرمول قابل محاسبه نبود.", "Formel konnte nicht berechnet werden.", "公式无法计算。"],
  single: ["Single approver", "تأییدکنندهٔ واحد", "Einzelne Freigabe", "单一审批"],
  sequential: ["Sequential", "ترتیبی", "Sequenziell", "顺序审批"],
  parallel: ["Parallel", "موازی", "Parallel", "并行审批"],
  noPermission: ["You do not have permission for this action.", "برای این عمل مجوز ندارید.", "Sie haben keine Berechtigung für diese Aktion.", "您无权执行此操作。"],
  chooseTemplate: ["Choose a published template.", "یک فرم منتشرشده انتخاب کنید.", "Wählen Sie eine veröffentlichte Vorlage.", "请选择一个已发布模板。"],
  restore: ["Use as new draft", "استفاده به‌عنوان پیش‌نویس جدید", "Als neuen Entwurf verwenden", "用作新草稿"],
  compare: ["Compare", "مقایسه", "Vergleichen", "比较"],
  from: ["From", "از", "Von", "从"],
  to: ["To", "تا", "Bis", "至"],
  changed: ["Changed", "تغییر یافته", "Geändert", "已更改"],
  added: ["Added", "افزوده‌شده", "Hinzugefügt", "已添加"],
  removed: ["Removed", "حذف‌شده", "Entfernt", "已移除"],
  binding: ["Project data binding", "اتصال به دادهٔ پروژه", "Projektdatenbindung", "项目数据绑定"],
  resolveBindings: ["Resolve project values", "خواندن مقادیر پروژه", "Projektwerte lesen", "读取项目值"],
  provenance: ["Provenance", "منشأ داده", "Herkunft", "数据来源"],
  missingValue: ["no value recorded", "مقداری ثبت نشده", "kein Wert erfasst", "无记录值"],
  changeReason: ["Change reason", "علت تغییر", "Änderungsgrund", "变更原因"],
  reason: ["Reason", "دلیل", "Grund", "原因"],
  apply: ["Apply", "اعمال", "Übernehmen", "应用"],
  filterAll: ["All reports", "همهٔ گزارش‌ها", "Alle Berichte", "所有报表"],
  filterMine: ["Assigned to me", "واگذارشده به من", "Mir zugewiesen", "分配给我"],
  approvalStep: ["Approval step", "مرحلهٔ تأیید", "Freigabeschritt", "审批步骤"],
  role: ["Role", "نقش", "Rolle", "角色"],
  addRow: ["Add row", "افزودن ردیف", "Zeile hinzufügen", "添加行"],
  removeRow: ["Remove row", "حذف ردیف", "Zeile entfernen", "删除行"],
  noRows: ["No rows recorded", "ردیفی ثبت نشده", "Keine Zeilen erfasst", "无记录行"],
  formBuilder: ["Form Builder", "سازندهٔ فرم", "Formular-Designer", "表单构建器"],
  formsWorkflows: ["Forms & Workflows", "فرم‌ها و گردش‌کارها", "Formulare & Workflows", "表单与工作流"],
  openBuilder: ["Open Form Builder", "بازکردن سازندهٔ فرم", "Formular-Designer öffnen", "打开表单构建器"],
  moduleHint: ["Create organization templates, version them per project, collect reports and approve them with real project data.", "فرم‌های سازمانی بسازید، برای هر پروژه نسخه‌بندی کنید، گزارش جمع کنید و با دادهٔ واقعی پروژه تأیید کنید.", "Organisationsvorlagen erstellen, pro Projekt versionieren, Berichte erfassen und mit echten Projektdaten freigeben.", "创建组织模板、按项目版本化、收集报表并使用真实项目数据审批。"],
};

function localeKey(locale: string): Locale {
  const base = locale.split("-")[0].toLowerCase();
  return base === "fa" || base === "de" || base === "zh" ? base : "en";
}

function tr(locale: string, key: keyof typeof TEXT): string {
  const entry = TEXT[key];
  if (!entry) return String(key);
  const index = { en: 0, fa: 1, de: 2, zh: 3 }[localeKey(locale)];
  return entry[index];
}

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function textOf(label: unknown, locale: string): string {
  if (typeof label === "string") return label;
  if (label && typeof label === "object" && !Array.isArray(label)) {
    const record = label as Record<string, unknown>;
    for (const key of [localeKey(locale), locale, "en", "fa", "de", "zh"]) {
      const value = record[key];
      if (typeof value === "string" && value.trim()) return value;
    }
  }
  return "";
}

function setText(label: unknown, locale: string, value: string): UnknownRecord {
  const base: UnknownRecord =
    label && typeof label === "object" && !Array.isArray(label)
      ? { ...(label as UnknownRecord) }
      : { en: typeof label === "string" ? label : "" };
  base[localeKey(locale)] = value;
  return base;
}

function deepClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function byId<T extends HTMLElement = HTMLElement>(root: ParentNode, selector: string): T | null {
  return root.querySelector<T>(selector);
}

function uid(prefix: string): string {
  const raw =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 10)
      : Math.random().toString(36).slice(2, 12);
  return `${prefix}_${raw}`;
}

class FormUiError extends Error {
  constructor(public readonly code: string, public readonly status: number) {
    super(code);
  }
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(new URL(path, window.location.origin), {
    credentials: "same-origin",
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
  const text = await response.text();
  let payload: any = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new FormUiError(String(payload?.code || `HTTP_${response.status}`), response.status);
  }
  return payload as T;
}

function formatDate(value: string | null | undefined, calendarMode: "gregorian" | "jalali"): string {
  const text = String(value || "");
  if (!text) return "";
  if (calendarMode !== "jalali") return text;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
  if (!match) return text;
  try {
    return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]))));
  } catch {
    return text;
  }
}

const STATUS_LABEL: Record<string, readonly [string, string, string, string]> = {
  draft: ["Draft", "پیش‌نویس", "Entwurf", "草稿"],
  published: ["Published", "منتشرشده", "Veröffentlicht", "已发布"],
  deprecated: ["Deprecated", "بازنشسته", "Zurückgezogen", "已弃用"],
  submitted: ["Submitted", "ارسال‌شده", "Eingereicht", "已提交"],
  under_review: ["Under review", "در بازبینی", "In Prüfung", "审核中"],
  returned: ["Returned", "بازگشتی", "Zurückgewiesen", "已退回"],
  approved: ["Approved", "تأییدشده", "Freigegeben", "已批准"],
  rejected: ["Rejected", "رد‌شده", "Abgelehnt", "已驳回"],
  issued: ["Issued", "صادرشده", "Ausgegeben", "已签发"],
  archived: ["Archived", "بایگانی‌شده", "Archiviert", "已归档"],
};

function statusText(locale: string, status: string): string {
  const entry = STATUS_LABEL[status];
  if (!entry) return status;
  return entry[{ en: 0, fa: 1, de: 2, zh: 3 }[localeKey(locale)]];
}

function defaultTemplate(templateId: string, title: string): UnknownRecord {
  return {
    contract_version: "cubi-form-template.v1",
    template_id: templateId,
    title: { en: title },
    category: "daily",
    tags: [],
    default_locale: "en",
    header: {
      title: { en: title },
      show_project: true,
      show_report_date: true,
      party_slots: [],
    },
    footer: {
      note: { en: "Generated from the CUBI Form Builder" },
      show_page_numbers: true,
      approval_block: true,
    },
    page: {
      paper: "A4",
      orientation: "portrait",
      margins: { top: 12, bottom: 12, left: 12, right: 12 },
      scale: 100,
    },
    fields: [],
    tables: [],
    formulas: [],
    charts: [],
    workflow: {
      reviewers: ["planner"],
      approvers: ["project_admin"],
      approval_mode: "single",
      allow_self_approval: false,
      require_reason_on_return: true,
      require_reason_on_reject: true,
      states: ["draft", "submitted", "under_review", "returned", "approved", "rejected", "issued", "archived"],
    },
    sections: [
      {
        section_id: "main",
        title: { en: "Main" },
        columns: 2,
        components: [],
      },
    ],
  };
}

function defaultField(type: string, locale: string): UnknownRecord {
  const id = uid(type === "formula" ? "calc" : type);
  const field: UnknownRecord = {
    field_id: id,
    type,
    label: { [localeKey(locale)]: id },
    required: false,
  };
  if (type === "select") {
    field.options = [{ option_id: "option_1", label: { en: "Option 1" } }];
  }
  if (type === "quantity") field.unit = "m3";
  if (type === "duration") field.unit = "day";
  if (type === "currency") field.currency = "USD";
  if (type === "number" || type === "integer" || type === "quantity") field.precision = type === "integer" ? 0 : 2;
  if (type === "formula") {
    field.formula_id = id;
    field.result_type = "number";
    field.precision = 2;
  }
  if (type === "engine") {
    field.binding = { source: "project", field: "name" };
    field.result_type = "text";
  }
  return field;
}

function rawFieldValue(field: UnknownRecord, envelope: unknown): string {
  if (!envelope || typeof envelope !== "object") return "";
  const record = envelope as UnknownRecord;
  const type = String(field.type || "text");
  if (type === "file") return String(record.asset_id || "");
  if (type === "multiselect") return Array.isArray(record.values) ? record.values.join(",") : "";
  if (type === "percent") {
    const number = Number(record.value);
    return Number.isFinite(number) ? String(Number((number * 100).toFixed(6))) : "";
  }
  if (typeof record.value === "boolean") return record.value ? "true" : "false";
  if (type === "date" || type === "datetime") return String(record.value || "").slice(0, type === "date" ? 10 : 19);
  return record.value == null ? "" : String(record.value);
}

function inputType(field: UnknownRecord): string {
  switch (String(field.type)) {
    case "integer":
    case "number":
    case "quantity":
    case "currency":
      return "number";
    case "percent":
      return "number";
    case "date":
      return "date";
    case "datetime":
      return "datetime-local";
    default:
      return "text";
  }
}

function tableRows(tables: UnknownRecord, tableId: string): UnknownRecord[] {
  const value = tables[tableId];
  return Array.isArray(value) ? value : [];
}

function rowRaw(row: UnknownRecord, columnId: string, column: UnknownRecord): string {
  const envelope = (row.values || {})[columnId];
  return rawFieldValue({ ...column, field_id: columnId }, envelope);
}

function bindFieldValue(field: UnknownRecord, raw: string): unknown {
  const type = String(field.type);
  if (raw === "" || raw == null) return null;
  if (type === "integer") {
    const number = Number(raw);
    return Number.isFinite(number) ? Math.trunc(number) : null;
  }
  if (["number", "quantity", "currency"].includes(type)) {
    return Number.isFinite(Number(raw)) ? raw : null;
  }
  if (type === "percent") {
    const number = Number(raw);
    return Number.isFinite(number) ? String(number / 100) : null;
  }
  if (type === "boolean") return raw === "true";
  if (type === "multiselect") return { type, values: raw.split(",").map((part) => part.trim()).filter(Boolean) };
  if (type === "file") return { type, asset_id: raw };
  return raw;
}

function bindingValue(field: UnknownRecord, resolved: UnknownRecord | null): string {
  if (!resolved || resolved.value == null) return "";
  const envelope = resolved.value;
  if (envelope && typeof envelope === "object") {
    const value = (envelope as UnknownRecord).value;
    if (value == null) return "";
    if (field.type === "percent") {
      const number = Number(value);
      return Number.isFinite(number) ? `${Number((number * 100).toFixed(2))}%` : String(value);
    }
    return String(value);
  }
  return String(envelope);
}

function chartColors(): string[] {
  return ["#1f5f8b", "#c2410c", "#0f766e", "#7c3aed", "#b45309", "#be123c"];
}

function roundRectPath(x: number, y: number, width: number, height: number): string {
  return `M${x},${y} h${width} v${height} h${-width} Z`;
}

function renderChartSvg(chart: UnknownRecord, tables: UnknownRecord, width = 520, height = 220): string {
  const type = String(chart.chart_type || "column");
  const source = chart.source || {};
  const tableId = String(source.table_id || "");
  const table = tableId ? tableRows(tables, tableId) : [];
  const series = Array.isArray(chart.series) ? chart.series : [];
  const categoryColumn = String(source.category_column || "");
  if (!table.length || !series.length) {
    return `<div class="cp-fb-chart-empty">${escapeHtml("—")}</div>`;
  }
  const categories = table.map((row, index) => {
    const envelope = (row.values || {})[categoryColumn];
    const label = envelope && typeof envelope === "object" ? (envelope as UnknownRecord).value : "";
    return String(label || `#${index + 1}`);
  });
  const data = series.map((item: UnknownRecord, seriesIndex: number) => ({
    label: String(item.column_id || `series ${seriesIndex + 1}`),
    color: chartColors()[seriesIndex % chartColors().length],
    values: table.map((row) => {
      const envelope = (row.values || {})[String(item.column_id || "")];
      const number = envelope && typeof envelope === "object" ? Number((envelope as UnknownRecord).value) : NaN;
      return Number.isFinite(number) ? number : 0;
    }),
  }));
  const allValues = data.flatMap((item) => item.values);
  const max = Math.max(1, ...allValues);
  const padding = { left: 46, right: 16, top: 16, bottom: 34 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const parts: string[] = [];
  if (type === "pie" || type === "donut") {
    const seriesData = data[0]?.values || [];
    const total = seriesData.reduce((sum, value) => sum + Math.abs(value), 0) || 1;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(width, height) / 2 - 12;
    let angle = -Math.PI / 2;
    seriesData.forEach((value, index) => {
      const sweep = (Math.abs(value) / total) * Math.PI * 2;
      const x1 = cx + radius * Math.cos(angle);
      const y1 = cy + radius * Math.sin(angle);
      const x2 = cx + radius * Math.cos(angle + sweep);
      const y2 = cy + radius * Math.sin(angle + sweep);
      const large = sweep > Math.PI ? 1 : 0;
      const path = `M${cx},${cy} L${x1},${y1} A${radius},${radius} 0 ${large} 1 ${x2},${y2} Z`;
      parts.push(`<path d="${path}" fill="${chartColors()[index % chartColors().length]}"><title>${escapeHtml(categories[index])}: ${value}</title></path>`);
      if (type === "donut") {
        // The donut hole is drawn after all slices.
      }
      angle += sweep;
    });
    if (type === "donut") {
      parts.push(`<circle cx="${cx}" cy="${cy}" r="${radius * 0.55}" fill="var(--cp-surface, #fff)"/>`);
    }
    return `<svg class="cp-fb-chart-svg" viewBox="0 0 ${width} ${height}" role="img">${parts.join("")}</svg>`;
  }
  if (type === "line") {
    data.forEach((item) => {
      const points = item.values.map((value, index) => {
        const x = padding.left + (plotWidth * (index + 0.5)) / Math.max(1, item.values.length);
        const y = padding.top + plotHeight - (value / max) * plotHeight;
        return `${x},${y}`;
      });
      parts.push(`<polyline points="${points.join(" ")}" fill="none" stroke="${item.color}" stroke-width="2.5"/>`);
      item.values.forEach((value, index) => {
        const x = padding.left + (plotWidth * (index + 0.5)) / Math.max(1, item.values.length);
        const y = padding.top + plotHeight - (value / max) * plotHeight;
        parts.push(`<circle cx="${x}" cy="${y}" r="3" fill="${item.color}"><title>${escapeHtml(item.label)}: ${value}</title></circle>`);
      });
    });
  } else {
    const groupWidth = plotWidth / Math.max(1, data[0]?.values.length || 1);
    const barWidth = (groupWidth * 0.7) / Math.max(1, data.length);
    data.forEach((item, seriesIndex) => {
      item.values.forEach((value, index) => {
        const x = padding.left + groupWidth * index + groupWidth * 0.15 + seriesIndex * barWidth;
        const barHeight = (value / max) * plotHeight;
        const y = padding.top + plotHeight - barHeight;
        parts.push(`<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${item.color}"><title>${escapeHtml(item.label)} / ${escapeHtml(categories[index])}: ${value}</title></rect>`);
      });
    });
  }
  parts.push(`<line x1="${padding.left}" y1="${padding.top + plotHeight}" x2="${width - padding.right}" y2="${padding.top + plotHeight}" stroke="currentColor" opacity=".25"/>`);
  categories.forEach((label, index) => {
    const x = padding.left + (plotWidth * (index + 0.5)) / Math.max(1, categories.length);
    parts.push(`<text x="${x}" y="${height - 12}" text-anchor="middle" font-size="10">${escapeHtml(label)}</text>`);
  });
  return `<svg class="cp-fb-chart-svg" viewBox="0 0 ${width} ${height}" role="img">${parts.join("")}</svg>`;
}

export function openFormBuilder(options: FormBuilderOptions): FormBuilderHandle {
  const { host, context, locale, calendarMode } = options;
  host.querySelector("[data-form-builder]")?.remove();
  const root = document.createElement("section");
  root.className = "cp-form-builder";
  root.dataset.formBuilder = "true";
  root.setAttribute("role", "dialog");
  root.setAttribute("aria-modal", "true");
  root.setAttribute("aria-label", tr(locale, "title"));
  host.append(root);

  const state: UiState = {
    tab: "library",
    designTab: "schema",
    designLibrary: "project",
    selectedTemplateId: null,
    template: null,
    orgTemplates: [],
    projectTemplates: [],
    submissions: [],
    submission: null,
    draftValues: {},
    draftTables: {},
    draftTitle: "",
    draftReportDate: "",
    draftAssignee: "",
    assignees: [],
    bindings: [],
    permissions: {},
    viewer: "",
    versions: [],
    diff: null,
    printHtml: "",
    selectedFieldId: null,
    selectedTableId: null,
    selectedFormulaId: null,
    selectedChartId: null,
    selectedSectionId: null,
    search: "",
    status: null,
    validationIssues: [],
    formulaTest: null,
    modal: null,
    dirty: false,
    saving: false,
    loading: false,
    undo: [],
    redo: [],
    draggedSection: null,
    draggedComponent: null,
    reportFilter: "all",
  };

  const base = `/api/projects/${encodeURIComponent(context.project_id)}/forms`;
  let evaluateTimer: ReturnType<typeof setTimeout> | null = null;
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  const setStatus = (message: string, kind: "info" | "ok" | "error" = "info"): void => {
    state.status = message ? { kind, message } : null;
    const status = byId(root, "[data-fb-status]");
    if (status) {
      status.dataset.kind = kind;
      status.textContent = message;
    }
  };

  const reportError = (error: unknown): void => {
    if (error instanceof FormUiError) {
      const message =
        error.status === 409
          ? tr(locale, "conflict")
          : error.code === "FORM_AUTHORIZATION_DENIED"
            ? tr(locale, "noPermission")
            : `${tr(locale, "failed")} (${error.code})`;
      setStatus(message, "error");
      if (error.status === 409) render();
      return;
    }
    setStatus(tr(locale, "failed"), "error");
  };

  const permission = (name: string): boolean => Boolean(state.permissions[name]);

  const refreshLibrary = async (): Promise<void> => {
    state.loading = true;
    render();
    try {
      const [overview, submissions, assignees] = await Promise.all([
        api<UnknownRecord>(`${base}/overview`),
        api<UnknownRecord>(`${base}/submissions?limit=200`),
        api<UnknownRecord>(`${base}/assignees`).catch(() => ({ assignees: [] })),
      ]);
      const libraries = (overview.libraries || {}) as UnknownRecord;
      state.orgTemplates = (libraries.organization?.templates || []) as TemplateSummary[];
      state.projectTemplates = (libraries.project?.templates || []) as TemplateSummary[];
      state.permissions = (overview.permissions || {}) as Record<string, boolean>;
      state.viewer = String((overview.viewer || {}).user_id || "");
      state.submissions = (submissions.submissions || []) as SubmissionSummary[];
      state.assignees = (assignees.assignees || []) as Assignee[];
      if (!state.draftAssignee) {
        state.draftAssignee = assignees.assignees?.[0]?.user_id || "";
      }
    } catch (error) {
      reportError(error);
    } finally {
      state.loading = false;
      render();
    }
  };

  const loadTemplate = async (library: Library, templateId: string): Promise<void> => {
    state.loading = true;
    state.designLibrary = library;
    state.selectedTemplateId = templateId;
    try {
      const detail = await api<TemplateDetail>(
        `${library === "organization" ? "/api/forms/organization" : base}/templates/${encodeURIComponent(templateId)}`,
      );
      state.template = detail;
      state.selectedFieldId = null;
      state.selectedTableId = detail.payload.tables?.[0]?.table_id || null;
      state.selectedFormulaId = detail.payload.formulas?.[0]?.formula_id || null;
      state.selectedChartId = detail.payload.charts?.[0]?.chart_id || null;
      state.selectedSectionId = detail.payload.sections?.[0]?.section_id || null;
      state.validationIssues = detail.issues || [];
      state.diff = null;
      state.formulaTest = null;
      state.undo = [];
      state.redo = [];
      state.dirty = false;
      state.tab = "design";
      state.designTab = "schema";
      state.versions = [];
      if (detail.published_version) {
        try {
          const versions = await api<UnknownRecord>(
            `${library === "organization" ? "/api/forms/organization" : base}/templates/${encodeURIComponent(templateId)}/versions`,
          );
          state.versions = versions.versions || [];
        } catch {
          state.versions = [];
        }
      }
      if (library === "project" && detail.published_version) {
        try {
          const bindings = await api<UnknownRecord>(`${base}/bindings`);
          state.bindings = (bindings.sources || []) as BindingSource[];
        } catch {
          state.bindings = [];
        }
      }
    } catch (error) {
      reportError(error);
    } finally {
      state.loading = false;
      render();
    }
  };

  const templatePath = (): string => {
    if (!state.template) return "";
    const prefix = state.template.library === "organization" ? "/api/forms/organization" : base;
    return `${prefix}/templates/${encodeURIComponent(state.template.template_id)}`;
  };

  const validateDraft = async (): Promise<void> => {
    if (!state.template) return;
    try {
      const result = await api<UnknownRecord>(`${templatePath()}/validate`, {
        method: "POST",
        body: JSON.stringify({ template: state.template.payload, for_publish: false }),
      });
      state.validationIssues = (result.issues || []) as UiState["validationIssues"];
      setStatus(result.valid ? tr(locale, "validationOk") : tr(locale, "validationIssues"), result.valid ? "ok" : "error");
    } catch (error) {
      reportError(error);
    }
    render();
  };

  /**
   * The in-flight template draft write. Publishing reads the server's draft,
   * so a publish must wait for (and flush) pending edits instead of snapshotting
   * a stale revision or publishing a payload the user has already changed.
   */
  let pendingTemplateSave: Promise<void> | null = null;

  const saveTemplate = (autosave = false): Promise<void> => {
    if (!state.template) return Promise.resolve();
    if (state.saving) return pendingTemplateSave ?? Promise.resolve();
    if (!autosave) {
      state.undo.push(JSON.stringify(state.template.payload));
      if (state.undo.length > 60) state.undo.shift();
      state.redo = [];
    }
    const task = (async () => {
      state.saving = true;
      setStatus(tr(locale, "saving"), "info");
      try {
        const saved = await api<TemplateDetail>(templatePath(), {
          method: "PUT",
          body: JSON.stringify({
            template: state.template!.payload,
            expected_revision: state.template!.record_revision,
            autosave,
          }),
        });
        state.template = { ...state.template!, ...saved, payload: state.template!.payload };
        state.validationIssues = saved.issues || [];
        state.dirty = false;
        // An autosave is still a save: leaving the status at "saving…" would
        // misreport a completed write. Only manual saves push an undo entry.
        setStatus(tr(locale, "saved"), "ok");
      } catch (error) {
        reportError(error);
      } finally {
        state.saving = false;
        pendingTemplateSave = null;
        render();
      }
    })();
    pendingTemplateSave = task;
    return task;
  };

  const scheduleAutosave = (): void => {
    state.dirty = true;
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (state.template && state.tab === "design" && !state.saving) void saveTemplate(true);
    }, 1200);
  };

  const publishTemplate = async (reason: string): Promise<void> => {
    if (!state.template) return;
    // Publish the exact draft the user is looking at: flush any queued edit or
    // in-flight write before the server takes its immutable snapshot.
    if (pendingTemplateSave) await pendingTemplateSave;
    if (state.dirty) {
      await saveTemplate(true);
      if (state.dirty) return;
    }
    try {
      const result = await api<TemplateDetail>(`${templatePath()}/publish`, {
        method: "POST",
        body: JSON.stringify({ expected_revision: state.template.record_revision, change_reason: reason }),
      });
      if (result.valid === false) {
        state.validationIssues = result.issues || [];
        setStatus(tr(locale, "validationIssues"), "error");
      } else {
        state.template = result;
        state.dirty = false;
        setStatus(`${tr(locale, "published")} v${result.published_version}`, "ok");
        await refreshLibrary();
        await loadTemplate(result.library as Library, result.template_id);
      }
    } catch (error) {
      reportError(error);
    }
    state.modal = null;
    render();
  };

  const copyTemplate = async (library: Library, templateId: string): Promise<void> => {
    try {
      const source = library === "organization" ? "/api/forms/organization" : base;
      const result = await api<TemplateDetail>(`${source}/templates/${encodeURIComponent(templateId)}/copy`, {
        method: "POST",
        body: JSON.stringify({ target_library: "project", target_project_id: context.project_id, publish: false }),
      });
      setStatus(`${tr(locale, "copy")}: ${result.template_id}`, "ok");
      await refreshLibrary();
      await loadTemplate("project", result.template_id);
    } catch (error) {
      reportError(error);
    }
  };

  const promoteTemplate = async (templateId: string): Promise<void> => {
    try {
      const result = await api<UnknownRecord>(
        `${base}/templates/${encodeURIComponent(templateId)}/promote`,
        { method: "POST", body: JSON.stringify({}) },
      );
      setStatus(`${tr(locale, "promote")}: ${result.template_id || templateId}`, "ok");
      await refreshLibrary();
    } catch (error) {
      reportError(error);
    }
  };

  const deprecateTemplate = async (): Promise<void> => {
    if (!state.template) return;
    if (!window.confirm(`${tr(locale, "deprecate")} ${state.template.template_id}?`)) return;
    try {
      await api(`${templatePath()}/deprecate`, {
        method: "POST",
        body: JSON.stringify({ expected_revision: state.template.record_revision }),
      });
      setStatus(tr(locale, "deprecated"), "ok");
      await refreshLibrary();
      await loadTemplate(state.template.library, state.template.template_id);
    } catch (error) {
      reportError(error);
    }
  };

  const createTemplate = async (form: HTMLFormElement): Promise<void> => {
    const data = new FormData(form);
    const library = (form.dataset.library || "project") as Library;
    const templateId = String(data.get("template_id") || "").trim();
    const title = String(data.get("title") || "").trim();
    const category = String(data.get("category") || "daily").trim();
    if (!templateId || !title) return;
    const payload = defaultTemplate(templateId, title);
    payload.category = category;
    payload.default_locale = localeKey(locale);
    payload.title = { [localeKey(locale)]: title, en: title };
    payload.header = { ...payload.header, title: payload.title };
    try {
      const created = await api<TemplateDetail>(
        `${library === "organization" ? "/api/forms/organization" : base}/templates`,
        { method: "POST", body: JSON.stringify({ template: payload, publish: false }) },
      );
      state.modal = null;
      await refreshLibrary();
      await loadTemplate(library, created.template_id);
    } catch (error) {
      reportError(error);
    }
  };

  const createAssistantDraft = async (): Promise<void> => {
    if (!state.template && state.selectedTemplateId) {
      // The assistant needs a project library scope; use the active designer.
    }
    const prompt = window.prompt(
      localeKey(locale) === "fa"
        ? "چه گزارشی می‌خواهید؟ (توضیح کوتاه)"
        : "What report do you need? (short description)",
      "",
    );
    if (!prompt) return;
    try {
      const draft = await api<UnknownRecord>(`${base}/assistant/draft`, {
        method: "POST",
        body: JSON.stringify({ prompt, locale: localeKey(locale) }),
      });
      const template = draft.template as UnknownRecord;
      if (!template) throw new FormUiError("ASSISTANT_DRAFT_EMPTY", 500);
      const created = await api<TemplateDetail>(`${base}/templates`, {
        method: "POST",
        body: JSON.stringify({ template, publish: false }),
      });
      state.modal = null;
      setStatus(
        localeKey(locale) === "fa"
          ? "پیش‌نویس محلی ساخته شد؛ انتشار یا تأیید خودکار انجام نشد."
          : "A local draft was created; nothing was published or approved automatically.",
        "ok",
      );
      await refreshLibrary();
      await loadTemplate("project", created.template_id);
    } catch (error) {
      reportError(error);
    }
  };

  const loadSubmission = async (submissionId: string): Promise<void> => {
    state.loading = true;
    render();
    try {
      const submission = await api<SubmissionDetail>(`${base}/submissions/${encodeURIComponent(submissionId)}`);
      state.submission = submission;
      state.draftValues = deepClone(submission.values || {});
      state.draftTables = deepClone(submission.tables || {});
      state.draftTitle = submission.title || "";
      state.draftReportDate = submission.report_date || "";
      state.draftAssignee = submission.assigned_to || "";
      state.printHtml = "";
      state.tab = "reports";
      state.selectedTemplateId = submission.template_id;
      const template = submission.template as UnknownRecord | undefined;
      if (template) {
        state.template = {
          ...(template as unknown as TemplateDetail),
          library: (submission as UnknownRecord).template_library || "project",
          payload: template,
        } as TemplateDetail;
      }
    } catch (error) {
      reportError(error);
    } finally {
      state.loading = false;
      render();
    }
  };

  const createReport = async (form: HTMLFormElement): Promise<void> => {
    const data = new FormData(form);
    const templateId = String(data.get("template_id") || "");
    const templateVersion = Number(data.get("template_version") || 0);
    const title = String(data.get("title") || "").trim();
    const reportDate = String(data.get("report_date") || "");
    const assignedTo = String(data.get("assigned_to") || "");
    if (!templateId) {
      setStatus(tr(locale, "chooseTemplate"), "error");
      return;
    }
    try {
      const created = await api<SubmissionDetail>(`${base}/submissions`, {
        method: "POST",
        body: JSON.stringify({
          template_id: templateId,
          template_version: templateVersion || undefined,
          library: "project",
          title: title || undefined,
          report_date: reportDate || undefined,
          assigned_to: assignedTo || undefined,
          values: {},
          tables: {},
        }),
      });
      state.modal = null;
      await refreshLibrary();
      await loadSubmission(created.submission_id);
    } catch (error) {
      reportError(error);
    }
  };

  const evaluateCurrent = async (): Promise<void> => {
    if (!state.submission) return;
    try {
      const result = await api<UnknownRecord>(
        `${base}/submissions/${encodeURIComponent(state.submission.submission_id)}/evaluate`,
        {
          method: "POST",
          body: JSON.stringify({
            values: state.draftValues,
            tables: state.draftTables,
            report_date: state.draftReportDate || undefined,
          }),
        },
      );
      state.submission = {
        ...state.submission,
        calculated: (result.calculated || {}) as UnknownRecord,
        bindings: (result.bindings || state.submission.bindings) as UnknownRecord,
      };
      const issues = (result.validation?.issues || []) as UiState["validationIssues"];
      state.validationIssues = issues;
      if (issues.some((issue) => issue.severity !== "warning")) {
        setStatus(tr(locale, "validationIssues"), "error");
      } else {
        setStatus(tr(locale, "calculated"), "ok");
      }
    } catch (error) {
      reportError(error);
    }
    render();
  };

  const scheduleEvaluate = (): void => {
    if (evaluateTimer) clearTimeout(evaluateTimer);
    evaluateTimer = setTimeout(() => void evaluateCurrent(), 700);
  };

  /**
   * The in-flight submission save, if any. A workflow transition must never
   * race an unsaved edit: the server applies the *persisted* values, so
   * submitting while a save is pending would either conflict or approve a
   * stale draft. ``transition`` waits for this promise first.
   */
  let pendingSave: Promise<void> | null = null;

  const saveSubmission = async (): Promise<void> => {
    if (!state.submission) return;
    if (pendingSave) return pendingSave;
    const task = (async () => {
      state.saving = true;
      try {
        const result = await api<SubmissionDetail>(
          `${base}/submissions/${encodeURIComponent(state.submission!.submission_id)}`,
          {
            method: "PUT",
            body: JSON.stringify({
              expected_revision: state.submission!.record_revision,
              values: state.draftValues,
              tables: state.draftTables,
              title: state.draftTitle,
              report_date: state.draftReportDate || undefined,
            }),
          },
        );
        state.submission = result;
        state.draftValues = deepClone(result.values || {});
        state.draftTables = deepClone(result.tables || {});
        state.validationIssues = (result.validation?.issues || result.issues || []) as UiState["validationIssues"];
        setStatus(tr(locale, "saved"), "ok");
      } catch (error) {
        reportError(error);
      } finally {
        state.saving = false;
        pendingSave = null;
        render();
      }
    })();
    pendingSave = task;
    return task;
  };

  const transition = async (action: string, reason = ""): Promise<void> => {
    if (!state.submission) return;
    // Flush a pending edit so the transition validates exactly the values the
    // user sees, and so expected_revision matches the persisted record.
    if (pendingSave) await pendingSave;
    try {
      const result = await api<SubmissionDetail>(
        `${base}/submissions/${encodeURIComponent(state.submission.submission_id)}/transition`,
        {
          method: "POST",
          body: JSON.stringify({
            action,
            expected_revision: state.submission.record_revision,
            reason,
          }),
        },
      );
      if ((result as UnknownRecord).valid === false) {
        state.validationIssues = ((result as UnknownRecord).issues || []) as UiState["validationIssues"];
        setStatus(tr(locale, "validationIssues"), "error");
        render();
        return;
      }
      state.submission = result;
      state.modal = null;
      setStatus(`${statusText(locale, result.status)}`, "ok");
      await refreshLibrary();
    } catch (error) {
      reportError(error);
    }
    render();
  };

  const loadPrint = async (): Promise<void> => {
    if (!state.submission) return;
    try {
      const response = await fetch(
        new URL(
          `${base}/submissions/${encodeURIComponent(state.submission.submission_id)}/print?locale=${encodeURIComponent(localeKey(locale))}`,
          window.location.origin,
        ),
        { credentials: "same-origin" },
      );
      if (!response.ok) throw new FormUiError(`HTTP_${response.status}`, response.status);
      state.printHtml = await response.text();
      state.tab = "print";
    } catch (error) {
      reportError(error);
    }
    render();
  };

  const testFormula = async (): Promise<void> => {
    if (!state.template) return;
    const formula = (state.template.payload.formulas || []).find(
      (item: UnknownRecord) => item.formula_id === state.selectedFormulaId,
    ) as UnknownRecord | undefined;
    if (!formula) return;
    const sampleInput = byId<HTMLInputElement>(root, "[data-fb-formula-samples]");
    const samples: UnknownRecord = {};
    for (const pair of (sampleInput?.value || "").split(",")) {
      const [key, value] = pair.split("=");
      if (key && value != null && key.trim()) samples[key.trim()] = value.trim();
    }
    try {
      const result = await api<UnknownRecord>(`${templatePath()}/formula-test`, {
        method: "POST",
        body: JSON.stringify({
          formula_id: formula.formula_id,
          expression: formula.expression || "",
          result_type: formula.result_type || "number",
          sample_values: samples,
        }),
      });
      state.formulaTest = result;
      setStatus(result.valid ? tr(locale, "formulaOk") : tr(locale, "formulaFailed"), result.valid ? "ok" : "error");
    } catch (error) {
      reportError(error);
    }
    render();
  };

  const exportWorkbook = async (): Promise<void> => {
    if (!state.submission) return;
    try {
      const response = await fetch(
        new URL(
          `${base}/submissions/${encodeURIComponent(state.submission.submission_id)}/export.xlsx?locale=${encodeURIComponent(localeKey(locale))}`,
          window.location.origin,
        ),
        { credentials: "same-origin" },
      );
      if (!response.ok) throw new FormUiError(`HTTP_${response.status}`, response.status);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${state.submission.submission_id}.xlsx`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      setStatus(tr(locale, "exportExcel"), "ok");
    } catch (error) {
      reportError(error);
    }
  };

  const renderLibrary = (): string => {
    const org = state.orgTemplates || [];
    const projectTemplates = state.projectTemplates || [];
    const search = state.search.trim().toLowerCase();
    const filter = (items: TemplateSummary[]): TemplateSummary[] =>
      search
        ? items.filter((item) =>
            [item.template_id, item.title, item.category, ...(item.tags || [])]
              .join(" ")
              .toLowerCase()
              .includes(search),
          )
        : items;
    const card = (item: TemplateSummary): string => `
      <article class="cp-fb-card" data-fb-open="${escapeHtml(item.template_id)}" data-fb-library="${item.library}" tabindex="0">
        <header>
          <div>
            <h4>${escapeHtml(item.title_text || item.title || item.template_id)}</h4>
            <code>${escapeHtml(item.template_id)}</code>
          </div>
          <span class="cp-fb-badge is-${escapeHtml(item.status)}">${escapeHtml(statusText(locale, item.status))}${item.published_version ? ` · v${item.published_version}` : ""}</span>
        </header>
        <p>${escapeHtml(item.category || "—")} · ${escapeHtml(item.updated_by || "")} · ${escapeHtml(item.updated_at ? formatDate(item.updated_at, calendarMode).slice(0, 10) : "")}</p>
        <div class="cp-fb-card-counts">
          <span>${item.field_count} ${escapeHtml(tr(locale, "fields"))}</span>
          <span>${item.table_count} ${escapeHtml(tr(locale, "tables"))}</span>
          <span>${item.formula_count} ${escapeHtml(tr(locale, "formulas"))}</span>
          <span>${item.chart_count} ${escapeHtml(tr(locale, "charts"))}</span>
        </div>
        ${item.draft_dirty ? `<span class="cp-fb-dirty">${escapeHtml(tr(locale, "unsaved"))}</span>` : ""}
        <div class="cp-fb-card-actions">
          ${item.library === "organization" && permission("form.create")
            ? `<button type="button" data-fb-copy="${escapeHtml(item.template_id)}" data-fb-library="organization">${escapeHtml(tr(locale, "copy"))}</button>`
            : ""}
          ${item.library === "project" && permission("form.library.admin")
            ? `<button type="button" data-fb-promote="${escapeHtml(item.template_id)}">${escapeHtml(tr(locale, "promote"))}</button>`
            : ""}
        </div>
      </article>`;
    return `
      <div class="cp-fb-toolbar">
        <label class="cp-fb-search"><span class="sr-only">${escapeHtml(tr(locale, "search"))}</span>
          <input type="search" data-fb-search value="${escapeHtml(state.search)}" placeholder="${escapeHtml(tr(locale, "search"))}" />
        </label>
        <div class="cp-fb-toolbar-actions">
          <button type="button" class="cp-fb-primary" data-fb-new="project" ${permission("form.create") && permission("form.design") ? "" : "disabled"}>${escapeHtml(tr(locale, "newTemplate"))}</button>
          <button type="button" data-fb-assistant ${permission("form.create") && permission("form.design") ? "" : "disabled"}>${escapeHtml(tr(locale, "aiDraft"))}</button>
          ${permission("form.library.admin") ? `<button type="button" data-fb-new="organization">${escapeHtml(tr(locale, "newTemplate"))} · ${escapeHtml(tr(locale, "organization"))}</button>` : ""}
        </div>
      </div>
      <div class="cp-fb-library">
        <section>
          <header><h3>${escapeHtml(tr(locale, "organization"))}</h3><span>${org.length}</span></header>
          <div class="cp-fb-cards">${filter(org).map(card).join("") || `<p class="cp-fb-empty">${escapeHtml(tr(locale, "noTemplates"))}</p>`}</div>
        </section>
        <section>
          <header><h3>${escapeHtml(tr(locale, "project"))}</h3><span>${projectTemplates.length}</span></header>
          <div class="cp-fb-cards">${filter(projectTemplates).map(card).join("") || `<p class="cp-fb-empty">${escapeHtml(tr(locale, "noTemplates"))}</p>`}</div>
        </section>
      </div>`;
  };

  const templateOutline = (): string => {
    const payload = state.template?.payload || {};
    const sections = Array.isArray(payload.sections) ? payload.sections : [];
    const fieldById = new Map<string, UnknownRecord>(
      (payload.fields || []).map((field: UnknownRecord) => [String(field.field_id), field]),
    );
    return `
      <aside class="cp-fb-outline" data-fb-template="${escapeHtml(state.template?.template_id || "")}" data-fb-template-status="${escapeHtml(state.template?.status || "")}">
        <div class="cp-fb-outline-head">
          <strong>${escapeHtml(textOf(payload.title, locale) || state.template?.template_id || "")}</strong>
          <span class="cp-fb-badge is-${escapeHtml(state.template?.status || "draft")}">${escapeHtml(statusText(locale, state.template?.status || "draft"))}${state.template?.published_version ? ` · v${state.template.published_version}` : ""}</span>
        </div>
        <div class="cp-fb-outline-actions">
          <button type="button" data-fb-design-tab="schema">${escapeHtml(tr(locale, "fields"))}</button>
          <button type="button" data-fb-design-tab="tables">${escapeHtml(tr(locale, "tables"))}</button>
          <button type="button" data-fb-design-tab="formulas">${escapeHtml(tr(locale, "formulas"))}</button>
          <button type="button" data-fb-design-tab="charts">${escapeHtml(tr(locale, "charts"))}</button>
          <button type="button" data-fb-design-tab="workflow">${escapeHtml(tr(locale, "workflow"))}</button>
          <button type="button" data-fb-design-tab="page">${escapeHtml(tr(locale, "pageSetup"))}</button>
          <button type="button" data-fb-design-tab="versions">${escapeHtml(tr(locale, "versions"))}</button>
        </div>
        ${sections
          .map(
            (section: UnknownRecord) => `
            <div class="cp-fb-outline-section" draggable="true" data-fb-section-drag="${escapeHtml(section.section_id)}" data-fb-drop-section="${escapeHtml(section.section_id)}">
              <header>
                <span>${escapeHtml(textOf(section.title, locale) || section.section_id)}</span>
                <small>${(section.components || []).length}</small>
              </header>
              <ul>
                ${(section.components || [])
                  .map((component: UnknownRecord) => {
                    const field = component.type === "field" ? fieldById.get(String(component.field_id)) : null;
                    const label =
                      component.type === "field"
                        ? textOf(field?.label, locale) || component.field_id
                        : component.type === "table"
                          ? textOf((payload.tables || []).find((item: UnknownRecord) => item.table_id === component.table_id)?.label, locale) || component.table_id
                          : component.type === "chart"
                            ? textOf((payload.charts || []).find((item: UnknownRecord) => item.chart_id === component.chart_id)?.title, locale) || component.chart_id
                            : component.type;
                    return `<li draggable="true" data-fb-component-drag="${escapeHtml(component.component_id)}" data-fb-component-id="${escapeHtml(component.component_id)}" data-fb-section-id="${escapeHtml(section.section_id)}">
                      <span class="cp-fb-kind">${escapeHtml(component.type)}</span>
                      <span>${escapeHtml(label)}</span>
                    </li>`;
                  })
                  .join("")}
              </ul>
            </div>`,
          )
          .join("")}
        <button type="button" class="cp-fb-ghost" data-fb-add-section>+ ${escapeHtml(tr(locale, "addSection"))}</button>
        <div class="cp-fb-outline-meta">
          <span>${escapeHtml(tr(locale, "revision"))} ${state.template?.record_revision ?? "—"}</span>
          <span>${state.dirty ? escapeHtml(tr(locale, "unsaved")) : state.saving ? escapeHtml(tr(locale, "saving")) : escapeHtml(tr(locale, "saved"))}</span>
        </div>
      </aside>`;
  };

  const renderFieldControl = (field: UnknownRecord, value: string): string => {
    const type = String(field.type);
    const fieldId = String(field.field_id);
    const required = Boolean(field.required);
    if (["formula", "engine"].includes(type)) {
      return `<output class="cp-fb-readonly" data-fb-calc="${escapeHtml(fieldId)}">—</output>`;
    }
    if (type === "select" || type === "multiselect") {
      const options = (field.options || []) as UnknownRecord[];
      return `<select data-fb-field="${escapeHtml(fieldId)}" ${required ? "required" : ""}>
        <option value="">—</option>
        ${options
          .map(
            (option) =>
              `<option value="${escapeHtml(option.option_id)}" ${String(option.option_id) === value ? "selected" : ""}>${escapeHtml(textOf(option.label, locale) || option.option_id)}</option>`,
          )
          .join("")}
      </select>`;
    }
    if (type === "long_text") {
      return `<textarea rows="3" data-fb-field="${escapeHtml(fieldId)}" ${required ? "required" : ""}>${escapeHtml(value)}</textarea>`;
    }
    if (type === "boolean") {
      return `<label class="cp-fb-check"><input type="checkbox" data-fb-field="${escapeHtml(fieldId)}" ${value === "true" ? "checked" : ""}/> ${escapeHtml(textOf(field.label, locale))}</label>`;
    }
    if (type === "file") {
      return `<span class="cp-fb-file">
        <input type="file" accept="image/png,image/jpeg" data-fb-upload="${escapeHtml(fieldId)}" />
        <input type="hidden" data-fb-field="${escapeHtml(fieldId)}" value="${escapeHtml(value)}" />
        ${value ? `<a href="${base}/assets/${encodeURIComponent(value)}" target="_blank" rel="noopener">${escapeHtml(value)}</a>` : ""}
      </span>`;
    }
    return `<input type="${inputType(field)}" step="${type === "integer" ? "1" : "any"}" data-fb-field="${escapeHtml(fieldId)}" ${required ? "required" : ""} value="${escapeHtml(value)}" ${type === "percent" ? 'min="0" max="100"' : ""}/>`;
  };

  const renderSection = (section: UnknownRecord): string => {
    const payload = state.template?.payload || {};
    const fieldById = new Map<string, UnknownRecord>(
      (payload.fields || []).map((field: UnknownRecord) => [String(field.field_id), field]),
    );
    const tableById = new Map<string, UnknownRecord>(
      (payload.tables || []).map((table: UnknownRecord) => [String(table.table_id), table]),
    );
    const chartById = new Map<string, UnknownRecord>(
      (payload.charts || []).map((chart: UnknownRecord) => [String(chart.chart_id), chart]),
    );
    const components = (section.components || []) as UnknownRecord[];
    const componentHtml = components
      .map((component, index) => {
        const id = String(component.component_id);
        const controls = `<div class="cp-fb-comp-actions">
          <button type="button" title="${escapeHtml(tr(locale, "moveUp"))}" data-fb-move-component="${escapeHtml(id)}" data-fb-direction="-1" ${index === 0 ? "disabled" : ""}>↑</button>
          <button type="button" title="${escapeHtml(tr(locale, "moveDown"))}" data-fb-move-component="${escapeHtml(id)}" data-fb-direction="1" ${index === components.length - 1 ? "disabled" : ""}>↓</button>
          <button type="button" title="${escapeHtml(tr(locale, "delete"))}" data-fb-delete-component="${escapeHtml(id)}">×</button>
        </div>`;
        if (component.type === "field") {
          const field = fieldById.get(String(component.field_id));
          if (!field) return "";
          const span = Number(component.span || 1);
          const selected = state.selectedFieldId === field.field_id;
          return `<div class="cp-fb-field${selected ? " is-selected" : ""}" style="--cp-fb-span:${span}" data-fb-select-field="${escapeHtml(field.field_id)}" draggable="true" data-fb-component-drag="${escapeHtml(id)}">
            ${controls}
            <label>${escapeHtml(textOf(field.label, locale) || field.field_id)}${field.required ? " *" : ""}</label>
            <div class="cp-fb-field-value">${field.type === "formula" ? `<output class="cp-fb-readonly">${escapeHtml(tr(locale, "calculated"))}</output>` : `<span class="cp-fb-placeholder">${escapeHtml(field.type)}</span>`}</div>
          </div>`;
        }
        if (component.type === "table") {
          const table = tableById.get(String(component.table_id));
          if (!table) return "";
          return `<div class="cp-fb-block" data-fb-select-table="${escapeHtml(table.table_id)}">
            ${controls}
            <strong>${escapeHtml(textOf(table.label, locale) || table.table_id)}</strong>
            <span>${(table.columns || []).length} ${escapeHtml(tr(locale, "fields"))}</span>
          </div>`;
        }
        if (component.type === "chart") {
          const chart = chartById.get(String(component.chart_id));
          if (!chart) return "";
          return `<div class="cp-fb-block" data-fb-select-chart="${escapeHtml(chart.chart_id)}">
            ${controls}
            <strong>${escapeHtml(textOf(chart.title, locale) || chart.chart_id)}</strong>
            <span>${escapeHtml(chart.chart_type || "column")}</span>
          </div>`;
        }
        return `<div class="cp-fb-block">
          ${controls}
          <strong>${escapeHtml(component.type)}</strong>
          <span>${escapeHtml(textOf(component.text, locale))}</span>
        </div>`;
      })
      .join("");
    return `<div class="cp-fb-section${state.selectedSectionId === section.section_id ? " is-selected" : ""}" data-fb-select-section="${escapeHtml(section.section_id)}" draggable="true" data-fb-section-drag="${escapeHtml(section.section_id)}" data-fb-drop-section="${escapeHtml(section.section_id)}">
      <header>
        <h3>${escapeHtml(textOf(section.title, locale) || section.section_id)}</h3>
        <div class="cp-fb-section-actions">
          <button type="button" data-fb-add-component="${escapeHtml(section.section_id)}">+ ${escapeHtml(tr(locale, "addComponent"))}</button>
          <button type="button" data-fb-delete-section="${escapeHtml(section.section_id)}">${escapeHtml(tr(locale, "delete"))}</button>
        </div>
      </header>
      <div class="cp-fb-grid" style="--cp-fb-columns:${Number(section.columns || 1)}">${componentHtml || `<p class="cp-fb-empty">—</p>`}</div>
    </div>`;
  };

  const renderFieldInspector = (): string => {
    const payload = state.template?.payload || {};
    const field = (payload.fields || []).find(
      (item: UnknownRecord) => item.field_id === state.selectedFieldId,
    ) as UnknownRecord | undefined;
    if (!field) return `<p class="cp-fb-empty">${escapeHtml(tr(locale, "properties"))}</p>`;
    const isSelect = field.type === "select" || field.type === "multiselect";
    const isNumeric = ["integer", "number", "percent", "currency", "quantity", "duration"].includes(String(field.type));
    const isFormula = field.type === "formula";
    const isEngine = field.type === "engine";
    const binding = field.binding || {};
    const bindingSource = (state.bindings || []).find((source) => source.source === binding.source);
    return `
      <div class="cp-fb-inspector-group">
        <h4>${escapeHtml(tr(locale, "properties"))}</h4>
        <label>ID <input readonly value="${escapeHtml(field.field_id)}"/></label>
        <label>${escapeHtml(tr(locale, "type"))}
          <select data-fp="type" data-fb-selected-field="${escapeHtml(field.field_id)}">
            ${["text", "long_text", "boolean", "select", "multiselect", "integer", "number", "percent", "currency", "quantity", "duration", "date", "datetime", "reference", "file", "formula", "engine"]
              .map((type) => `<option value="${type}" ${field.type === type ? "selected" : ""}>${type}</option>`)
              .join("")}
          </select>
        </label>
        <label>${escapeHtml(tr(locale, "titleField"))} (en) <input data-fp="label.en" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(textOf(field.label, "en"))}"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} (fa) <input dir="rtl" data-fp="label.fa" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(textOf(field.label, "fa"))}"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} (de) <input data-fp="label.de" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(textOf(field.label, "de"))}"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} (zh) <input data-fp="label.zh" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(textOf(field.label, "zh"))}"/></label>
        <label class="cp-fb-check"><input type="checkbox" data-fp="required" data-fb-selected-field="${escapeHtml(field.field_id)}" ${field.required ? "checked" : ""}/> ${escapeHtml(tr(locale, "required"))}</label>
        ${isSelect ? `<label>${escapeHtml(tr(locale, "options"))}<textarea rows="3" data-fp="options.raw" data-fb-selected-field="${escapeHtml(field.field_id)}">${escapeHtml((field.options || []).map((option: UnknownRecord) => `${option.option_id}:${textOf(option.label, "en")}`).join(", "))}</textarea></label>` : ""}
        ${["quantity", "duration"].includes(String(field.type)) ? `<label>${escapeHtml(tr(locale, "unit"))} <input data-fp="unit" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(field.unit || "")}"/></label>` : ""}
        ${isNumeric ? `<label>${escapeHtml(tr(locale, "precision"))} <input type="number" min="0" max="6" data-fp="precision" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(field.precision ?? 2)}"/></label>
          <label>${escapeHtml(tr(locale, "min"))} <input type="number" step="any" data-fp="validation.min" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(field.validation?.min ?? "")}"/></label>
          <label>${escapeHtml(tr(locale, "max"))} <input type="number" step="any" data-fp="validation.max" data-fb-selected-field="${escapeHtml(field.field_id)}" value="${escapeHtml(field.validation?.max ?? "")}"/></label>` : ""}
        ${isFormula ? `<label>${escapeHtml(tr(locale, "expression"))}
            <select data-fp="formula_id" data-fb-selected-field="${escapeHtml(field.field_id)}">
              <option value="">—</option>
              ${(payload.formulas || []).map((formula: UnknownRecord) => `<option value="${escapeHtml(formula.formula_id)}" ${field.formula_id === formula.formula_id ? "selected" : ""}>${escapeHtml(formula.formula_id)}</option>`).join("")}
            </select>
          </label>` : ""}
        ${isEngine ? `<label>${escapeHtml(tr(locale, "binding"))}
            <select data-fp="binding.source" data-fb-selected-field="${escapeHtml(field.field_id)}">
              <option value="">—</option>
              ${(state.bindings || []).map((source) => `<option value="${escapeHtml(source.source)}" ${binding.source === source.source ? "selected" : ""}>${escapeHtml(textOf(source.label, locale) || source.source)}</option>`).join("")}
            </select>
          </label>
          <label>${escapeHtml(tr(locale, "source"))}
            <select data-fp="binding.field" data-fb-selected-field="${escapeHtml(field.field_id)}">
              <option value="">—</option>
              ${(bindingSource?.fields || []).map((entry) => `<option value="${escapeHtml(entry.field)}" ${binding.field === entry.field ? "selected" : ""}>${escapeHtml(entry.field)} · ${escapeHtml(entry.result_type)}</option>`).join("")}
            </select>
          </label>` : ""}
        <div class="cp-fb-inspector-actions">
          <button type="button" data-fb-delete-field="${escapeHtml(field.field_id)}">${escapeHtml(tr(locale, "delete"))}</button>
        </div>
      </div>`;
  };

  const designerToolbar = (): string => `
    <div class="cp-fb-design-actions">
      <button type="button" data-fb-undo ${state.undo.length ? "" : "disabled"}>↶ ${escapeHtml(tr(locale, "undo"))}</button>
      <button type="button" data-fb-redo ${state.redo.length ? "" : "disabled"}>↷ ${escapeHtml(tr(locale, "redo"))}</button>
      <button type="button" data-fb-save ${state.saving ? "disabled" : ""}>${escapeHtml(tr(locale, "save"))}</button>
      <button type="button" data-fb-validate>${escapeHtml(tr(locale, "validate"))}</button>
      <button type="button" class="cp-fb-primary" data-fb-publish ${state.template?.status === "deprecated" ? "disabled" : ""}>${escapeHtml(tr(locale, "publish"))}</button>
    </div>`;

  const renderSchemaCanvas = (): string => {
    const payload = state.template?.payload || {};
    const sections = (payload.sections || []) as UnknownRecord[];
    const placed = new Set<string>();
    for (const section of sections) {
      for (const component of section.components || []) {
        if (component.type === "field") placed.add(String(component.field_id));
      }
    }
    const unplaced = (payload.fields || []).filter(
      (field: UnknownRecord) => !placed.has(String(field.field_id)),
    );
    return `
      <div class="cp-fb-canvas-head">
        <div>
          <h3>${escapeHtml(textOf(payload.title, locale) || state.template?.template_id || "")}</h3>
          <p>${escapeHtml(state.template?.template_id || "")} · ${escapeHtml(state.template?.category || "")} · ${escapeHtml(tr(locale, "fields"))}: ${(payload.fields || []).length}</p>
        </div>
      </div>
      <div class="cp-fb-sections">${sections.map(renderSection).join("")}</div>
      ${
        unplaced.length
          ? `<div class="cp-fb-unplaced"><h4>${escapeHtml(tr(locale, "unplaced"))}</h4>
              <div>${unplaced
                .map(
                  (field: UnknownRecord) => `<button type="button" data-fb-place-field="${escapeHtml(field.field_id)}">${escapeHtml(textOf(field.label, locale) || field.field_id)} <small>${escapeHtml(field.type)}</small></button>`,
                )
                .join("")}</div></div>`
          : ""
      }
      <div class="cp-fb-add-row">
        ${["text", "number", "integer", "date", "select", "long_text", "boolean", "quantity", "currency", "percent", "file", "formula", "engine"]
          .map((type) => `<button type="button" data-fb-add-field="${type}">+ ${type}</button>`)
          .join("")}
      </div>
      ${renderIssues()}`;
  };

  const renderIssues = (): string => {
    if (!state.validationIssues.length) return "";
    return `<div class="cp-fb-issues" role="alert">
      <h4>${escapeHtml(tr(locale, "validationIssues"))} (${state.validationIssues.length})</h4>
      <ul>${state.validationIssues
        .slice(0, 30)
        .map((issue) => `<li class="is-${escapeHtml(issue.severity || "error")}"><code>${escapeHtml(issue.code)}</code> <span>${escapeHtml(issue.path)}</span> <small>${escapeHtml(issue.message_key)}</small></li>`)
        .join("")}</ul>
    </div>`;
  };

  const renderTablesCanvas = (): string => {
    const payload = state.template?.payload || {};
    const tables = (payload.tables || []) as UnknownRecord[];
    const table = tables.find((item) => item.table_id === state.selectedTableId) || tables[0];
    if (table && state.selectedTableId !== table.table_id) state.selectedTableId = String(table.table_id);
    return `
      <div class="cp-fb-canvas-head">
        <h3>${escapeHtml(tr(locale, "tables"))}</h3>
        <div class="cp-fb-canvas-actions">
          <button type="button" data-fb-add-table>+ ${escapeHtml(tr(locale, "addTable"))}</button>
          <button type="button" data-fb-place-component="table">${escapeHtml(tr(locale, "addComponent"))}</button>
        </div>
      </div>
      <div class="cp-fb-master">
        <ul class="cp-fb-master-list">
          ${tables.map((item) => `<li class="${table?.table_id === item.table_id ? "is-active" : ""}"><button type="button" data-fb-select-table="${escapeHtml(item.table_id)}">${escapeHtml(textOf(item.label, locale) || item.table_id)}</button><button type="button" data-fb-delete-table="${escapeHtml(item.table_id)}">×</button></li>`).join("") || `<li class="cp-fb-empty">—</li>`}
        </ul>
        ${
          table
            ? `<div class="cp-fb-detail">
                <label>ID <input readonly value="${escapeHtml(table.table_id)}"/></label>
                <label>${escapeHtml(tr(locale, "titleField"))} (en) <input data-fb-table-prop="label.en" value="${escapeHtml(textOf(table.label, "en"))}"/></label>
                <label>${escapeHtml(tr(locale, "titleField"))} (fa) <input dir="rtl" data-fb-table-prop="label.fa" value="${escapeHtml(textOf(table.label, "fa"))}"/></label>
                <label class="cp-fb-check"><input type="checkbox" data-fb-table-prop="repeat_header" ${table.repeat_header !== false ? "checked" : ""}/> repeat header</label>
                <h4>${escapeHtml(tr(locale, "fields"))}</h4>
                <table class="cp-fb-mini-table"><thead><tr><th>ID</th><th>${escapeHtml(tr(locale, "titleField"))}</th><th>${escapeHtml(tr(locale, "type"))}</th><th>Aggregate</th><th>${escapeHtml(tr(locale, "unit"))}</th><th></th></tr></thead><tbody>
                  ${(table.columns || []).map((column: UnknownRecord, index: number) => `<tr>
                    <td><input value="${escapeHtml(column.column_id)}" data-fb-column-id="${index}"/></td>
                    <td><input value="${escapeHtml(textOf(column.label, "en"))}" data-fb-column-prop="${index}:label.en"/></td>
                    <td><select data-fb-column-prop="${index}:type">${["text", "integer", "number", "percent", "currency", "quantity", "duration", "date", "select", "boolean"].map((type) => `<option ${column.type === type ? "selected" : ""}>${type}</option>`).join("")}</select></td>
                    <td><select data-fb-column-prop="${index}:aggregate">${["none", "sum", "min", "max", "average", "count"].map((value) => `<option ${(column.aggregate || "none") === value ? "selected" : ""}>${value}</option>`).join("")}</select></td>
                    <td><input value="${escapeHtml(column.unit || "")}" data-fb-column-prop="${index}:unit"/></td>
                    <td><button type="button" data-fb-delete-column="${index}">×</button></td>
                  </tr>`).join("")}
                </tbody></table>
                <button type="button" data-fb-add-column>+ column</button>
              </div>`
            : ""
        }
      </div>
      ${renderIssues()}`;
  };

  const renderFormulasCanvas = (): string => {
    const payload = state.template?.payload || {};
    const formulas = (payload.formulas || []) as UnknownRecord[];
    const formula = formulas.find((item) => item.formula_id === state.selectedFormulaId) || formulas[0];
    if (formula && state.selectedFormulaId !== formula.formula_id) state.selectedFormulaId = String(formula.formula_id);
    return `
      <div class="cp-fb-canvas-head">
        <h3>${escapeHtml(tr(locale, "formulas"))} · <small>${escapeHtml("cubi-formula-core.v1")}</small></h3>
        <button type="button" data-fb-add-formula>+ ${escapeHtml(tr(locale, "addFormula"))}</button>
      </div>
      <div class="cp-fb-master">
        <ul class="cp-fb-master-list">
          ${formulas.map((item) => `<li class="${formula?.formula_id === item.formula_id ? "is-active" : ""}"><button type="button" data-fb-select-formula="${escapeHtml(item.formula_id)}">${escapeHtml(item.formula_id)}</button><button type="button" data-fb-delete-formula="${escapeHtml(item.formula_id)}">×</button></li>`).join("") || `<li class="cp-fb-empty">—</li>`}
        </ul>
        ${
          formula
            ? `<div class="cp-fb-detail">
                <label>${escapeHtml(tr(locale, "id"))} <input data-fb-formula-prop="formula_id" value="${escapeHtml(formula.formula_id)}"/></label>
                <label>${escapeHtml(tr(locale, "expression"))}<textarea rows="3" dir="ltr" data-fb-formula-prop="expression">${escapeHtml(formula.expression || "")}</textarea></label>
                <label>${escapeHtml(tr(locale, "resultType"))}
                  <select data-fb-formula-prop="result_type">${["number", "boolean", "text", "date", "datetime"].map((type) => `<option ${(formula.result_type || "number") === type ? "selected" : ""}>${type}</option>`).join("")}</select>
                </label>
                <label>${escapeHtml(tr(locale, "precision"))} <input type="number" min="0" max="6" data-fb-formula-prop="precision" value="${escapeHtml(formula.precision ?? 2)}"/></label>
                <label>${escapeHtml(tr(locale, "unit"))} <input data-fb-formula-prop="unit" value="${escapeHtml(formula.unit || "")}"/></label>
                <label>${escapeHtml(tr(locale, "samples"))}<input data-fb-formula-samples value="planned_qty=200, completed_qty=150, workforce=12, hours_worked=8.5"/></label>
                <button type="button" data-fb-test-formula>${escapeHtml(tr(locale, "test"))}</button>
                ${
                  state.formulaTest
                    ? `<div class="cp-fb-formula-result"><strong>${escapeHtml(tr(locale, "testResult"))}</strong>
                        <code>${escapeHtml(JSON.stringify(state.formulaTest.result ?? state.formulaTest.errors ?? {}))}</code></div>`
                    : ""
                }
                <p class="cp-fb-hint">${escapeHtml(tr(locale, "formulaOk"))}</p>
              </div>`
            : ""
        }
      </div>
      ${renderIssues()}`;
  };

  const renderChartsCanvas = (): string => {
    const payload = state.template?.payload || {};
    const charts = (payload.charts || []) as UnknownRecord[];
    const chart = charts.find((item) => item.chart_id === state.selectedChartId) || charts[0];
    if (chart && state.selectedChartId !== chart.chart_id) state.selectedChartId = String(chart.chart_id);
    const tables = (payload.tables || []) as UnknownRecord[];
    const source = (chart?.source || {}) as UnknownRecord;
    const table = tables.find((item) => item.table_id === source.table_id);
    return `
      <div class="cp-fb-canvas-head">
        <h3>${escapeHtml(tr(locale, "charts"))}</h3>
        <button type="button" data-fb-add-chart>+ ${escapeHtml(tr(locale, "addChart"))}</button>
      </div>
      <div class="cp-fb-master">
        <ul class="cp-fb-master-list">
          ${charts.map((item) => `<li class="${chart?.chart_id === item.chart_id ? "is-active" : ""}"><button type="button" data-fb-select-chart="${escapeHtml(item.chart_id)}">${escapeHtml(textOf(item.title, locale) || item.chart_id)}</button><button type="button" data-fb-delete-chart="${escapeHtml(item.chart_id)}">×</button></li>`).join("") || `<li class="cp-fb-empty">—</li>`}
        </ul>
        ${
          chart
            ? `<div class="cp-fb-detail">
                <label>ID <input readonly value="${escapeHtml(chart.chart_id)}"/></label>
                <label>${escapeHtml(tr(locale, "titleField"))} (en) <input data-fb-chart-prop="title.en" value="${escapeHtml(textOf(chart.title, "en"))}"/></label>
                <label>${escapeHtml(tr(locale, "titleField"))} (fa) <input dir="rtl" data-fb-chart-prop="title.fa" value="${escapeHtml(textOf(chart.title, "fa"))}"/></label>
                <label>${escapeHtml(tr(locale, "chartType"))}
                  <select data-fb-chart-prop="chart_type">${["column", "bar", "line", "pie", "donut", "s_curve"].map((type) => `<option ${chart.chart_type === type ? "selected" : ""}>${type}</option>`).join("")}</select>
                </label>
                <label>${escapeHtml(tr(locale, "source"))}
                  <select data-fb-chart-prop="source.table_id"><option value="">—</option>${tables.map((item) => `<option value="${escapeHtml(item.table_id)}" ${source.table_id === item.table_id ? "selected" : ""}>${escapeHtml(textOf(item.label, locale) || item.table_id)}</option>`).join("")}</select>
                </label>
                <label>${escapeHtml(tr(locale, "category"))}
                  <select data-fb-chart-prop="source.category_column"><option value="">—</option>${(table?.columns || []).map((column: UnknownRecord) => `<option value="${escapeHtml(column.column_id)}" ${source.category_column === column.column_id ? "selected" : ""}>${escapeHtml(column.column_id)}</option>`).join("")}</select>
                </label>
                <fieldset><legend>${escapeHtml(tr(locale, "series"))}</legend>
                  ${(table?.columns || []).map((column: UnknownRecord) => {
                    const checked = (chart.series || []).some((item: UnknownRecord) => item.column_id === column.column_id);
                    return `<label class="cp-fb-check"><input type="checkbox" data-fb-chart-series="${escapeHtml(column.column_id)}" ${checked ? "checked" : ""}/> ${escapeHtml(column.column_id)}</label>`;
                  }).join("") || "—"}
                </fieldset>
                <div class="cp-fb-chart-preview" data-fb-chart-preview>${renderChartSvg(chart, state.draftTables)}</div>
              </div>`
            : ""
        }
      </div>
      ${renderIssues()}`;
  };

  const renderWorkflowCanvas = (): string => {
    const payload = state.template?.payload || {};
    const workflow = (payload.workflow || {}) as UnknownRecord;
    return `
      <div class="cp-fb-canvas-head"><h3>${escapeHtml(tr(locale, "workflow"))}</h3></div>
      <div class="cp-fb-detail">
        <label>${escapeHtml(tr(locale, "approvalMode"))}
          <select data-fb-workflow="approval_mode">${["single", "sequential", "parallel"].map((mode) => `<option value="${mode}" ${(workflow.approval_mode || "single") === mode ? "selected" : ""}>${escapeHtml(tr(locale, mode as "single" | "sequential" | "parallel"))}</option>`).join("")}</select>
        </label>
        <label>${escapeHtml(tr(locale, "reviewers"))} <input data-fb-workflow="reviewers" value="${escapeHtml((workflow.reviewers || []).join(", "))}"/></label>
        <label>${escapeHtml(tr(locale, "approvers"))} <input data-fb-workflow="approvers" value="${escapeHtml((workflow.approvers || []).join(", "))}"/></label>
        <label>${escapeHtml(tr(locale, "approvalStep"))}
          <textarea rows="3" dir="ltr" data-fb-workflow="approval_steps" placeholder="step_id:role, step_id:role">${escapeHtml((workflow.approval_steps || []).map((step: UnknownRecord) => `${step.step_id}:${step.role}`).join(", "))}</textarea>
        </label>
        <label class="cp-fb-check"><input type="checkbox" data-fb-workflow="allow_self_approval" ${workflow.allow_self_approval ? "checked" : ""}/> ${escapeHtml(tr(locale, "allowSelf"))}</label>
        <label class="cp-fb-check"><input type="checkbox" data-fb-workflow="require_reason_on_return" ${workflow.require_reason_on_return !== false ? "checked" : ""}/> ${escapeHtml(tr(locale, "reason"))} · ${escapeHtml(tr(locale, "return"))}</label>
        <label class="cp-fb-check"><input type="checkbox" data-fb-workflow="require_reason_on_reject" ${workflow.require_reason_on_reject !== false ? "checked" : ""}/> ${escapeHtml(tr(locale, "reason"))} · ${escapeHtml(tr(locale, "reject"))}</label>
        <p class="cp-fb-hint">${escapeHtml(tr(locale, "moduleHint"))}</p>
      </div>
      ${renderIssues()}`;
  };

  const renderPageCanvas = (): string => {
    const payload = state.template?.payload || {};
    const page = (payload.page || {}) as UnknownRecord;
    const margins = (page.margins || {}) as UnknownRecord;
    const header = (payload.header || {}) as UnknownRecord;
    const footer = (payload.footer || {}) as UnknownRecord;
    return `
      <div class="cp-fb-canvas-head"><h3>${escapeHtml(tr(locale, "pageSetup"))}</h3></div>
      <div class="cp-fb-detail cp-fb-page-settings">
        <label>${escapeHtml(tr(locale, "paper"))}
          <select data-fb-page="paper">${["A4", "A3", "A5", "custom"].map((paper) => `<option ${page.paper === paper ? "selected" : ""}>${paper}</option>`).join("")}</select>
        </label>
        <label>${escapeHtml(tr(locale, "orientation"))}
          <select data-fb-page="orientation"><option value="portrait" ${page.orientation !== "landscape" ? "selected" : ""}>${escapeHtml(tr(locale, "portrait"))}</option><option value="landscape" ${page.orientation === "landscape" ? "selected" : ""}>${escapeHtml(tr(locale, "landscape"))}</option></select>
        </label>
        ${page.paper === "custom" ? `<label>${escapeHtml(tr(locale, "customWidth"))} <input type="number" min="50" data-fb-page="width_mm" value="${escapeHtml(page.width_mm ?? 210)}"/></label><label>${escapeHtml(tr(locale, "customHeight"))} <input type="number" min="50" data-fb-page="height_mm" value="${escapeHtml(page.height_mm ?? 297)}"/></label>` : ""}
        <fieldset><legend>${escapeHtml(tr(locale, "margins"))}</legend>
          ${["top", "bottom", "left", "right"].map((side) => `<label>${side} <input type="number" min="0" max="100" data-fb-page="margins.${side}" value="${escapeHtml(margins[side] ?? 12)}"/></label>`).join("")}
        </fieldset>
        <label>${escapeHtml(tr(locale, "scale"))} <input type="number" min="25" max="200" data-fb-page="scale" value="${escapeHtml(page.scale ?? 100)}"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} · header (en) <input data-fb-header="title.en" value="${escapeHtml(textOf(header.title, "en"))}"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} · header (fa) <input dir="rtl" data-fb-header="title.fa" value="${escapeHtml(textOf(header.title, "fa"))}"/></label>
        <label>Footer note (en) <input data-fb-footer="note.en" value="${escapeHtml(textOf(footer.note, "en"))}"/></label>
        <label>Footer note (fa) <input dir="rtl" data-fb-footer="note.fa" value="${escapeHtml(textOf(footer.note, "fa"))}"/></label>
        <label class="cp-fb-check"><input type="checkbox" data-fb-footer="show_page_numbers" ${footer.show_page_numbers !== false ? "checked" : ""}/> page numbers</label>
        <label class="cp-fb-check"><input type="checkbox" data-fb-footer="approval_block" ${footer.approval_block !== false ? "checked" : ""}/> ${escapeHtml(tr(locale, "approvalTrail"))}</label>
      </div>
      ${renderIssues()}`;
  };

  const renderVersionsCanvas = (): string => {
    const versions = state.versions || [];
    return `
      <div class="cp-fb-canvas-head">
        <h3>${escapeHtml(tr(locale, "versions"))}</h3>
        ${versions.length > 1 ? `<button type="button" data-fb-diff>${escapeHtml(tr(locale, "compare"))}</button>` : ""}
      </div>
      <ul class="cp-fb-versions">
        ${versions
          .map(
            (version) => `<li>
              <div><strong>v${escapeHtml(version.version)}</strong> <span>${escapeHtml(version.published_by || "")}</span> <small>${escapeHtml(version.published_at ? formatDate(version.published_at, calendarMode).slice(0, 16) : "")}</small></div>
              <p>${escapeHtml(version.change_reason || "—")}</p>
              <code>${escapeHtml(String(version.schema_hash || "").slice(0, 16))}</code>
              <button type="button" data-fb-restore-version="${escapeHtml(version.version)}">${escapeHtml(tr(locale, "restore"))}</button>
            </li>`,
          )
          .join("") || `<li class="cp-fb-empty">—</li>`}
      </ul>
      ${renderDiffBlock()}`;
  };

  const renderDiffBlock = (): string => {
    const diff = state.diff;
    if (!diff) return "";
    return `<div class="cp-fb-diff">
      <h4>${escapeHtml(tr(locale, "compare"))} v${escapeHtml(diff.from_version)} → v${escapeHtml(diff.to_version)}</h4>
      ${(["fields", "formulas"] as const).map((section) => `<div><strong>${escapeHtml(tr(locale, section as "formulas"))}</strong>
        <p>${escapeHtml(tr(locale, "added"))}: ${escapeHtml((diff.diff?.[section]?.added || []).join(", ") || "—")}</p>
        <p>${escapeHtml(tr(locale, "removed"))}: ${escapeHtml((diff.diff?.[section]?.removed || []).join(", ") || "—")}</p>
        <p>${escapeHtml(tr(locale, "changed"))}: ${escapeHtml((diff.diff?.[section]?.changed || []).join(", ") || "—")}</p>
      </div>`).join("")}
    </div>`;
  };

  const renderDesigner = (): string => {
    if (!state.template) {
      return `<div class="cp-fb-empty-state"><h3>${escapeHtml(tr(locale, "designer"))}</h3><p>${escapeHtml(tr(locale, "chooseTemplate"))}</p><button type="button" data-fb-back>${escapeHtml(tr(locale, "library"))}</button></div>`;
    }
    const canvas =
      state.designTab === "schema"
        ? renderSchemaCanvas()
        : state.designTab === "tables"
          ? renderTablesCanvas()
          : state.designTab === "formulas"
            ? renderFormulasCanvas()
            : state.designTab === "charts"
              ? renderChartsCanvas()
              : state.designTab === "workflow"
                ? renderWorkflowCanvas()
                : state.designTab === "page"
                  ? renderPageCanvas()
                  : renderVersionsCanvas();
    return `
      <div class="cp-fb-designer">
        ${templateOutline()}
        <main class="cp-fb-canvas">${state.loading ? `<p class="cp-fb-empty">${escapeHtml(tr(locale, "loading"))}</p>` : `${designerToolbar()}${canvas}`}</main>
        <aside class="cp-fb-inspector">${renderFieldInspector()}</aside>
      </div>`;
  };

  const reportTemplateChoices = (): TemplateSummary[] =>
    (state.projectTemplates || []).filter((item) => item.published_version && item.status !== "deprecated");

  const renderReportEditor = (): string => {
    const submission = state.submission;
    if (!submission) return "";
    const template = (submission.template || {}) as UnknownRecord;
    const sections = (template.sections || []) as UnknownRecord[];
    const fieldById = new Map<string, UnknownRecord>(
      (template.fields || []).map((field: UnknownRecord) => [String(field.field_id), field]),
    );
    const tableById = new Map<string, UnknownRecord>(
      (template.tables || []).map((table: UnknownRecord) => [String(table.table_id), table]),
    );
    const bindings = (submission.bindings || {}) as UnknownRecord;
    const resolved = (bindings.values || {}) as UnknownRecord;
    const canFill =
      ["draft", "returned"].includes(submission.status) &&
      permission("form.fill") &&
      (!submission.assigned_to ||
        submission.assigned_to === state.viewer ||
        (!submission.assigned_to && submission.author === state.viewer));
    const workflow = (template.workflow || {}) as UnknownRecord;
    const selfApprovalBlocked =
      !workflow.allow_self_approval &&
      (submission.author === state.viewer || submission.assigned_to === state.viewer);
    const actions: string[] = [];
    if (["draft", "returned"].includes(submission.status) && permission("form.submit")) {
      actions.push(`<button type="button" class="cp-fb-primary" data-fb-transition="submit">${escapeHtml(tr(locale, "submit"))}</button>`);
      actions.push(`<button type="button" data-fb-save-report>${escapeHtml(tr(locale, "saveDraft"))}</button>`);
    }
    if (submission.status === "submitted" && permission("form.review")) {
      actions.push(`<button type="button" data-fb-transition="start_review">${escapeHtml(tr(locale, "startReview"))}</button>`);
      actions.push(`<button type="button" data-fb-transition="return">${escapeHtml(tr(locale, "return"))}</button>`);
    }
    if (submission.status === "under_review" && permission("form.review")) {
      actions.push(`<button type="button" data-fb-transition="return">${escapeHtml(tr(locale, "return"))}</button>`);
    }
    if (["submitted", "under_review"].includes(submission.status) && permission("form.approve") && !selfApprovalBlocked) {
      actions.push(`<button type="button" class="cp-fb-primary" data-fb-transition="approve">${escapeHtml(tr(locale, "approve"))}</button>`);
      actions.push(`<button type="button" class="cp-fb-danger" data-fb-transition="reject">${escapeHtml(tr(locale, "reject"))}</button>`);
    }
    if (submission.status === "approved" && permission("form.approve")) {
      actions.push(`<button type="button" data-fb-transition="issue">${escapeHtml(tr(locale, "issue"))}</button>`);
    }
    if (["issued", "approved", "rejected", "returned"].includes(submission.status) && permission("form.approve")) {
      actions.push(`<button type="button" data-fb-transition="archive">${escapeHtml(tr(locale, "archive"))}</button>`);
    }
    const body = sections.length
      ? sections
          .map((section) => {
            const components = (section.components || []) as UnknownRecord[];
            return `<section class="cp-fb-report-section">
              <h3>${escapeHtml(textOf(section.title, locale) || section.section_id)}</h3>
              <div class="cp-fb-report-grid" style="--cp-fb-columns:${Number(section.columns || 1)}">
                ${components
                  .map((component) => {
                    if (component.type === "field") {
                      const field = fieldById.get(String(component.field_id));
                      if (!field) return "";
                      const fieldId = String(field.field_id);
                      if (field.type === "engine") {
                        const entry = resolved[fieldId] as UnknownRecord | undefined;
                        const envelope = entry?.value as UnknownRecord | undefined;
                        return `<div class="cp-fb-report-field">
                          <label>${escapeHtml(textOf(field.label, locale) || fieldId)}</label>
                          <output class="cp-fb-readonly">${escapeHtml(bindingValue(field, entry || null) || tr(locale, "missingValue"))}</output>
                          <small class="cp-fb-provenance">${escapeHtml(tr(locale, "provenance"))}: ${escapeHtml(entry?.provenance?.source || "—")} · ${escapeHtml(entry?.provenance?.read_at || "")}</small>
                        </div>`;
                      }
                      if (field.type === "formula") {
                        const calculated = (submission.calculated || {})[fieldId] as UnknownRecord | undefined;
                        const value = calculated?.value;
                        return `<div class="cp-fb-report-field">
                          <label>${escapeHtml(textOf(field.label, locale) || fieldId)}</label>
                          <output class="cp-fb-readonly" data-fb-calc="${escapeHtml(fieldId)}">${escapeHtml(value == null ? "—" : String(value))}${calculated?.unit ? ` ${escapeHtml(calculated.unit)}` : ""}</output>
                        </div>`;
                      }
                      const value = rawFieldValue(field, state.draftValues[fieldId]);
                      return `<div class="cp-fb-report-field">
                        <label>${escapeHtml(textOf(field.label, locale) || fieldId)}${field.required ? " *" : ""}</label>
                        ${canFill ? renderFieldControl(field, value) : `<output class="cp-fb-readonly">${escapeHtml(value || "—")}</output>`}
                      </div>`;
                    }
                    if (component.type === "table") {
                      const table = tableById.get(String(component.table_id));
                      if (!table) return "";
                      const rows = tableRows(state.draftTables, String(table.table_id));
                      const columns = (table.columns || []) as UnknownRecord[];
                      return `<div class="cp-fb-report-table" style="grid-column:1/-1">
                        <h4>${escapeHtml(textOf(table.label, locale) || table.table_id)}</h4>
                        <table><thead><tr>${columns.map((column) => `<th>${escapeHtml(textOf(column.label, locale) || column.column_id)}</th>`).join("")}${canFill ? "<th></th>" : ""}</tr></thead>
                        <tbody>
                          ${rows.map((row, rowIndex) => `<tr>${columns.map((column) => {
                            const raw = rowRaw(row, String(column.column_id), column);
                            return `<td>${canFill ? `<input type="${inputType(column)}" data-fb-cell="${escapeHtml(table.table_id)}|${rowIndex}|${escapeHtml(column.column_id)}" value="${escapeHtml(raw)}"/>` : escapeHtml(raw)}</td>`;
                          }).join("")}${canFill ? `<td><button type="button" data-fb-remove-row="${escapeHtml(table.table_id)}|${rowIndex}">×</button></td>` : ""}</tr>`).join("") || `<tr><td colspan="${columns.length + (canFill ? 1 : 0)}" class="cp-fb-empty">${escapeHtml(tr(locale, "noRows"))}</td></tr>`}
                        </tbody></table>
                        ${canFill ? `<button type="button" data-fb-add-row="${escapeHtml(table.table_id)}">+ ${escapeHtml(tr(locale, "addRow"))}</button>` : ""}
                      </div>`;
                    }
                    if (component.type === "chart") {
                      const chart = (template.charts || []).find((item: UnknownRecord) => item.chart_id === component.chart_id);
                      if (!chart) return "";
                      return `<div class="cp-fb-report-chart" style="grid-column:1/-1"><h4>${escapeHtml(textOf(chart.title, locale) || chart.chart_id)}</h4>${renderChartSvg(chart, state.draftTables)}</div>`;
                    }
                    return `<div class="cp-fb-block"><strong>${escapeHtml(component.type)}</strong><span>${escapeHtml(textOf(component.text, locale))}</span></div>`;
                  })
                  .join("")}
              </div>
            </section>`;
          })
          .join("")
      : `<p class="cp-fb-empty">${escapeHtml(tr(locale, "chooseTemplate"))}</p>`;
    return `
      <div class="cp-fb-report">
        <header class="cp-fb-report-head" data-fb-report-status="${escapeHtml(submission.status)}" data-fb-report-version="${submission.template_version}">
          <div>
            <h2>${escapeHtml(submission.title || submission.submission_id)}</h2>
            <p><code>${escapeHtml(submission.submission_id)}</code> · ${escapeHtml(statusText(locale, submission.status))} · v${submission.template_version} · ${escapeHtml(tr(locale, "revision"))} ${submission.record_revision}</p>
            <p>${escapeHtml(tr(locale, "assignee"))}: ${escapeHtml(submission.assigned_to || submission.author)} · ${escapeHtml(tr(locale, "reportDate"))}: ${escapeHtml(formatDate(submission.report_date, calendarMode))}</p>
          </div>
          <div class="cp-fb-report-actions">${actions.join("")}<button type="button" data-fb-print-html>${escapeHtml(tr(locale, "printPreview"))}</button><button type="button" data-fb-export>xlsx</button><button type="button" data-fb-back>← ${escapeHtml(tr(locale, "reports"))}</button></div>
        </header>
        ${renderIssues()}
        <div class="cp-fb-report-body">${body}</div>
        ${renderCalculated(submission)}
        ${renderTrail(submission)}
      </div>`;
  };

  const renderCalculated = (submission: SubmissionDetail): string => {
    const entries = Object.entries(submission.calculated || {});
    if (!entries.length) return "";
    return `<section class="cp-fb-calculated"><h3>${escapeHtml(tr(locale, "calculated"))}</h3>
      <div>${entries.map(([key, raw]) => {
        const record = raw as UnknownRecord;
        return `<span><strong>${escapeHtml(key)}</strong> ${escapeHtml(record?.value == null ? "—" : String(record.value))}${record?.unit ? ` ${escapeHtml(record.unit)}` : ""}</span>`;
      }).join("")}</div></section>`;
  };

  const renderTrail = (submission: SubmissionDetail): string => `
    <section class="cp-fb-trail">
      <div>
        <h3>${escapeHtml(tr(locale, "approvalTrail"))}</h3>
        <ol>${(submission.approvals || []).map((event) => `<li><strong>${escapeHtml(event.action)}</strong> ${escapeHtml(statusText(locale, event.from_status))} → ${escapeHtml(statusText(locale, event.to_status))} <span>${escapeHtml(event.actor)}</span> <small>${escapeHtml(event.at ? formatDate(event.at, calendarMode).slice(0, 16) : "")}</small>${event.reason ? `<p>${escapeHtml(event.reason)}</p>` : ""}</li>`).join("") || `<li class="cp-fb-empty">—</li>`}</ol>
      </div>
      <div>
        <h3>${escapeHtml(tr(locale, "revisions"))}</h3>
        <ol>${(submission.revisions || []).slice().reverse().map((revision) => `<li><strong>R${escapeHtml(revision.revision)}</strong> ${escapeHtml(revision.event_type)} <span>${escapeHtml(revision.actor)}</span> <small>${escapeHtml(revision.created_at ? formatDate(revision.created_at, calendarMode).slice(0, 16) : "")}</small></li>`).join("") || `<li class="cp-fb-empty">—</li>`}</ol>
      </div>
    </section>`;

  const renderReports = (): string => {
    if (state.submission) return renderReportEditor();
    const filter =
      state.reportFilter === "mine" && state.submission === null
        ? state.submissions.filter((item) => item.assigned_to === undefined || item.assigned_to === item.author)
        : state.submissions;
    return `
      <div class="cp-fb-toolbar">
        <div class="cp-fb-toolbar-actions">
          <button type="button" class="cp-fb-primary" data-fb-new-report ${permission("form.fill") && reportTemplateChoices().length ? "" : "disabled"}>+ ${escapeHtml(tr(locale, "createReport"))}</button>
          <button type="button" data-fb-filter="all" ${state.reportFilter === "all" ? "aria-pressed=\"true\"" : ""}>${escapeHtml(tr(locale, "filterAll"))}</button>
          <button type="button" data-fb-filter="mine" ${state.reportFilter === "mine" ? "aria-pressed=\"true\"" : ""}>${escapeHtml(tr(locale, "filterMine"))}</button>
        </div>
        <span>${filter.length}</span>
      </div>
      ${
        filter.length
          ? `<div class="cp-fb-report-list">${filter
              .map(
                (item) => `<article data-fb-open-report="${escapeHtml(item.submission_id)}" tabindex="0">
                  <header><strong>${escapeHtml(item.title || item.submission_id)}</strong><span class="cp-fb-badge is-${escapeHtml(item.status)}">${escapeHtml(statusText(locale, item.status))}</span></header>
                  <p><code>${escapeHtml(item.submission_id)}</code> · ${escapeHtml(item.template_id)} v${item.template_version}</p>
                  <p>${escapeHtml(tr(locale, "assignee"))}: ${escapeHtml(item.assigned_to || item.author)} · ${escapeHtml(formatDate(item.report_date, calendarMode))}</p>
                </article>`,
              )
              .join("")}</div>`
          : `<p class="cp-fb-empty">${escapeHtml(tr(locale, "noReports"))}</p>`
      }`;
  };

  const renderPrint = (): string => {
    if (!state.printHtml) {
      return `<div class="cp-fb-empty-state"><h3>${escapeHtml(tr(locale, "print"))}</h3><p>${escapeHtml(tr(locale, "printPreview"))}</p><button type="button" data-fb-print-html>${escapeHtml(tr(locale, "printPreview"))}</button></div>`;
    }
    return `
      <div class="cp-fb-print">
        <div class="cp-fb-toolbar">
          <div class="cp-fb-toolbar-actions">
            <button type="button" class="cp-fb-primary" data-fb-print-frame>${escapeHtml(tr(locale, "printPdf"))}</button>
            <button type="button" data-fb-export>${escapeHtml(tr(locale, "exportExcel"))}</button>
            <button type="button" data-fb-print-refresh>${escapeHtml(tr(locale, "reloadLatest"))}</button>
          </div>
        </div>
        <iframe data-fb-print-frame-src title="${escapeHtml(tr(locale, "printPreview"))}" srcdoc="${escapeHtml(state.printHtml)}"></iframe>
      </div>`;
  };

  const renderModal = (): string => {
    const modal = state.modal;
    if (!modal) return "";
    let inner = "";
    if (modal.kind === "new-template") {
      inner = `<form data-fb-modal="new-template" data-library="${modal.library}">
        <label>${escapeHtml(tr(locale, "id"))} <input name="template_id" required pattern="[A-Za-z0-9][A-Za-z0-9._-]*" placeholder="site-daily-report"/></label>
        <label>${escapeHtml(tr(locale, "titleField"))} <input name="title" required/></label>
        <label>${escapeHtml(tr(locale, "category"))} <input name="category" value="daily"/></label>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button><button type="submit" class="cp-fb-primary">${escapeHtml(tr(locale, "create"))}</button></div>
      </form>`;
    } else if (modal.kind === "new-report") {
      const choices = reportTemplateChoices();
      inner = `<form data-fb-modal="new-report">
        <label>${escapeHtml(tr(locale, "chooseTemplate"))}
          <select name="template_id" required>${choices.map((item) => `<option value="${escapeHtml(item.template_id)}" data-version="${item.published_version}">${escapeHtml(item.title_text || item.title)} · v${item.published_version}</option>`).join("")}</select>
        </label>
        <input type="hidden" name="template_version" value="${escapeHtml(choices[0]?.published_version || "")}"/>
        <label>${escapeHtml(tr(locale, "reportTitle"))} <input name="title" placeholder="${escapeHtml(choices[0]?.title_text || "")}"/></label>
        <label>${escapeHtml(tr(locale, "reportDate"))} <input type="date" name="report_date" value="${new Date().toISOString().slice(0, 10)}"/></label>
        <label>${escapeHtml(tr(locale, "assignTo"))}
          <select name="assigned_to">${(state.assignees || []).map((member) => `<option value="${escapeHtml(member.user_id)}">${escapeHtml(localeKey(locale) === "fa" && member.label_fa ? member.label_fa : member.label)} · ${escapeHtml(member.roles.join("/"))}</option>`).join("")}</select>
        </label>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button><button type="submit" class="cp-fb-primary">${escapeHtml(tr(locale, "create"))}</button></div>
      </form>`;
    } else if (modal.kind === "publish") {
      inner = `<form data-fb-modal="publish">
        <p>${escapeHtml(tr(locale, "publish"))} · v${(state.template?.published_version || 0) + 1}</p>
        <label>${escapeHtml(tr(locale, "changeReason"))} <textarea name="reason" rows="3"></textarea></label>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button><button type="submit" class="cp-fb-primary">${escapeHtml(tr(locale, "publish"))}</button></div>
      </form>`;
    } else if (modal.kind === "reason") {
      inner = `<form data-fb-modal="reason" data-action="${modal.action}">
        <p>${escapeHtml(statusText(locale, modal.action === "return" ? "returned" : "rejected"))}</p>
        <label>${escapeHtml(tr(locale, "reason"))} <textarea name="reason" rows="3" required></textarea></label>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button><button type="submit" class="cp-fb-primary">${escapeHtml(tr(locale, "confirm"))}</button></div>
      </form>`;
    } else if (modal.kind === "add-component") {
      const payload = state.template?.payload || {};
      const section = (payload.sections || []).find((item: UnknownRecord) => item.section_id === modal.sectionId);
      const placed = new Set<string>(
        (section?.components || []).map((component: UnknownRecord) => String(component.field_id || component.table_id || component.chart_id)),
      );
      inner = `<div class="cp-fb-modal-body">
        <h3>${escapeHtml(tr(locale, "addComponent"))}</h3>
        <h4>${escapeHtml(tr(locale, "fields"))}</h4>
        <div class="cp-fb-chip-list">${(payload.fields || []).filter((field: UnknownRecord) => !placed.has(String(field.field_id))).map((field: UnknownRecord) => `<button type="button" data-fb-place-existing="field:${escapeHtml(field.field_id)}">${escapeHtml(textOf(field.label, locale) || field.field_id)}</button>`).join("") || "—"}</div>
        <h4>${escapeHtml(tr(locale, "tables"))}</h4>
        <div class="cp-fb-chip-list">${(payload.tables || []).filter((table: UnknownRecord) => !placed.has(String(table.table_id))).map((table: UnknownRecord) => `<button type="button" data-fb-place-existing="table:${escapeHtml(table.table_id)}">${escapeHtml(textOf(table.label, locale) || table.table_id)}</button>`).join("") || "—"}</div>
        <h4>${escapeHtml(tr(locale, "charts"))}</h4>
        <div class="cp-fb-chip-list">${(payload.charts || []).filter((chart: UnknownRecord) => !placed.has(String(chart.chart_id))).map((chart: UnknownRecord) => `<button type="button" data-fb-place-existing="chart:${escapeHtml(chart.chart_id)}">${escapeHtml(textOf(chart.title, locale) || chart.chart_id)}</button>`).join("") || "—"}</div>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button></div>
      </div>`;
    } else if (modal.kind === "diff") {
      inner = `<form data-fb-modal="diff">
        <div class="cp-fb-diff-picker">
          <label>${escapeHtml(tr(locale, "from"))} <select name="from">${(state.versions || []).map((version) => `<option value="${escapeHtml(version.version)}">v${escapeHtml(version.version)}</option>`).join("")}</select></label>
          <label>${escapeHtml(tr(locale, "to"))} <select name="to">${(state.versions || []).map((version) => `<option value="${escapeHtml(version.version)}">v${escapeHtml(version.version)}</option>`).join("")}</select></label>
        </div>
        <div class="cp-fb-modal-actions"><button type="button" data-fb-modal-close>${escapeHtml(tr(locale, "cancel"))}</button><button type="submit" class="cp-fb-primary">${escapeHtml(tr(locale, "compare"))}</button></div>
      </form>`;
    }
    return `<div class="cp-fb-modal-backdrop" data-fb-modal-backdrop><div class="cp-fb-modal" role="dialog" aria-modal="true">${inner}</div></div>`;
  };

  const render = (): void => {
    if (closed) return;
    const tab = state.tab;
    const body =
      tab === "library"
        ? renderLibrary()
        : tab === "design"
          ? renderDesigner()
          : tab === "reports"
            ? renderReports()
            : renderPrint();
    root.innerHTML = `
      <div class="cp-fb-shell">
        <header class="cp-fb-topbar">
          <div class="cp-fb-brand">
            <span class="cp-fb-logo">CUBI</span>
            <div><h1>${escapeHtml(tr(locale, "title"))}</h1><p>${escapeHtml(tr(locale, "subtitle"))}</p></div>
          </div>
          <nav class="cp-fb-tabs" role="tablist">
            ${(["library", "design", "reports", "print"] as const)
              .map((key) => `<button type="button" role="tab" aria-selected="${tab === key}" class="${tab === key ? "is-active" : ""}" data-fb-tab="${key}">${escapeHtml(tr(locale, key))}</button>`)
              .join("")}
          </nav>
          <div class="cp-fb-topbar-actions">
            <span class="cp-fb-project">${escapeHtml(context.project_id)}</span>
            <button type="button" class="cp-fb-close" data-fb-close aria-label="${escapeHtml(tr(locale, "close"))}">×</button>
          </div>
        </header>
        <div class="cp-fb-status" data-fb-status data-kind="${state.status?.kind || "info"}" aria-live="polite">${escapeHtml(state.status?.message || "")}</div>
        <div class="cp-fb-content">${body}</div>
        ${renderModal()}
      </div>`;
  };

  const commit = (): void => {
    scheduleAutosave();
    render();
  };

  const payload = (): UnknownRecord => (state.template?.payload || {}) as UnknownRecord;

  const getPath = (record: UnknownRecord, path: string): any =>
    path.split(".").reduce<any>((value, key) => (value == null ? undefined : value[key]), record);

  const setPath = (record: UnknownRecord, path: string, value: unknown): void => {
    const keys = path.split(".");
    let target: UnknownRecord = record;
    for (const key of keys.slice(0, -1)) {
      if (!target[key] || typeof target[key] !== "object") target[key] = {};
      target = target[key] as UnknownRecord;
    }
    target[keys[keys.length - 1]] = value;
  };

  const findSection = (sectionId: string): UnknownRecord | undefined =>
    (payload().sections || []).find((section: UnknownRecord) => section.section_id === sectionId);

  const findComponent = (componentId: string): { section: UnknownRecord; component: UnknownRecord; index: number } | null => {
    for (const section of payload().sections || []) {
      const index = (section.components || []).findIndex(
        (component: UnknownRecord) => component.component_id === componentId,
      );
      if (index >= 0) return { section, component: section.components[index], index };
    }
    return null;
  };

  const addFieldToSection = (type: string): void => {
    const field = defaultField(type, locale);
    payload().fields = [...(payload().fields || []), field];
    const sectionId = state.selectedSectionId || (payload().sections || [])[0]?.section_id;
    const section = sectionId ? findSection(String(sectionId)) : undefined;
    if (section) {
      section.components = [
        ...(section.components || []),
        { component_id: uid("c"), type: "field", field_id: field.field_id, span: 1 },
      ];
    }
    state.selectedFieldId = field.field_id;
    commit();
  };

  const removeField = (fieldId: string): void => {
    payload().fields = (payload().fields || []).filter((field: UnknownRecord) => field.field_id !== fieldId);
    for (const section of payload().sections || []) {
      section.components = (section.components || []).filter(
        (component: UnknownRecord) => component.field_id !== fieldId,
      );
    }
    if (state.selectedFieldId === fieldId) state.selectedFieldId = null;
    commit();
  };

  const selectedField = (): UnknownRecord | undefined =>
    (payload().fields || []).find((field: UnknownRecord) => field.field_id === state.selectedFieldId);

  const handlePropertyChange = (element: HTMLInputElement | HTMLSelectElement): void => {
    const path = element.dataset.fp;
    const field = selectedField();
    if (!path || !field) return;
    let value: unknown;
    if (element instanceof HTMLInputElement && element.type === "checkbox") value = element.checked;
    else if (path === "options.raw") {
      value = element.value
        .split(",")
        .map((pair) => pair.trim())
        .filter(Boolean)
        .map((pair, index) => {
          const [id, ...rest] = pair.split(":");
          return { option_id: id.trim() || `option_${index + 1}`, label: { en: rest.join(":").trim() || id.trim() } };
        });
      element.dataset.fp = "options";
    } else if (path === "precision") value = element.value === "" ? null : Number(element.value);
    else if (path === "validation.min" || path === "validation.max") {
      value = element.value === "" ? undefined : Number(element.value);
      if (value === undefined) {
        const validation = { ...(field.validation || {}) };
        delete validation[path.split(".")[1]];
        field.validation = validation;
        commit();
        return;
      }
    } else if (path === "required") value = element instanceof HTMLInputElement ? element.checked : Boolean(element.value);
    else value = element.value;
    setPath(field as UnknownRecord, path, value);
    if (path === "type") {
      const type = String(value);
      delete field.formula_id;
      delete field.binding;
      delete field.options;
      delete field.currency;
      if (type === "formula") {
        field.formula_id = field.field_id;
        field.result_type = "number";
      }
      if (type === "engine") field.binding = { source: "project", field: "name" };
      if (type === "select") field.options = [{ option_id: "option_1", label: { en: "Option 1" } }];
      if (type === "currency") field.currency = "USD";
      if (type === "quantity") field.unit = "m3";
      if (type === "duration") field.unit = "day";
    }
    if (path === "binding.source") {
      const source = state.bindings.find((entry) => entry.source === element.value);
      field.binding = { source: element.value, field: source?.fields?.[0]?.field || "" };
    }
    commit();
  };

  const onTransitionClick = (action: string): void => {
    if (action === "return" || action === "reject") {
      state.modal = { kind: "reason", action };
      render();
      return;
    }
    void transition(action);
  };

  root.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const closest = (selector: string): HTMLElement | null => target.closest<HTMLElement>(selector);
    if (closest("[data-fb-close]")) {
      close();
      return;
    }
    if (closest("[data-fb-modal-close]") || closest("[data-fb-modal-backdrop]") === target) {
      state.modal = null;
      render();
      return;
    }
    const tabNode = closest("[data-fb-tab]");
    if (tabNode) {
      state.tab = tabNode.dataset.fbTab as FormTab;
      if (state.tab === "library") void refreshLibrary();
      if (state.tab === "reports" && !state.submission) void refreshLibrary();
      render();
      return;
    }
    const back = closest("[data-fb-back]");
    if (back) {
      state.submission = null;
      state.tab = state.tab === "reports" ? "reports" : "library";
      state.printHtml = "";
      render();
      return;
    }
    // Card actions must win over the card's open handler; the buttons live
    // inside the same card element that carries [data-fb-open].
    const copy = closest("[data-fb-copy]");
    if (copy?.dataset.fbCopy) {
      event.stopPropagation();
      void copyTemplate("organization", copy.dataset.fbCopy);
      return;
    }
    const promote = closest("[data-fb-promote]");
    if (promote?.dataset.fbPromote) {
      event.stopPropagation();
      void promoteTemplate(promote.dataset.fbPromote);
      return;
    }
    const open = closest("[data-fb-open]");
    if (open?.dataset.fbOpen) {
      void loadTemplate((open.dataset.fbLibrary || "project") as Library, open.dataset.fbOpen);
      return;
    }
    if (closest("[data-fb-assistant]")) {
      void createAssistantDraft();
      return;
    }
    const newTemplate = closest("[data-fb-new]");
    if (newTemplate) {
      state.modal = { kind: "new-template", library: (newTemplate.dataset.fbNew || "project") as Library };
      render();
      return;
    }
    if (closest("[data-fb-save]")) {
      void saveTemplate(false);
      return;
    }
    if (closest("[data-fb-validate]")) {
      void validateDraft();
      return;
    }
    if (closest("[data-fb-publish]")) {
      state.modal = { kind: "publish" };
      render();
      return;
    }
    if (closest("[data-fb-deprecate]")) {
      void deprecateTemplate();
      return;
    }
    const designTab = closest("[data-fb-design-tab]");
    if (designTab) {
      state.designTab = designTab.dataset.fbDesignTab as DesignTab;
      state.diff = null;
      render();
      return;
    }
    if (closest("[data-fb-undo]")) {
      const previous = state.undo.pop();
      if (previous && state.template) {
        state.redo.push(JSON.stringify(state.template.payload));
        state.template.payload = JSON.parse(previous);
        commit();
      }
      return;
    }
    if (closest("[data-fb-redo]")) {
      const next = state.redo.pop();
      if (next && state.template) {
        state.undo.push(JSON.stringify(state.template.payload));
        state.template.payload = JSON.parse(next);
        commit();
      }
      return;
    }
    const addField = closest("[data-fb-add-field]");
    if (addField?.dataset.fbAddField) {
      addFieldToSection(addField.dataset.fbAddField);
      return;
    }
    if (closest("[data-fb-add-section]")) {
      const id = uid("section");
      payload().sections = [...(payload().sections || []), { section_id: id, title: { [localeKey(locale)]: id }, columns: 2, components: [] }];
      state.selectedSectionId = id;
      state.selectedFieldId = null;
      commit();
      return;
    }
    const deleteSection = closest("[data-fb-delete-section]");
    if (deleteSection?.dataset.fbDeleteSection) {
      payload().sections = (payload().sections || []).filter(
        (section: UnknownRecord) => section.section_id !== deleteSection.dataset.fbDeleteSection,
      );
      commit();
      return;
    }
    const selectSection = closest("[data-fb-select-section]");
    if (selectSection?.dataset.fbSelectSection && !closest("[data-fb-delete-section]")) {
      state.selectedSectionId = selectSection.dataset.fbSelectSection;
      state.selectedFieldId = null;
    }
    const selectField = closest("[data-fb-select-field]");
    if (selectField?.dataset.fbSelectField) {
      state.selectedFieldId = selectField.dataset.fbSelectField;
      render();
      return;
    }
    const deleteField = closest("[data-fb-delete-field]");
    if (deleteField?.dataset.fbDeleteField) {
      removeField(deleteField.dataset.fbDeleteField);
      return;
    }
    const deleteComponent = closest("[data-fb-delete-component]");
    if (deleteComponent?.dataset.fbDeleteComponent) {
      const found = findComponent(deleteComponent.dataset.fbDeleteComponent);
      if (found) {
        found.section.components = found.section.components.filter(
          (component: UnknownRecord) => component.component_id !== deleteComponent.dataset.fbDeleteComponent,
        );
        commit();
      }
      return;
    }
    const moveComponent = closest("[data-fb-move-component]");
    if (moveComponent?.dataset.fbMoveComponent) {
      const found = findComponent(moveComponent.dataset.fbMoveComponent);
      if (found) {
        const direction = Number(moveComponent.dataset.fbDirection || "0");
        const next = found.index + direction;
        if (next >= 0 && next < found.section.components.length) {
          const [component] = found.section.components.splice(found.index, 1);
          found.section.components.splice(next, 0, component);
          commit();
        }
      }
      return;
    }
    const addComponent = closest("[data-fb-add-component]");
    if (addComponent?.dataset.fbAddComponent) {
      state.modal = { kind: "add-component", sectionId: addComponent.dataset.fbAddComponent };
      render();
      return;
    }
    const placeExisting = closest("[data-fb-place-existing]");
    if (placeExisting?.dataset.fbPlaceExisting && state.modal?.kind === "add-component") {
      const [kind, id] = placeExisting.dataset.fbPlaceExisting.split(":");
      const section = findSection(state.modal.sectionId);
      if (section) {
        section.components = [...(section.components || []), { component_id: uid("c"), type: kind, [`${kind}_id`]: id, ...(kind === "field" ? { span: 1 } : {}) }];
        state.modal = null;
        commit();
      }
      return;
    }
    const placeField = closest("[data-fb-place-field]");
    if (placeField?.dataset.fbPlaceField) {
      const section = findSection(state.selectedSectionId || String((payload().sections || [])[0]?.section_id || ""));
      if (section) {
        section.components = [...(section.components || []), { component_id: uid("c"), type: "field", field_id: placeField.dataset.fbPlaceField, span: 1 }];
        commit();
      }
      return;
    }
    const placeComponent = closest("[data-fb-place-component]");
    if (placeComponent?.dataset.fbPlaceComponent) {
      state.modal = { kind: "add-component", sectionId: state.selectedSectionId || String((payload().sections || [])[0]?.section_id || "") };
      render();
      return;
    }
    if (closest("[data-fb-add-table]")) {
      const id = uid("table");
      payload().tables = [
        ...(payload().tables || []),
        {
          table_id: id,
          label: { [localeKey(locale)]: id },
          columns: [
            { column_id: "item", type: "text", label: { en: "Item" }, aggregate: "none", width: 220 },
            { column_id: "qty", type: "quantity", label: { en: "Quantity" }, aggregate: "sum", width: 120, unit: "m3" },
          ],
          repeat_header: true,
        },
      ];
      state.selectedTableId = id;
      commit();
      return;
    }
    const selectTable = closest("[data-fb-select-table]");
    if (selectTable?.dataset.fbSelectTable) {
      state.selectedTableId = selectTable.dataset.fbSelectTable;
      state.designTab = "tables";
      render();
      return;
    }
    const deleteTable = closest("[data-fb-delete-table]");
    if (deleteTable?.dataset.fbDeleteTable) {
      payload().tables = (payload().tables || []).filter((table: UnknownRecord) => table.table_id !== deleteTable.dataset.fbDeleteTable);
      for (const section of payload().sections || []) {
        section.components = (section.components || []).filter((component: UnknownRecord) => component.table_id !== deleteTable.dataset.fbDeleteTable);
      }
      state.selectedTableId = null;
      commit();
      return;
    }
    if (closest("[data-fb-add-column]")) {
      const table = (payload().tables || []).find((item: UnknownRecord) => item.table_id === state.selectedTableId);
      if (table) {
        const columnId = uid("col");
        table.columns = [...(table.columns || []), { column_id: columnId, type: "text", label: { en: columnId }, aggregate: "none" }];
        commit();
      }
      return;
    }
    const deleteColumn = closest("[data-fb-delete-column]");
    if (deleteColumn?.dataset.fbDeleteColumn) {
      const table = (payload().tables || []).find((item: UnknownRecord) => item.table_id === state.selectedTableId);
      if (table) {
        table.columns.splice(Number(deleteColumn.dataset.fbDeleteColumn), 1);
        commit();
      }
      return;
    }
    if (closest("[data-fb-add-formula]")) {
      const id = uid("formula");
      payload().formulas = [...(payload().formulas || []), { formula_id: id, expression: "1", result_type: "number", authority: "PROJECT-CONFIGURED", version: "1" }];
      state.selectedFormulaId = id;
      commit();
      return;
    }
    const selectFormula = closest("[data-fb-select-formula]");
    if (selectFormula?.dataset.fbSelectFormula) {
      state.selectedFormulaId = selectFormula.dataset.fbSelectFormula;
      state.formulaTest = null;
      render();
      return;
    }
    const deleteFormula = closest("[data-fb-delete-formula]");
    if (deleteFormula?.dataset.fbDeleteFormula) {
      payload().formulas = (payload().formulas || []).filter((formula: UnknownRecord) => formula.formula_id !== deleteFormula.dataset.fbDeleteFormula);
      for (const field of payload().fields || []) {
        if (field.type === "formula" && field.formula_id === deleteFormula.dataset.fbDeleteFormula) removeField(field.field_id);
      }
      state.selectedFormulaId = null;
      commit();
      return;
    }
    if (closest("[data-fb-test-formula]")) {
      void testFormula();
      return;
    }
    if (closest("[data-fb-add-chart]")) {
      const id = uid("chart");
      const table = (payload().tables || [])[0];
      payload().charts = [
        ...(payload().charts || []),
        {
          chart_id: id,
          chart_type: "column",
          title: { [localeKey(locale)]: id },
          source: { kind: "table", table_id: table?.table_id || "", category_column: table?.columns?.[0]?.column_id || "" },
          series: (table?.columns || []).filter((column: UnknownRecord) => column.aggregate === "sum").slice(0, 2).map((column: UnknownRecord) => ({ column_id: column.column_id })),
          show_legend: true,
        },
      ];
      state.selectedChartId = id;
      commit();
      return;
    }
    const selectChart = closest("[data-fb-select-chart]");
    if (selectChart?.dataset.fbSelectChart) {
      state.selectedChartId = selectChart.dataset.fbSelectChart;
      state.designTab = "charts";
      render();
      return;
    }
    const deleteChart = closest("[data-fb-delete-chart]");
    if (deleteChart?.dataset.fbDeleteChart) {
      payload().charts = (payload().charts || []).filter((chart: UnknownRecord) => chart.chart_id !== deleteChart.dataset.fbDeleteChart);
      for (const section of payload().sections || []) {
        section.components = (section.components || []).filter((component: UnknownRecord) => component.chart_id !== deleteChart.dataset.fbDeleteChart);
      }
      state.selectedChartId = null;
      commit();
      return;
    }
    if (closest("[data-fb-diff]")) {
      state.modal = { kind: "diff" };
      render();
      return;
    }
    const restoreVersion = closest("[data-fb-restore-version]");
    if (restoreVersion?.dataset.fbRestoreVersion && state.template) {
      const version = state.versions.find((item) => Number(item.version) === Number(restoreVersion.dataset.fbRestoreVersion));
      if (version) {
        state.template.payload = deepClone(version.payload);
        state.validationIssues = [];
        setStatus(tr(locale, "restore"), "ok");
        commit();
      }
      return;
    }
    if (closest("[data-fb-new-report]")) {
      state.modal = { kind: "new-report" };
      render();
      return;
    }
    const openReport = closest("[data-fb-open-report]");
    if (openReport?.dataset.fbOpenReport) {
      void loadSubmission(openReport.dataset.fbOpenReport);
      return;
    }
    const filter = closest("[data-fb-filter]");
    if (filter?.dataset.fbFilter) {
      state.reportFilter = filter.dataset.fbFilter as "all" | "mine";
      render();
      return;
    }
    if (closest("[data-fb-save-report]")) {
      void saveSubmission();
      return;
    }
    const transitionNode = closest("[data-fb-transition]");
    if (transitionNode?.dataset.fbTransition) {
      onTransitionClick(transitionNode.dataset.fbTransition);
      return;
    }
    if (closest("[data-fb-print-html]")) {
      void loadPrint();
      return;
    }
    if (closest("[data-fb-export]")) {
      void exportWorkbook();
      return;
    }
    if (closest("[data-fb-print-frame]")) {
      const frame = byId<HTMLIFrameElement>(root, "[data-fb-print-frame-src]");
      frame?.contentWindow?.focus();
      frame?.contentWindow?.print();
      return;
    }
    if (closest("[data-fb-print-refresh]")) {
      void loadPrint();
      return;
    }
    const addRow = closest("[data-fb-add-row]");
    if (addRow?.dataset.fbAddRow) {
      const tableId = addRow.dataset.fbAddRow;
      const rows = tableRows(state.draftTables, tableId);
      state.draftTables[tableId] = [...rows, { row_id: uid("row"), values: {} }];
      scheduleEvaluate();
      render();
      return;
    }
    const removeRow = closest("[data-fb-remove-row]");
    if (removeRow?.dataset.fbRemoveRow) {
      const [tableId, rowIndex] = removeRow.dataset.fbRemoveRow.split("|");
      const rows = tableRows(state.draftTables, tableId);
      rows.splice(Number(rowIndex), 1);
      state.draftTables[tableId] = rows;
      scheduleEvaluate();
      render();
      return;
    }
  });

  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (state.modal) {
        state.modal = null;
        render();
      } else if (state.submission) {
        state.submission = null;
        render();
      } else {
        close();
      }
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z" && state.template) {
      const target = event.target as HTMLElement;
      if (target.matches("input, textarea, select")) return;
      event.preventDefault();
      const previous = state.undo.pop();
      if (previous && state.template) {
        state.redo.push(JSON.stringify(state.template.payload));
        state.template.payload = JSON.parse(previous);
        commit();
      }
    }
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (target.matches("[data-fp]")) {
      handlePropertyChange(target);
      return;
    }
    if (target.matches("[data-fb-selected-field]")) {
      handlePropertyChange(target);
      return;
    }
    const tableProp = target.dataset.fbTableProp;
    if (tableProp) {
      const table = (payload().tables || []).find((item: UnknownRecord) => item.table_id === state.selectedTableId);
      if (table) {
        setPath(table, tableProp, target instanceof HTMLInputElement && target.type === "checkbox" ? target.checked : target.value);
        commit();
      }
      return;
    }
    const columnProp = target.dataset.fbColumnProp;
    if (columnProp) {
      const [indexRaw, path] = columnProp.split(":");
      const table = (payload().tables || []).find((item: UnknownRecord) => item.table_id === state.selectedTableId);
      const column = table?.columns?.[Number(indexRaw)];
      if (column) {
        setPath(column, path, target.value);
        commit();
      }
      return;
    }
    const columnId = target.dataset.fbColumnId;
    if (columnId != null) {
      const table = (payload().tables || []).find((item: UnknownRecord) => item.table_id === state.selectedTableId);
      const column = table?.columns?.[Number(columnId)];
      if (column) {
        column.column_id = target.value;
        commit();
      }
      return;
    }
    const formulaProp = target.dataset.fbFormulaProp;
    if (formulaProp) {
      const formula = (payload().formulas || []).find((item: UnknownRecord) => item.formula_id === state.selectedFormulaId);
      if (formula) {
        setPath(formula, formulaProp, formulaProp === "precision" ? Number(target.value) : target.value);
        commit();
      }
      return;
    }
    const chartProp = target.dataset.fbChartProp;
    if (chartProp) {
      const chart = (payload().charts || []).find((item: UnknownRecord) => item.chart_id === state.selectedChartId);
      if (chart) {
        setPath(chart, chartProp, target.value);
        commit();
      }
      return;
    }
    const chartSeries = target.dataset.fbChartSeries;
    if (chartSeries) {
      const chart = (payload().charts || []).find((item: UnknownRecord) => item.chart_id === state.selectedChartId);
      if (chart) {
        const existing = new Set((chart.series || []).map((item: UnknownRecord) => String(item.column_id)));
        if (target instanceof HTMLInputElement && target.checked) existing.add(chartSeries);
        else existing.delete(chartSeries);
        chart.series = [...existing].map((columnId) => ({ column_id: columnId }));
        commit();
      }
      return;
    }
    const workflowProp = target.dataset.fbWorkflow;
    if (workflowProp) {
      const workflow = (payload().workflow || {}) as UnknownRecord;
      if (workflowProp === "reviewers" || workflowProp === "approvers") {
        workflow[workflowProp] = target.value.split(",").map((value) => value.trim()).filter(Boolean);
      } else if (workflowProp === "approval_steps") {
        workflow.approval_steps = target.value
          .split(",")
          .map((pair) => pair.trim())
          .filter(Boolean)
          .map((pair, index) => {
            const [stepId, role] = pair.split(":");
            return { step_id: stepId?.trim() || `step_${index + 1}`, role: role?.trim() || "project_admin" };
          });
      } else if (target instanceof HTMLInputElement && target.type === "checkbox") {
        workflow[workflowProp] = target.checked;
      } else {
        workflow[workflowProp] = target.value;
      }
      payload().workflow = workflow;
      commit();
      return;
    }
    const pageProp = target.dataset.fbPage;
    if (pageProp) {
      const page = (payload().page || {}) as UnknownRecord;
      setPath(page, pageProp, pageProp === "paper" || pageProp === "orientation" ? target.value : Number(target.value));
      payload().page = page;
      commit();
      return;
    }
    const headerProp = target.dataset.fbHeader;
    if (headerProp) {
      const header = (payload().header || {}) as UnknownRecord;
      setPath(header, headerProp, target.value);
      payload().header = header;
      commit();
      return;
    }
    const footerProp = target.dataset.fbFooter;
    if (footerProp) {
      const footer = (payload().footer || {}) as UnknownRecord;
      if (footerProp === "show_page_numbers" || footerProp === "approval_block") footer[footerProp] = (target as HTMLInputElement).checked;
      else setPath(footer, footerProp, target.value);
      payload().footer = footer;
      commit();
      return;
    }
    const fieldId = target.dataset.fbField;
    if (fieldId) {
      if (target instanceof HTMLInputElement && target.type === "checkbox") {
        state.draftValues[fieldId] = bindFieldValue({ type: "boolean" }, String(target.checked));
      } else {
        const field = ((state.submission?.template?.fields || []) as UnknownRecord[]).find(
          (item) => item.field_id === fieldId,
        );
        state.draftValues[fieldId] = bindFieldValue(field || { type: "text" }, target.value);
      }
      scheduleEvaluate();
      return;
    }
    const cell = target.dataset.fbCell;
    if (cell) {
      const [tableId, rowIndex, columnId] = cell.split("|");
      const table = ((state.submission?.template?.tables || []) as UnknownRecord[]).find(
        (item) => item.table_id === tableId,
      );
      const column = ((table?.columns || []) as UnknownRecord[]).find((item) => item.column_id === columnId) || { type: "text" };
      const rows = tableRows(state.draftTables, tableId);
      const row = rows[Number(rowIndex)];
      if (row) {
        row.values = { ...(row.values || {}), [columnId]: bindFieldValue(column, target.value) };
        state.draftTables[tableId] = rows;
        scheduleEvaluate();
      }
      return;
    }
    const upload = target.dataset.fbUpload;
    if (upload && target instanceof HTMLInputElement && target.files?.[0]) {
      const file = target.files[0];
      void (async () => {
        try {
          const response = await fetch(new URL(`${base}/assets`, window.location.origin), {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": file.type, "X-Filename": file.name },
            body: file,
          });
          const payloadJson = await response.json();
          if (!response.ok) throw new FormUiError(payloadJson.code || "UPLOAD_FAILED", response.status);
          state.draftValues[upload] = { type: "file", asset_id: payloadJson.asset_id };
          setStatus(`${tr(locale, "saved")}: ${payloadJson.asset_id}`, "ok");
          render();
        } catch (error) {
          reportError(error);
        }
      })();
    }
  });

  root.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (target.matches("[data-fb-search]")) {
      state.search = target.value;
      render();
      const input = byId<HTMLInputElement>(root, "[data-fb-search]");
      input?.focus();
      input?.setSelectionRange(input.value.length, input.value.length);
    }
    if (target.matches("[data-fb-chart-prop], [data-fb-chart-series]")) {
      // handled on change to avoid rerender on every keystroke
    }
  });

  root.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.target as HTMLFormElement;
    const kind = form.dataset.fbModal;
    if (kind === "new-template") void createTemplate(form);
    else if (kind === "new-report") void createReport(form);
    else if (kind === "publish") {
      const data = new FormData(form);
      void publishTemplate(String(data.get("reason") || ""));
    } else if (kind === "reason") {
      const data = new FormData(form);
      void transition(String(form.dataset.action || ""), String(data.get("reason") || ""));
    } else if (kind === "diff") {
      const data = new FormData(form);
      const from = Number(data.get("from"));
      const to = Number(data.get("to"));
      void (async () => {
        try {
          const diff = await api<UnknownRecord>(`${templatePath()}/diff?from=${from}&to=${to}`);
          state.diff = diff;
          state.modal = null;
          state.designTab = "versions";
          render();
        } catch (error) {
          reportError(error);
        }
      })();
    }
  });

  const draggable = (target: HTMLElement, selector: string): HTMLElement | null =>
    target.closest<HTMLElement>(selector);
  root.addEventListener("dragstart", (event) => {
    const target = event.target as HTMLElement;
    const section = draggable(target, "[data-fb-section-drag]");
    const component = draggable(target, "[data-fb-component-drag]");
    if (component?.dataset.fbComponentDrag) {
      state.draggedComponent = component.dataset.fbComponentDrag;
      event.dataTransfer?.setData("text/plain", `component:${state.draggedComponent}`);
    } else if (section?.dataset.fbSectionDrag) {
      state.draggedSection = section.dataset.fbSectionDrag;
      event.dataTransfer?.setData("text/plain", `section:${state.draggedSection}`);
    }
  });
  root.addEventListener("dragover", (event) => {
    const zone = draggable(event.target as HTMLElement, "[data-fb-drop-section]");
    if (zone) event.preventDefault();
  });
  root.addEventListener("drop", (event) => {
    event.preventDefault();
    const zone = draggable(event.target as HTMLElement, "[data-fb-drop-section]");
    const targetSectionId = zone?.dataset.fbDropSection;
    if (!targetSectionId) return;
    if (state.draggedComponent) {
      const found = findComponent(state.draggedComponent);
      const targetSection = findSection(targetSectionId);
      if (found && targetSection && found.section.section_id !== targetSectionId) {
        found.section.components.splice(found.index, 1);
        targetSection.components = [...(targetSection.components || []), found.component];
        commit();
      }
    } else if (state.draggedSection && state.draggedSection !== targetSectionId) {
      const sections = payload().sections || [];
      const from = sections.findIndex((section: UnknownRecord) => section.section_id === state.draggedSection);
      const to = sections.findIndex((section: UnknownRecord) => section.section_id === targetSectionId);
      if (from >= 0 && to >= 0) {
        const [moved] = sections.splice(from, 1);
        sections.splice(to, 0, moved);
        commit();
      }
    }
    state.draggedComponent = null;
    state.draggedSection = null;
  });

  const close = (): void => {
    if (closed) return;
    closed = true;
    if (evaluateTimer) clearTimeout(evaluateTimer);
    if (saveTimer) clearTimeout(saveTimer);
    root.remove();
    options.onClose?.();
  };

  const refresh = async (): Promise<void> => {
    await refreshLibrary();
  };

  render();
  void refresh();

  return { close, isOpen: () => !closed };
}
