import type { WorkspaceLocale, WorkspaceMenuKey } from "./workspace-model.js";
import {
  getWorkspaceNavigation,
  getWorkspaceNavigationLabel,
} from "./workspace-navigation.js";
import { getAvailableWorkspaceLocales, translateWorkspaceText } from "./workspace-localization.js";

/**
 * A deterministic, testable contract for the operational help the global
 * assistant can offer. Every entry describes a page or workspace state that the
 * product can actually detect, and every action points at a control that exists
 * in the rendered page. Model output is never used to invent a page, a control
 * or a result.
 */
export type AssistantPageKey =
  | "home"
  | "platform"
  | "solutions"
  | "resources"
  | "contact"
  | "login"
  | "workspace"
  | "unknown";

export type AssistantGuideState =
  | "visitor"
  | "loading"
  | "no-project"
  | "multiple-projects"
  | "empty-wbs"
  | "empty-activities"
  | "ready"
  | "error"
  | "unknown";

export type AssistantGuideQuery = {
  page: AssistantPageKey;
  state: AssistantGuideState;
  menu?: WorkspaceMenuKey;
  locale: WorkspaceLocale;
  /** The reference code the failure page already shows to the user. */
  reference?: string | null;
};

export type AssistantGuideAction = {
  label: string;
  /** A selector that must resolve in the current document before it is offered. */
  target: string;
};

export type AssistantGuide = {
  page: AssistantPageKey;
  state: AssistantGuideState;
  menu: WorkspaceMenuKey | null;
  heading: string;
  purpose: string;
  steps: readonly string[];
  commonError: string | null;
  action: AssistantGuideAction | null;
};

type Copy = { en: string; fa: string };

type GuideShape = {
  purpose: Copy;
  steps: readonly Copy[];
  commonError?: Copy;
  action?: { label: Copy; target: string };
};

/**
 * Every action target in this registry. The launcher additionally checks the
 * selector against the live document, so a data-dependent panel that is absent
 * never produces a dead button.
 */
export const ASSISTANT_GUIDE_TARGETS: readonly string[] = Object.freeze([
  "#cp-project-wbs",
  "#cp-activity-grid",
  "#cp-resource-capacity",
  "#cp-interchange",
  "#cp-schedule-run",
  ".cp-control-summary",
  "[data-language-toggle]",
]);

export const WORKSPACE_MENU_KEYS: readonly WorkspaceMenuKey[] = Object.freeze([
  "project",
  "schedule",
  "progress",
  "resources",
  "cost",
  "documents",
  "reports",
  "control",
  "settings",
]);

export function isWorkspaceMenuKey(value: string | undefined): value is WorkspaceMenuKey {
  return Boolean(value) && (WORKSPACE_MENU_KEYS as readonly string[]).includes(value as string);
}

const PUBLIC_GUIDES: Record<
  Exclude<AssistantPageKey, "workspace" | "unknown">,
  GuideShape
