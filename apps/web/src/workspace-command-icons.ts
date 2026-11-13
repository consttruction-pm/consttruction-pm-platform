/**
 * Single icon registry for application menu commands.
 *
 * The icon family is shared with the toolbars and shortcut menus, so a command
 * looks the same wherever it appears. Entries are keyed by the stable menu item
 * id rather than by the localized label; a missing id is a programming error
 * that the unit tests catch, not a silent fallback to an unrelated glyph.
 */
import type { WorkspaceIconName } from "./workspace-icons.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";

/**
 * The one window→glyph map. The navigation rail, the full-menu flyout and the
 * desktop shell all read this table so a destination can never look like a
 * different one depending on where it is drawn.
 */
export const WORKSPACE_WINDOW_ICONS: Record<WorkspaceMenuKey, WorkspaceIconName> = {
  project: "folder",
  wbs: "wbs",
  schedule: "gantt",
  progress: "progress",
  resources: "resource",
  assignments: "assignment",
  roles: "roles",
  calendars: "calendar",
  cost: "money",
  expenses: "expense",
  documents: "documents",
  reports: "reports",
  tracking: "tracking",
  issues: "issues",
  risks: "risks",
  thresholds: "thresholds",
  control: "control",
  settings: "settings",
  administration: "administration",
  exchange: "exchange",
  backup: "backup",
};

const MENU_ITEM_ICONS: Readonly<Record<string, WorkspaceIconName>> = {
  // File
  "file.new": "plus",
  "file.open": "open",
  "file.open-layout": "folder",
  "file.save-layout": "save",
  "file.save-layout-as": "saveAs",
  "file.settings": "project",
  "file.interchange": "export",
  "file.print": "print",
  "file.refresh": "refresh",
  "workspace.close": "close",
  // Edit
  "edit.undo": "undo",
  "edit.redo": "redo",
  "edit.cut": "cut",
  "edit.copy": "copy",
  "edit.paste": "paste",
  "edit.delete": "delete",
  "edit.find": "find",
  "edit.group-wbs": "group",
  "edit.sort-toggle": "sort",
  "edit.select-all": "check",
  "edit.link": "link",
  "edit.unlink": "unlink",
  "edit.fill-down": "fill",
  "edit.dissolve": "dissolve",
  // View
  "view.fields": "columns",
  "view.filters": "filter",
  "view.group-sort": "sort",
  "view.timescale": "clock",
  "view.bars": "bars",
  "view.font-row": "font",
  "view.preferences": "settings",
  "view.line-numbers": "lineNumbers",
  "view.expand-all": "expand",
  "view.collapse-all": "collapse",
  "view.collapse-to": "collapseTo",
  "view.zoom-in": "zoomIn",
  "view.zoom-out": "zoomOut",
  "view.fit": "fit",
  "view.toggle-wbs": "wbs",
  "view.toggle-gantt": "gantt",
  "view.toggle-details": "panels",
  "view.top-table": "table",
  "view.top-table-gantt": "gantt",
  "view.top-network": "network",
  "view.bottom-details": "activity",
  "view.bottom-trace": "tracking",
  "view.bottom-usage-spreadsheet": "activity",
  "view.bottom-usage-profile": "activity",
  "view.bottom-none": "close",
  "view.calendar": "calendar",
  "view.close-window": "close",
  // Project
  "project.settings": "project",
  "project.add-wbs": "wbs",
  "project.add-activity": "plus",
  "project.edit-activity": "edit",
  "project.relationships": "link",
  "project.additional-activities": "activity",
  "project.schedule": "calendar",
  "project.schedule-options": "settings",
  "project.formula": "fill",
  "project.reference": "book",
  "project.assign-resources": "assignment",
  "project.predecessors": "link",
  "project.successors": "network",
  "project.level": "resource",
  "project.baseline": "baseline",
  "project.compare": "compare",
  "project.progress": "progress",
  // Enterprise
  "enterprise.projects": "project",
  "enterprise.resources": "resource",
  "enterprise.assignments": "assignment",
  "enterprise.roles": "roles",
  "enterprise.calendars": "calendar",
  "enterprise.udfs": "columns",
  "enterprise.forms": "forms",
  // Tools
  "tools.forms": "forms",
  "tools.search": "find",
  "tools.preferences": "settings",
  "tools.reports": "reports",
  "tools.import-export": "exchange",
  "tools.backup": "backup",
  "tools.print-preview": "print",
  "tools.generate-report": "reports",
  "tools.language": "language",
  "tools.help": "help",
  // Admin
  "admin.window": "settings",
  "admin.preferences": "settings",
  "admin.language": "language",
  "admin.calendar": "calendar",
  "admin.users": "roles",
  "admin.security": "administration",
  "admin.permissions": "administration",
  "admin.categories": "group",
  "admin.currencies": "money",
  "admin.periods": "calendar",
  "admin.audit": "book",
  "admin.recovery": "backup",
  // Help
  "help.shortcuts": "help",
  "help.about": "help",
};

/**
 * Resolve the icon for a menu entry.
 *
 * Window entries and the View menu's generated toggle/theme rows carry dynamic
 * ids, so those families are resolved structurally; the fixed commands come
 * from the exact map above. Separators return `undefined` and render no icon.
 */
export function desktopMenuIcon(id: string): WorkspaceIconName | undefined {
  if (id.startsWith("window.")) {
    return WORKSPACE_WINDOW_ICONS[id.slice("window.".length) as WorkspaceMenuKey];
  }
  if (id.startsWith("view.toolbar-") || id.startsWith("view.theme-")) {
    return "workspace";
  }
  return MENU_ITEM_ICONS[id];
}
