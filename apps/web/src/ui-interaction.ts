export type UiTextDirection = "auto" | "ltr" | "rtl";
export type ResolvedTextDirection = "ltr" | "rtl";
export type UiMouseButton = "left" | "right";

export type UiInteractiveElement = {
  kind: "menu" | "field" | "help" | "action";
  leftClick: "activate";
  rightClick: "context-menu";
  keyboardEquivalent: "enter-or-space";
};

const RTL_LANGUAGE_BASES = new Set(["ar", "dv", "fa", "he", "ku", "ps", "ur", "yi"]);

export function resolveTextDirection(
  languageTag: string,
  direction: UiTextDirection = "auto",
): ResolvedTextDirection {
  if (direction !== "auto") return direction;
  const base = languageTag.trim().toLowerCase().split("-")[0];
  return RTL_LANGUAGE_BASES.has(base) ? "rtl" : "ltr";
}

export function interactivePolicy(kind: UiInteractiveElement["kind"]): UiInteractiveElement {
  return {
    kind,
    leftClick: "activate",
    rightClick: "context-menu",
    keyboardEquivalent: "enter-or-space",
  };
}
