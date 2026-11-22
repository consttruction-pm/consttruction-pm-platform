import type { PublicPageContext } from "../app.js";
import { ApiError, api, probe, type CapabilityProbe } from "../api.js";
import { BASE_PATH, safeNextPath } from "../router.js";
import { resolveWorkspaceLoginPath } from "../../workspace-visual-demo-route.js";
import { badge, el } from "../ui.js";
import { labelled, note, section, sectionBody, testId, textInput } from "./shared.js";

/**
 * Page 2 — Sign in.
 *
 * Production authentication posts to /api/session and lets the server issue the
 * session cookie. The client never stores roles or decides access. The local
 * preview exposes a separate, clearly labelled demo identity page.
 */

const SECURITY_HELP = "https://docs.oracle.com/cd/G48897_01/p6help/en/9001.htm";
const HELP_TOC = "https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm";

export function renderLogin(ctx: PublicPageContext, host: HTMLElement): void {
  const next = safeNextPath(ctx.query.get("next"));
  const wrap = el("div", { class: "cubi-auth-wrap" });

  // The deployed runtime signs in with the product credential form below. The
  // local preview has no password directory and declares its demo sign-in in a
  // meta tag; posting the email form there would fail, so offer the real path.
  const loginPath = resolveWorkspaceLoginPath();
  if (loginPath !== "/login") {
    renderPreviewSignIn(ctx, wrap, loginPath, next);
    host.append(wrap);
    return;
  }

  const card = el("div", { class: "cubi-auth-card" });
  card.append(
    el("span", { class: "cubi-eyebrow", text: "CUBI IDENTITY" }),
    el("h1", { text: ctx.t("page.login.title") }),
    el("p", { class: "desc", text: ctx.t("page.login.subtitle") }),
  );

  const form = el("form", { class: "cubi-auth-form", attrs: { method: "post", action: "/api/session", novalidate: "novalidate" } });
  const email = testId(textInput({ type: "email", name: "email", placeholder: "name@organization.example", autocomplete: "username", required: true }), "login-email");
  const password = testId(textInput({ type: "password", name: "password", placeholder: "Password", autocomplete: "current-password", required: true }), "login-password");
  const reveal = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Show", attrs: { type: "button" } });
  reveal.addEventListener("click", () => {
    const hidden = password.type === "password";
    password.type = hidden ? "text" : "password";
    reveal.textContent = hidden ? "Hide" : "Show";
  });
  const passwordRow = el("div", { class: "cubi-password-row" }, password, reveal);
  const error = testId(el("p", { class: "cubi-alert cubi-alert-error", attrs: { role: "alert", hidden: "hidden" } }), "login-error");
  const submit = testId(el("button", { class: "cubi-btn cubi-btn-primary", text: ctx.t("common.signIn"), attrs: { type: "submit" } }), "login-submit");

  form.append(
    labelled("Work email", email),
    labelled("Password", passwordRow),
    error,
    submit,
    el("p", { class: "cubi-field-hint", text: "The server resolves your organization, project roles and Enterprise entitlements. This form never stores them." }),
  );

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    error.hidden = true;
    if (!email.value.trim() || !password.value) {
      error.textContent = "Enter both your work email and password.";
      error.hidden = false;
      return;
    }
    submit.disabled = true;
    submit.textContent = "Signing in…";
    void api.login(email.value.trim(), password.value)
      .then(() => {
        // Reload so the shell bootstraps from the server-issued session.
        window.location.assign(next);
      })
      .catch((cause: unknown) => {
        submit.disabled = false;
        submit.textContent = ctx.t("common.signIn");
        if (cause instanceof ApiError && cause.status === 401) {
          error.textContent = "The server rejected these credentials. Check your account with your administrator.";
        } else if (cause instanceof ApiError && cause.status === 403) {
          error.textContent = "This account is not permitted to start a session here.";
        } else if (cause instanceof ApiError && cause.status === 0) {
          error.textContent = "The server could not be reached. Your session was not created.";
        } else {
          const detail = cause instanceof ApiError ? `${cause.code} (HTTP ${cause.status})` : String(cause);
          error.textContent = `Sign-in did not complete: ${detail}. No session was created.`;
        }
        error.hidden = false;
      });
  });

  card.append(
    form,
    el("div", { class: "cubi-auth-form" },
      el("p", { class: "cubi-field-hint", text: "Do not have an account? Accounts are provisioned by an administrator; this product has no self-service role creation." }),
      linkRow("Request access", "/contact/"),
    ),
  );
  wrap.append(card);

  const side = el("aside", { class: "cubi-auth-art" });
  side.append(
    el("span", { class: "cubi-eyebrow", text: "SECURE BY DEFAULT" }),
    el("h2", { text: "One identity, two environments" }),
    el("p", { text: "CUBI Engineering keeps scheduling authority. CUBI Enterprise carries organizational collaboration. The session is shared, but every permission is checked again by the server." }),
    el("div", { class: "cubi-list" },
      securityLine("HttpOnly session cookie", "Scripts cannot read the session identifier."),
      securityLine("Server-side authorization", "Project, tenant and Enterprise entitlements are enforced on each request."),
      securityLine("CSRF-protected mutations", "Writes require the same-origin token issued with the session."),
      securityLine("Audited decisions", "Approvals and access changes record actor and source revision."),
    ),
    el("p", { class: "cubi-field-hint" },
      el("a", { text: "Product Help — About Security", attrs: { href: SECURITY_HELP, target: "_blank", rel: "noopener noreferrer" } }),
      " · ",
      el("a", { text: "Help contents", attrs: { href: HELP_TOC, target: "_blank", rel: "noopener noreferrer" } }),
    ),
  );
  wrap.append(side);
  host.append(wrap);

  // The preview-only identity page is offered only when the local server
  // actually exposes it. It is never presented as production authentication.
  void probe("/preview/health").then((health) => {
    if (health.state === "available") host.append(previewPanel(ctx, next, health));
  });
}

