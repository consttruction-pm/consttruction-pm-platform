import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDirection,
  translateWorkspaceText,
} from "./workspace-localization.js";
import { cubiAssistantAvatarUrl } from "./cubi-brand-assets.js";
import {
  readAssistantGuideQuery,
  resolveAssistantGuide,
} from "./assistant-guide.js";

const ROOT_ID = "cubi-global-assistant";
const AVATAR_ALT = "";
const COMPACT_MEDIA_QUERY = "(max-width: 520px)";

function isWorkspaceRoute(): boolean {
  return /(?:^|\/)app(?:\/|$)/.test(window.location.pathname);
}

function getAssistantLocale(): string {
  const supported = getAvailableWorkspaceLocales();
  const htmlLocale = document.documentElement.lang.trim().toLowerCase();

  // The assistant speaks the language of the document it is mounted on: either
  // the locale the workspace selected on the root element, or the language route
  // served for this document. A stored landing preference deliberately does not
  // apply, because Persian assistant copy on an English document would contradict
  // the page itself and its localized metadata.
  if (supported.includes(htmlLocale)) return htmlLocale;
  const routeLocale = getLanguageRouteLocale(supported);
  if (routeLocale) return routeLocale;

  const browserLocale = navigator.language.toLowerCase().split("-")[0] ?? "en";
  if (supported.includes(browserLocale)) return browserLocale;
  return supported.includes("en") ? "en" : (supported[0] ?? "en");
}

function getLanguageRouteLocale(supported: readonly string[]): string | null {
  const lastSegment = window.location.pathname
    .replace(/index\.html$/, "")
    .replace(/\/+$/, "")
    .split("/")
    .filter(Boolean)
    .pop();
  return lastSegment && supported.includes(lastSegment) ? lastSegment : null;
}

function translated(locale: string, key: string, fallback: string): string {
  return translateWorkspaceText(locale, `landing.assistant.${key}`, fallback);
}

/**
 * The avatar image is decorative; the entry point itself is labelled by the
 * button. A failed image load must never hide or break the assistant entry,
 * so the artwork is swapped for a text badge instead of being removed.
 */
function createAvatarSlot(): { slot: HTMLElement; image: HTMLImageElement } {
  const slot = document.createElement("span");
  slot.className = "cubi-assistant-avatar-slot";

  const image = document.createElement("img");
  image.src = cubiAssistantAvatarUrl();
  image.alt = AVATAR_ALT;
  image.width = 52;
  image.height = 52;
  image.setAttribute("aria-hidden", "true");
  image.decoding = "async";

  const fallback = document.createElement("span");
  fallback.className = "cubi-assistant-avatar-fallback";
  fallback.setAttribute("aria-hidden", "true");
  fallback.textContent = "CUBI";

  image.addEventListener("error", () => {
    slot.dataset.avatarFailed = "true";
  });
  image.addEventListener("load", () => {
    delete slot.dataset.avatarFailed;
  });

  slot.append(image, fallback);
  return { slot, image };
}

/**
 * Add the same fixed assistant entry point to every public page and workspace
 * shell. Mounting directly under <body> avoids clipping by page-level overflow
 * containers and keeps the launcher pinned to the viewport while scrolling.
 *
 * The launcher is intentionally presentation-only: it never calls an API, never
 * waits for a model response and never depends on project data, so an assistant
 * service failure cannot remove the entry point or block the page.
 */