> = {
  home: {
    purpose: {
      en: "CUBI brings construction planning, project controls and project evidence into one workspace.",
      fa: "کوبی برنامه‌ریزی ساخت، کنترل پروژه و شواهد پروژه را در یک محیط کار کنار هم می‌آورد.",
    },
    steps: [
      {
        en: "Explore the platform capabilities, or open the workspace to work on a project.",
        fa: "قابلیت‌های پلتفرم را ببینید یا برای کار روی یک پروژه، محیط کار را باز کنید.",
      },
      {
        en: "The workspace creates or reopens a project before it shows WBS, activities and schedules.",
        fa: "محیط کار پیش از نمایش WBS، فعالیت‌ها و زمان‌بندی، یک پروژه را ایجاد یا دوباره باز می‌کند.",
      },
      {
        en: "This entry only guides you; project actions always run inside the workspace with your permission.",
        fa: "این ورودی فقط راهنمایی می‌کند؛ اقدامات پروژه همیشه با اجازهٔ شما در محیط کار اجرا می‌شوند.",
      },
    ],
  },
  platform: {
    purpose: {
      en: "This page describes the connected project-controls capabilities of CUBI.",
      fa: "این صفحه قابلیت‌های یکپارچهٔ کنترل پروژهٔ کوبی را معرفی می‌کند.",
    },
    steps: [
      {
        en: "Read the capability areas that matter for your project stage.",
        fa: "حوزه‌های قابلیتی را که برای مرحلهٔ پروژهٔ شما مهم‌اند بخوانید.",
      },
      {
        en: "Open the workspace to use the same capabilities on real project data.",
        fa: "برای استفاده از همین قابلیت‌ها روی داده‌های واقعی پروژه، محیط کار را باز کنید.",
      },
      {
        en: "Ask here when a scheduling or controls term is unclear.",
        fa: "اگر اصطلاح زمان‌بندی یا کنترل پروژه روشن نیست، همین‌جا بپرسید.",
      },
    ],
  },
  solutions: {
    purpose: {
      en: "This page explains how CUBI supports construction delivery roles and stages.",
      fa: "این صفحه توضیح می‌دهد کوبی چگونه از نقش‌ها و مراحل تحویل ساخت پشتیبانی می‌کند.",
    },
    steps: [
      {
        en: "Compare the delivery scenarios with the way your team works.",
        fa: "سناریوهای تحویل را با روش کار تیم خود مقایسه کنید.",
      },
      {
        en: "Open the platform page for the detailed capabilities behind each scenario.",
        fa: "برای جزئیات قابلیت‌های هر سناریو، صفحهٔ پلتفرم را باز کنید.",
      },
      {
        en: "Use the workspace to apply the workflow to a real project.",
        fa: "برای اجرای این جریان روی یک پروژهٔ واقعی از محیط کار استفاده کنید.",
      },
    ],
  },
  resources: {
    purpose: {
      en: "This page points to the product overview, documentation and next steps.",
      fa: "این صفحه مسیر معرفی محصول، مستندات و گام‌های بعدی را نشان می‌دهد.",
    },
    steps: [
      {
        en: "Start with the product overview if you are evaluating CUBI.",
        fa: "اگر در حال ارزیابی کوبی هستید، با معرفی محصول شروع کنید.",
      },
      {
        en: "The scheduling reference and formula contracts live inside a project workspace.",
        fa: "مرجع زمان‌بندی و قراردادهای محاسباتی در محیط کار پروژه در دسترس‌اند.",
      },
      {
        en: "Use the contact page for account access and product questions.",
        fa: "برای دسترسی به حساب و پرسش‌های محصول از صفحهٔ تماس استفاده کنید.",
      },
    ],
  },
  contact: {
    purpose: {
      en: "This page routes account-access and product questions to the right destination.",
      fa: "این صفحه پرسش‌های دسترسی به حساب و محصول را به مقصد درست هدایت می‌کند.",
    },
    steps: [
      {
        en: "Open the workspace to sign in or create the first project.",
        fa: "برای ورود یا ایجاد اولین پروژه، محیط کار را باز کنید.",
      },
      {
        en: "Review the platform page for product detail before contacting the team.",
        fa: "پیش از تماس با تیم، جزئیات محصول را در صفحهٔ پلتفرم ببینید.",
      },
      {
        en: "This page does not submit a form; nothing is sent from here.",
        fa: "این صفحه فرمی ارسال نمی‌کند؛ چیزی از اینجا فرستاده نمی‌شود.",
      },
    ],
  },
  login: {
    purpose: {
      en: "The local preview offers fixed demo roles so the real workflow can be tested.",
      fa: "پیش‌نمایش محلی نقش‌های نمایشی ثابت را ارائه می‌کند تا جریان واقعی قابل آزمایش باشد.",
    },
    steps: [
      {
        en: "Pick the role that matches the task: planner, viewer or project administrator.",
        fa: "نقشی را که با کار شما هم‌خوان است انتخاب کنید: برنامه‌ریز، بازبین یا مدیر پروژه.",
      },
      {
        en: "The newcomer role starts with no project and tests first-project creation.",
        fa: "نقش حساب تازه بدون پروژه شروع می‌شود و ایجاد اولین پروژه را آزمایش می‌کند.",
      },
      {
        en: "This is a local demo; do not enter real credentials or sensitive project data.",
        fa: "این یک نمایش محلی است؛ اطلاعات ورود واقعی یا دادهٔ حساس پروژه وارد نکنید.",
      },
    ],
  },
};

