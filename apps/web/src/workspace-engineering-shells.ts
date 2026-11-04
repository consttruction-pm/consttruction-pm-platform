import { translateWorkspaceUiText } from "./workspace-localization.js";

export type EngineeringShellWindowId =
  | "engineering-analysis"
  | "project-watchdog"
  | "scenario-lab"
  | "optimization-studio"
  | "project-quality"
  | "construction-productivity"
  | "data-reconciliation"
  | "portfolio-capacity"
  | "automation-center"
  | "engineering-standards"
  | "project-templates"
  | "decision-register"
  | "deadline-monitor"
  | "data-quality"
  | "recovery-center"
  | "command-dictionaries";

type Bilingual = readonly [string, string];

type EngineeringShellDefinition = {
  id: EngineeringShellWindowId;
  title: Bilingual;
  description: Bilingual;
  viewTitle: Bilingual;
  columns: readonly Bilingual[];
  metrics: readonly Bilingual[];
  methods: readonly Bilingual[];
  inputs: readonly Bilingual[];
  outputs: readonly Bilingual[];
  details: readonly { id: string; label: Bilingual }[];
};

export const ENGINEERING_SHELLS: readonly EngineeringShellDefinition[] = [
  {
    id: "engineering-analysis",
    title: ["Engineering Analysis & Root Cause", "تحلیل مهندسی و علت ریشه‌ای"],
    description: ["Trace project conditions to their evidence, rules and contributing causes.", "شرایط پروژه را تا شواهد، قواعد و عوامل ایجادکننده ردیابی کنید."],
    viewTitle: ["Findings and cause register", "فهرست یافته‌ها و علل"],
    columns: [["Finding ID", "شناسه یافته"], ["Affected object", "موضوع متأثر"], ["Condition", "شرایط"], ["Cause status", "وضعیت علت"], ["Evidence", "شواهد"]],
    metrics: [["Findings", "یافته‌ها"], ["Confirmed causes", "علل تأییدشده"], ["Open investigations", "بررسی‌های باز"], ["Rule set", "مجموعه قواعد"]],
    methods: [["Forward and backward rule chaining", "زنجیره‌سازی قواعد رو به جلو و عقب"], ["Dependency and causal graph traversal", "پیمایش گراف وابستگی و علیت"], ["Fault isolation and cause trees", "جداسازی خطا و درخت علل"], ["Constraint propagation and counterfactual checks", "انتشار محدودیت و آزمون خلاف‌واقع"]],
    inputs: [["Revision-bound project facts", "واقعیت‌های پروژه با نسخه مشخص"], ["Versioned engineering rules", "قواعد مهندسی نسخه‌بندی‌شده"], ["Source records and evidence links", "رکوردهای منبع و پیوند شواهد"]],
    outputs: [["Evidence trace and rule path", "رد شواهد و مسیر قواعد"], ["Confirmed causes vs possible contributors", "علل تأییدشده در برابر عوامل احتمالی"], ["Remedy alternatives and missing evidence", "راهکارهای جایگزین و شواهد مفقود"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "methods", label: ["Methods", "روش‌ها"] }, { id: "inputs", label: ["Inputs", "ورودی‌ها"] }, { id: "outputs", label: ["Outputs", "خروجی‌ها"] }, { id: "evidence", label: ["Evidence", "شواهد"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "project-watchdog",
    title: ["Project Watchdog", "ناظر هوشمند پروژه"],
    description: ["Monitor project events, thresholds and trends; explain every alert.", "رویدادها، آستانه‌ها و روندهای پروژه را پایش و هر هشدار را مستند کنید."],
    viewTitle: ["Monitoring rules and alerts", "قواعد پایش و هشدارها"],
    columns: [["Monitor", "پایشگر"], ["Scope", "دامنه"], ["Rule / threshold", "قاعده / آستانه"], ["Severity", "شدت"], ["Last detection", "آخرین تشخیص"]],
    metrics: [["Active monitors", "پایشگرهای فعال"], ["Open alerts", "هشدارهای باز"], ["Escalations", "ارجاعات"], ["Last event", "آخرین رویداد"]],
    methods: [["Event and scheduled evaluation", "ارزیابی رویدادمحور و زمان‌بندی‌شده"], ["Threshold bands and rate-of-change", "بازه آستانه و نرخ تغییر"], ["Moving average, EWMA and CUSUM", "میانگین متحرک، EWMA و CUSUM"], ["Hysteresis, debounce and deduplication", "هیسترزیس، حذف جهش و تکرارزدایی"]],
    inputs: [["Domain events and revision snapshots", "رویدادهای دامنه و تصویر نسخه"], ["Approved monitor rules", "قواعد پایش تأییدشده"], ["Alert owners and escalation policy", "مسئول هشدار و سیاست ارجاع"]],
    outputs: [["Traceable alert and detection rule", "هشدار قابل ردیابی و قاعده تشخیص"], ["Acknowledgement and escalation history", "تاریخچه تأیید و ارجاع"], ["Corrective-action proposal", "پیشنهاد اقدام اصلاحی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "rules", label: ["Monitor rules", "قواعد پایش"] }, { id: "thresholds", label: ["Thresholds", "آستانه‌ها"] }, { id: "escalation", label: ["Escalation", "ارجاع"] }, { id: "alerts", label: ["Alert history", "تاریخچه هشدار"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "scenario-lab",
    title: ["Scenario Lab & Simulation", "آزمایشگاه سناریو و شبیه‌سازی"],
    description: ["Explore isolated, revision-bound what-if scenarios without changing the approved project.", "سناریوهای مستقل و وابسته به نسخه را بدون تغییر پروژه مصوب بررسی کنید."],
    viewTitle: ["Scenario register and comparisons", "فهرست و مقایسه سناریوها"],
    columns: [["Scenario", "سناریو"], ["Source revision", "نسخه مبنا"], ["Changed variables", "متغیرهای تغییرکرده"], ["Run state", "وضعیت اجرا"], ["Comparison", "مقایسه"]],
    metrics: [["Scenarios", "سناریوها"], ["Completed runs", "اجراهای کامل"], ["Pending reviews", "بازبینی‌های معوق"], ["Source revision", "نسخه منبع"]],
    methods: [["Immutable snapshot and scenario fork", "تصویر تغییرناپذیر و انشعاب سناریو"], ["Single and multi-factor what-if analysis", "تحلیل تک‌عاملی و چندعاملی چه می‌شود اگر"], ["Parameter sweeps and boundary scenarios", "پویش پارامتر و سناریوی مرزی"], ["Sensitivity matrices and variance waterfalls", "ماتریس حساسیت و آبشار انحراف"]],
    inputs: [["Source project revision and calculation context", "نسخه پروژه و زمینه محاسبات"], ["Scenario assumptions and changed values", "فرض‌ها و مقادیر تغییرکرده سناریو"], ["Units, calendars and resource constraints", "واحدها، تقویم‌ها و محدودیت منابع"]],
    outputs: [["Scenario result and reproducible run ID", "نتیجه سناریو و شناسه اجرای بازتولیدپذیر"], ["Schedule, cost and resource deltas", "اختلاف زمان، هزینه و منابع"], ["Promotion proposal for separate approval", "پیشنهاد اعمال با تأیید مستقل"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "source", label: ["Source snapshot", "تصویر منبع"] }, { id: "inputs", label: ["Assumptions", "فرض‌ها"] }, { id: "results", label: ["Results", "نتایج"] }, { id: "comparison", label: ["Comparison", "مقایسه"] }, { id: "history", label: ["Run history", "تاریخچه اجرا"] }],
  },
  {
    id: "optimization-studio",
    title: ["Optimization Studio", "استودیوی بهینه‌سازی"],
    description: ["Compare feasible schedule, resource and cost solutions against explicit objectives.", "راه‌حل‌های شدنی زمان، منابع و هزینه را بر اساس اهداف شفاف مقایسه کنید."],
    viewTitle: ["Optimization problems and candidate solutions", "مسائل بهینه‌سازی و راه‌حل‌های پیشنهادی"],
    columns: [["Problem", "مسئله"], ["Objective", "هدف"], ["Constraints", "محدودیت‌ها"], ["Feasibility", "شدنی‌بودن"], ["Best candidate", "بهترین گزینه"]],
    metrics: [["Problems", "مسائل"], ["Feasible solutions", "راه‌حل‌های شدنی"], ["Active constraints", "محدودیت‌های فعال"], ["Compute status", "وضعیت پردازش"]],
    methods: [["Linear and mixed-integer programming", "برنامه‌ریزی خطی و عددصحیح مختلط"], ["Constraint programming and branch-and-bound", "برنامه‌ریزی محدودیت و شاخه‌وکران"], ["Greedy and local-search heuristics", "ابتکاری حریصانه و جست‌وجوی محلی"], ["Tabu, simulated annealing and Pareto analysis", "جست‌وجوی ممنوعه، تبرید شبیه‌سازی‌شده و تحلیل پارتو"]],
    inputs: [["Decision variables and objective weights", "متغیرهای تصمیم و وزن اهداف"], ["Resource capacity and calendars", "ظرفیت منابع و تقویم‌ها"], ["Schedule, cost and contractual constraints", "محدودیت‌های زمان‌بندی، هزینه و قرارداد"]],
    outputs: [["Feasible candidate solutions", "راه‌حل‌های شدنی پیشنهادی"], ["Objective values and constraint violations", "مقادیر اهداف و نقض محدودیت‌ها"], ["Trade-offs, bounds and solver provenance", "مصالحه‌ها، کران‌ها و شناسنامه حل‌گر"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "objectives", label: ["Objectives", "اهداف"] }, { id: "variables", label: ["Variables", "متغیرها"] }, { id: "constraints", label: ["Constraints", "محدودیت‌ها"] }, { id: "solutions", label: ["Solutions", "راه‌حل‌ها"] }, { id: "history", label: ["Run history", "تاریخچه اجرا"] }],
  },
  {
    id: "project-quality",
    title: ["Schedule & Project Quality", "ممیزی کیفیت زمان‌بندی و پروژه"],
    description: ["Audit schedule logic, project data and control consistency before release.", "منطق زمان‌بندی، داده‌ها و سازگاری کنترل پروژه را پیش از انتشار ممیزی کنید."],
    viewTitle: ["Audit findings and remediation", "یافته‌های ممیزی و اصلاحات"],
    columns: [["Finding", "یافته"], ["Object", "موضوع"], ["Rule", "قاعده"], ["Severity", "شدت"], ["Resolution", "رفع اشکال"]],
    metrics: [["Findings", "یافته‌ها"], ["Critical", "بحرانی"], ["Warnings", "هشدارها"], ["Quality score", "امتیاز کیفیت"]],
    methods: [["Open ends, cycles and relationship validation", "بررسی روابط باز، چرخه‌ها و اعتبار روابط"], ["Float, constraints, lag and duration checks", "کنترل شناوری، محدودیت، وقفه و مدت"], ["Calendar, data-date and progress consistency", "سازگاری تقویم، تاریخ داده و پیشرفت"], ["Baseline, resource, cost and import audits", "ممیزی مبنا، منابع، هزینه و ورود اطلاعات"]],
    inputs: [["Authoritative schedule snapshot", "تصویر معتبر زمان‌بندی"], ["Field and relationship registry", "فهرست فیلدها و روابط"], ["Versioned quality policy pack", "بسته سیاست کیفیت نسخه‌بندی‌شده"]],
    outputs: [["Finding severity and exact object reference", "شدت یافته و ارجاع دقیق موضوع"], ["Transparent quality score breakdown", "تجزیه شفاف امتیاز کیفیت"], ["Remediation proposal and recheck", "پیشنهاد اصلاح و بازبینی مجدد"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "logic", label: ["Schedule logic", "منطق زمان‌بندی"] }, { id: "calendar", label: ["Calendars", "تقویم‌ها"] }, { id: "data", label: ["Data quality", "کیفیت داده"] }, { id: "findings", label: ["Findings", "یافته‌ها"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "construction-productivity",
    title: ["Construction Productivity", "بهره‌وری عملیات ساخت"],
    description: ["Connect quantities, production rates, crews, equipment and field performance.", "مقادیر، نرخ تولید، اکیپ‌ها، تجهیزات و عملکرد کارگاه را به هم متصل کنید."],
    viewTitle: ["Production and productivity register", "فهرست تولید و بهره‌وری"],
    columns: [["Work package", "بسته کاری"], ["Quantity / unit", "مقدار / واحد"], ["Production rate", "نرخ تولید"], ["Crew / equipment", "اکیپ / تجهیز"], ["Variance", "انحراف"]],
    metrics: [["Work packages", "بسته‌های کاری"], ["Planned output", "تولید برنامه‌ای"], ["Actual output", "تولید واقعی"], ["Productivity variance", "انحراف بهره‌وری"]],
    methods: [["Quantity and production-rate calculations", "محاسبه مقدار و نرخ تولید"], ["Earned hours and productivity variance", "ساعات کسب‌شده و انحراف بهره‌وری"], ["Crew balancing and shift output analysis", "تعادل اکیپ و تحلیل تولید شیفت"], ["Cycle-time, fleet and equipment utilization", "زمان چرخه، ناوگان و بهره‌برداری تجهیزات"], ["Line of Balance, takt and workface planning", "Line of Balance، تاکت و برنامه‌ریزی جبهه کاری"]],
    inputs: [["Measured quantities and unit rules", "مقادیر اندازه‌گیری‌شده و قواعد واحد"], ["Crew, equipment and shift definitions", "تعاریف اکیپ، تجهیزات و شیفت"], ["Daily reports, timesheets and production records", "گزارش روزانه، کارکرد و رکورد تولید"]],
    outputs: [["Required crew/equipment capacity", "ظرفیت موردنیاز اکیپ و تجهیزات"], ["Production and duration forecasts", "پیش‌بینی تولید و مدت"], ["Bottleneck and productivity variance", "گلوگاه و انحراف بهره‌وری"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "quantities", label: ["Quantities", "مقادیر"] }, { id: "crews", label: ["Crews", "اکیپ‌ها"] }, { id: "equipment", label: ["Equipment", "تجهیزات"] }, { id: "methods", label: ["Methods", "روش‌ها"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "data-reconciliation",
    title: ["Project Data Reconciliation", "تطبیق اطلاعات پروژه"],
    description: ["Reconcile source files and project domains with field-level provenance and conflict review.", "فایل‌های منبع و حوزه‌های پروژه را با شناسنامه فیلد و بررسی تعارض تطبیق دهید."],
    viewTitle: ["Source mapping and reconciliation results", "تطبیق منابع و نتایج مغایرت‌گیری"],
    columns: [["Source", "منبع"], ["Target domain", "حوزه مقصد"], ["Match method", "روش تطبیق"], ["Conflicts", "تعارض‌ها"], ["Review state", "وضعیت بازبینی"]],
    metrics: [["Sources", "منابع"], ["Matched records", "رکوردهای تطبیق‌یافته"], ["Conflicts", "تعارض‌ها"], ["Unresolved", "حل‌نشده"]],
    methods: [["Exact and composite-key matching", "تطبیق شناسه دقیق و کلید ترکیبی"], ["Edit distance and Jaro-Winkler", "فاصله ویرایشی و Jaro-Winkler"], ["Token overlap and trigram similarity", "هم‌پوشانی واژه و شباهت سه‌تایی"], ["Duplicate, source-precedence and tolerance checks", "کنترل تکرار، اولویت منبع و تلورانس"]],
    inputs: [["Immutable source file and checksum", "فایل منبع تغییرناپذیر و چکیده"], ["Canonical field and mapping registry", "فهرست فیلد و نگاشت مرجع"], ["Units, dates and source-precedence policy", "واحدها، تاریخ‌ها و سیاست اولویت منبع"]],
    outputs: [["Matched, missing and ambiguous records", "رکوردهای تطبیق، مفقود و مبهم"], ["Field-level differences and source lineage", "اختلاف فیلد و ریشه منبع"], ["Conflict-resolution proposal", "پیشنهاد رفع تعارض"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "sources", label: ["Sources", "منابع"] }, { id: "mapping", label: ["Mapping", "نگاشت"] }, { id: "matches", label: ["Matches", "تطبیق‌ها"] }, { id: "conflicts", label: ["Conflicts", "تعارض‌ها"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "portfolio-capacity",
    title: ["Portfolio Capacity", "ظرفیت سبد پروژه‌ها"],
    description: ["Review authorized cross-project demand, supply, utilization and allocation alternatives.", "تقاضا، عرضه، بهره‌برداری و گزینه‌های تخصیص بین پروژه‌های مجاز را بررسی کنید."],
    viewTitle: ["Portfolio resource demand and supply", "عرضه و تقاضای منابع سبد پروژه"],
    columns: [["Resource / role", "منبع / نقش"], ["Available capacity", "ظرفیت موجود"], ["Demand", "تقاضا"], ["Conflict", "تعارض"], ["Allocation", "تخصیص"]],
    metrics: [["Resource pools", "مخازن منابع"], ["Demand peaks", "اوج تقاضا"], ["Capacity gaps", "کمبود ظرفیت"], ["Projects in scope", "پروژه‌های مجاز"]],
    methods: [["Time-phased demand and supply", "عرضه و تقاضای زمان‌مند"], ["Skill/role and calendar matching", "تطبیق مهارت، نقش و تقویم"], ["Cross-project conflict and shortage detection", "تشخیص تعارض و کمبود بین پروژه‌ها"], ["Priority-based leveling and allocation scenarios", "تسطیح و سناریوی تخصیص مبتنی بر اولویت"]],
    inputs: [["Authorized portfolio/project scopes", "دامنه‌های مجاز سبد و پروژه"], ["Resource skills, rates and calendars", "مهارت، نرخ و تقویم منابع"], ["Time-phased demand and project priorities", "تقاضای زمان‌مند و اولویت پروژه"]],
    outputs: [["Capacity gaps and utilization profile", "کمبود ظرفیت و پروفایل بهره‌برداری"], ["Allocation alternatives and conflicts", "گزینه‌های تخصیص و تعارض‌ها"], ["Approval-bound allocation proposal", "پیشنهاد تخصیص نیازمند تأیید"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "projects", label: ["Projects", "پروژه‌ها"] }, { id: "demand", label: ["Demand", "تقاضا"] }, { id: "supply", label: ["Supply", "عرضه"] }, { id: "allocation", label: ["Allocation", "تخصیص"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "automation-center",
    title: ["Automation Center", "مرکز اتوماسیون"],
    description: ["Design governed workflows with triggers, conditions, approvals and execution history.", "گردش‌کارهای کنترل‌شده با محرک، شرط، تأیید و تاریخچه اجرا طراحی کنید."],
    viewTitle: ["Workflow catalogue and run monitor", "فهرست گردش‌کار و پایش اجرا"],
    columns: [["Workflow", "گردش‌کار"], ["Trigger", "محرک"], ["Version", "نسخه"], ["Owner", "مسئول"], ["Activation state", "وضعیت فعال‌سازی"]],
    metrics: [["Workflows", "گردش‌کارها"], ["Active", "فعال"], ["Pending approvals", "تأییدهای معوق"], ["Failed runs", "اجراهای ناموفق"]],
    methods: [["Event, schedule and threshold triggers", "محرک رویداد، زمان‌بندی و آستانه"], ["Finite-state and decision-table routing", "ماشین حالت و مسیریابی جدول تصمیم"], ["Sequential/parallel tasks and approval gates", "وظایف ترتیبی/موازی و گیت تأیید"], ["Retry, backoff, idempotency and compensation", "تلاش مجدد، مکث، تکرارپذیری و جبران"]],
    inputs: [["Versioned workflow definition", "تعریف گردش‌کار نسخه‌بندی‌شده"], ["Trigger event and execution scope", "رویداد محرک و دامنه اجرا"], ["Actors, grants and approval policies", "عامل‌ها، مجوزها و سیاست تأیید"]],
    outputs: [["Step trace and pending user tasks", "رد گام‌ها و وظایف معوق کاربر"], ["Run status, failures and retries", "وضعیت اجرا، خطاها و تلاش مجدد"], ["Compensating-action record", "رکورد اقدام جبرانی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "triggers", label: ["Triggers", "محرک‌ها"] }, { id: "steps", label: ["Steps", "گام‌ها"] }, { id: "approvals", label: ["Approvals", "تأییدها"] }, { id: "runs", label: ["Run history", "تاریخچه اجرا"] }, { id: "history", label: ["Versions", "نسخه‌ها"] }],
  },
  {
    id: "engineering-standards",
    title: ["Engineering Standards & Methods", "استانداردها و روش‌های مهندسی"],
    description: ["Govern engineering standards, clauses, methods and validated project rules.", "استانداردها، بندها، روش‌ها و قواعد معتبر پروژه را مدیریت کنید."],
    viewTitle: ["Standards and methods catalogue", "فهرست استانداردها و روش‌ها"],
    columns: [["Reference", "مرجع"], ["Discipline", "رشته"], ["Edition", "ویرایش"], ["Effective date", "تاریخ اجرا"], ["Review state", "وضعیت بازبینی"]],
    metrics: [["Sources", "منابع"], ["Current editions", "ویرایش‌های جاری"], ["Rules mapped", "قواعد نگاشت‌شده"], ["Pending reviews", "بازبینی‌های معوق"]],
    methods: [["Versioned source and clause catalogues", "فهرست نسخه‌بندی‌شده منبع و بند"], ["Applicability predicates and rule mapping", "شرط‌های کاربرد و نگاشت قواعد"], ["Conflict and supersession detection", "تشخیص تعارض و جایگزینی"], ["Review, validation and publish lifecycle", "چرخه بازبینی، اعتبارسنجی و انتشار"]],
    inputs: [["Source publisher, edition and rights", "ناشر، ویرایش و حقوق منبع"], ["Discipline, jurisdiction and effective dates", "رشته، حوزه قضایی و تاریخ اجرا"], ["Validation evidence and reviewer roles", "شواهد اعتبارسنجی و نقش بازبین"]],
    outputs: [["Applicable source/version/section", "منبع/نسخه/بند قابل کاربرد"], ["Mapped rule and applicability result", "قاعده نگاشت‌شده و نتیجه کاربرد"], ["Conflict and supersession register", "فهرست تعارض و جایگزینی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "source", label: ["Source & edition", "منبع و ویرایش"] }, { id: "applicability", label: ["Applicability", "قابلیت کاربرد"] }, { id: "rules", label: ["Rules", "قواعد"] }, { id: "review", label: ["Review & publish", "بازبینی و انتشار"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "project-templates",
    title: ["Project & Work-Method Templates", "الگوهای پروژه و روش اجرا"],
    description: ["Manage organization and project template libraries with controlled inheritance and application.", "کتابخانه الگوهای سازمانی و پروژه‌ای را با وراثت و اعمال کنترل‌شده مدیریت کنید."],
    viewTitle: ["Template libraries and catalogue", "کتابخانه‌ها و فهرست الگوها"],
    columns: [["Template", "الگو"], ["Library", "کتابخانه"], ["Version", "نسخه"], ["Scope", "دامنه"], ["Compatibility", "سازگاری"]],
    metrics: [["Templates", "الگوها"], ["Organization", "سازمانی"], ["Project-specific", "اختصاصی پروژه"], ["Pending review", "بازبینی معوق"]],
    methods: [["Versioning, inheritance and deprecation", "نسخه‌بندی، وراثت و بازنشستگی"], ["Clone/customize and template diff", "کپی/سفارشی‌سازی و اختلاف الگو"], ["Schema compatibility and migration checks", "سازگاری ساختار و کنترل مهاجرت"], ["Preview of proposed project delta", "پیش‌نمایش تغییرات پیشنهادی پروژه"]],
    inputs: [["Template library scope and owner", "دامنه و مالک کتابخانه الگو"], ["Versioned project schema and dictionaries", "ساختار نسخه‌بندی‌شده پروژه و واژه‌نامه‌ها"], ["Calendar, units and permission rules", "قواعد تقویم، واحدها و مجوزها"]],
    outputs: [["Compatible template version", "نسخه سازگار الگو"], ["Template difference and warnings", "اختلاف و هشدارهای الگو"], ["Project creation/application proposal", "پیشنهاد ایجاد یا اعمال در پروژه"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "library", label: ["Library", "کتابخانه"] }, { id: "structure", label: ["Structure", "ساختار"] }, { id: "compatibility", label: ["Compatibility", "سازگاری"] }, { id: "preview", label: ["Preview / diff", "پیش‌نمایش / اختلاف"] }, { id: "history", label: ["Versions", "نسخه‌ها"] }],
  },
  {
    id: "decision-register",
    title: ["Decision Register & Support", "دفتر ثبت و پشتیبانی تصمیم"],
    description: ["Record project decisions and compare alternatives against explicit criteria.", "تصمیم‌های پروژه را ثبت و گزینه‌ها را با معیارهای روشن مقایسه کنید."],
    viewTitle: ["Decision register and alternatives", "فهرست تصمیم‌ها و گزینه‌ها"],
    columns: [["Decision ID", "شناسه تصمیم"], ["Subject", "موضوع"], ["Owner", "مسئول"], ["Review date", "تاریخ بازبینی"], ["State", "وضعیت"]],
    metrics: [["Decisions", "تصمیم‌ها"], ["Under review", "در حال بازبینی"], ["Approved", "تأییدشده"], ["Outcome reviews", "بازبینی نتیجه"]],
    methods: [["Weighted decision matrix", "ماتریس تصمیم وزن‌دار"], ["Pairwise comparison and AHP", "مقایسه زوجی و AHP"], ["TOPSIS ranking where criteria permit", "رتبه‌بندی TOPSIS در صورت تناسب معیارها"], ["Weight and criteria sensitivity", "حساسیت وزن و معیار"]],
    inputs: [["Decision context and candidate options", "زمینه تصمیم و گزینه‌ها"], ["Comparable criteria, weights and constraints", "معیارهای قابل مقایسه، وزن‌ها و محدودیت‌ها"], ["Evidence, assumptions and approvers", "شواهد، فرض‌ها و تأییدکنندگان"]],
    outputs: [["Traceable ranking and trade-offs", "رتبه‌بندی قابل ردیابی و مصالحه‌ها"], ["Sensitivity to weight changes", "حساسیت به تغییر وزن‌ها"], ["Approved decision and outcome record", "تصمیم تأییدشده و رکورد نتیجه"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "context", label: ["Context", "زمینه"] }, { id: "options", label: ["Options", "گزینه‌ها"] }, { id: "criteria", label: ["Criteria & weights", "معیارها و وزن‌ها"] }, { id: "evidence", label: ["Evidence", "شواهد"] }, { id: "history", label: ["Outcome history", "تاریخچه نتایج"] }],
  },
  {
    id: "deadline-monitor",
    title: ["Deadlines & SLA", "مهلت‌ها و SLA"],
    description: ["Track contractual, procurement, approval and delivery deadlines using project calendars.", "مهلت‌های قراردادی، تدارکات، تأیید و تحویل را با تقویم پروژه پایش کنید."],
    viewTitle: ["Obligations and due-date register", "فهرست تعهدات و سررسیدها"],
    columns: [["Obligation", "تعهد"], ["Owner", "مسئول"], ["Due date", "سررسید"], ["Calendar basis", "مبنای تقویم"], ["Escalation", "ارجاع"]],
    metrics: [["Due soon", "نزدیک سررسید"], ["Overdue", "سررسیدگذشته"], ["Escalations", "ارجاعات"], ["Acknowledgements", "تأیید دریافت"]],
    methods: [["Working-calendar date offsets", "فاصله تاریخ بر مبنای تقویم کاری"], ["Recurring and lead-time reminders", "یادآوری تکرارشونده و پیش‌دستانه"], ["Timezone-safe due-date evaluation", "ارزیابی سررسید ایمن نسبت به منطقه زمانی"], ["Escalation ladder and deduplication", "نردبان ارجاع و تکرارزدایی"]],
    inputs: [["Contract/procurement/approval obligations", "تعهدات قرارداد/تدارکات/تأیید"], ["Effective working calendar and timezone", "تقویم کاری معتبر و منطقه زمانی"], ["Owner, role and escalation policy", "مسئول، نقش و سیاست ارجاع"]],
    outputs: [["Due and overdue list", "فهرست سررسید و تأخیر"], ["Reminder and escalation record", "رکورد یادآوری و ارجاع"], ["Acknowledgement and audit trail", "تأیید دریافت و رد ممیزی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "obligations", label: ["Obligations", "تعهدات"] }, { id: "calendar", label: ["Calendar", "تقویم"] }, { id: "reminders", label: ["Reminders", "یادآوری‌ها"] }, { id: "escalation", label: ["Escalation", "ارجاع"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "data-quality",
    title: ["Data Quality Profiler", "ارزیاب کیفیت داده"],
    description: ["Profile project data completeness, validity, consistency and provenance.", "کامل‌بودن، اعتبار، سازگاری و منشأ داده‌های پروژه را ارزیابی کنید."],
    viewTitle: ["Data quality profiles and findings", "پروفایل کیفیت داده و یافته‌ها"],
    columns: [["Dataset / domain", "مجموعه / حوزه"], ["Rule", "قاعده"], ["Quality dimension", "بُعد کیفیت"], ["Finding count", "تعداد یافته"], ["Remediation", "اصلاح"]],
    metrics: [["Datasets", "مجموعه‌ها"], ["Missing fields", "فیلدهای مفقود"], ["Invalid values", "مقادیر نامعتبر"], ["Quality trend", "روند کیفیت"]],
    methods: [["Completeness and validity checks", "کنترل کامل‌بودن و اعتبار"], ["Consistency and uniqueness checks", "کنترل سازگاری و یکتایی"], ["Referential integrity and provenance", "یکپارچگی ارجاع و منشأ"], ["Distribution and cross-domain rules", "قواعد توزیع و بین‌حوزه‌ای"]],
    inputs: [["Canonical field/schema registry", "فهرست ساختار و فیلد مرجع"], ["Domain records and data lineage", "رکوردهای حوزه و ریشه داده"], ["Quality policies and tolerances", "سیاست‌ها و تلورانس‌های کیفیت"]],
    outputs: [["Field/record/dataset profile", "پروفایل فیلد/رکورد/مجموعه"], ["Transparent score breakdown", "تجزیه شفاف امتیاز"], ["Remediation and recheck plan", "برنامه اصلاح و بازبینی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "completeness", label: ["Completeness", "کامل‌بودن"] }, { id: "validity", label: ["Validity", "اعتبار"] }, { id: "consistency", label: ["Consistency", "سازگاری"] }, { id: "provenance", label: ["Provenance", "منشأ داده"] }, { id: "history", label: ["Trend / history", "روند / تاریخچه"] }],
  },
  {
    id: "recovery-center",
    title: ["Recovery & Change History", "بازیابی و تاریخچه تغییرات"],
    description: ["Review command history and safely preview reversible or compensating actions.", "تاریخچه فرمان‌ها را بررسی و عملیات برگشت‌پذیر یا جبرانی را پیش‌نمایش کنید."],
    viewTitle: ["Change journal and recovery points", "دفتر تغییرات و نقاط بازیابی"],
    columns: [["Change ID", "شناسه تغییر"], ["Command / object", "فرمان / موضوع"], ["Actor", "عامل"], ["Revision", "نسخه"], ["Reversibility", "برگشت‌پذیری"]],
    metrics: [["Changes", "تغییرات"], ["Reversible", "برگشت‌پذیر"], ["Compensation required", "نیازمند جبران"], ["Restore points", "نقاط بازیابی"]],
    methods: [["Typed before/after change journal", "دفتر تغییر تایپ‌شده قبل/بعد"], ["Undo/redo for supported reversible commands", "بازگردانی/تکرار فرمان‌های برگشت‌پذیر"], ["Compensating transactions and sagas", "تراکنش جبرانی و Saga"], ["Snapshot restore preview and revision checks", "پیش‌نمایش بازیابی تصویر و کنترل نسخه"]],
    inputs: [["Append-only command/audit history", "تاریخچه فرمان و ممیزی الحاقی"], ["Versioned snapshots and transaction IDs", "تصاویر نسخه‌بندی‌شده و شناسه تراکنش"], ["Current grants and revision", "مجوزها و نسخه جاری"]],
    outputs: [["Before/after diff and impact preview", "اختلاف قبل/بعد و پیش‌نمایش اثر"], ["Undo or compensation proposal", "پیشنهاد بازگردانی یا جبران"], ["Recovery result and audit event", "نتیجه بازیابی و رویداد ممیزی"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "journal", label: ["Change journal", "دفتر تغییرات"] }, { id: "diff", label: ["Before / after", "قبل / بعد"] }, { id: "recovery", label: ["Recovery", "بازیابی"] }, { id: "approval", label: ["Approval", "تأیید"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
  {
    id: "command-dictionaries",
    title: ["Command Dictionaries", "فرهنگ واژگان فرمان"],
    description: ["Manage scoped multilingual terms, aliases and approved command phrases.", "اصطلاحات چندزبانه، نام‌های مستعار و عبارت‌های فرمان را در دامنه مجاز مدیریت کنید."],
    viewTitle: ["Terms, aliases and phrase catalogue", "فهرست اصطلاحات، مترادف‌ها و عبارت‌ها"],
    columns: [["Canonical term", "اصطلاح مرجع"], ["Alias", "نام مستعار"], ["Language", "زبان"], ["Scope", "دامنه"], ["Review state", "وضعیت بازبینی"]],
    metrics: [["Terms", "اصطلاحات"], ["Aliases", "مترادف‌ها"], ["Conflicts", "تعارض‌ها"], ["Pending review", "بازبینی معوق"]],
    methods: [["Unicode and digit normalization", "یکسان‌سازی یونیکد و ارقام"], ["Alias and synonym resolution by scope", "حل مترادف و نام مستعار بر اساس دامنه"], ["Collision and precedence detection", "تشخیص برخورد و اولویت"], ["Golden phrase testing and versioning", "آزمون عبارت مرجع و نسخه‌بندی"]],
    inputs: [["Language catalogue and domain ontology", "فهرست زبان و هستی‌شناسی دامنه"], ["User/project/tenant scoped terms", "اصطلاحات دامنه کاربر/پروژه/سازمان"], ["Canonical command schemas", "ساختار مرجع فرمان"]],
    outputs: [["Resolved canonical term and dictionary version", "اصطلاح مرجع حل‌شده و نسخه واژه‌نامه"], ["Collision diagnostics", "تشخیص تعارض"], ["Parser regression phrase set", "مجموعه عبارت‌های آزمون تحلیل‌گر"]],
    details: [{ id: "general", label: ["General", "عمومی"] }, { id: "terms", label: ["Terms", "اصطلاحات"] }, { id: "aliases", label: ["Aliases", "مترادف‌ها"] }, { id: "scope", label: ["Scope", "دامنه"] }, { id: "tests", label: ["Test phrases", "عبارت‌های آزمون"] }, { id: "history", label: ["History", "تاریخچه"] }],
  },
];

const SHELL_BY_ID = new Map(ENGINEERING_SHELLS.map((item) => [item.id, item]));

export function isEngineeringShellWindow(value: string): value is EngineeringShellWindowId {
  return SHELL_BY_ID.has(value as EngineeringShellWindowId);
}

function text(locale: string, values: Bilingual): string {
  return translateWorkspaceUiText(locale, values[0], values[1]);
}

function esc(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderList(values: readonly Bilingual[], locale: string): string {
  return values.map((value) => "<li>" + esc(text(locale, value)) + "</li>").join("");
}

export const ENGINEERING_SHELL_STYLES = `
.cp-vd-engine-shell{display:flex;flex-direction:column;min-width:0;min-height:520px;background:#f3f6fa;color:#263d56}
.cp-vd-engine-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:12px 14px;border-bottom:1px solid #d5dee8;background:#fff}
.cp-vd-engine-title{min-width:0}.cp-vd-engine-title h2{margin:0;color:#173d68;font-size:16px;font-weight:700}
.cp-vd-engine-title p{margin:5px 0 0;color:#6b7d91;font-size:11px;line-height:1.55}
.cp-vd-engine-state{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;padding:4px 8px;border:1px solid #d6b98f;border-radius:3px;background:#fff8ed;color:#80531d;font-size:10px;font-weight:700}
.cp-vd-engine-state:before{content:"";width:6px;height:6px;border-radius:50%;background:#c87935}
.cp-vd-engine-notice{display:flex;gap:9px;align-items:flex-start;margin:10px 12px 0;padding:8px 10px;border:1px solid #d6e0eb;border-inline-start:3px solid #7898bb;background:#f8fbff;color:#53677e;font-size:10px;line-height:1.6}
.cp-vd-engine-toolbar{display:flex;align-items:center;gap:5px;flex-wrap:wrap;padding:7px 10px;border-block:1px solid #d8e0e9;background:#eef3f8}
.cp-vd-engine-toolbar button{border:1px solid #d0d9e3;border-radius:3px;background:#fff;color:#52677e;padding:5px 9px;font:10px Inter,Vazirmatn,sans-serif}
.cp-vd-engine-toolbar button:disabled{opacity:.52;cursor:not-allowed}
.cp-vd-engine-toolbar .cp-vd-engine-toolbar-note{margin-inline-start:auto;color:#7a8796;font-size:10px}
.cp-vd-engine-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:10px 12px 0}
.cp-vd-engine-kpi{display:flex;flex-direction:column;gap:4px;min-width:0;padding:9px;border:1px solid #dbe3ec;border-radius:4px;background:#fff}
.cp-vd-engine-kpi span{color:#718096;font-size:10px}
.cp-vd-engine-kpi strong{color:#52677e;font-size:18px;font-weight:600;line-height:1.2}
.cp-vd-engine-kpi small{color:#9aa6b4;font-size:9px}
.cp-vd-engine-workarea{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(230px,.8fr);gap:8px;padding:10px 12px 0;min-width:0}
.cp-vd-engine-panel{min-width:0;border:1px solid #d9e1ea;border-radius:4px;background:#fff}
.cp-vd-engine-panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 10px;border-bottom:1px solid #e2e8f0}
.cp-vd-engine-panel-head strong{font-size:11px;color:#314d6b}
.cp-vd-engine-panel-head span{font-size:9px;color:#8b98a8}
.cp-vd-engine-table-wrap{overflow:auto;min-height:190px}
.cp-vd-engine-table{width:100%;min-width:570px;border-collapse:collapse;font-size:10px}
.cp-vd-engine-table th{padding:8px 9px;background:#f5f8fb;border-bottom:1px solid #e1e7ee;color:#51657d;text-align:start;white-space:nowrap;font-weight:700}
.cp-vd-engine-table td{padding:20px 10px;border-bottom:1px solid #edf1f5;color:#7b8795;text-align:center}
.cp-vd-engine-empty{min-height:152px;padding:22px 12px!important;text-align:center!important;white-space:normal;line-height:1.7}
.cp-vd-engine-empty strong{display:block;margin-bottom:5px;color:#596e86;font-size:11px}
.cp-vd-engine-empty span{display:block;max-width:520px;margin:auto;color:#8996a5;font-size:10px}
.cp-vd-engine-side{display:grid;grid-template-rows:1fr 1fr;gap:8px;min-width:0}
.cp-vd-engine-side-body{padding:9px 10px}
.cp-vd-engine-side-body ul{display:grid;gap:7px;margin:0;padding-inline-start:18px;color:#65768a;font-size:10px;line-height:1.5}
.cp-vd-engine-side-body li::marker{color:#c87935}
.cp-vd-engine-placeholder{display:grid;place-items:center;min-height:86px;margin:3px;padding:12px;border:1px dashed #d5dee8;border-radius:3px;background:repeating-linear-gradient(135deg,#fbfcfe 0,#fbfcfe 8px,#f6f8fb 8px,#f6f8fb 16px);color:#9aa6b4;text-align:center;font-size:10px;line-height:1.55}
.cp-vd-engine-details{margin:10px 12px 12px;border:1px solid #d9e1ea;border-radius:4px;background:#fff;min-width:0}
.cp-vd-engine-details-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 10px;border-bottom:1px solid #e1e7ee}
.cp-vd-engine-details-head strong{font-size:11px;color:#314d6b}
.cp-vd-engine-details-head span{font-size:9px;color:#8a97a6}
.cp-vd-engine-detail-tabs{display:flex;gap:2px;overflow-x:auto;border-bottom:1px solid #e1e7ee;padding-inline:5px}
.cp-vd-engine-detail-tabs button{flex:0 0 auto;border:0;border-bottom:2px solid transparent;background:transparent;padding:8px 9px;color:#687b91;font-size:10px;white-space:nowrap;cursor:pointer}
.cp-vd-engine-detail-tabs button.is-active{border-color:#c87935;color:#173d68;font-weight:700}
.cp-vd-engine-detail-panel{min-height:104px;padding:12px}
.cp-vd-engine-detail-panel p{margin:0;color:#66788d;font-size:10px;line-height:1.7}
.cp-vd-engine-detail-panel ul{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px 18px;margin:0;padding-inline-start:18px;color:#53677e;font-size:10px;line-height:1.6}
.cp-vd-engine-detail-panel li::marker{color:#c87935}
.cp-vd-engine-detail-panel .cp-vd-engine-detail-note{margin-top:10px;padding:7px 9px;border-inline-start:2px solid #d5a36b;background:#fffaf3;color:#876337;font-size:9px}
@media(max-width:900px){.cp-vd-engine-workarea{grid-template-columns:1fr}.cp-vd-engine-side{grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:none}.cp-vd-engine-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.cp-vd-engine-head{display:grid}.cp-vd-engine-state{justify-self:start}.cp-vd-engine-side{grid-template-columns:1fr}.cp-vd-engine-detail-panel ul{grid-template-columns:1fr}.cp-vd-engine-toolbar .cp-vd-engine-toolbar-note{width:100%;margin-inline-start:0}}
.cp-vd-engine-menu{position:relative;display:inline-flex;min-width:0}
.cp-vd-engine-menu>summary{display:inline-flex;align-items:center;gap:6px;min-height:27px;padding:5px 9px;border:1px solid #c9d5e0;border-radius:4px;background:#fff;color:#36536f;font:10px Inter,Vazirmatn,sans-serif;cursor:pointer;list-style:none;user-select:none;white-space:nowrap}
.cp-vd-engine-menu>summary::-webkit-details-marker{display:none}
.cp-vd-engine-menu>summary:after{content:"";width:5px;height:5px;margin-inline-start:3px;border-inline-end:1.5px solid currentColor;border-block-end:1.5px solid currentColor;transform:rotate(45deg) translateY(-2px)}
.cp-vd-engine-menu[open]>summary{border-color:#6f91b2;background:#e8f0f7;color:#173d68}
.cp-vd-engine-menu-icon{display:inline-flex;align-items:center;justify-content:center;width:14px;height:14px}
.cp-vd-engine-menu-icon svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
.cp-vd-engine-menu-panel{position:absolute;z-index:90;inset-block-start:calc(100% + 5px);inset-inline-start:0;display:grid;gap:5px;width:min(220px,calc(100vw - 40px));padding:7px;border:1px solid #c8d4df;border-radius:5px;background:#fff;box-shadow:0 10px 24px rgba(23,47,72,.18)}
.cp-vd-engine-menu-panel>button{display:flex;align-items:center;gap:8px;min-height:28px;padding:6px 8px;border:1px solid #e0e6ed;border-radius:3px;background:#f9fbfd;color:#4a6178;text-align:start;font:10px Inter,Vazirmatn,sans-serif}
.cp-vd-engine-menu-panel>button>span{display:inline-grid;place-items:center;width:15px;height:15px;border-radius:3px;background:#eaf0f6;color:#345f84;font-size:13px;font-weight:700}
.cp-vd-engine-menu-panel>button:disabled{opacity:.58;cursor:not-allowed}
.cp-vd-engine-filter-panel{width:min(270px,calc(100vw - 40px))}
.cp-vd-engine-filter-panel label{display:grid;gap:4px;color:#405b76;font-size:9px;font-weight:700}
.cp-vd-engine-filter-panel input,.cp-vd-engine-filter-panel select{width:100%;min-width:0;min-height:27px;padding:5px 7px;border:1px solid #d4dee8;border-radius:3px;background:#f4f7fa;color:#667a8e;font:10px Inter,Vazirmatn,sans-serif}
.cp-vd-engine-filter-panel input:disabled,.cp-vd-engine-filter-panel select:disabled{opacity:.72;cursor:not-allowed}
.cp-vd-engine-filter-panel p{margin:2px 0 0;padding:6px 7px;border-inline-start:2px solid #c87935;background:#fff8ef;color:#8a6748;font-size:9px;line-height:1.5}

`;

export function renderEngineeringShell(
  windowId: EngineeringShellWindowId,
  locale: string,
  selectedDetailTab: string,
): string {
  const definition = SHELL_BY_ID.get(windowId);
  if (!definition) return "";
  const tabId = definition.details.some((tab) => tab.id === selectedDetailTab)
    ? selectedDetailTab
    : definition.details[0].id;
  const activeDetail = definition.details.find((tab) => tab.id === tabId) ?? definition.details[0];
  let detailContent = "";
  if (tabId === "methods") detailContent = "<ul>" + renderList(definition.methods, locale) + "</ul>";
  else if (tabId === "inputs") detailContent = "<ul>" + renderList(definition.inputs, locale) + "</ul>";
  else if (tabId === "outputs") detailContent = "<ul>" + renderList(definition.outputs, locale) + "</ul>";
  else if (tabId === "history" || tabId === "runs") {
    detailContent = "<p>" + esc(text(locale, ["No execution history is available because this engine is not connected yet.", "هنوز تاریخچه اجرایی وجود ندارد؛ این موتور هنوز متصل نشده است."])) + "</p>";
  } else {
    detailContent = "<p>" + esc(text(locale, definition.description)) + "</p>";
  }
  const headers = definition.columns.map((column) => "<th>" + esc(text(locale, column)) + "</th>").join("");
  const metrics = definition.metrics.map((metric) =>
    "<div class=\"cp-vd-engine-kpi\"><span>" + esc(text(locale, metric)) + "</span><strong>—</strong><small>" + esc(text(locale, ["Awaiting data connection", "در انتظار اتصال داده"])) + "</small></div>",
  ).join("");
  const tabs = definition.details.map((tab) =>
    "<button type=\"button\" role=\"tab\" class=\"" + (tab.id === tabId ? "is-active" : "") + "\" aria-selected=\"" + (tab.id === tabId ? "true" : "false") + "\" data-vd-engine-tab=\"" + esc(tab.id) + "\">" + esc(text(locale, tab.label)) + "</button>",
  ).join("");
  const disabledTitle = text(locale, ["Not connected in this shell preview.", "در این پیش‌نمایش به عملیات واقعی متصل نیست."]);
  const commandGroups = [
    {
      id: "records",
      label: ["Records", "رکوردها"] as Bilingual,
      icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6.5h16M4 12h16M4 17.5h16"/><circle cx="7" cy="6.5" r="1"/><circle cx="7" cy="12" r="1"/><circle cx="7" cy="17.5" r="1"/></svg>',
      commands: [["Add", "افزودن", "+"], ["Edit", "ویرایش", "✎"], ["Delete", "حذف", "×"]] as const,
    },
    {
      id: "analysis",
      label: ["Analysis", "تحلیل"] as Bilingual,
      icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V5m0 14h15"/><path d="m8 15 3-4 3 2 5-7"/></svg>',
      commands: [["Run", "اجرا", "▶"]] as const,
    },
    {
      id: "filters",
      label: ["Filters", "فیلترها"] as Bilingual,
      icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16l-6.2 7.1v5.1l-3.6 1.8v-6.9L4 5Z"/></svg>',
      commands: [] as const,
    },
    {
      id: "export",
      label: ["Export", "خروجی"] as Bilingual,
      icon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4"/><path d="M5 16v4h14v-4"/></svg>',
      commands: [["Export", "خروجی", "↓"]] as const,
    },
  ] as const;
  const commands = commandGroups.map((group) => {
    const groupLabel = esc(text(locale, group.label));
    const groupIcon = '<span class="cp-vd-engine-menu-icon">' + group.icon + "</span>";
    const content = group.id === "filters"
      ? '<div class="cp-vd-engine-menu-panel cp-vd-engine-filter-panel">'
        + '<label><span>' + esc(text(locale, ["Search records", "جست‌وجو در رکوردها"])) + '</span><input type="search" disabled title="' + esc(disabledTitle) + '" placeholder="' + esc(text(locale, ["Connect the data source first", "ابتدا منبع داده را متصل کنید"])) + '"></label>'
        + '<label><span>' + esc(text(locale, ["Status", "وضعیت"])) + '</span><select disabled title="' + esc(disabledTitle) + '"><option>' + esc(text(locale, ["All statuses", "همه وضعیت‌ها"])) + '</option></select></label>'
        + '<label><span>' + esc(text(locale, ["Category", "دسته‌بندی"])) + '</span><select disabled title="' + esc(disabledTitle) + '"><option>' + esc(text(locale, ["All categories", "همه دسته‌بندی‌ها"])) + '</option></select></label>'
        + '<p>' + esc(text(locale, ["Filters unlock when authorized project records are connected.", "فیلترها پس از اتصال رکوردهای مجاز پروژه فعال می‌شوند."])) + '</p></div>'
      : '<div class="cp-vd-engine-menu-panel">' + group.commands.map((command) =>
        '<button type="button" disabled title="' + esc(disabledTitle) + '"><span aria-hidden="true">' + esc(command[2]) + '</span><strong>' + esc(text(locale, [command[0], command[1]])) + '</strong></button>',
      ).join("") + '</div>';
    return '<details class="cp-vd-engine-menu cp-vd-engine-' + group.id + '-menu">'
      + '<summary aria-label="' + groupLabel + '">' + groupIcon + '<span>' + groupLabel + '</span></summary>'
      + content + '</details>';
  }).join("");
  const methodList = renderList(definition.methods.slice(0, 4), locale);
  const inputList = renderList(definition.inputs, locale);
  return "<section class=\"cp-vd-windowbody cp-vd-engine-shell\" data-engine-window=\"" + windowId + "\">"
    + "<header class=\"cp-vd-engine-head cp-vd-winhead\"><div class=\"cp-vd-engine-title\"><h2>" + esc(text(locale, definition.title)) + "</h2><p>" + esc(text(locale, definition.description)) + "</p></div>"
    + "<span class=\"cp-vd-engine-state\">" + esc(text(locale, ["Planned · shell only", "برنامه‌ریزی‌شده · پوسته بصری"])) + "</span></header>"
    + "<div class=\"cp-vd-engine-notice\"><strong>ⓘ</strong><span>" + esc(text(locale, ["Visual shell only. No project records, calculations, alerts or actions are connected in this window yet.", "این صفحه فعلاً فقط پوسته بصری است؛ هنوز رکورد پروژه، محاسبات، هشدارها یا عملیات واقعی به آن متصل نشده‌اند."])) + "</span></div>"
    + "<div class=\"cp-vd-engine-toolbar\" role=\"toolbar\" aria-label=\"" + esc(text(locale, ["Engine commands", "فرمان‌های موتور"])) + "\">" + commands
    + "<span class=\"cp-vd-engine-toolbar-note\">" + esc(text(locale, ["Commands and filters stay disabled until the real data and permission paths pass acceptance.", "فرمان‌ها و فیلترها تا تأیید مسیر واقعی داده و مجوز غیرفعال می‌مانند."])) + "</span></div>"
    + "<div class=\"cp-vd-engine-kpis\">" + metrics + "</div>"
    + "<div class=\"cp-vd-engine-workarea\">"
    + "<section class=\"cp-vd-engine-panel\"><header class=\"cp-vd-engine-panel-head\"><strong>" + esc(text(locale, definition.viewTitle)) + "</strong><span>" + esc(text(locale, ["No live records", "بدون رکورد زنده"])) + "</span></header>"
    + "<div class=\"cp-vd-engine-table-wrap\"><table class=\"cp-vd-engine-table\"><thead><tr>" + headers + "</tr></thead><tbody><tr><td class=\"cp-vd-engine-empty\" colspan=\"" + definition.columns.length + "\"><strong>" + esc(text(locale, ["No records to display", "رکوردی برای نمایش وجود ندارد"])) + "</strong><span>" + esc(text(locale, ["The data contract and read service are pending. This placeholder contains no sample project values.", "قرارداد داده و سرویس خواندن هنوز آماده نیست. این بخش هیچ مقدار نمونه ساختگی از پروژه ندارد."])) + "</span></td></tr></tbody></table></div></section>"
    + "<div class=\"cp-vd-engine-side\">"
    + "<section class=\"cp-vd-engine-panel\"><header class=\"cp-vd-engine-panel-head\"><strong>" + esc(text(locale, ["Method families", "خانواده روش‌ها"])) + "</strong><span>" + esc(text(locale, ["Design scope", "دامنه طراحی"])) + "</span></header><div class=\"cp-vd-engine-side-body\"><ul>" + methodList + "</ul></div></section>"
    + "<section class=\"cp-vd-engine-panel\"><header class=\"cp-vd-engine-panel-head\"><strong>" + esc(text(locale, ["Required inputs", "ورودی‌های موردنیاز"])) + "</strong><span>" + esc(text(locale, ["Prerequisites", "پیش‌نیازها"])) + "</span></header><div class=\"cp-vd-engine-side-body\"><ul>" + inputList + "</ul></div></section>"
    + "</div></div>"
    + "<section class=\"cp-vd-engine-details\"><header class=\"cp-vd-engine-details-head\"><strong>" + esc(text(locale, ["Engine Details", "جزئیات موتور"])) + "</strong><span>" + esc(text(locale, ["Window-specific properties", "مشخصات اختصاصی پنجره"])) + "</span></header>"
    + "<div class=\"cp-vd-engine-detail-tabs\" role=\"tablist\">" + tabs + "</div><div class=\"cp-vd-engine-detail-panel\" role=\"tabpanel\" aria-label=\"" + esc(text(locale, activeDetail.label)) + "\">" + detailContent
    + "<div class=\"cp-vd-engine-detail-note\">" + esc(text(locale, ["Design reference: Issue #1706 · Engine implementation is not claimed.", "مرجع طراحی: Issue #1706 · پیاده‌سازی موتور ادعا نمی‌شود."])) + "</div></div></section>"
    + "</section>";
}
