import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

test("visual workspace exposes language, full-screen and sign-out controls without a second workspace link", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));

  assert.match(html, /<select data-vd-locale/);
  assert.match(html, /<option value="en" selected>English<\/option>/);
  assert.match(html, /<option value="fa">فارسی<\/option>/);
  assert.doesNotMatch(html, /Open live workspace/);
  assert.match(html, /data-vd-fullscreen/);
  assert.match(html, />Full screen<\/button>/);
  assert.match(html, />Sign out<\/button>/);
  assert.match(html, /data-vd-action='\{"command":"sign-out"\}'/);
  assert.match(html, /Sign out/);
});

test("visual workspace language selector respects Persian direction and label", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));

  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /<option value="fa" selected>فارسی<\/option>/);
  assert.match(html, /تمام‌صفحه/);
  assert.match(html, /خروج از حساب/);
  assert.match(html, /خروج از حساب/);
});

test("full-screen control changes to return-to-normal-view while active", () => {
  const state = createVisualDemoState("en");
  state.fullscreen = true;
  const html = renderVisualDemo(state);

  assert.match(html, /aria-pressed="true"/);
  assert.match(html, />Return to normal view<\/button>/);
});

test("WBS Activities and Dates tabs show scoped activity records and derived sample date bounds", () => {
  const activities = createVisualDemoState("en");
  activities.window = "wbs";
  activities.selectedWbsCode = "1.2";
  activities.wbsDetailTab = "activities";
  const activityHtml = renderVisualDemo(activities);

  assert.match(activityHtml, /cp-vd-wbs-activity-table/);
  assert.match(activityHtml, /A1110/);
  assert.match(activityHtml, /Process and hydraulic design/);
  assert.match(activityHtml, /Civil and structural design/);
  assert.match(activityHtml, /% complete/);

  const dates = createVisualDemoState("en");
  dates.window = "wbs";
  dates.selectedWbsCode = "1.2";
  dates.wbsDetailTab = "dates";
  const dateHtml = renderVisualDemo(dates);
  assert.match(dateHtml, /Earliest activity start/);
  assert.match(dateHtml, /Latest activity finish/);
  assert.match(dateHtml, /02\/11\/26/);
  assert.match(dateHtml, /21\/12\/26/);
});

test("activity network uses the typed relationship register and includes all linked activities", () => {
  const state = createVisualDemoState("en");
  state.window = "network";
  const html = renderVisualDemo(state);

  assert.match(html, /12 boxes · 8 typed links/);
  for (const id of ["A1010", "A1110", "A1120", "A1130", "A1210", "A1220", "A1310", "A1320", "A1330", "A1340", "A1350"]) {
    assert.match(html, new RegExp(`data-vd-node="${id}"`));
  }
  assert.match(html, /data-vd-node="A1350"/);
  assert.match(html, /cp-vd-node-links/);
});

test("WBS window renders a selectable hierarchy and a dedicated details inspector", () => {
  const state = createVisualDemoState("en");
  state.window = "wbs";
  state.selectedWbsCode = "1.2";
  const html = renderVisualDemo(state);

  assert.match(html, /cp-vd-wbs-layout/);
  assert.match(html, /data-vd-wbs="1\.2"/);
  assert.match(html, /Engineering/);
  assert.match(html, /data-vd-wbs-toggle="1"/);
  assert.match(html, /data-vd-wbs-dtab="general"/);
  assert.match(html, /Selected WBS element/);
  assert.match(html, /Parent code/);
  assert.match(html, /Visual sample only/);
  assert.doesNotMatch(html, /data-vd-wbs="1\.2\.1"[^>]*aria-selected="true"/);
});

test("WBS detail tab state is rendered as the active accessible tab", () => {
  const state = createVisualDemoState("fa");
  state.window = "wbs";
  state.selectedWbsCode = "1.2.1";
  state.wbsDetailTab = "dates";
  const html = renderVisualDemo(state);

  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /data-vd-wbs="1\.2\.1"[^>]*aria-selected="true"/);
  assert.match(html, /data-vd-wbs-dtab="dates" aria-selected="true" class="is-active"/);
  assert.match(html, /04\/12\/26/);
});

test("calendar editor presents properties, workweek and exception panes", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  assert.match(html, /data-vd-dialog="calendar"/);
  assert.match(html, /cp-vd-calendar-editor/);
  assert.match(html, /Calendar properties/);
  assert.match(html, /Workweek/);
  assert.match(html, /Exceptions and holidays/);
  assert.match(html, /2027-03-20/);
  assert.match(html, /not saved or used for scheduling/);
});


test("Activities window switches to an explicit relationship register with all four link types and signed lag", () => {
  const state = createVisualDemoState("en");
  state.activityView = "relationships";
  const html = renderVisualDemo(state);

  assert.match(html, /data-vd-activity-view="relationships"[^>]*aria-pressed="true"/);
  assert.match(html, /Activity relationships/);
  for (const type of ["FS", "SS", "FF", "SF"]) assert.match(html, new RegExp(`cp-vd-rel-type[^>]*>${type}<`));
  assert.match(html, /\+2 d/);
  assert.match(html, /-1 d/);
  assert.match(html, /Visual sample only\. Relationship rows and lag values are illustrative/);
  assert.doesNotMatch(html, /cp-vd-gantt-body/);
});

test("relationship register has Persian labels and preserves the RTL visual shell", () => {
  const state = createVisualDemoState("fa");
  state.activityView = "relationships";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /روابط فعالیت‌ها/);
  assert.match(html, /تأخیر \/ پیش‌افتادگی/);
  assert.match(html, /ذخیره یا در موتور زمان‌بندی استفاده نمی‌شوند/);
});


test("selected activity details show configured predecessor and successor relationship type and signed lag", () => {
  const state = createVisualDemoState("en");
  state.activityId = "A1320";
  state.detailTab = "predecessors";
  let html = renderVisualDemo(state);
  assert.match(html, /A1310/);
  assert.match(html, /FS/);
  assert.match(html, /0 d/);
  assert.match(html, /Activity name/);

  state.detailTab = "successors";
  html = renderVisualDemo(state);
  assert.match(html, /A1330/);
  assert.match(html, /SS/);
  assert.match(html, /\+8 h/);

  state.detailTab = "relationships";
  html = renderVisualDemo(state);
  assert.match(html, /Predecessors/);
  assert.match(html, /Successors/);
  assert.match(html, /Relationship type and signed lag are shown exactly/);
});