const WORKSPACE_STATE_GUIDES: Record<
  "loading" | "no-project" | "multiple-projects" | "error" | "unknown",
  GuideShape
> = {
  loading: {
    purpose: {
      en: "The workspace is loading the server-confirmed session, project list and project data.",
      fa: "محیط کار در حال بارگذاری نشست تأییدشدهٔ سرور، فهرست پروژه‌ها و داده‌های پروژه است.",
    },
    steps: [
      {
        en: "Wait for the project list or workspace to appear.",
        fa: "منتظر بمانید تا فهرست پروژه‌ها یا محیط کار نمایش داده شود.",
      },
      {
        en: "If loading fails, use Retry; the error shows a reference code for support.",
        fa: "اگر بارگذاری ناموفق بود، «تلاش مجدد» را بزنید؛ خطا یک کد مرجع برای پشتیبانی نشان می‌دهد.",
      },
      {
        en: "No project data is shown until the server confirms access.",
        fa: "تا زمانی که سرور دسترسی را تأیید نکند، هیچ دادهٔ پروژه‌ای نمایش داده نمی‌شود.",
      },
    ],
  },
  "no-project": {
    purpose: {
      en: "The signed-in account has no project yet; this is a first-run state, not an error state.",
      fa: "حساب واردشده هنوز پروژه‌ای ندارد؛ این وضعیت شروع کار است، نه خطا.",
    },
    steps: [
      {
        en: "Enter a project name between 2 and 120 characters.",
        fa: "نام پروژه را بین ۲ تا ۱۲۰ نویسه وارد کنید.",
      },
      {
        en: "Choose Create and open; the new project is stored by the server before it opens.",
        fa: "«ایجاد و باز کردن» را بزنید؛ پروژهٔ جدید پیش از باز شدن در سرور ذخیره می‌شود.",
      },
      {
        en: "The new project starts empty: load or import WBS and activities next.",
        fa: "پروژهٔ جدید خالی است: در گام بعد WBS و فعالیت‌ها را بارگذاری یا وارد کنید.",
      },
    ],
    commonError: {
      en: "If creation fails, the form stays open with the entered name and shows a reference code.",
      fa: "اگر ایجاد پروژه ناموفق باشد، فرم با نام واردشده باز می‌ماند و کد مرجع نشان می‌دهد.",
    },
  },
  "multiple-projects": {
    purpose: {
      en: "The account can open more than one project; choose the one to work on.",
      fa: "این حساب به بیش از یک پروژه دسترسی دارد؛ پروژهٔ مورد نظر را انتخاب کنید.",
    },
    steps: [
      {
        en: "Select a project from the list to open its confirmed workspace.",
        fa: "برای باز کردن محیط کار تأییدشده، یک پروژه را از فهرست انتخاب کنید.",
      },
      {
        en: "The last project reopens automatically in this browser after a refresh.",
        fa: "آخرین پروژه پس از بازخوانی به‌طور خودکار در این مرورگر باز می‌شود.",
      },
      {
        en: "Use Create and open to start another project without leaving this account.",
        fa: "برای شروع پروژهٔ دیگر بدون ترک این حساب، از «ایجاد و باز کردن» استفاده کنید.",
      },
    ],
    commonError: {
      en: "A project that the account no longer owns is not opened; choose another project.",
      fa: "پروژه‌ای که حساب دیگر به آن دسترسی ندارد باز نمی‌شود؛ پروژهٔ دیگری انتخاب کنید.",
    },
  },
  error: {
    purpose: {
      en: "The workspace could not open because the server request failed.",
      fa: "محیط کار باز نشد چون درخواست سرور ناموفق بود.",
    },
    steps: [
      {
        en: "Use Retry on the page to request the session and project list again.",
        fa: "با «تلاش مجدد» در همین صفحه، نشست و فهرست پروژه‌ها را دوباره درخواست کنید.",
      },
      {
        en: "No project data was loaded, so nothing is shown as a result of this failure.",
        fa: "هیچ دادهٔ پروژه‌ای بارگذاری نشد؛ بنابراین چیزی به‌عنوان نتیجهٔ این خطا نمایش داده نمی‌شود.",
      },
      {
        en: "If Retry keeps failing, give the reference code below to the workspace administrator.",
        fa: "اگر تلاش مجدد ناموفق ماند، کد مرجع زیر را به مدیر محیط کار بدهید.",
      },
    ],
    commonError: {
      en: "The page shows a reference code; it identifies this failure without exposing project data.",
      fa: "صفحه یک کد مرجع نشان می‌دهد؛ این کد خطا را بدون افشای دادهٔ پروژه مشخص می‌کند.",
    },
  },
  unknown: {
    purpose: {
      en: "The workspace state could not be determined from the page.",
      fa: "وضعیت محیط کار از روی صفحه قابل تشخیص نبود.",
    },
    steps: [
      {
        en: "Reload the page and wait for the workspace to finish loading.",
        fa: "صفحه را بازخوانی کنید و منتظر بمانید تا محیط کار کامل بارگذاری شود.",
      },
      {
        en: "If the problem continues, share the reference code shown next to the error message.",
        fa: "اگر مشکل ادامه داشت، کد مرجعی را که خطا نشان می‌دهد بازگو کنید.",
      },
    ],
  },
};

