/**
 * Mobile landscape handling for the professional workspace.
 *
 * On a touch device the workspace keeps its desktop table/Gantt/details
 * arrangement. The module asks the Screen Orientation API for landscape inside
 * the first user gesture (browsers reject such a request outside a gesture). If
 * the request is denied, a rotate-device prompt appears instead of CSS-rotating
 * or dragging the page, which would break the fixed workspace geometry.
 */
import { translateWorkspaceUiText } from "./workspace-localization.js";

const MOBILE_MAX_WIDTH = 900;
const GUIDANCE_ATTRIBUTE = "data-mobile-orientation";
let continueInPortrait = false;
let bound = false;
let attemptedLock = false;

type OrientationWithLock = ScreenOrientation & { lock?: (orientation: string) => Promise<void> };

export function isMobileWorkspace(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
  const narrow = window.matchMedia(`(max-width: ${MOBILE_MAX_WIDTH}px)`).matches;
  return coarsePointer && narrow;
}

function isPortrait(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(orientation: portrait)").matches;
}

async function requestLandscape(): Promise<boolean> {
  if (typeof document === "undefined" || typeof screen === "undefined") return false;
  try {
    const orientation = screen.orientation as OrientationWithLock | undefined;
    if (!orientation?.lock) return false;
    // Element fullscreen is permitted inside a user gesture and is required by
    // several mobile browsers before an orientation lock is accepted.
    if (!document.fullscreenElement) {
      const element = document.documentElement;
      if (typeof element.requestFullscreen === "function") {
        await element.requestFullscreen().catch(() => undefined);
      }
    }
    await orientation.lock("landscape");
    return true;
  } catch {
    return false;
  }
}

function ensurePanel(container: HTMLElement): HTMLElement {
  const existing = container.querySelector<HTMLElement>(`[${GUIDANCE_ATTRIBUTE}]`);
  if (existing) return existing;
  const panel = document.createElement("section");
  panel.setAttribute(GUIDANCE_ATTRIBUTE, "true");
  panel.className = "cp-mobile-orientation";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.hidden = true;
  panel.innerHTML = `<div class="cp-mobile-orientation-card">
    <span class="cp-mobile-orientation-device" aria-hidden="true"></span>
    <h2 data-mobile-orientation-title></h2>
    <p data-mobile-orientation-body></p>
    <div class="cp-mobile-orientation-actions">
      <button type="button" data-mobile-orientation-retry></button>
      <button type="button" data-mobile-orientation-continue></button>
    </div>
  </div>`;
  container.append(panel);
  panel.querySelector<HTMLButtonElement>("[data-mobile-orientation-retry]")?.addEventListener("click", () => {
    attemptedLock = false;
    void attemptLandscape(container);
  });
  panel.querySelector<HTMLButtonElement>("[data-mobile-orientation-continue]")?.addEventListener("click", () => {
    continueInPortrait = true;
    updateMobileOrientation(container);
  });
  return panel;
}

function updateText(container: HTMLElement, locale: string): void {
  const panel = ensurePanel(container);
  const title = panel.querySelector<HTMLElement>("[data-mobile-orientation-title]");
  const body = panel.querySelector<HTMLElement>("[data-mobile-orientation-body]");
  const retry = panel.querySelector<HTMLButtonElement>("[data-mobile-orientation-retry]");
  const keep = panel.querySelector<HTMLButtonElement>("[data-mobile-orientation-continue]");
  if (title) title.textContent = translateWorkspaceUiText(locale, "Rotate your device", "دستگاه خود را بچرخانید");
  if (body) {
    body.textContent = translateWorkspaceUiText(
      locale,
      "The workspace is designed for landscape: the activity table, Gantt and details stay side by side. Rotate your phone, or try landscape mode again.",
      "محیط کار برای حالت افقی طراحی شده است تا جدول فعالیت‌ها، گانت و جزئیات کنار هم بمانند. گوشی را بچرخانید یا دوباره حالت افقی را امتحان کنید.",
    );
  }
  if (retry) retry.textContent = translateWorkspaceUiText(locale, "Try landscape again", "امتحان دوبارهٔ حالت افقی");
  if (keep) keep.textContent = translateWorkspaceUiText(locale, "Continue in portrait", "ادامه در حالت عمودی");
}

function updateMobileOrientation(container: HTMLElement): void {
  if (!isMobileWorkspace()) {
    container.querySelector<HTMLElement>(`[${GUIDANCE_ATTRIBUTE}]`)?.setAttribute("hidden", "");
    return;
  }
  const panel = ensurePanel(container);
  const visible = isPortrait() && !continueInPortrait;
  panel.hidden = !visible;
  if (visible) panel.removeAttribute("hidden");
  else panel.setAttribute("hidden", "");
}

async function attemptLandscape(container: HTMLElement): Promise<void> {
  if (!isMobileWorkspace() || attemptedLock) return;
  attemptedLock = true;
  const locked = await requestLandscape();
  if (!locked) updateMobileOrientation(container);
  else continueInPortrait = false;
}

export function mountWorkspaceMobile(container: HTMLElement, locale: string): void {
  if (typeof window === "undefined") return;
  ensurePanel(container);
  updateText(container, locale);
  updateMobileOrientation(container);
  if (bound) return;
  bound = true;
  // The orientation lock must run inside a user gesture. The first tap is the
  // earliest permissible moment after the workspace has rendered.
  container.addEventListener("pointerdown", () => { void attemptLandscape(container); }, { once: true, passive: true });
  window.addEventListener("orientationchange", () => updateMobileOrientation(container));
  window.matchMedia?.(`(max-width: ${MOBILE_MAX_WIDTH}px)`).addEventListener?.("change", () => updateMobileOrientation(container));
  // Rotating a phone does not necessarily cross the width breakpoint (for
  // example 390px -> 844px still matches max-width: 900px). Listen to the
  // orientation query itself so the guidance hides as soon as landscape begins.
  window.matchMedia?.("(orientation: portrait)").addEventListener?.("change", () => updateMobileOrientation(container));
}