test("activity relationship detail tabs retain Persian labels and left-to-right IDs and lag values", () => {
  const state = createVisualDemoState("fa");
  state.activityId = "A1320";
  state.detailTab = "successors";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /شناسه فعالیت/);
  assert.match(html, /نام فعالیت/);
  assert.match(html, /A1330/);
  assert.ok(html.includes('<bdi dir="ltr">+8 h</bdi>'));
});


test("activity Status details expose early/late dates, actual dates, duration and float fields", () => {
  const state = createVisualDemoState("en");
  state.detailTab = "status";
  const html = renderVisualDemo(state);
  for (const label of ["Early start", "Early finish", "Late start", "Late finish", "Actual start", "Actual finish", "Original duration", "Remaining duration", "Total float", "Free float", "Critical"]) {
    assert.match(html, new RegExp(label));
  }
});

test("Activity Details uses the desktop tab set, exposes selected record context, and keeps calendar in General", () => {
  const state = createVisualDemoState("fa");
  state.detailTab = "general";
  const html = renderVisualDemo(state);
  assert.doesNotMatch(html, /data-vd-dtab="calendar"/);
  assert.match(html, /data-vd-dtab="custom-fields"/);
  assert.doesNotMatch(html, /data-vd-dtab="udfs"/);
  assert.match(html, /data-vd-details-context-name/);
  assert.match(html, /Project management/);
  assert.match(html, /CUBI-DEMO-001/);
  assert.match(html, /تقویم/);
});


test("activity Resources details expose budgeted, actual and remaining units and costs", () => {
  const state = createVisualDemoState("en");
  state.activityId = "A1320";
  state.detailTab = "resources";
  const html = renderVisualDemo(state);
  for (const label of ["Resource type", "Budgeted units", "Actual units", "Remaining units", "Budgeted cost", "Actual cost", "Remaining cost", "Concrete crew", "Labor"]) {
    assert.match(html, new RegExp(label));
  }
  assert.match(html, /Illustrative assignment values only/);
  assert.match(html, /does not save resource assignments or recalculate costs/);
});


test("Resource Assignments window presents separate resource and role assignment registers with unit and cost columns", () => {
  const state = createVisualDemoState("en");
  state.window = "assignments";
  const html = renderVisualDemo(state);
  assert.match(html, /Resource Assignments/);
  assert.match(html, /Resource assignments/);
  assert.match(html, /Role assignments/);
  for (const label of ["Budgeted units", "Actual units", "Remaining units", "Budgeted cost", "Actual cost", "Remaining cost", "Level resources"]) {
    assert.match(html, new RegExp(label));
  }
  assert.match(html, /not persisted/);
  assert.match(html, /do not run resource leveling or cost calculations/);
});

test("calendar workspace shows calendar definitions and exception registers in both locales", () => {
  const fa = createVisualDemoState("fa");
  fa.window = "calendars";
  const faHtml = renderVisualDemo(fa);
  assert.match(faHtml, /تقویم‌های تعریف‌شده/);
  assert.match(faHtml, /هفته کاری/);
  assert.match(faHtml, /استثناها و تعطیلات/);
  assert.match(faHtml, /تعطیلات نوروز/);
  const en = createVisualDemoState("en");
  en.window = "calendars";
  const enHtml = renderVisualDemo(en);
  assert.match(enHtml, /Available calendars/);
  assert.match(enHtml, /Exceptions and holidays/);
  assert.match(enHtml, /Reduced shift/);
  assert.match(enHtml, /not saved or applied to schedule calculations/);
});

test("Resources and Roles have independent Primavera-style dictionaries and Persian RTL labels", () => {
  const resources = createVisualDemoState("fa");
  resources.window = "resources";
  const resourceHtml = renderVisualDemo(resources);
  assert.match(resourceHtml, /data-visual-demo dir="rtl"/);
  assert.match(resourceHtml, /واژه‌نامه منابع/);
  assert.match(resourceHtml, /شناسه منبع/);
  assert.match(resourceHtml, /نیروی انسانی/);
  assert.match(resourceHtml, /تجهیزات/);

  const roles = createVisualDemoState("fa");
  roles.window = "roles";
  const roleHtml = renderVisualDemo(roles);
  assert.match(roleHtml, /نقش‌ها/);
  assert.match(roleHtml, /واژه‌نامه نقش‌ها و ظرفیت/);
  assert.match(roleHtml, /شناسه نقش/);
  assert.match(roleHtml, /ظرفیت/);
  assert.match(roleHtml, /نرخ و ظرفیت در این پیش‌نمایش هزینه پروژه یا تسطیح منابع را محاسبه نمی‌کنند/);
});


test("Version 26 Gantt visual surface exposes dedicated controls for chart layers and annotations", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  for (const label of ["Background Lines…", "Relationship Lines…", "Data Date Line…", "Legend…", "Progress Line…", "Attachments…", "Collapsed Bars…"]) {
    assert.ok(html.includes(label), `expected Gantt command: ${label}`);
  }
  for (const dialog of ["background-lines", "relationship-lines", "data-date-line", "gantt-legend", "progress-line", "attachments", "collapsed-bars"]) {
    assert.match(html, new RegExp(`data-vd-dialog="${dialog}"`));
  }
  for (const control of ["Major vertical lines", "Arrowhead", "Display data date line", "Show legend", "Display progress line", "Add curtain", "Show all", "Delete selected", "Remove text", "Attach notebook", "Customize collapsed bars"]) {
    assert.ok(html.includes(control), `expected Gantt detail control: ${control}`);
  }
  assert.match(html, /non-persistent visual examples/);
});