const MENU_GUIDES: Record<WorkspaceMenuKey, GuideShape> = {
  project: {
    purpose: {
      en: "Work breakdown, activity details and project interchange for the open project.",
      fa: "شکست ساختاری کار، جزئیات فعالیت و ورود/خروجی پروژهٔ بازشده.",
    },
    steps: [
      {
        en: "Pick a WBS node to focus the grid on that part of the project.",
        fa: "یک گره WBS را انتخاب کنید تا جدول روی همان بخش پروژه متمرکز شود.",
      },
      {
        en: "Select an activity row to inspect its details beside the grid.",
        fa: "یک ردیف فعالیت را انتخاب کنید تا جزئیات آن کنار جدول نمایش داده شود.",
      },
      {
        en: "Check the mapped row count after an import or export.",
        fa: "پس از ورود یا خروجی، تعداد ردیف‌های نگاشت‌شده را بررسی کنید.",
      },
    ],
    commonError: {
      en: "A stale layout or revision conflict is reported, not merged silently; reload before repeating the change.",
      fa: "تعارض نسخه یا چیدمان قدیمی بی‌صدا ادغام نمی‌شود؛ پیش از تکرار تغییر، صفحه را بازخوانی کنید.",
    },
    action: {
      label: { en: "Go to the WBS", fa: "رفتن به WBS" },
      target: "#cp-project-wbs",
    },
  },
  schedule: {
    purpose: {
      en: "Activities, relationships and the shared scheduling core in one view.",
      fa: "فعالیت‌ها، روابط و هستهٔ مشترک زمان‌بندی در یک نما.",
    },
    steps: [
      {
        en: "Filter or sort the activity grid to find the work you need.",
        fa: "جدول فعالیت‌ها را پالایش یا مرتب کنید تا کار مورد نظر را پیدا کنید.",
      },
      {
        en: "Review relationships and lags; dates are calculated by the shared core, not this panel.",
        fa: "روابط و وقفه‌ها را بررسی کنید؛ تاریخ‌ها با هستهٔ مشترک محاسبه می‌شوند، نه این پنل.",
      },
      {
        en: "Run the schedule and verify the data date, early/late dates and total float.",
        fa: "زمان‌بندی را اجرا کنید و تاریخ داده، تاریخ‌های زودترین/دیرترین و شناوری کل را بررسی کنید.",
      },
    ],
    commonError: {
      en: "If the schedule cannot run, read the error; the previously stored result is kept.",
      fa: "اگر زمان‌بندی اجرا نشد، خطا را بخوانید؛ نتیجهٔ ذخیره‌شدهٔ قبلی حفظ می‌شود.",
    },
    action: {
      label: { en: "Go to the activity grid", fa: "رفتن به جدول فعالیت‌ها" },
      target: "#cp-activity-grid",
    },
  },
  progress: {
    purpose: {
      en: "Progress entries and their effect on dates and float.",
      fa: "ثبت پیشرفت و تأثیر آن بر تاریخ‌ها و شناوری.",
    },
    steps: [
      {
        en: "Review or enter % complete per activity in the grid.",
        fa: "درصد تکمیل هر فعالیت را در جدول بررسی یا وارد کنید.",
      },
      {
        en: "Compare early/late dates and total float after progress is applied.",
        fa: "پس از اعمال پیشرفت، تاریخ‌های زودترین/دیرترین و شناوری کل را مقایسه کنید.",
      },
      {
        en: "Re-run the schedule and confirm the stored result before reporting.",
        fa: "زمان‌بندی را دوباره اجرا و پیش از گزارش، نتیجهٔ ذخیره‌شده را تأیید کنید.",
      },
    ],
    commonError: {
      en: "Progress on a stale revision is rejected; reload so the current revision is used.",
      fa: "پیشرفت روی نسخهٔ قدیمی رد می‌شود؛ صفحه را بازخوانی کنید تا نسخهٔ جاری استفاده شود.",
    },
    action: {
      label: { en: "Go to progress fields", fa: "رفتن به فیلدهای پیشرفت" },
      target: "#cp-activity-grid",
    },
  },
  resources: {
    purpose: {
      en: "Effective-dated resource capacity and its history.",
      fa: "ظرفیت منابع با تاریخ اجرا و تاریخچهٔ آن.",
    },
    steps: [
      {
        en: "Review the registered Max Units / Time and its effective date.",
        fa: "حداکثر واحد/زمان ثبت‌شده و تاریخ اجرای آن را بررسی کنید.",
      },
      {
        en: "Add a change with the close option so the prior segment stays in history.",
        fa: "تغییر را با گزینهٔ بستن ثبت کنید تا بازهٔ قبلی در تاریخچه بماند.",
      },
      {
        en: "Reload and confirm the server returns the same segments and resolved units.",
        fa: "بازخوانی کنید و تأیید کنید سرور همان بازه‌ها و واحدهای محاسبه‌شده را برمی‌گرداند.",
      },
    ],
    commonError: {
      en: "An invalid effective date is rejected; no capacity value is invented.",
      fa: "تاریخ اجرای نامعتبر رد می‌شود؛ هیچ مقدار ظرفیتی ساخته نمی‌شود.",
    },
    action: {
      label: { en: "Go to resource capacity", fa: "رفتن به ظرفیت منابع" },
      target: "#cp-resource-capacity",
    },
  },
  cost: {
    purpose: {
      en: "Cost and commercial signals from the project control data.",
      fa: "نشانه‌های هزینه و بازرگانی از داده‌های کنترل پروژه.",
    },
    steps: [
      {
        en: "Read the control summary and its generated time first.",
        fa: "ابتدا خلاصهٔ کنترل و زمان تولید آن را بخوانید.",
      },
      {
        en: "Check changes, claims and procurement records for amounts and approvals.",
        fa: "تغییرات، ادعاها و سوابق خرید را از نظر مبلغ و تأیید بررسی کنید.",
      },
      {
        en: "Export the project file when a source record is needed elsewhere.",
        fa: "وقتی سابقهٔ منبع در جای دیگری لازم است، فایل پروژه را خروجی بگیرید.",
      },
    ],
    commonError: {
      en: "Absent cost data is shown as empty, never as a zero amount.",
      fa: "دادهٔ هزینهٔ نبوده به‌صورت خالی نمایش داده می‌شود، نه مبلغ صفر.",
    },
    action: {
      label: { en: "Go to the control summary", fa: "رفتن به خلاصهٔ کنترل" },
      target: ".cp-control-summary",
    },
  },
  documents: {
    purpose: {
      en: "Project documents, evidence and the interchange file.",
      fa: "اسناد پروژه، مستندات و فایل ورود/خروجی.",
    },
    steps: [
      {
        en: "Review documents linked to changes and claims.",
        fa: "اسناد مرتبط با تغییرات و ادعاها را بررسی کنید.",
      },
      {
        en: "Use Import / Export for the provider project data file.",
        fa: "برای فایل دادهٔ پروژه از «ورود / خروجی» استفاده کنید.",
      },
      {
        en: "Verify the mapped row count after an import.",
        fa: "پس از ورود، تعداد ردیف‌های نگاشت‌شده را بررسی کنید.",
      },
    ],
    commonError: {
      en: "An invalid document is rejected with a code; no rows are fabricated.",
      fa: "سند نامعتبر با کد رد می‌شود؛ هیچ ردیفی ساخته نمی‌شود.",
    },
    action: {
      label: { en: "Open import / export", fa: "باز کردن ورود / خروجی" },
      target: "#cp-interchange",
    },
  },
  reports: {
    purpose: {
      en: "Evidence-backed views that can be read or printed from this page.",
      fa: "نماهای مستند که از همین صفحه خوانده یا چاپ می‌شوند.",
    },
    steps: [
      {
        en: "Open the control summary for generated metrics and findings.",
        fa: "برای شاخص‌ها و یافته‌های تولیدشده، خلاصهٔ کنترل را باز کنید.",
      },
      {
        en: "Check the source time before sharing a report.",
        fa: "پیش از اشتراک‌گذاری گزارش، زمان منبع را بررسی کنید.",
      },
      {
        en: "Use the browser print dialog to produce a document.",
        fa: "برای تهیهٔ سند، از پنجرهٔ چاپ مرورگر استفاده کنید.",
      },
    ],
    commonError: {
      en: "A report without a source time is not presented as current.",
      fa: "گزارشی که زمان منبع ندارد، به‌عنوان به‌روز ارائه نمی‌شود.",
    },
    action: {
      label: { en: "Go to the control summary", fa: "رفتن به خلاصهٔ کنترل" },
      target: ".cp-control-summary",
    },
  },
  control: {
    purpose: {
      en: "Control summary, changes, claims and field evidence for this project.",
      fa: "خلاصهٔ کنترل، تغییرات، ادعاها و شواهد میدانی این پروژه.",
    },
    steps: [
      {
        en: "Read the summary and its generated time first.",
        fa: "ابتدا خلاصه و زمان تولید آن را بخوانید.",
      },
      {
        en: "Review changes, claims and field issues with their status.",
        fa: "تغییرات، ادعاها و مسائل میدانی را همراه وضعیت بررسی کنید.",
      },
      {
        en: "Follow an item back to its source record before deciding.",
        fa: "پیش از تصمیم‌گیری، هر مورد را تا سابقهٔ منبع آن دنبال کنید.",
      },
    ],
    commonError: {
      en: "An unavailable source is shown as empty, not as a successful result.",
      fa: "منبع در دسترس‌نبوده خالی نمایش داده می‌شود، نه نتیجهٔ موفق.",
    },
    action: {
      label: { en: "Go to the control summary", fa: "رفتن به خلاصهٔ کنترل" },
      target: ".cp-control-summary",
    },
  },
  settings: {
    purpose: {
      en: "Language and workspace preferences for this browser.",
      fa: "زبان و ترجیحات محیط کار برای این مرورگر.",
    },
    steps: [
      {
        en: "Switch the workspace language with the header control; the choice is remembered.",
        fa: "زبان محیط کار را با کنترل سرصفحه تغییر دهید؛ انتخاب شما به یاد می‌ماند.",
      },
      {
        en: "The last project and menu reopen automatically on this browser.",
        fa: "آخرین پروژه و منو به‌طور خودکار در این مرورگر باز می‌شوند.",
      },
      {
        en: "Refresh the page to verify the stored preference.",
        fa: "برای بررسی ترجیح ذخیره‌شده، صفحه را بازخوانی کنید.",
      },
    ],
    commonError: {
      en: "If the browser blocks storage, the workspace still works but preferences are not saved.",
      fa: "اگر مرورگر ذخیره‌سازی را مسدود کند، محیط کار کار می‌کند اما ترجیحات ذخیره نمی‌شوند.",
    },
    action: {
      label: { en: "Open the language control", fa: "باز کردن کنترل زبان" },
      target: "[data-language-toggle]",
    },
  },
};

