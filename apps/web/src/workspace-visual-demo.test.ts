import assert from "node:assert/strict";
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
  assert.match(html, /Not available in this visual sample/);
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

test("activity Calendar details link to the visual calendar editor and disclose sample-only values", () => {
  const state = createVisualDemoState("fa");
  state.detailTab = "calendar";
  const html = renderVisualDemo(state);
  assert.match(html, /data-vd-dtab="calendar"/);
  assert.match(html, /data-vd-dialog="calendar"/);
  assert.match(html, /باز کردن ویرایشگر تقویم/);
  assert.match(html, /تقویم فعالیت/);
  assert.match(html, /ذخیره تغییرات و اتصال به زمان‌بندی در این پیش‌نمایش فعال نیست/);
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