test("Version 26 Gantt presentation commands are localized and preserve Persian RTL layout", () => {
  const state = createVisualDemoState("fa");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["خطوط پس‌زمینه…", "خطوط روابط…", "خط تاریخ داده…", "راهنما…", "خط پیشرفت…", "پیوست‌ها…", "میله‌های جمع‌شده…"]) {
    assert.ok(html.includes(label), `expected Persian Gantt command: ${label}`);
  }
  assert.match(html, /خطوط پس‌زمینه گانت/);
  assert.match(html, /تنظیمات خطوط روابط/);
});


test("Activity Network and Trace Logic expose Version 26 layout and inspection preferences", () => {
  const network = createVisualDemoState("en");
  network.window = "network";
  const networkHtml = renderVisualDemo(network);
  assert.match(networkHtml, /data-vd-dialog="network-box-layout"/);
  assert.match(networkHtml, /Box layout/);
  const trace = createVisualDemoState("en");
  trace.window = "trace";
  const traceHtml = renderVisualDemo(trace);
  assert.match(traceHtml, /data-vd-dialog="trace-options"/);
  assert.match(traceHtml, /Trace preferences/);
  assert.match(traceHtml, /Predecessor levels/);
  assert.match(traceHtml, /Successor levels/);
  assert.match(traceHtml, /relationship type and lag/i);
  assert.match(traceHtml, /Orthogonal/);
});

test("Activity and Resource Usage Profile and Spreadsheet expose display and data-field controls", () => {
  for (const window of ["activity-profile", "resource-profile", "activity-sheet", "resource-sheet"] as const) {
    const state = createVisualDemoState("en");
    state.window = window;
    const html = renderVisualDemo(state);
    assert.match(html, /data-vd-dialog="usage-profile-options"/);
    assert.match(html, /Profile options|Data fields/);
  }
  const state = createVisualDemoState("en");
  state.window = "resource-profile";
  const html = renderVisualDemo(state);
  for (const option of ["Regular histogram", "Stacked histogram", "Financial period", "Budgeted units", "Actual units", "Remaining units", "Show resource availability", "Show resource limits", "Highlight overallocation"]) {
    assert.ok(html.includes(option), `expected usage display option: ${option}`);
  }
});


test("Activity table formatting exposes independent table and group-band typography controls", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-vd-dialog="font-row"/);
  for (const control of ["Activity table appearance", "Table font", "Text color", "Row height", "Row background", "Grid lines", "Group row appearance", "Group font", "Group text color", "Group background", "Group row height", "Group band format", "Show empty title bands", "Page break after each group"]) {
    assert.ok(html.includes(control), `expected table-format control: ${control}`);
  }
});


test("Gantt bar editor presents independent definitions, styles, settings, labels and preview controls", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  for (const value of ["Remaining Work", "Actual Work", "Critical Remaining", "Primary Baseline", "Target", "Level of Effort", "Milestone", "Bar Style", "Bar Settings", "Bar Labels", "Copy From…", "Necking", "Start point", "End point", "Left label", "Right label", "Top label", "Bottom label", "Live style preview"]) {
    assert.ok(html.includes(value), `expected bar editor element: ${value}`);
  }
  assert.match(html, /data-vd-dialog="bars"/);
  assert.match(html, /data-vd-dialog="bar-options"/);
  assert.match(html, /Show nonworking time/);
});


test("Activity Details customization exposes the complete desktop tab inventory and excludes non-desktop Tasks", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const [id, label] of [
    ["general", "General"],
    ["status", "Status"],
    ["resources", "Resources"],
    ["predecessors", "Predecessors"],
    ["successors", "Successors"],
    ["codes", "Codes"],
    ["discussion", "Discussion"],
    ["notebook", "Notebook"],
    ["steps", "Steps"],
    ["feedback", "Feedback"],
    ["documents", "Documents"],
    ["expenses", "Expenses"],
    ["summary", "Summary"],
    ["relationships", "Relationships"],
    ["risks", "Risks"],
    ["custom-fields", "Custom Fields"],
    ["update-history", "Update History"],
  ] as const) {
    assert.match(html, new RegExp(`data-vd-detail-tab="${id}"`));
    assert.ok(html.includes(label), `missing Details tab label: ${label}`);
  }
  assert.match(html, /Displayed tabs · example order/);
  assert.match(html, /Move General up/);
  assert.match(html, /tab visibility and order are not saved/);
  assert.doesNotMatch(html, /data-vd-detail-tab="tasks"/);
});

test("Activity Details customization provides Persian RTL labels for all standard tabs", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["عمومی", "وضعیت", "منابع", "پیش‌نیازها", "جانشین‌ها", "گفت‌وگو", "دفترچه", "گام‌ها", "بازخورد", "اسناد", "هزینه‌ها", "روابط", "ریسک‌ها", "فیلدهای سفارشی", "تاریخچه تغییرات"]) {
    assert.ok(html.includes(label), `missing Persian Details tab label: ${label}`);
  }
});


test("Activity Details renders a truthful no-selection state instead of silently selecting the first activity", () => {
  const state = createVisualDemoState("en");
  state.activityId = "";
  const html = renderVisualDemo(state);
  assert.match(html, /No activity selected/);
  assert.match(html, /Select an activity in the table or Activity Network/);
  assert.doesNotMatch(html, /<span class="cp-vd-details-context-name"/);
});

test("Activity Details context and empty state are localized in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.activityId = "";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /فعالیتی انتخاب نشده است/);
  assert.match(html, /برای مشاهده جزئیات، یک فعالیت را از جدول یا شبکه فعالیت انتخاب کنید/);
});


test("Activity General and Status Details expose the complete field groups without inventing unavailable values", () => {
  const general = createVisualDemoState("en");
  general.detailTab = "general";
  let html = renderVisualDemo(general);
  for (const field of ["Project", "Activity duration type", "Responsible manager", "Primary constraint", "Secondary constraint", "Expected finish", "Description", "Notebook summary"]) {
    assert.ok(html.includes(field), `missing General field: ${field}`);
  }
  assert.match(html, /Primary constraint[\s\S]*?<input value="—"/);

  const status = createVisualDemoState("en");
  status.detailTab = "status";
  html = renderVisualDemo(status);
  for (const field of ["Duration % complete", "Units % complete", "Physical % complete", "Actual start", "Actual finish", "Remaining start", "Remaining finish", "Suspend date", "Resume date", "Data date"]) {
    assert.ok(html.includes(field), `missing Status field: ${field}`);
  }
});