/** Locale-aware text with the same fallback contract as the rest of the UI. */
function localized(locale: WorkspaceLocale, key: string, value: Copy): string {
  const base = locale.split("-")[0] as "en" | "fa";
  return translateWorkspaceText(locale, `assistant.guide.${key}`, value[base] ?? value.en);
}

function shapeToGuide(
  shape: GuideShape,
  query: AssistantGuideQuery,
  keyPrefix: string,
): AssistantGuide {
  const heading = keyPrefix === "workspace"
    ? localized(query.locale, "workspaceHeading", {
        en: "Workspace guide",
        fa: "راهنمای محیط کار",
      })
    : localized(query.locale, "pageHeading", {
        en: "On this page",
        fa: "در این صفحه",
      });
  const action = shape.action;
  return {
    page: query.page,
    state: query.state,
    menu: query.menu ?? null,
    heading,
    purpose: localized(query.locale, `${keyPrefix}.purpose`, shape.purpose),
    steps: shape.steps.map((step, index) =>
      localized(query.locale, `${keyPrefix}.step.${index}`, step),
    ),
    commonError: shape.commonError
      ? localized(query.locale, `${keyPrefix}.error`, shape.commonError)
      : null,
    action: action
      ? {
          label: localized(query.locale, `${keyPrefix}.action`, action.label),
          target: action.target,
        }
      : null,
  };
}