export function mountGlobalAssistantLauncher(): void {
  if (typeof document === "undefined" || !document.body) return;
  if (document.getElementById(ROOT_ID)) return;

  const root = document.createElement("div");
  root.id = ROOT_ID;
  root.className = "cubi-assistant-launcher";
  root.dataset.cubiAssistantEntry = "true";

  const popover = document.createElement("section");
  popover.className = "cubi-assistant-popover";
  popover.id = "cubi-assistant-popover";
  popover.setAttribute("role", "dialog");
  popover.setAttribute("aria-modal", "false");
  popover.setAttribute("aria-labelledby", "cubi-assistant-title");
  popover.setAttribute("aria-describedby", "cubi-assistant-description");
  popover.hidden = true;

  const header = document.createElement("header");
  header.className = "cubi-assistant-popover-header";
  header.append(createAvatarSlot().slot);

  const heading = document.createElement("div");
  heading.className = "cubi-assistant-popover-heading";

  const title = document.createElement("strong");
  title.id = "cubi-assistant-title";
  const subtitle = document.createElement("span");
  heading.append(title, subtitle);

  const closeButton = document.createElement("button");
  closeButton.className = "cubi-assistant-close";
  closeButton.id = "cubi-assistant-close";
  closeButton.type = "button";
  closeButton.textContent = "×";
  header.append(heading, closeButton);

  const description = document.createElement("p");
  description.id = "cubi-assistant-description";

  // Page-aware operational guidance. The content comes from a deterministic
  // registry of pages and workspace states, and every action is only offered
  // when its target control actually exists in this document.
  const guide = document.createElement("section");
  guide.className = "cubi-assistant-guide";
  guide.id = "cubi-assistant-guide";
  guide.setAttribute("aria-labelledby", "cubi-assistant-guide-heading");

  const guideHeading = document.createElement("h2");
  guideHeading.id = "cubi-assistant-guide-heading";
  const guidePurpose = document.createElement("p");
  guidePurpose.className = "cubi-assistant-guide-purpose";
  const guideStepsLabel = document.createElement("h3");
  const guideSteps = document.createElement("ol");
  guideSteps.className = "cubi-assistant-guide-steps";
  const guideError = document.createElement("p");
  guideError.className = "cubi-assistant-guide-error";
  guideError.hidden = true;
  const guideAction = document.createElement("button");
  guideAction.type = "button";
  guideAction.className = "cubi-assistant-guide-action";
  guideAction.hidden = true;
  guide.append(
    guideHeading,
    guidePurpose,
    guideStepsLabel,
    guideSteps,
    guideError,
    guideAction,
  );

  const action = document.createElement("a");
  action.className = "cubi-assistant-workspace-link";
  const siteRoot = new URL("../../../", import.meta.url);
  const siteBasePath = siteRoot.pathname;
  const workspaceUrl = new URL("app/", siteRoot);
  action.href = workspaceUrl.href;

  const launcher = document.createElement("button");
  launcher.className = "cubi-assistant-launcher-button";
  launcher.id = "cubi-assistant-launcher";
  launcher.type = "button";
  launcher.setAttribute("aria-controls", popover.id);
  launcher.setAttribute("aria-expanded", "false");
  launcher.setAttribute("aria-haspopup", "dialog");
  const launcherAvatar = createAvatarSlot();
  launcher.append(launcherAvatar.slot);
  const launcherLabel = document.createElement("span");
  launcher.append(launcherLabel);

  popover.append(header, description, guide, action);
  root.append(popover, launcher);
  document.body.append(root);

  let isOpen = false;
  let locale = getAssistantLocale();

  const setPopoverOpen = (open: boolean, options: { restoreFocus?: boolean } = {}): void => {
    if (isOpen === open) return;
    const hadFocusInsidePopover = open ? false : popover.contains(document.activeElement);
    isOpen = open;
    popover.hidden = !open;
    root.dataset.open = String(open);
    launcher.setAttribute("aria-expanded", String(open));
    if (open) {
      // State can change while the panel is closed (project opened, menu
      // switched, workspace loaded), so guidance is resolved from the live page
      // every time the panel becomes visible.
      renderGuide();
      closeButton.focus();
      return;
    }
    if (options.restoreFocus !== false && hadFocusInsidePopover) launcher.focus();
  };

  const renderGuide = (): void => {
    const query = readAssistantGuideQuery(document, siteBasePath);
    const entry = resolveAssistantGuide({ ...query, locale });
    guideHeading.textContent = entry.heading;
    guidePurpose.textContent = entry.purpose;
    guideStepsLabel.textContent = translateWorkspaceText(
      locale,
      "assistant.guide.stepsLabel",
      locale === "fa" ? "گام‌های بعدی" : "Next steps",
    );
    guideSteps.replaceChildren(
      ...entry.steps.map((step) => {
        const item = document.createElement("li");
        item.textContent = step;
        return item;
      }),
    );
    if (entry.commonError) {
      guideError.textContent = entry.commonError;
      guideError.hidden = false;
    } else {
      guideError.textContent = "";
      guideError.hidden = true;
    }
    // A target that is absent in this state (for example a control summary with
    // no generated data) must not produce a button that does nothing.
    if (entry.action && document.querySelector(entry.action.target)) {
      guideAction.textContent = entry.action.label;
      guideAction.dataset.guideTarget = entry.action.target;
      guideAction.hidden = false;
    } else {
      guideAction.hidden = true;
      guideAction.textContent = "";
      delete guideAction.dataset.guideTarget;
    }
    guide.dataset.page = entry.page;
    guide.dataset.state = entry.state;
    if (entry.menu) guide.dataset.menu = entry.menu;
    else delete guide.dataset.menu;
  };

  guideAction.addEventListener("click", () => {
    const targetSelector = guideAction.dataset.guideTarget;
    if (!targetSelector) return;
    const target = document.querySelector<HTMLElement>(targetSelector);
    if (!target) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "center",
    });
    const focusTarget = target.matches(
      "button,a,input,select,textarea,[tabindex]",
    )
      ? target
      : target.querySelector<HTMLElement>(
          "button,a,input,select,textarea,[tabindex]",
        );
    focusTarget?.focus({ preventScroll: true });
    setPopoverOpen(false, { restoreFocus: false });
  });

  const renderCopy = (): void => {
    locale = getAssistantLocale();
    root.dir = getWorkspaceLocaleDirection(locale);

    const isWorkspace = isWorkspaceRoute();
    const titleText = translated(
      locale,
      "title",
      locale === "fa" ? "دستیار هوشمند کوبی" : "CUBI AI Assistant",
    );
    launcherLabel.textContent = titleText;
    launcher.setAttribute("aria-label", titleText);
    title.textContent = titleText;
    subtitle.textContent = translated(
      locale,
      "subtitle",
      locale === "fa" ? "راهنمای پروژه، همیشه در دسترس" : "Project help, one step away",
    );
    closeButton.setAttribute(
      "aria-label",
      translated(
        locale,
        "close",
        locale === "fa" ? "بستن پنل دستیار" : "Close assistant panel",
      ),
    );
    description.textContent = isWorkspace
      ? translated(
          locale,
          "workspaceDescription",
          locale === "fa"
            ? "برای استفاده از دستیار، یک پروژه را باز کنید. دستیار پس از آماده شدن فضای کاری به پنل گفتگو دسترسی می‌دهد."
            : "Open a project to use the assistant with its project context.",
        )
      : translated(
          locale,
          "description",
          locale === "fa"
            ? "برای پاسخ‌های اختصاصی پروژه یا کمک در زمان‌بندی، وارد فضای کاری شوید و یک پروژه انتخاب کنید."
            : "For project-specific answers or schedule support, open your workspace and select a project.",
        );
    action.textContent = isWorkspace
      ? translated(
          locale,
          "openPanel",
          locale === "fa" ? "باز کردن پنل دستیار ←" : "Open assistant panel →",
        )
      : translated(
          locale,
          "workspaceAction",
          locale === "fa" ? "ورود به فضای کاری پروژه ←" : "Open project workspace →",
        );
    renderGuide();
  };

  launcher.addEventListener("click", () => setPopoverOpen(!isOpen));
  closeButton.addEventListener("click", () => {
    setPopoverOpen(false);
    launcher.focus();
  });

  // Escape closes from anywhere on the page, not only while the panel holds
  // focus, so the assistant can never trap the keyboard.
  document.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Escape" && isOpen) {
      event.preventDefault();
      setPopoverOpen(false);
    }
  });

  // A click outside the entry point dismisses the panel without navigating.
  document.addEventListener("pointerdown", (event: PointerEvent) => {
    if (!isOpen) return;
    if (root.contains(event.target as Node | null)) return;
    setPopoverOpen(false, { restoreFocus: false });
  });

  // Narrow viewports switch to the icon-only entry so the fixed button cannot
  // cover page controls; the accessible name stays on the button.
  const compactMedia = window.matchMedia(COMPACT_MEDIA_QUERY);
  const applyCompactMode = (): void => {
    root.dataset.compact = compactMedia.matches ? "true" : "false";
  };
  applyCompactMode();
  if (typeof compactMedia.addEventListener === "function") {
    compactMedia.addEventListener("change", applyCompactMode);
  }

  action.addEventListener("click", (event: MouseEvent) => {
    if (!isWorkspaceRoute()) return;

    event.preventDefault();
    const assistantPanel = document.querySelector<HTMLDetailsElement>("#cp-ai-assistant-chat");
    if (assistantPanel) {
      assistantPanel.open = true;
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      const scrollToPanel = (): void => {
        assistantPanel.scrollIntoView({
          behavior: reducedMotion ? "auto" : "smooth",
          block: "center",
        });
      };
      scrollToPanel();
      // Opening the panel changes its own height, so the first centring can be
      // measured against the collapsed box. Re-assert it once the expanded layout
      // is known, otherwise the routed panel can stay below the fold.
      window.requestAnimationFrame(() => window.requestAnimationFrame(scrollToPanel));
      assistantPanel.querySelector<HTMLElement>("summary")?.focus({ preventScroll: true });
      setPopoverOpen(false, { restoreFocus: false });
      return;
    }

    description.textContent = translated(
      locale,
      "workspaceDescription",
      locale === "fa"
        ? "برای استفاده از دستیار، یک پروژه را باز کنید."
        : "Open or create a project to use the assistant.",
    );
    description.tabIndex = -1;
    description.focus();
  });

  const localeObserver = new MutationObserver((records) => {
    if (records.some((record) => record.attributeName === "lang" || record.attributeName === "dir")) {
      renderCopy();
    }
  });
  localeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang", "dir"],
  });

  // Back/forward and hash navigation change the page without reloading, so the
  // guidance must be recomputed for the step the user actually landed on.
  window.addEventListener("popstate", renderGuide);
  window.addEventListener("hashchange", renderGuide);

  renderCopy();
}

mountGlobalAssistantLauncher();
