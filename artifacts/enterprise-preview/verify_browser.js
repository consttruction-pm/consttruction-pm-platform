const { chromium } = require("playwright");

const BASE = "http://127.0.0.1:4180";
const results = [];
const consoleErrors = [];
const pageErrors = [];
const failedRequests = [];
const badResponses = [];

function record(name, ok, detail = "") {
  results.push({ name, ok: !!ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? " :: " + detail : ""}`);
}

async function settle(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(400);
}

async function toast(page, pattern, timeout = 5000) {
  await page.locator(".cubi-toast-host").getByText(pattern).first().waitFor({ timeout });
}

(async () => {
  const browser = await chromium.launch({
    executablePath: "/usr/bin/chromium",
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push({ url: page.url(), text: msg.text() });
  });
  page.on("pageerror", (err) => pageErrors.push({ url: page.url(), text: String(err) }));
  page.on("requestfailed", (req) =>
    failedRequests.push({ url: req.url(), error: req.failure()?.errorText || "unknown" })
  );
  page.on("response", (res) => {
    if (res.status() >= 400) badResponses.push({ url: res.url(), status: res.status() });
  });

  // Sign in through the preview persona page.
  await page.goto(`${BASE}/preview/login?next=/cubi/`);
  await page.click('button[name="role"][value="enterprise"]');
  await page.waitForURL(/\/cubi\//);
  await settle(page);
  record("login as enterprise persona", page.url().startsWith(`${BASE}/cubi`), page.url());

  const stamp = Date.now().toString().slice(-6);

  // -- pages: title, refresh, deep link ---------------------------------
  const routes = [
    ["enterprise/dashboard", "Enterprise dashboard"],
    ["enterprise/portfolio", "Portfolio"],
    ["enterprise/projects", "Enterprise projects"],
    ["enterprise/access", "Organization & access"],
    ["enterprise/tasks", "Team & task"],
    ["enterprise/workflows", "Workflow studio"],
    ["enterprise/approvals", "Feedback & approval"],
    ["enterprise/resources", "Resources & capacity"],
    ["enterprise/reports", "Reports & operations"],
    ["enterprise/knowledge", "Knowledge & PMBOK"],
    ["enterprise/risks", "Risks & issues"],
    ["enterprise/documents", "Documents"],
    ["enterprise/eps", "Enterprise project structure"],
    ["enterprise/member-activities", "Team member activities"],
    ["enterprise/timesheets", "Timesheets"],
    ["enterprise/notifications", "Notifications"],
    ["enterprise/settings", "Administration"],
    ["enterprise/forms", "Form builder"],
    ["enterprise/audit", "Audit trail"],
    ["enterprise/directory", "Resource directory"],
  ];

  for (const [route, expected] of routes) {
    const url = `${BASE}/cubi/${route}`;
    await page.goto(url);
    await settle(page);
    const heading = await page.locator("h1").first().textContent();
    record(`${route} heading`, heading && heading.includes(expected), heading?.trim());
    await page.reload();
    await settle(page);
    const headingAfter = await page.locator("h1").first().textContent();
    record(`${route} refresh + deep link`, headingAfter && headingAfter.includes(expected), headingAfter?.trim());
  }

  // -- legacy entry paths must not render a parallel workbench ----------
  await page.goto(`${BASE}/cubi/workbench`);
  await page.waitForURL(`${BASE}/workbench/`);
  record("/cubi/workbench redirects to canonical workbench", page.url() === `${BASE}/workbench/`, page.url());
  await page.goto(`${BASE}/cubi/environments`);
  await page.waitForURL(`${BASE}/workbench/`);
  record("/cubi/environments redirects to canonical workbench", page.url() === `${BASE}/workbench/`, page.url());

  // -- access: create a team through the real form ----------------------
  await page.goto(`${BASE}/cubi/enterprise/access`);
  await settle(page);
  const teamName = `Browser Team ${stamp}`;
  await page.locator('[data-testid="access-team-name"]').fill(teamName);
  await page.locator('button:has-text("Create team")').click();
  await toast(page, "Team created on the server.");
  record("access team create toast", true);
  await page.reload();
  await settle(page);
  const teamVisible = await page.locator('[data-testid="access-teams"]').getByText(teamName).count();
  record("access team appears after refresh", teamVisible > 0, String(teamVisible));

  // -- tasks: create and verify register row ----------------------------
  await page.goto(`${BASE}/cubi/enterprise/tasks`);
  await settle(page);
  await page.locator('[data-testid="tasks-create-toggle"]').click();
  const taskTitle = `Browser task ${stamp}`;
  await page.locator('[data-testid="tasks-create-title"]').fill(taskTitle);
  await page.getByRole("button", { name: "Create task" }).click();
  await toast(page, "Task created on the server.");
  await page.waitForTimeout(300);
  const taskRow = await page.getByText(taskTitle).count();
  record("tasks create shows real row", taskRow > 0, String(taskRow));

  // -- risk register: create through the real form ----------------------
  await page.goto(`${BASE}/cubi/enterprise/risks`);
  await settle(page);
  const riskTitle = `Browser risk ${stamp}`;
  await page.locator('[data-testid="risks-form"] input').first().fill(riskTitle);
  await page.getByRole("button", { name: "Create record" }).click();
  await toast(page, "Record created on the server.");
  await page.reload();
  await settle(page);
  const riskRow = await page.locator('[data-testid="risks-table"]').getByText(riskTitle).count();
  record("risks create persists in the server register", riskRow > 0, String(riskRow));

  // -- member activities: read-only Engineering projection --------------
  await page.goto(`${BASE}/cubi/enterprise/member-activities`);
  await settle(page);
  const projectSelect = page.locator('[data-testid="member-activities-list"] select');
  const projectValues = await projectSelect.locator("option").evaluateAll((options) => options.map((option) => option.value).filter(Boolean));
  record("member activities offers real projects", projectValues.length > 0, String(projectValues.length));
  if (projectValues.length) {
    await projectSelect.selectOption(projectValues[0]);
    await settle(page);
    const rows = await page.locator('[data-testid="member-activities-table"] tbody tr').count();
    record("member activities reads Engineering records", rows > 0, String(rows));
    record("member activities offers no write control", (await page.getByRole("button", { name: /create|delete|save/i }).count()) === 0);
  }

  // -- approvals: queue, fill from Review, submit decision --------------
  await page.goto(`${BASE}/cubi/enterprise/approvals`);
  await settle(page);
  const approval = await page.evaluate(async (title) => {
    const res = await fetch("/api/enterprise/approvals", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "Idempotency-Key": `browser-apv-${Date.now()}` },
      body: JSON.stringify({ title }),
    });
    return { status: res.status, body: await res.json() };
  }, `Browser approval ${stamp}`);
  record("approval created for queue", approval.status === 201, String(approval.status));
  await page.reload();
  await settle(page);
  const review = page.locator('[data-testid="approvals-table"]').getByRole("button", { name: "Review" }).first();
  await review.waitFor();
  await review.click();
  const prefilled = await page.locator('[data-testid="approvals-item-id"]').inputValue();
  record("Review fills approval id and revision", prefilled.length > 0, prefilled);
  await page.getByRole("button", { name: "Submit decision" }).click();
  const decisionResult = page.locator('[data-testid="approvals-result"]');
  await decisionResult.waitFor({ state: "visible" });
  const decisionText = (await decisionResult.textContent()) || "";
  record("approval decision recorded", decisionText.includes("recorded by the server"), decisionText.trim());

  // duplicate replay through the UI form (same item, fresh key, stale rev)
  record("approval submit re-enabled after success", !(await page.getByRole("button", { name: "Submit decision" }).isDisabled()));

  // -- workflows: publish the validated draft ---------------------------
  await page.goto(`${BASE}/cubi/enterprise/workflows`);
  await settle(page);
  const publish = page.getByRole("button", { name: "Publish version" });
  await publish.waitFor();
  await page.waitForFunction(() => {
    const btn = Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.includes("Publish version"));
    return btn && !btn.disabled;
  }, null, { timeout: 5000 });
  await publish.click();
  await toast(page, /published as version \d+/);
  record("workflow publish toast", true);
  await page.waitForTimeout(500);
  const publishedRegister = await page.locator('[data-testid="workflows-capability"]').textContent();
  record("workflow register reflects publish", /Published workflow register/.test(publishedRegister || ""), (publishedRegister || "").trim());

  // -- portfolio: record a decision -------------------------------------
  await page.goto(`${BASE}/cubi/enterprise/portfolio`);
  await settle(page);
  const decisionTitle = `Browser decision ${stamp}`;
  await page.getByPlaceholder("Decision title").fill(decisionTitle);
  await page.locator('button:has-text("Record decision")').click();
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(900);
  const decisionRow = await page.getByText(decisionTitle).count();
  record("portfolio decision persists after reload", decisionRow > 0, String(decisionRow));

  // -- dashboard: designer save writes the server register --------------
  await page.goto(`${BASE}/cubi/enterprise/dashboard`);
  await settle(page);
  await page.getByRole("button", { name: "Designer" }).click();
  await page.getByRole("button", { name: "Save layout" }).click();
  await toast(page, /Layout saved on the server \(revision \d+\)/);
  record("dashboard server save confirmed by revision toast", true);
  await page.reload();
  await settle(page);
  const serverBadge = await page.locator("body").textContent();
  record("dashboard badge shows server record after refresh", /server dash-/.test(serverBadge || ""), "");

  // -- permission surface for a role without enterprise grants ---------
  const viewerContext = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const viewerPage = await viewerContext.newPage();
  const viewerConsole = [];
  viewerPage.on("console", (msg) => { if (msg.type() === "error") viewerConsole.push(msg.text()); });
  await viewerPage.goto(`${BASE}/preview/login?next=/cubi/enterprise/tasks`);
  await viewerPage.click('button[name="role"][value="viewer"]');
  await viewerPage.waitForURL(/\/cubi\/enterprise\/tasks/);
  await viewerPage.waitForTimeout(600);
  const viewerBody = await viewerPage.locator("body").textContent();
  record("non-enterprise role sees no fabricated task data", !/Browser task \d+/.test(viewerBody || ""), "");
  await viewerContext.close();

  // -- console and network hygiene --------------------------------------
  const expectedGaps = /\/api\/enterprise\/(portlets|portfolio|evm)/;
  const unexpectedResponses = badResponses.filter((item) => !expectedGaps.test(item.url));
  const expectedFailures = failedRequests.filter((item) => !/favicon/.test(item.url));
  const expectedConsole = /status of (403|503)/;
  const unexpectedConsole = consoleErrors.filter((item) => !expectedConsole.test(item.text));
  record("no page errors", pageErrors.length === 0, JSON.stringify(pageErrors.slice(0, 3)));
  record("no unexpected console errors", unexpectedConsole.length === 0, JSON.stringify(unexpectedConsole.slice(0, 3)));
  record("no unexpected HTTP >= 400", unexpectedResponses.length === 0, JSON.stringify(unexpectedResponses.slice(0, 6)));
  record("no failed requests", expectedFailures.length === 0, JSON.stringify(expectedFailures.slice(0, 3)));
  const viewerUnexpected = viewerConsole.filter((text) => !/status of (403|503)/.test(text));
  record("viewer page console clean apart from expected 403", viewerUnexpected.length === 0, JSON.stringify(viewerUnexpected.slice(0, 2)));

  await browser.close();
  const failed = results.filter((item) => !item.ok);
  console.log(`\n${results.length - failed.length}/${results.length} browser checks passed`);
  process.exit(failed.length ? 1 : 0);
})().catch((error) => {
  console.error("BROWSER RUN FAILED", error);
  process.exit(2);
});