function menuShape(menu: WorkspaceMenuKey): GuideShape {
  return MENU_GUIDES[menu];
}

/**
 * Resolve the guide for a detected page/state. The caller supplies the state so
 * this function stays pure and every branch is unit-testable without a browser.
 */
export function resolveAssistantGuide(query: AssistantGuideQuery): AssistantGuide {
  if (query.page === "workspace") {
    const state = query.state;
    if (state === "ready" || state === "empty-wbs" || state === "empty-activities") {
      const menu = query.menu ?? "project";
      const base = menuShape(menu);
      const steps = [...base.steps];
      if (state === "empty-activities") {
        steps.unshift({
          en: "No activities are loaded. Use Import / Export to load project data; the schedule has nothing to calculate until then.",
          fa: "هیچ فعالیتی بارگذاری نشده است. برای بارگذاری دادهٔ پروژه از «ورود / خروجی» استفاده کنید؛ تا آن زمان چیزی برای محاسبهٔ زمان‌بندی وجود ندارد.",
        });
      } else if (state === "empty-wbs") {
        steps.unshift({
          en: "No work breakdown is loaded. Import the project structure before relying on WBS filters.",
          fa: "شکست ساختاری کار بارگذاری نشده است. پیش از اتکا به پالایه‌های WBS، ساختار پروژه را وارد کنید.",
        });
      }
      const guide = shapeToGuide(
        { ...base, steps },
        { ...query, menu },
        `menu.${menu}`,
      );
      const label = getWorkspaceNavigationLabel(
        getWorkspaceNavigation(menu),
        query.locale,
      );
      return { ...guide, heading: `${guide.heading} · ${label}` };
    }
    if (
      state === "no-project" ||
      state === "multiple-projects" ||
      state === "loading" ||
      state === "error" ||
      state === "unknown"
    ) {
      const guide = shapeToGuide(
        WORKSPACE_STATE_GUIDES[state],
        query,
        `state.${state}`,
      );
      if (state !== "error") return guide;
      // The failure page already owns the code; repeat it verbatim so the guide
      // stays a pointer to the same evidence instead of inventing a reason.
      const reference = query.reference?.trim() ?? "";
      if (!reference) return guide;
      return {
        ...guide,
        commonError: localized(query.locale, "state.error.reference", {
          en: `Reference: ${reference}`,
          fa: `مرجع: ${reference}`,
        }),
      };
    }
    return shapeToGuide(WORKSPACE_STATE_GUIDES.unknown, query, "state.unknown");
  }

  if (query.page === "unknown") {
    return {
      page: "unknown",
      state: query.state,
      menu: null,
      heading: localized(query.locale, "unknownHeading", {
        en: "Page not recognized",
        fa: "صفحه شناسایی نشد",
      }),
      purpose: localized(query.locale, "unknown.purpose", {
        en: "This address is not a CUBI page in the current build.",
        fa: "این نشانی در نسخهٔ فعلی، صفحه‌ای از کوبی نیست.",
      }),
      steps: [
        localized(query.locale, "unknown.step.0", {
          en: "Return to the home page from the header.",
          fa: "از سرصفحه به صفحهٔ اصلی برگردید.",
        }),
        localized(query.locale, "unknown.step.1", {
          en: "Open the workspace to work on a project.",
          fa: "برای کار روی یک پروژه، محیط کار را باز کنید.",
        }),
      ],
      commonError: null,
      action: null,
    };
  }

  const shape = PUBLIC_GUIDES[query.page];
  return shapeToGuide(shape, query, `page.${query.page}`);
}