test("Activity Resources Details show capacity and assignment context fields without fabricated values", () => {
  const state = createVisualDemoState("en");
  state.activityId = "A1320";
  state.detailTab = "resources";
  const html = renderVisualDemo(state);
  for (const field of ["Units/Time", "Driving", "Assignment calendar", "Budgeted units", "Actual units", "Remaining units", "Budgeted cost", "Actual cost", "Remaining cost"]) {
    assert.ok(html.includes(field), `missing Resources field: ${field}`);
  }
  assert.match(html, /<td>—<\/td><td>—<\/td><td>—<\/td>/);
});


test("Filters dialog exposes categorized filters, All/Any matching, parameter/operator/value rows and management controls", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const text of ["Available filters", "Default", "Global", "Layout", "User-defined", "All selected filters", "Any selected filter", "Filter definition", "All of the following", "Any of the following", "Parameter", "Operator", "Value", "Is within range of", "Current Date + 6w", "Optimize", "Make Global"]) {
    assert.ok(html.includes(text), `missing filter dialog control: ${text}`);
  }
  assert.match(html, /cp-vd-filter-manager/);
  assert.match(html, /Criteria, operators, All\/Any logic/);
});

test("Filters dialog presents localized Persian controls and truthful preview-only status", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const text of ["فیلترهای موجود", "پیش‌فرض", "سراسری", "چیدمان", "تعریف‌شده توسط کاربر", "نمایش فعالیت‌های منطبق با", "همه موارد زیر", "هر یک از موارد زیر"]) {
    assert.ok(html.includes(text), `missing Persian filter label: ${text}`);
  }
  assert.match(html, /هیچ موردی اعمال یا ذخیره نمی‌شود/);
});


test("Group and Sort dialog supports hierarchical grouping, multiple sort levels and complete band formatting controls", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Group By", "Up to 20 grouping levels", "WBS Path", "To level", "All levels", "Font & Color", "Show field title", "Show ID / Code", "Show Name / Description", "Show empty title bands", "Page break after group band", "Show group totals", "Show grand total", "Multiple sort criteria", "Hierarchical", "Grouping is applied before sorting"]) {
    assert.ok(html.includes(label), `missing Group and Sort control: ${label}`);
  }
  assert.match(html, /cp-vd-group-sort/);
  assert.match(html, /aria-label="Group field"/);
  assert.match(html, /aria-label="Sort field"/);
  assert.match(html, /Group levels, sort criteria, band formatting/);
});

test("Group and Sort dialog exposes Persian RTL labels and the WBS-first default", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["گروه‌بندی بر اساس", "تا ۲۰ سطح گروه‌بندی", "مرتب‌سازی", "تا سطح", "قلم و رنگ", "گروه‌بندی پیش از مرتب‌سازی اعمال می‌شود"]) {
    assert.ok(html.includes(label), `missing Persian Group and Sort label: ${label}`);
  }
});


test("Timescale dialog exposes two/three-line, start date, primary/ordinal, fiscal and financial-period controls", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Timescale lines", "Two Lines", "Three Lines", "Timescale start", "Date interval", "Day / Shift", "Year / Financial Period", "Type", "Calendar", "Fiscal", "Date Format", "Show Primary Dates", "Show Ordinal Dates", "Primary date format", "Ordinal start", "Ordinal interval", "Shift calendar", "Financial period calendar", "Font & Color", "Default Font", "Preview"]) {
    assert.ok(html.includes(label), `missing Timescale control: ${label}`);
  }
  assert.match(html, /cp-vd-timescale-preview/);
  assert.match(html, /do not change project dates or calendar rules/);
});

test("Timescale dialog localizes Persian headings and preserves the visual RTL shell", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["ردیف‌های مقیاس زمانی", "شروع مقیاس زمانی", "بازه تاریخ", "قالب تاریخ", "نمایش تاریخ‌های اصلی", "نمایش تاریخ‌های ترتیبی", "شروع ترتیبی", "تقویم شیفت", "تقویم دوره مالی", "قلم و رنگ"]) {
    assert.ok(html.includes(label), `missing Persian Timescale label: ${label}`);
  }
});


test("Columns dialog exposes available/selected lists, transfer, ordering, title, width, alignment and copy-from controls", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Available Columns Options", "Find a column", "Group available columns", "Expand All", "Collapse All", "Available Columns", "Selected Options", "Edit Column", "Column title", "Width", "Alignment", "Visible", "Copy From", "Default", "at least one visible column"]) {
    assert.ok(html.includes(label), `missing Columns control: ${label}`);
  }
  assert.match(html, /cp-vd-columns-transfer/);
  assert.match(html, /data-vd-selected-column=/);
  assert.match(html, /title="Preview only"/);
});

test("Columns dialog localizes Persian labels and shows the one-column minimum", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["ستون‌های موجود", "گزینه‌های انتخاب‌شده", "ویرایش ستون", "عنوان ستون", "عرض", "تراز", "کپی از", "هر چیدمان باید دست‌کم یک ستون نمایان داشته باشد"]) {
    assert.ok(html.includes(label), `missing Persian Columns label: ${label}`);
  }
});


test("New Project dialog exposes the four-step domain, identity, configuration and development wizard", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Business Domain", "Project Identity", "Planning Configuration", "Project Development", "Business domain", "Portfolio", "Responsible organization", "Project name", "Project ID", "Description", "Start date", "Target finish", "Date system", "Project calendar", "Default activity duration type", "WBS template", "Copy from project", "Create starter WBS and activities", "Create Project"]) {
    assert.ok(html.includes(label), `missing New Project wizard field: ${label}`);
  }
  assert.match(html, /cp-vd-project-steps/);
  assert.match(html, /name="projectId" required/);
  assert.match(html, /name="projectName" required/);
  assert.match(html, /Required fields are marked/);
  assert.match(html, /not connected in this visual preview/);
});

