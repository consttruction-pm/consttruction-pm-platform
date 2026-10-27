import {
  getAvailableWorkspaceLocales,
  getWorkspaceLocaleDirection,
  translateWorkspaceText,
} from "./workspace-localization.js";
import { cubiAssistantAvatarUrl } from "./cubi-brand-assets.js";

const ROOT_ID = "cubi-global-assistant";
const AVATAR_ALT = "";

function isWorkspaceRoute(): boolean {
  return /(?:^|\/)app(?:\/|$)/.test(window.location.pathname);
}

function getAssistantLocale(): string {
  const supported = getAvailableWorkspaceLocales();
  const htmlLocale = document.documentElement.lang.trim().toLowerCase();
  const workspaceRoute = isWorkspaceRoute();

  if (workspaceRoute && supported.includes(htmlLocale)) return htmlLocale;

  try {
    const saved = window.localStorage.getItem("cubi:landing-locale");
    if (saved && supported.includes(saved)) return saved;
  } catch {
    // The launcher still works when storage is unavailable.
  }

  if (supported.includes(htmlLocale)) return htmlLocale;

  const browserLocale = navigator.language.toLowerCase().split("-")[0] ?? "en";
  if (supported.includes(browserLocale)) return browserLocale;
  return supported.includes("en") ? "en" : (supported[0] ?? "en");
}

function translated(locale: string, key: string, fallback: string): string {
  return translateWorkspaceText(locale, `landing.assistant.${key}`, fallback);
}

function createAvatar(): HTMLImageElement {
  const image = document.createElement("img");
  image.src = cubiAssistantAvatarUrl();
  image.alt = AVATAR_ALT;
  image.width = 52;
  image.height = 52;
  image.setAttribute("aria-hidden", "true");
  image.decoding = "async";
  return image;
}

/**
 * Add the same fixed assistant entry point to every public page and workspace
 * shell. Mounting directly under <body> avoids clipping by page-level overflow
 * containers and keeps the launcher pinned to the viewport while scrolling.
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
  header.append(createAvatar());

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

  const action = document.createElement("a");
  action.className = "cubi-assistant-workspace-link";
  const siteRoot = new URL("../../../", import.meta.url);
  const workspaceUrl = new URL("app/", siteRoot);
  action.href = workspaceUrl.href;

  const launcher = document.createElement("button");
  launcher.className = "cubi-assistant-launcher-button";
  launcher.id = "cubi-assistant-launcher";
  launcher.type = "button";
  launcher.setAttribute("aria-controls", popover.id);
  launcher.setAttribute("aria-expanded", "false");
  launcher.append(createAvatar());
  const launcherLabel = document.createElement("span");
  launcher.append(launcherLabel);

  popover.append(header, description, action);
  root.append(popover, launcher);
  document.body.append(root);

  let isOpen = false;
  let locale = getAssistantLocale();

  const setPopoverOpen = (open: boolean): void => {
    isOpen = open;
    popover.hidden = !open;
    launcher.setAttribute("aria-expanded", String(open));
    if (open) closeButton.focus();
    else launcher.focus();
  };

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
  };

  launcher.addEventListener("click", () => setPopoverOpen(!isOpen));
  closeButton.addEventListener("click", () => setPopoverOpen(false));
  popover.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Escape") setPopoverOpen(false);
  });

  action.addEventListener("click", (event: MouseEvent) => {
    if (!isWorkspaceRoute()) return;

    event.preventDefault();
    const assistantPanel = document.querySelector<HTMLDetailsElement>("#cp-ai-assistant-chat");
    if (assistantPanel) {
      assistantPanel.open = true;
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      assistantPanel.scrollIntoView({
        behavior: reducedMotion ? "auto" : "smooth",
        block: "center",
      });
      assistantPanel.querySelector<HTMLElement>("summary")?.focus({ preventScroll: true });
      setPopoverOpen(false);
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
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === "cubi:landing-locale") renderCopy();
  });

  renderCopy();
}

mountGlobalAssistantLauncher();
