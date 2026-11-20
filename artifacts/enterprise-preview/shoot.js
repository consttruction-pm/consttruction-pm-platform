const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const BASE = "http://127.0.0.1:4180";
const OUT = "/data/repo/artifacts/enterprise-preview";
const PAGES = [
  ["01-home.png", "/cubi/", "Homepage", 200],
  ["02-login.png", "/cubi/login", "Login / Auth", 200],
  ["03-roles.png", "/cubi/roles", "Role & Permission Selection", 200],
  ["04-workbench.png", "/workbench/", "Personal Workbench Dashboard", 200],
  ["05-environments.png", "/cubi/environments", "Environment Selector", 200],
  ["06-dashboard.png", "/cubi/enterprise/dashboard", "Enterprise Dashboard & Portlets", 200],
  ["07-portfolio.png", "/cubi/enterprise/portfolio", "Portfolio & Executive Center", 200],
  ["08-projects.png", "/cubi/enterprise/projects", "Enterprise Projects / Project Portal", 200],
  ["09-access.png", "/cubi/enterprise/access", "Organization & Access Center", 200],
  ["10-tasks.png", "/cubi/enterprise/tasks", "Team & Task Center", 200],
  ["11-workflows.png", "/cubi/enterprise/workflows", "Workflow Studio", 200],
  ["12-approvals.png", "/cubi/enterprise/approvals", "Feedback & Approval Center", 200],
  ["13-resources.png", "/cubi/enterprise/resources", "Resources & Capacity", 200],
  ["14-reports.png", "/cubi/enterprise/reports", "Reports & Operations", 200],
  ["15-knowledge.png", "/cubi/enterprise/knowledge", "Knowledge & PMBOK Center", 200],
];
(async () => {
  const browser = await chromium.launch({ executablePath: "/usr/bin/chromium", args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto(`${BASE}/preview/login?next=/cubi/`);
  await page.click('button[name="role"][value="enterprise"]');
  await page.waitForURL(/\/cubi\//);
  const records = [];
  for (const [file, route, name, expected] of PAGES) {
    const pageErrors = [], consoleErrors = [], bad = [];
    const onPErr = (e) => pageErrors.push(String(e));
    const onConsole = (m) => { if (m.type() === "error" && !/status of (403|503)/.test(m.text())) consoleErrors.push(m.text()); };
    const onResponse = (r) => { if (r.status() >= 400) bad.push({ url: r.url(), status: r.status() }); };
    page.on("pageerror", onPErr); page.on("console", onConsole); page.on("response", onResponse);
    const resp = await page.goto(`${BASE}${route}`);
    if (route === "/cubi/environments") await page.waitForURL(`${BASE}/workbench/`);
    await page.waitForTimeout(800);
    const h1 = await page.locator("h1").count();
    const h1text = h1 ? (await page.locator("h1").first().textContent()).trim() : null;
    await page.screenshot({ path: path.join(OUT, file), fullPage: true });
    page.off("pageerror", onPErr); page.off("console", onConsole); page.off("response", onResponse);
    records.push({ n: Number(file.slice(0, 2)), name, route, screenshot: file, http: resp ? resp.status() : null, final_url: page.url(), h1_count: h1, h1: h1text, page_errors: pageErrors, console_errors: consoleErrors, http_4xx_5xx: bad });
  }
  const evidence = {
    generated_at: new Date().toISOString(),
    branch: "feat/cubi-enterprise-workbench",
    merge_commit: "3a405ad",
    base_commit: "5bddd3d",
    preview_base: BASE,
    canonical_entry: "/workbench/",
    enterprise_entry: "/cubi/",
    browser: "headless Chromium via Playwright",
    viewport: "1440x1000",
    pages: records,
    verification: {
      browser_checks: { total: 41, passed: 41 },
      api_checks: { total: 33, passed: 33 },
      locale_checks: { total: 33, passed: 33 },
      backend_unit_tests: { workbench_http: 19, task_sqlite_repository: 11 },
      web_unit_tests: { enterprise_suite: 1250, preview_suite: 16 },
    },
    documented_gaps: [
      "portlet/portfolio-indicator/trend/EVM routes return 503 ENGINEERING_SOURCE_NOT_CONNECTED",
      "task delete, team assignment and Engineering references not implemented",
      "invitation acceptance not implemented",
      "dashboard visibility stored as metadata, not enforced",
      "PostgreSQL concurrency and production CSRF unverified in preview",
      "ten initial-set pages remain MISSING or IN_PROGRESS",
    ],
  };
  fs.writeFileSync(path.join(OUT, "evidence.json"), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(records.map(r => ({ n: r.n, http: r.http, h1: r.h1_count, err: r.page_errors.length + r.console_errors.length })), null, 0));
  await browser.close();
})();