/**
 * Resolve a public/known page from a pathname. The optional base path removes
 * a GitHub Pages project prefix, and a trailing language segment is removed
 * before the page segment is read.
 */
export function resolveAssistantPage(
  pathname: string,
  basePath = "",
  locales: readonly string[] = getAvailableWorkspaceLocales(),
): AssistantPageKey {
  const withoutIndex = pathname.replace(/index\.html$/, "");
  let path = withoutIndex.replace(/\/+$/, "");
  const normalizedBase = `${basePath.replace(/index\.html$/, "").replace(/\/+$/, "")}/`;
  if (normalizedBase !== "/" && (path + "/").startsWith(normalizedBase)) {
    path = (path + "/").slice(normalizedBase.length).replace(/\/+$/, "");
  }
  const segments = path.split("/").filter(Boolean);
  const last = segments[segments.length - 1] ?? "";
  if (locales.includes(last)) segments.pop();
  const page = segments[segments.length - 1] ?? "";
  if (page === "app") return "workspace";
  if (segments.includes("preview") && segments.includes("login")) return "login";
  if (!page) return "home";
  if (page === "platform" || page === "solutions" || page === "resources" || page === "contact") {
    return page;
  }
  return "unknown";
}

/**
 * Read the live page state. Counts come from the rendered workspace, so the
 * guidance describes what the user can actually see rather than a guess.
 */
