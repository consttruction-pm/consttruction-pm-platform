export type UiTextDirection = "auto" | "ltr" | "rtl";
export type ResolvedTextDirection = "ltr" | "rtl";
export type UiMouseButton = "left" | "right";

export type UiInteractiveElement = {
  kind: "menu" | "field" | "help" | "action";
  leftClick: "activate";
  rightClick: "context-menu";
  keyboardEquivalent: "enter-or-space";
};

export function resolveTextDirection(
  _languageTag: string,
  direction: UiTextDirection = "auto",
  registeredDirection: ResolvedTextDirection = "ltr",
): ResolvedTextDirection {
  if (direction !== "auto") return direction;
  return registeredDirection;
}

export function interactivePolicy(kind: UiInteractiveElement["kind"]): UiInteractiveElement {
  return {
    kind,
    leftClick: "activate",
    rightClick: "context-menu",
    keyboardEquivalent: "enter-or-space",
  };
}
