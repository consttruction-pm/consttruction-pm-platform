/**
 * Browser-local clipboard state for the WBS window Cut/Copy/Paste commands.
 *
 * The clipboard never leaves the page: Cut is applied by moving the existing
 * record (PATCH parent), Copy is applied by the server-side subtree copy. The
 * V26 help topics define the target of a paste as the selected element.
 */
export type WorkspaceWbsClipboardMode = "copy" | "cut";

export type WorkspaceWbsClipboardEntry = {
  mode: WorkspaceWbsClipboardMode;
  wbsId: string;
  code: string;
  name: string;
};

type ClipboardNode = {
  id: string;
  parentKind: "project" | "wbs";
  parentWbsId: string | null;
  localCode: string;
};

/**
 * Derive a sibling-unique local code for a copied subtree root.
 *
 * The copy preserves the source code when the target has no such sibling;
 * otherwise it appends the documented copy suffix. The server remains the
 * authority and returns a conflict if the derived code still collides.
 */
export function nextWbsCopyCode(
  nodes: readonly ClipboardNode[],
  targetParentId: string,
  sourceCode: string,
): string {
  const taken = new Set(
    nodes
      .filter((node) => node.parentKind === "wbs" && node.parentWbsId === targetParentId)
      .map((node) => node.localCode),
  );
  if (!taken.has(sourceCode)) return sourceCode;
  const first = `${sourceCode} (copy)`;
  if (!taken.has(first)) return first;
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${sourceCode} (copy ${index})`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${sourceCode} (copy ${Date.now().toString(36)})`;
}

export function wbsClipboardText(locale: string, entry: WorkspaceWbsClipboardEntry | null): string {
  if (!entry) {
    return locale === "fa" ? "حافظهٔ موقت خالی است" : "Clipboard empty";
  }
  const mode = entry.mode === "cut"
    ? (locale === "fa" ? "برش" : "cut")
    : (locale === "fa" ? "کپی" : "copy");
  const prefix = locale === "fa" ? "حافظهٔ موقت" : "Clipboard";
  return `${prefix}: ${mode} — ${entry.name} (${entry.code})`;
}

export function wbsClipboardLabels(locale: string): {
  cut: string;
  copy: string;
  paste: string;
  selectTarget: string;
  cannotPasteIntoSelf: string;
  deleteGuidance: string;
} {
  if (locale === "fa") {
    return {
      cut: "برش",
      copy: "کپی",
      paste: "چسباندن",
      selectTarget: "ابتدا عنصر هدف را انتخاب کنید و سپس بچسبانید.",
      cannotPasteIntoSelf: "یک عنصر ساختار شکست را نمی‌توان در خودش چسباند.",
      deleteGuidance:
        "این عنصر ساختار شکست هنوز زیرعنصر یا تخصیص فعالیت دارد. پیش از حذف، زیرعنصرها را جابه‌جا یا حذف کنید و فعالیت‌های آن را به عنصر والد منتقل کنید.",
    };
  }
  return {
    cut: "Cut",
    copy: "Copy",
    paste: "Paste",
    selectTarget: "Select the target WBS element, then paste.",
    cannotPasteIntoSelf: "A WBS element cannot be pasted into itself.",
    deleteGuidance:
      "This WBS element still has child elements or activity assignments. Move or delete its children and reassign its activities to the parent element before deleting it.",
  };
}