export function readAssistantGuideQuery(
  doc: Document,
  basePath = "",
): AssistantGuideQuery {
  const locale = (doc.documentElement.lang || "en").trim().toLowerCase() || "en";
  const page = resolveAssistantPage(doc.location?.pathname ?? "", basePath);
  const workspace = doc.querySelector(".cp-workspace[data-project]");
  const selection = doc.querySelector(".cp-project-selection");
  const shellError = doc.querySelector(".cp-shell-error");
  const loading = doc.querySelector(".cp-shell-loading");
  const menuElement = doc.querySelector<HTMLElement>(
    '.cp-menu [data-menu][aria-current="page"]',
  );
  const menu = isWorkspaceMenuKey(menuElement?.dataset.menu)
    ? menuElement.dataset.menu
    : undefined;
  const activityCount = doc.querySelectorAll(
    "#cp-activity-grid tbody tr[data-activity-id]",
  ).length;
  const wbsCount = doc.querySelectorAll(".cp-wbs-node").length;
  const selectionCount = doc.querySelectorAll(
    ".cp-project-selection button[data-project-id]",
  ).length;
  // The failure page already renders the support reference as page text, so the
  // guide repeats that exact code and never derives one of its own.
  const reference =
    doc.querySelector(".cp-error-reference code")?.textContent?.trim() ?? null;

  let state: AssistantGuideState;
  if (workspace) {
    state = activityCount === 0
      ? "empty-activities"
      : wbsCount === 0
        ? "empty-wbs"
        : "ready";
  } else if (selection) {
    state = selectionCount > 1 ? "multiple-projects" : "no-project";
  } else if (shellError) {
    state = "error";
  } else if (loading) {
    state = "loading";
  } else {
    state = page === "workspace" ? "unknown" : "visitor";
  }

  return { page, state, menu, locale, reference };
}
