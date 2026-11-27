import { HELP_REGISTRY, WORKSPACE_MENU_HELP } from "./help-registry.js";
import type { OfficialHelpTopic } from "./help-registry.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";

/**
 * Command → official P6 Professional V26 Help topic.
 *
 * The map points at a traceability row (`docs/traceability/engineering-v26.json`)
 * and resolves to that row's recorded topic. Nothing here invents a title or a
 * URL: a command either has an evidence-backed topic or is listed as having no
 * official topic, with the reason. The shortcuts dialog links every mapped
 * command, and the coverage test fails if a command silently loses its mapping.
 */
export const COMMAND_HELP_ROWS: Readonly<Record<string, string>> = Object.freeze({
  // Navigation destinations, aligned with WORKSPACE_MENU_HELP.
  "nav.activities": "ENG-WS-SCHEDULE",
  "nav.wbs": "ENG-WS-WBS",
  "nav.projects": "ENG-WS-PROJECTS",
  "nav.resources": "ENG-WS-RESOURCES",
  "nav.assignments": "ENG-WS-RESOURCE-USAGE",
  "nav.roles": "ENG-WS-ROLES",
  "nav.calendars": "ENG-WS-CALENDARS",
  "nav.cost": "ENG-WS-EXPENSES",
  "nav.expenses": "ENG-WS-EXPENSES",
  "nav.documents": "ENG-WS-DOCUMENTS",
  "nav.reports": "ENG-WS-REPORTS",
  "nav.tracking": "ENG-WS-TRACKING",
  "nav.progress": "ENG-WS-TRACKING",
  "nav.control": "ENG-WS-TRACKING",
  "nav.issues": "ENG-WS-ISSUES",
  "nav.risks": "ENG-WS-RISKS",
  "nav.thresholds": "ENG-WS-THRESHOLDS",
  "nav.settings": "ENG-WS-ADMIN",
  "nav.administration": "ENG-WS-ADMIN",
  "nav.exchange": "ENG-WS-EXCHANGE",

  // Planning and activities.
  "planning.add-activity": "ENG-WS-ACTIVITY-TABLE",
  "planning.add-wbs": "ENG-WS-WBS",
  "planning.collapse-to": "ENG-WS-WBS",
  "project.add-activity": "ENG-WS-ACTIVITY-TABLE",
  "activity.edit": "ENG-WS-DETAILS",
  "activity.predecessors": "ENG-WS-RELATIONSHIPS",
  "activity.successors": "ENG-WS-RELATIONSHIPS",
  "assign.activity": "ENG-WS-RESOURCE-USAGE",
  "assignments.create": "ENG-WS-RESOURCE-USAGE",

  // Editing.
  "edit.dissolve": "ENG-WS-WBS",
  "edit.fill-down": "ENG-WS-ACTIVITY-TABLE",
  "edit.link": "ENG-WS-RELATIONSHIPS",
  "edit.unlink": "ENG-WS-RELATIONSHIPS",
  "edit.redo": "ENG-WS-LAYOUTS",
  "edit.undo": "ENG-WS-LAYOUTS",
  "edit.select-all": "ENG-WS-SELECTION",

  // Layout, grouping, filters and display.
  "layout.bars": "ENG-WS-GANTT-BARS",
  "layout.columns": "ENG-WS-ACTIVITY-TABLE",
  "layout.filters": "ENG-WS-FILTERS",
  "layout.font-row": "ENG-WS-LAYOUTS",
  "layout.group-sort": "ENG-WS-GROUPING",
  "layout.group-wbs": "ENG-WS-WBS",
  "layout.open": "ENG-WS-LAYOUTS",
  "layout.save": "ENG-WS-LAYOUTS",
  "layout.save-as": "ENG-WS-LAYOUTS",
  "layout.timescale": "ENG-WS-GANTT",
  "display.collapse-all": "ENG-WS-GANTT",
  "display.collapse-to": "ENG-WS-GANTT",
  "display.expand-all": "ENG-WS-GANTT",
  "display.fit": "ENG-WS-GANTT",
  "display.gantt": "ENG-WS-GANTT",
  "display.zoom-in": "ENG-WS-GANTT",
  "display.zoom-out": "ENG-WS-GANTT",
  "view.collapse-all": "ENG-WS-GANTT",
  "view.collapse-to": "ENG-WS-GANTT",
  "view.expand-all": "ENG-WS-GANTT",

  // Bottom panes.
  "bottom.details": "ENG-WS-DETAILS",
  "bottom.trace": "ENG-WS-TRACE-LOGIC",
  "bottom.usage-profile": "ENG-WS-USAGE-PROFILE",
  "bottom.usage-spreadsheet": "ENG-WS-USAGE-PROFILE",

  // Critical path and scheduling.
  "critical.collapse-all": "ENG-WS-CRITICAL-PATH",
  "critical.expand-all": "ENG-WS-CRITICAL-PATH",
  "tools.schedule": "ENG-WS-SCHEDULE",
  "tools.run-schedule": "ENG-WS-SCHEDULE",
  "project.schedule-options": "ENG-WS-SCHEDULE",
  "project.baselines": "ENG-WS-BASELINES",

  // Dictionaries and tools.
  "dict.activity-codes": "ENG-WS-ACTIVITY-CODES",
  "dict.project-codes": "ENG-WS-PROJECTS",
  "dict.resource-codes": "ENG-WS-RESOURCES",
  "tools.formula": "ENG-WS-UDF",
  "tools.options": "ENG-WS-ADMIN",
  "tools.reference": "ENG-WS-ACTIVITY-CODES",

  // Create verbs.
  "calendars.create": "ENG-WS-CALENDARS",
  "documents.create": "ENG-WS-DOCUMENTS",
  "expenses.create": "ENG-WS-EXPENSES",
  "issues.create": "ENG-WS-ISSUES",
  "resources.create": "ENG-WS-RESOURCES",
  "risks.create": "ENG-WS-RISKS",
  "roles.create": "ENG-WS-ROLES",
  "thresholds.create": "ENG-WS-THRESHOLDS",

  // Project and interchange.
  "project.additional-activities": "ENG-WS-PROJECTS",
  "project.interchange": "ENG-WS-EXCHANGE",
  "project.properties": "ENG-WS-PROJECTS",
  "action.details": "ENG-WS-DETAILS",

  // Reports, printing and publishing.
  "reports.open": "ENG-WS-REPORTS",
  "reports.tracking": "ENG-WS-REPORTS",
  "reports.wizard": "ENG-WS-REPORTS",
  "print.page-setup": "ENG-WS-REPORTS",
  "print.print": "ENG-WS-REPORTS",
  "file.print": "ENG-WS-REPORTS",
  "publish.pdf": "ENG-WS-REPORTS",

  // Administration and enterprise.
  "admin.calendar": "ENG-WS-CALENDARS",
  "admin.categories": "ENG-WS-UDF",
  "admin.permissions": "ENG-WS-ADMIN",
  "admin.settings": "ENG-WS-ADMIN",
  "enterprise.audit": "ENG-WS-ADMIN",
  "enterprise.currencies": "ENG-WS-EXPENSES",
  "enterprise.security": "ENG-WS-ADMIN",
  "enterprise.udfs": "ENG-WS-UDF",
  "enterprise.users": "ENG-WS-ADMIN",
});