test("New Project wizard has Persian RTL labels for all four steps and calendar options", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["حوزه کسب‌وکار", "مشخصات پروژه", "پیکربندی برنامه‌ریزی", "توسعه ساختار پروژه", "نام پروژه", "شناسه پروژه", "تاریخ شروع", "پایان هدف", "سیستم تاریخ", "تقویم پروژه", "قالب ساختار شکست کار"]) {
    assert.ok(html.includes(label), `missing Persian New Project label: ${label}`);
  }
});


test("Layout Manager exposes scoped layouts, properties, preview and PLF interchange without fake persistence", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-vd-dialog="layout-manager"/);
  for (const label of ["Available layouts", "Layout properties", "CUBI Classic Schedule", "Cost and Resource Control", "Commissioning Look-ahead", "Executive Milestones", "Another User", "Current User", "All Users", "Project", "Apply", "Save As…", "Import .PLF…", "Export .PLF…", "Use as default layout for this project"]) {
    assert.ok(html.includes(label), `missing Layout Manager control: ${label}`);
  }
  assert.match(html, /cp-vd-layout-manager-grid/);
  assert.match(html, /layout storage is not connected/i);
  assert.match(html, /<button type="button" disabled>.*Import \.PLF/s);
});

test("Layout Manager localizes its scope and property controls in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["چیدمان‌های موجود", "مشخصات چیدمان", "دامنه", "مالک", "آخرین تغییر", "شرح", "ذخیره با نام…", "ورود فایل .PLF…", "خروجی فایل .PLF…", "استفاده به‌عنوان چیدمان پیش‌فرض پروژه"]) {
    assert.ok(html.includes(label), `missing Persian Layout Manager label: ${label}`);
  }
});


test("Resource assignment dialog exposes resource catalogue and assignment parameters without mutating data", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  for (const label of ["Assign resources to activity", "Available resources", "Resource type", "Budget units", "Budget cost", "Rate / unit", "Assignment details", "Units / time", "Rate type", "Resource calendar", "Assignment start", "Assignment finish", "Resource curve", "Cost account", "Resource catalogue figures are demonstration data", "assignment, availability, cost recalculation"]) {
    assert.ok(html.includes(label), `missing resource assignment control: ${label}`);
  }
  assert.match(html, /cp-vd-assignment-grid/);
  assert.match(html, /data-vd-dialog="assign-resources"/);
});

test("Role assignment keeps role requirements distinct from resource assignments and localizes RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["تخصیص نقش به فعالیت", "واحد نقش", "حداکثر واحد \/ زمان", "سطح مهارت", "منبع نامزد", "نیاز نقش و تخصیص منبع دو رکورد مستقل هستند"]) {
    assert.ok(html.includes(label), `missing Persian role assignment control: ${label}`);
  }
});


test("Assign resources by role presents eligible resources and explicit rate-source handling", () => {
  const state = createVisualDemoState("en");
  state.window = "activities";
  const html = renderVisualDemo(state);
  for (const label of ["Assign resources by role", "Eligible resources", "Required role", "Proficiency", "Assignment units", "Rate source", "Prompt when resource and role share an assignment", "The role remains the requirement"]) {
    assert.ok(html.includes(label), `missing assign-by-role control: ${label}`);
  }
  assert.match(html, /data-vd-dialog="assign-resources-by-role"/);
  assert.match(html, /data-vd-dialog="assign-resources"/);
  assert.match(html, /Rate source/);
  assert.match(html, /Price \/ unit override/);
  assert.match(html, /Primary resource/);
});

test("Assign resources by role dialog is localized for Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "activities";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["تخصیص منابع بر اساس نقش", "منابع واجد شرایط", "نقش موردنیاز", "سطح مهارت", "واحد تخصیص", "منبع نرخ", "نقش به‌عنوان نیاز باقی می‌ماند"]) {
    assert.ok(html.includes(label), `missing Persian assign-by-role label: ${label}`);
  }
});


test("Project Details dialog exposes the desktop project tab inventory and project defaults", () => {
  const state = createVisualDemoState("en");
  state.window = "projects";
  const html = renderVisualDemo(state);
  for (const label of ["General", "Dates", "Notebook", "Budget Log", "Spending Plan", "Budget Summary", "Funding", "Codes", "Defaults", "Resources", "Settings", "Calculations", "Custom Fields", "Project ID", "Responsible manager", "EPS / Portfolio", "Planned start", "Must finish by", "Data date", "Anticipated start", "Default activity type", "Default duration type", "Percent complete type", "Default activity calendar", "Default rate type", "Default cost account", "Drive activity dates by default"]) {
    assert.ok(html.includes(label), `missing Project Details field or tab: ${label}`);
  }
  assert.match(html, /cp-vd-project-tabs/);
  assert.match(html, /aria-selected="true"/);
  assert.match(html, /read-only/);
  assert.match(html, /Planning Resources tab is intentionally excluded/);
});

test("Project Details dialog localizes project tabs and date/default fields in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "projects";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["تاریخ‌ها", "دفترچه", "گزارش بودجه", "برنامه هزینه", "خلاصه بودجه", "تأمین مالی", "پیش‌فرض‌ها", "محاسبات", "شناسه پروژه", "تاریخ داده", "نوع مدت پیش‌فرض", "تقویم فعالیت پیش‌فرض", "پیش‌فرض تخصیص منابع"]) {
    assert.ok(html.includes(label), `missing Persian Project Details label: ${label}`);
  }
});


test("Calendar dictionary and editor expose all three pools, inheritance, exceptions and time-period conversion", () => {
  const state = createVisualDemoState("en");
  state.window = "calendars";
  const html = renderVisualDemo(state);
  for (const label of ["Global", "Project", "Resource", "Shared Resource Shift", "Personal Resource Calendar", "Add…", "Modify…", "Delete", "Used By…", "Calendar pool", "Parent global calendar", "Standard workweek", "Total work hours/day", "Detailed work hours/day", "Work", "Nonwork", "Standard", "Hours per time period", "Hours per week", "Hours per month", "Hours per year", "manual future-period assignment values"]) {
    assert.ok(html.includes(label), `missing calendar control or concept: ${label}`);
  }
  assert.match(html, /cp-vd-calendar-pools/);
  assert.match(html, /cp-vd-calendar-editor-bottom/);
  assert.match(html, /Calendar inheritance/);
});