function previewPanel(ctx: PublicPageContext, next: string, health: CapabilityProbe): HTMLElement {
  const card = section("Local preview demo identity", "This panel exists only on the local preview server. It creates a demo session for a fixed persona and is not a production credential.");
  sectionBody(card, demoGrid(next), note(`${ctx.t("common.localOnly")}. Health ${health.status} · ${health.code}. No production account is contacted.`));
  testId(card, "login-preview-panel");
  return card;
}

const PREVIEW_PERSONAS = [
  { role: "enterprise", name: "Enterprise administrator", detail: "Enterprise admin entitlement plus project administration. Best for this workbench." },
  { role: "admin", name: "Project administrator", detail: "Project administration without an Enterprise entitlement." },
  { role: "planner", name: "Planner", detail: "Planning and scheduling in Engineering; read-only Enterprise." },
  { role: "viewer", name: "Viewer", detail: "Read-only project access." },
];

function demoGrid(next: string, action = "/preview/login"): HTMLElement {
  const grid = el("div", { class: "cubi-demo-grid" });
  for (const persona of PREVIEW_PERSONAS) {
    const form = el("form", { attrs: { method: "post", action } });
    const nextInput = el("input");
    nextInput.type = "hidden";
    nextInput.name = "next";
    nextInput.value = next;
    const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: persona.name, attrs: { type: "submit", name: "role", value: persona.role } });
    form.append(nextInput, button);
    const row = el("div", { class: "cubi-demo-role" });
    row.append(el("div", {}, el("strong", { text: persona.name }), el("p", { class: "cubi-field-hint", text: persona.detail })), form);
    grid.append(row);
  }
  return grid;
}

/**
 * Local preview sign-in. The preview server has no password directory and
 * declares its demo endpoint in a meta tag, so the production credential form
 * is replaced with persona buttons instead of failing on submit.
 */
function renderPreviewSignIn(
  ctx: PublicPageContext,
  wrap: HTMLElement,
  loginPath: string,
  next: string,
): void {
  const card = el("div", { class: "cubi-auth-card" });
  card.append(
    el("span", { class: "cubi-eyebrow", text: "LOCAL PREVIEW" }),
    el("h1", { text: ctx.t("page.login.title") }),
    el("p", { class: "desc", text: "This server is the local full-stack preview. It holds no password directory; choose a demo persona. No production account is contacted and no production session is created." }),
    demoGrid(next, loginPath),
    note(`${ctx.t("common.localOnly")}. The demo session is issued by ${loginPath}, and Enterprise entitlements are still checked server-side.`),
  );
  testId(card, "login-preview-signin");
  wrap.append(card);
}

function securityLine(title: string, body: string): HTMLElement {
  return el("div", { class: "cubi-list-item" }, el("div", {}, el("strong", { text: title }), el("p", { class: "cubi-field-hint", text: body })), badge("server", "success"));
}

function linkRow(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}

export { BASE_PATH };