/**
 * Commands that intentionally have no official topic. Each is a CUBI shell
 * affordance that P6 Professional Help does not document, so the dialog offers
 * no Help link instead of citing a page that would not answer the question.
 */
export const NO_OFFICIAL_TOPIC: Readonly<Record<string, string>> = Object.freeze({
  "action.assistant": "CUBI assistant panel; no P6 Professional topic documents it",
  "action.comments": "CUBI collaboration surface; not a P6 Professional window",
  "action.help": "Opens CUBI's own Help; it is the destination, not a documented command",
  "action.notes": "CUBI notebook pane; not a P6 Professional window",
  "action.proposals": "CUBI proposal workflow; not a P6 Professional window",
  "admin.language": "CUBI language preference; not a P6 Professional command",
  "bottom.none": "CUBI-empty bottom pane; no P6 Professional topic",
  "display.fullscreen": "Browser fullscreen; no P6 Professional topic",
  "display.panels": "CUBI panel chrome; no P6 Professional topic",
  "edit.find": "Find is CUBI's activity search; no traceability topic names it",
  "edit.cut": "P6 Professional Help records no Cut Activity topic in the traceability set; the command is contracted by CUBI's activity-operations API",
  "edit.copy": "P6 Professional Help records no Copy Activity topic in the traceability set; the command is contracted by CUBI's activity-operations API",
  "edit.paste": "P6 Professional Help records no Paste Activity topic in the traceability set; the command is contracted by CUBI's activity-operations API",
  "edit.delete": "P6 Professional Help records no Delete Activity topic in the traceability set; the command is contracted by CUBI's activity-operations API",
  "find.find": "Find is CUBI's activity search; no traceability topic names it",
  "find.next": "Find Next is CUBI's activity search; no traceability topic names it",
  "forms.open": "CUBI forms catalogue; not a P6 Professional command",
  "help.about": "CUBI About dialog; not a P6 Professional window",
  "help.shortcuts": "CUBI shortcut dialog; not a P6 Professional window",
  "layout.line-numbers": "CUBI table option; no P6 Professional topic",
  "nav.all": "CUBI window chooser; no single P6 Professional topic",
  "nav.backup": "CUBI backup surface; P6 Professional Help documents no matching page",
  "prefs.user": "CUBI user preferences; no P6 Professional topic",
  "project.close": "Window close is browser chrome, not a P6 Professional command",
  "publish.excel": "CUBI spreadsheet export; no P6 Professional topic",
  "publish.web": "CUBI web publishing; no P6 Professional topic",
  "tools.refresh": "CUBI data refresh; P6 Professional Help documents no matching command",
  "workspace.refresh": "CUBI data refresh; P6 Professional Help documents no matching command",
});

const TOPIC_BY_ROW = new Map(HELP_REGISTRY.map((entry) => [entry.id, entry.help]));

export type CommandHelp = { row: string; topic: OfficialHelpTopic };

/** The official topic for a command, or null when it is deliberately unmapped. */
export function commandHelp(command: string): CommandHelp | null {
  const row = COMMAND_HELP_ROWS[command];
  if (!row) return null;
  const topic = TOPIC_BY_ROW.get(row);
  return topic ? { row, topic } : null;
}

export function noTopicReason(command: string): string | null {
  return NO_OFFICIAL_TOPIC[command] ?? null;
}

/** The official topic for a window, through the menu-surface map. */
export function windowHelp(key: WorkspaceMenuKey): CommandHelp | null {
  const row = WORKSPACE_MENU_HELP[key];
  if (!row) return null;
  const topic = TOPIC_BY_ROW.get(row);
  return topic ? { row, topic } : null;
}