test("Calendar dictionary and editor expose Persian RTL labels and conversion warnings", () => {
  const state = createVisualDemoState("fa");
  state.window = "calendars";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["مخازن تقویم", "سراسری", "پروژه", "منبع", "تقویم والد", "هفته کاری استاندارد", "مجموع ساعات کاری روز", "جزئیات ساعات کاری روز", "ساعات هر دوره زمانی", "موارد استفاده…", "تقویم‌های پروژه و منابعِ پیوندخورده"]) {
    assert.ok(html.includes(label), `missing Persian calendar label: ${label}`);
  }
});


test("Resource dictionary follows desktop columns and exposes the resource detail pane", () => {
  const state = createVisualDemoState("en");
  state.window = "resources";
  const html = renderVisualDemo(state);
  for (const label of ["Resource hierarchy and dictionary", "Resource ID", "Resource name", "Unit of measure", "Primary role", "Default units/time", "Calendar", "Average unit rate", "Delete / Merge", "Resource Details", "Ready-mix concrete C30", "Material"]) {
    assert.ok(html.includes(label), `missing resource dictionary control: ${label}`);
  }
  assert.match(html, /cp-vd-resource-table/);
  assert.match(html, /data-vd-dialog="resource-details"/);
  assert.match(html, /resource rates over time, shifts, calendars, roles, codes/);
});

test("Resource Details follows the desktop General, Codes, Details, Units & Prices, Roles, Notes and Custom Fields tabs", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Resource detail sections", "Units & Prices", "Employee ID", "E-mail address", "Office phone", "Active resource — available for assignment", "Maximum units/time", "Price factor", "Assigned roles", "Resource codes", "Progress Reporter tab is excluded"]) {
    assert.ok(html.includes(label), `missing Resource Details field or tab: ${label}`);
  }
  assert.match(html, /data-vd-dialog="resource-details"/);
  assert.match(html, /cp-vd-resource-detail-body/);
});

test("Resource Details exposes localized tabs and fields in Persian RTL", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["جزئیات منبع", "کدها", "واحدها و قیمت‌ها", "شناسه کارمند", "تقویم منبع", "شیفت", "نقش‌ها و کدها", "فیلدهای سفارشی"]) {
    assert.ok(html.includes(label), `missing Persian Resource Details label: ${label}`);
  }
});


test("Resource shift dialog shows effective dates, weekly periods and capacity separation", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Define shifts…", "Resource shifts", "Shift name", "Shift calendar", "Effective start", "Effective finish", "Shift pattern", "Hours per shift", "Daily shift periods", "Net work hours", "Allow overtime", "Shift definitions are separate from the base calendar"]) {
    assert.ok(html.includes(label), `missing resource shift control: ${label}`);
  }
  assert.match(html, /data-vd-dialog="resource-shifts"/);
});

test("Resource shift dialog has Persian RTL labels", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["شیفت‌های منابع", "نام شیفت", "تقویم شیفت", "شروع اعتبار", "پایان اعتبار", "الگوی شیفت", "بازه‌های روزانه شیفت", "ساعات خالص کار", "اجازه اضافه‌کاری"]) {
    assert.ok(html.includes(label), `missing Persian resource shift label: ${label}`);
  }
});


test("Print preview and Page Setup expose page navigation, scaling, paper, margins, headers and sheet options", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["Print preview toolbar", "Page 1 of 3", "Page Setup…", "Print Setup…", "Activity Schedule", "Portrait", "Landscape", "Page", "Margins", "Header/Footer", "Sheet", "Adjust to", "Fit to", "Fit timescale to", "Paper size", "A4", "Top", "Bottom", "Header left", "Footer right", "Date range", "Pages wide", "Columns to print", "Repeat table on every page", "Print with gradient", "Tiled page order", "Printer selection and properties", "Save as PDF"]) {
    assert.ok(html.includes(label), `missing print/page setup control: ${label}`);
  }
  assert.match(html, /data-vd-dialog="page-setup"/);
  assert.match(html, /data-vd-dialog="print-setup"/);
  assert.match(html, /cp-vd-print-stage/);
});

test("Print preview and Page Setup localize orientation, margins and sheet controls in Persian RTL", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["پیش‌نمایش چاپ", "تنظیم صفحه…", "تنظیم چاپ…", "جهت صفحه", "عمودی", "افقی", "مقیاس‌بندی", "اندازه کاغذ", "حاشیه‌ها", "سربرگ / پابرگ", "گزینه‌های برگه", "تکرار جدول در همه صفحات", "ترتیب صفحات کاشی‌شده", "انتخاب چاپگر و مشخصات آن"]) {
    assert.ok(html.includes(label), `missing Persian print label: ${label}`);
  }
});


test("Enterprise code dictionaries distinguish activity, project, resource and role scopes", () => {
  const state = createVisualDemoState("en");
  state.window = "administration";
  state.adminSection = "codes";
  const html = renderVisualDemo(state);
  for (const label of ["Code dictionary", "All code types", "Activity", "Project", "Resource", "Role", "Global", "EPS", "PHASE", "DISC", "AREA", "CONTRACT", "TRADE", "DISC-ROLE", "Value colors", "Promote Scope…", "Assigned", "Activity codes can be global, EPS-level or project-level"]) {
    assert.ok(html.includes(label), `missing code dictionary control: ${label}`);
  }
  assert.match(html, /cp-vd-code-dictionary/);
  assert.match(html, /cp-vd-code-swatch/);
});

test("Enterprise code dictionary labels are localized in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "administration";
  state.adminSection = "codes";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["واژه‌نامه کد", "نوع کد", "دامنه", "مقادیر", "رنگ مقادیر", "تخصیص‌یافته", "ارتقای دامنه…", "کدهای پروژه، منبع و نقش واژه‌نامه مستقل دارند"]) {
    assert.ok(html.includes(label), `missing Persian code dictionary label: ${label}`);
  }
});


test("Budget, earned value, expenses and cost-account dialogs expose the Version 26 financial workflow", () => {
  const state = createVisualDemoState("en");
  state.window = "cost-control";
  const html = renderVisualDemo(state);
  for (const label of ["Budget and Spending Plan", "Budget Log and Changes", "Funding Sources and Assignments", "Monthly Spending Plan", "Financial period", "Earned Value Analysis", "Earned Value Calculation Settings", "Planned Value (PV)", "Earned Value (EV)", "Actual Cost (AC)", "Schedule Variance (SV)", "Cost Variance (CV)", "SPI", "CPI", "Expense Details", "Accrual type", "Cost Account Dictionary"]) {
    assert.ok(html.includes(label), `missing financial control: ${label}`);
  }
  for (const name of ["budgeting", "earned-value", "expense-details", "cost-accounts", "store-period-performance"]) {
    assert.match(html, new RegExp(`data-vd-dialog="${name}"`));
  }
  assert.match(html, /not saved or posted/);
});

test("Progress update, apply actuals and period close dialogs are present and localized in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "progress-control";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["به‌روزرسانی پیشرفت فعالیت", "نوع درصد پیشرفت", "درصد پیشرفت فیزیکی", "شروع واقعی", "مدت باقی‌مانده", "اعمال واقعیات", "تاریخ داده", "ثبت عملکرد دوره", "دوره مالی", "عملیات پیشرفت", "زمان‌بندی نمی‌کند"]) {
    assert.ok(html.includes(label), `missing Persian progress control: ${label}`);
  }
  for (const name of ["update-progress", "apply-actuals", "store-period-performance"]) {
    assert.match(html, new RegExp(`data-vd-dialog="${name}"`));
  }
});

test("Global Change exposes conditions, Then/Else statements, preview exceptions and commit safeguards", () => {
  const state = createVisualDemoState("en");
  state.window = "cost-control";
  const html = renderVisualDemo(state);
  for (const label of ["Global Change Specification", "Available to", "Change subject", "Activities", "Resource Assignments", "Project Expenses", "If — Conditions", "Then / Else Statements", "Preview Change Report", "Old value", "New value", "Exception", "exclude exception rows"]) {
    assert.ok(html.includes(label), "missing Global Change control: " + label);
  }
  assert.match(html, /data-vd-dialog="global-change"/);
  assert.match(html, /data-vd-dialog="recalculate-assignment-costs"/);
  assert.match(html, /no project values are changed/);
});

test("Reports runner exposes library, scope, import/export, batch and run parameters", () => {
  const state = createVisualDemoState("en");
  state.window = "reports";
  const html = renderVisualDemo(state);
  for (const label of ["Report Library", "Global", "Project", "Run Batch", "Import", "Export", "Report Wizard", "Report Editor", "Groups / Batches", "Run Parameters", "Output format", "Output destination"]) {
    assert.ok(html.includes(label), "missing report runner control: " + label);
  }
  assert.match(html, /data-vd-dialog="reports-runner"/);
  assert.match(html, /report execution are not connected/);
});

test("Threshold monitor and issue navigator expose thresholds, responsibility and issue history", () => {
  const state = createVisualDemoState("en");
  state.window = "thresholds";
  const html = renderVisualDemo(state);
  for (const label of ["Monitor / Issue Navigator", "Threshold Monitoring", "Lower / Upper limit", "Assign Responsible", "Generated Issues", "Issue ID", "Issue Details and History", "Tracking layout", "Created · Assigned · Commented"]) {
    assert.ok(html.includes(label), "missing threshold / issue control: " + label);
  }
  assert.match(html, /data-vd-dialog="threshold-monitor"/);
});

test("Global Change dialog is reachable in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "cost-control";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  for (const label of ["تغییر سراسری", "مشخصات تغییر سراسری", "قابل دسترس برای", "موضوع تغییر", "اگر — شروط", "دستورات آنگاه / در غیر این صورت", "پیش‌نمایش گزارش تغییرات"]) {
    assert.ok(html.includes(label), "missing Persian control: " + label);
  }
});

test("Administration covers EPS, OBS, categories, currencies, financial periods and custom fields", () => {
  const state = createVisualDemoState("en");
  state.window = "administration";
  const html = renderVisualDemo(state);
  const panels: string[] = [];
  for (const section of ["users", "security", "eps", "obs", "preferences", "categories", "currencies", "financial-periods", "custom-fields"]) {
    state.adminSection = section;
    const panel = renderVisualDemo(state);
    panels.push(panel);
    assert.match(panel, new RegExp(`data-vd-admin="${section}"[^>]*aria-pressed="true"`));
  }
  const allPanels = panels.join("\\n");
  for (const label of ["Enterprise Project Structure", "Administrative categories", "Set base currency", "Financial periods", "Create batch", "Custom fields", "Indicator", "Formula (read-only)", "Assigned WBS", "Responsible OBS", "rate direction", "Data Limits", "ID Lengths", "Time Periods", "Time abbreviations", "Earned Value", "Every n Weeks", "Every n Months", "Every Year", "Period ends on", "minimum 1 week", "Units per base currency", "Effective date", "Global Security Profiles", "Project Security Profiles", "Module Access Matrix", "Resource access", "Last sign-in", "Project Superuser", "Team Member", "profile label alone"]) {
    assert.ok(allPanels.includes(label), "missing administration control: " + label);
  }
  assert.match(allPanels, /cp-vd-admin-workspace/);
  assert.match(allPanels, /cp-vd-admin-tree/);
  assert.match(allPanels, /cp-vd-admin-summary/);
  assert.match(allPanels, /Rates are illustrative/);
  assert.match(allPanels, /separate from work calendars/);
});

test("Administration hierarchy and financial controls retain RTL layout and Persian labels", () => {
  const state = createVisualDemoState("fa");
  state.window = "administration";
  state.adminSection = "financial-periods";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /دوره‌های مالی/);
  assert.match(html, /تقویم دوره/);
  state.adminSection = "eps";
  const eps = renderVisualDemo(state);
  assert.match(eps, /ساختار سازمانی پروژه‌ها/);
  assert.match(eps, /ساختار سلسله‌مراتبی سبد پروژه/);
});


test("administration visual styles stay on canonical CUBI tokens and mirrored bundles", () => {
  const sourceStyles = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  const publicStyles = readFileSync(new URL("../public/styles.css", import.meta.url), "utf8");
  const adminStyles = sourceStyles.slice(sourceStyles.lastIndexOf("/* Administration workspaces"));

  assert.equal(sourceStyles, publicStyles, "source and public stylesheets must remain byte-identical");
  for (const token of ["--cp-border", "--cp-surface", "--cp-navy", "--cp-blue", "--cp-copper", "--cp-success", "--cp-muted"]) {
    assert.ok(adminStyles.includes(`var(${token})`), `administration styles must use ${token}`);
  }
  assert.doesNotMatch(adminStyles, /#[0-9a-fA-F]{3,8}\\b/, "administration surfaces must not introduce unregistered hard-coded palette values");
});


test("Activity and WBS selection context menus expose scoped commands and safe disabled destructive actions", () => {
  const activity = renderVisualDemo(createVisualDemoState("en"));
  for (const action of ["activity-details", "assign-resources", "add-predecessor", "add-successor", "activity-codes"]) {
    assert.match(activity, new RegExp(`data-vd-context-action="${action}"`));
  }
  assert.match(activity, /aria-label="Selection commands"/);
  assert.match(activity, /Delete Activity/);
  assert.match(activity, /<button type="button" role="menuitem" disabled>Delete Activity/);

  const wbsState = createVisualDemoState("en");
  wbsState.window = "wbs";
  const wbs = renderVisualDemo(wbsState);
  for (const action of ["wbs-details", "wbs-activities", "wbs-add-child"]) {
    assert.match(wbs, new RegExp(`data-vd-context-action="${action}"`));
  }
  assert.match(wbs, /Delete WBS/);
});

test("Context menu labels and selection semantics are available in Persian RTL", () => {
  const state = createVisualDemoState("fa");
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /فرمان‌های انتخاب/);
  assert.match(html, /جزئیات فعالیت…/);
  assert.match(html, /تخصیص منابع…/);
  assert.match(html, /تخصیص پیش‌نیازها…/);
});


test("Import and export dialogs expose file formats, templates, mapping, baseline and conflict controls", () => {
  const state = createVisualDemoState("en");
  state.window = "projects";
  const html = renderVisualDemo(state);
  assert.match(html, /data-vd-dialog="import"/);
  assert.match(html, /data-vd-dialog="export"/);
  for (const label of ["Import action", "Create New", "Add Into Existing Project", "Replace Existing", "Update Existing", "Template Manager", "Resource Only", "Role Only", "Baseline import (XML only)", "Unavailable for XER", "IPMDAR", "CPP", "Field mapping preview", "Calendar reference", "Convert to project / ignore", "Financial-period date alignment", "Export Project Data privilege", "Personal information disclosure", "Stored period performance"]) {
    assert.ok(html.includes(label), "missing interchange control: " + label);
  }
  assert.match(html, /cp-vd-interchange-grid/);
  assert.match(html, /Project Archive \(\.xer\)/);
  assert.match(html, /Structured Project XML \(\.xml\)/);
  assert.doesNotMatch(html, /Primavera|Oracle|P6 XML/);
  assert.match(html, /no file is read, parsed, mapped, validated or imported/);
  assert.match(html, /no project data is serialized and no file is written/);
});

test("Import/export mapping workbench is mirrored for Persian RTL", () => {
  const state = createVisualDemoState("fa");
  state.window = "projects";
  const html = renderVisualDemo(state);
  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.ok(html.includes("ورود / خروجی"));
  assert.match(html, /پیش‌نمایش بصری است/);
});


test("Workspace menu hierarchy exposes project, organization, tools and administration commands", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  for (const label of ["File", "Edit", "View", "Project", "Organization", "Tools", "Administration", "Help", "Close project", "Save layout as…", "Collapse To…", "Enterprise Project Structure", "Responsibility Structure (OBS)", "Currencies…", "Financial Periods…", "Administrative Categories…", "Global Change…", "Recalculate Assignment Costs…", "Threshold Monitor…", "Update Progress…", "Apply Actuals…", "Store Period Performance…", "Report Library / Runner…"]) {
    assert.ok(html.includes(label), "missing workspace menu entry: " + label);
  }
  assert.match(html, /adminSection&quot;|adminSection/);
});

test("Workspace menu hierarchy keeps Persian labels for key administration and project tools", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /ساختار سازمانی پروژه‌ها/);
  assert.match(html, /ساختار مسئولیت‌ها/);
  assert.match(html, /دوره‌های مالی…/);
  assert.match(html, /ارزها…/);
  assert.match(html, /تغییر سراسری…/);
  assert.match(html, /ثبت عملکرد دوره…/);
});


test("Visible CUBI workspace preview does not expose external product branding or reference URLs", () => {
  for (const locale of ["en", "fa"]) {
    const html = renderVisualDemo(createVisualDemoState(locale));
    assert.doesNotMatch(html, /Oracle|Primavera|P6 Professional|docs\.oracle\.com/i);
  }
});


test("Version 26 dialog registry renders resource assignment, resource details, shifts and print setup surfaces in both locales", () => {
  for (const locale of ["en", "fa"] as const) {
    const html = renderVisualDemo(createVisualDemoState(locale));
    for (const dialog of ["assign-resources-by-role", "resource-details", "resource-shifts", "page-setup", "print-setup", "collapse-to", "dissolve"]) {
      assert.match(html, new RegExp(`data-vd-dialog="${dialog}"`), `missing ${dialog} dialog in ${locale}`);
    }
    assert.match(html, /Threshold Monitor \/ Issue Navigator|پایش آستانه \/ راهنمای مسائل/);
  }
});
