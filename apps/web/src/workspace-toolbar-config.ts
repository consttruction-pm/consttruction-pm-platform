import { readStoredValue, writeStoredValue, type PreferenceStorage } from "./workspace-preferences.js";
import {
  TOOLBAR_FAMILIES,
  TOOLBAR_FAMILY_IDS,
  TOOLBAR_COMMANDS,
  toolbarCommand,
  toolbarCommandsForFamily,
  toolbarFamily,
} from "./workspace-toolbar-registry.js";

/**
 * Versioned, user-specific and workspace-aware toolbar configuration.
 *
 * The configuration never stores project data. It is keyed by the signed-in
 * user and the open project so two workspaces can keep different toolbars
 * while the project's saved Activity Layout stays untouched.
 */

export const WORKSPACE_TOOLBAR_CONFIG_VERSION = 2;
export const WORKSPACE_TOOLBAR_CONFIG_KEY = "cubi:workspace-toolbars:v2";
/** The pre-rail preference this version migrates from. */
export const LEGACY_WORKSPACE_TOOLBAR_KEY = "cubi:workspace-toolbars";

export type ToolbarRail = "left" | "right" | "floating";
export type ToolbarIconStyle = "icon" | "text" | "both";

export type ToolbarButtonState = {
  id: string;
  visible: boolean;
  /** User rename from the icon context menu, in the current interface language. */
  label?: string;
};

export type ToolbarFamilyState = {
  id: string;
  rail: ToolbarRail;
  visible: boolean;
  style: ToolbarIconStyle;
  buttons: ToolbarButtonState[];
  /** Command ids that start a new visual group (a separator before the button). */
  separators: string[];
  /** Custom toolbars are user-created and may hold any registered command. */
  custom?: boolean;
  name?: string;
};

export type WorkspaceToolbarConfig = {
  version: typeof WORKSPACE_TOOLBAR_CONFIG_VERSION;
  locked: boolean;
  families: ToolbarFamilyState[];
};

export type ToolbarWorkspaceConfig = Omit<WorkspaceToolbarConfig, "version">;

export type ToolbarConfigDocument = {
  version: typeof WORKSPACE_TOOLBAR_CONFIG_VERSION;
  workspaces: Record<string, ToolbarWorkspaceConfig>;
  migratedFromV1?: boolean;
};

const CUSTOM_PREFIX = "custom:";

export function isCustomFamilyId(id: string): boolean {
  return id.startsWith(CUSTOM_PREFIX);
}

export function toolbarConfigStorageKey(userId: string): string {
  return `${WORKSPACE_TOOLBAR_CONFIG_KEY}:${encodeURIComponent(userId.trim())}`;
}

export function toolbarWorkspaceKey(projectId: string | null | undefined): string {
  const id = projectId?.trim() ?? "";
  return id ? `project:${id}` : "workspace";
}

function defaultButtonState(familyId: string): ToolbarButtonState[] {
  return toolbarCommandsForFamily(familyId).map((command) => ({ id: command.id, visible: command.defaultVisible }));
}

export function defaultFamilyState(familyId: string): ToolbarFamilyState {
  const definition = toolbarFamily(familyId);
  return {
    id: familyId,
    rail: definition?.rail ?? "floating",
    visible: true,
    style: "icon",
    buttons: defaultButtonState(familyId),
    separators: [],
  };
}

/** Registry order defines the first-run configuration for both rails. */
export function defaultToolbarConfig(): ToolbarWorkspaceConfig {
  return {
    locked: false,
    families: TOOLBAR_FAMILIES.map((family) => defaultFamilyState(family.id)),
  };
}

function normalizeButton(raw: unknown, familyId: string, custom: boolean): ToolbarButtonState | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const record = raw as Record<string, unknown>;
  const id = typeof record.id === "string" ? record.id.trim() : "";
  const command = toolbarCommand(id);
  if (!command) return null;
  if (!custom && !command.families.includes(familyId)) return null;
  const visible = record.visible !== false;
  const label = typeof record.label === "string" && record.label.trim() && record.label.trim().length <= 80
    ? record.label.trim()
    : undefined;
  return label ? { id, visible, label } : { id, visible };
}

function normalizeFamily(raw: unknown): ToolbarFamilyState | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const record = raw as Record<string, unknown>;
  const id = typeof record.id === "string" ? record.id.trim() : "";
  const custom = isCustomFamilyId(id);
  if (!custom && !toolbarFamily(id)) return null;
  const rail: ToolbarRail = record.rail === "left" || record.rail === "right" || record.rail === "floating"
    ? record.rail
    : custom ? "floating" : toolbarFamily(id)?.rail ?? "right";
  const style: ToolbarIconStyle = record.style === "text" || record.style === "both" ? record.style : "icon";
  const seen = new Set<string>();
  const buttons: ToolbarButtonState[] = [];
  for (const item of Array.isArray(record.buttons) ? record.buttons : []) {
    const button = normalizeButton(item, id, custom);
    if (!button || seen.has(button.id)) continue;
    seen.add(button.id);
    buttons.push(button);
  }
  if (!custom) {
    // A command added to the registry after the preference was written appears
    // with its default visibility instead of silently disappearing.
    for (const command of toolbarCommandsForFamily(id)) {
      if (seen.has(command.id)) continue;
      seen.add(command.id);
      buttons.push({ id: command.id, visible: command.defaultVisible });
    }
  }
  const separators = Array.isArray(record.separators)
    ? [...new Set(record.separators.filter((value): value is string => typeof value === "string" && seen.has(value)))]
    : [];
  const name = typeof record.name === "string" && record.name.trim() && record.name.trim().length <= 80
    ? record.name.trim()
    : undefined;
  return {
    id,
    rail,
    visible: record.visible !== false,
    style,
    buttons,
    separators,
    ...(custom ? { custom: true, name: name ?? "Custom Toolbar" } : {}),
  };
}

export function normalizeToolbarConfig(raw: unknown): ToolbarWorkspaceConfig {
  const fallback = defaultToolbarConfig();
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return fallback;
  const record = raw as Record<string, unknown>;
  const families: ToolbarFamilyState[] = [];
  const seen = new Set<string>();
  for (const item of Array.isArray(record.families) ? record.families : []) {
    const family = normalizeFamily(item);
    if (!family || seen.has(family.id)) continue;
    seen.add(family.id);
    families.push(family);
  }
  // Registry families introduced after the preference was written are appended
  // so a release never loses a toolbar family.
  for (const definition of TOOLBAR_FAMILIES) {
    if (seen.has(definition.id)) continue;
    families.push(defaultFamilyState(definition.id));
  }
  return { locked: record.locked === true, families };
}

type StoredDocument = {
  version: 2;
  workspaces: Record<string, unknown>;
  migratedFromV1?: boolean;
};

function readDocument(key: string, storage: PreferenceStorage | null): StoredDocument {
  const raw = readStoredValue(key, storage);
  if (!raw) return { version: WORKSPACE_TOOLBAR_CONFIG_VERSION, workspaces: {} };
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return { version: WORKSPACE_TOOLBAR_CONFIG_VERSION, workspaces: {} };
    const record = parsed as Record<string, unknown>;
    if (record.version !== WORKSPACE_TOOLBAR_CONFIG_VERSION) return { version: WORKSPACE_TOOLBAR_CONFIG_VERSION, workspaces: {} };
    const workspaces = record.workspaces && typeof record.workspaces === "object" && !Array.isArray(record.workspaces)
      ? record.workspaces as Record<string, unknown>
      : {};
    return {
      version: WORKSPACE_TOOLBAR_CONFIG_VERSION,
      workspaces,
      migratedFromV1: record.migratedFromV1 === true,
    };
  } catch {
    return { version: WORKSPACE_TOOLBAR_CONFIG_VERSION, workspaces: {} };
  }
}

// `readDocument` receives the resolved key from the public read/write
// functions, which stay symmetrical and testable.

const LEGACY_GROUP_MAP: Record<string, string> = {
  workspace: "navigation",
  edit: "edit",
  layout: "layout",
  view: "display",
  project: "project-tools",
  activities: "activity",
  wbs: "planning",
  gantt: "display",
  resources: "assign",
  reports: "standard-reports",
  tools: "tools",
};

/** Migrate the pre-rail hidden-family list into the versioned configuration. */
function migrateLegacy(userId: string, storage: PreferenceStorage | null): ToolbarWorkspaceConfig | null {
  if (!userId.trim()) return null;
  const raw = readStoredValue(`${LEGACY_WORKSPACE_TOOLBAR_KEY}:${encodeURIComponent(userId.trim())}`, storage);
  if (!raw) return null;
  let hidden: string[] = [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (Array.isArray(parsed)) hidden = parsed.filter((value): value is string => typeof value === "string");
  } catch {
    return null;
  }
  const config = defaultToolbarConfig();
  for (const legacy of hidden) {
    const familyId = LEGACY_GROUP_MAP[legacy];
    const family = familyId ? config.families.find((item) => item.id === familyId) : undefined;
    if (family) family.visible = false;
  }
  return config;
}

export function readToolbarConfig(
  userId: string,
  workspaceKey: string,
  storage: PreferenceStorage | null = browserStorage(),
): ToolbarWorkspaceConfig {
  if (!userId.trim()) return defaultToolbarConfig();
  const key = toolbarConfigStorageKey(userId);
  const document = readDocument(key, storage);
  const stored = document.workspaces[workspaceKey];
  if (stored) return normalizeToolbarConfig(stored);
  if (Object.keys(document.workspaces).length === 0) {
    const migrated = migrateLegacy(userId, storage);
    if (migrated) {
      writeToolbarConfig(userId, workspaceKey, migrated, storage);
      return migrated;
    }
  }
  return defaultToolbarConfig();
}

export function writeToolbarConfig(
  userId: string,
  workspaceKey: string,
  config: ToolbarWorkspaceConfig,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  if (!userId.trim() || !workspaceKey.trim()) return;
  const key = toolbarConfigStorageKey(userId);
  const previous = readStoredValue(key, storage);
  let workspaces: Record<string, unknown> = {};
  let migratedFromV1 = false;
  if (previous) {
    try {
      const parsed = JSON.parse(previous) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        const record = parsed as Record<string, unknown>;
        if (record.workspaces && typeof record.workspaces === "object" && !Array.isArray(record.workspaces)) {
          workspaces = { ...(record.workspaces as Record<string, unknown>) };
        }
        migratedFromV1 = record.migratedFromV1 === true;
      }
    } catch {
      workspaces = {};
    }
  }
  workspaces[workspaceKey] = config;
  const document: ToolbarConfigDocument = {
    version: WORKSPACE_TOOLBAR_CONFIG_VERSION,
    workspaces: workspaces as Record<string, ToolbarWorkspaceConfig>,
    ...(migratedFromV1 ? { migratedFromV1: true } : {}),
  };
  writeStoredValue(key, JSON.stringify(document), storage);
}

// ---------------------------------------------------------------------------
// Pure configuration operations. Every function returns a new configuration so
// the renderer never observes a half-applied change.
// ---------------------------------------------------------------------------

export function findToolbarFamily(config: ToolbarWorkspaceConfig, familyId: string): ToolbarFamilyState | undefined {
  return config.families.find((family) => family.id === familyId);
}

export function familiesForRail(config: ToolbarWorkspaceConfig, rail: ToolbarRail): ToolbarFamilyState[] {
  return config.families.filter((family) => family.rail === rail);
}

export function setFamilyVisible(config: ToolbarWorkspaceConfig, familyId: string, visible: boolean): ToolbarWorkspaceConfig {
  return { ...config, families: config.families.map((family) => (family.id === familyId ? { ...family, visible } : family)) };
}

export function setFamilyRail(
  config: ToolbarWorkspaceConfig,
  familyId: string,
  rail: ToolbarRail,
  targetIndex = Number.MAX_SAFE_INTEGER,
): ToolbarWorkspaceConfig {
  const source = findToolbarFamily(config, familyId);
  if (!source) return config;
  const rest = config.families.filter((family) => family.id !== familyId);
  const moved = { ...source, rail };
  const peers = rest.filter((family) => family.rail === rail);
  const before = peers.slice(0, Math.max(0, Math.min(peers.length, targetIndex)));
  const after = peers.slice(before.length);
  // Rebuild in place: keep the global array ordered by rail group (left, right,
  // floating) so the config stays readable and deterministic.
  const left = rail === "left" ? [...before, moved, ...after] : rest.filter((family) => family.rail === "left");
  const right = rail === "right" ? [...before, moved, ...after] : rest.filter((family) => family.rail === "right");
  const floating = rail === "floating" ? [...before, moved, ...after] : rest.filter((family) => family.rail === "floating");
  return { ...config, families: [...left, ...right, ...floating] };
}

export function reorderFamily(config: ToolbarWorkspaceConfig, familyId: string, targetIndex: number): ToolbarWorkspaceConfig {
  const family = findToolbarFamily(config, familyId);
  if (!family) return config;
  return setFamilyRail(config, familyId, family.rail, targetIndex);
}

export function setButtonVisible(
  config: ToolbarWorkspaceConfig,
  familyId: string,
  commandId: string,
  visible: boolean,
): ToolbarWorkspaceConfig {
  const command = toolbarCommand(commandId);
  if (!command) return config;
  return {
    ...config,
    families: config.families.map((family) => {
      if (family.id !== familyId) return family;
      let found = false;
      const buttons = family.buttons.map((button) => {
        if (button.id !== commandId) return button;
        found = true;
        return { ...button, visible };
      });
      // A command removed from a custom toolbar can be added back from its
      // Add or Remove menu; default families always carry every command.
      if (!found) {
        if (!family.custom && !command.families.includes(family.id)) return family;
        buttons.push({ id: commandId, visible });
      }
      return { ...family, buttons };
    }),
  };
}

export function moveButton(
  config: ToolbarWorkspaceConfig,
  commandId: string,
  sourceFamilyId: string,
  targetFamilyId: string,
  targetIndex: number,
): ToolbarWorkspaceConfig {
  const source = findToolbarFamily(config, sourceFamilyId);
  const target = findToolbarFamily(config, targetFamilyId);
  const command = toolbarCommand(commandId);
  if (!source || !target || !command) return config;
  if (!target.custom && !command.families.includes(target.id)) return config;
  const sourceButton = source.buttons.find((button) => button.id === commandId);
  const button: ToolbarButtonState = sourceButton ? { ...sourceButton, visible: true } : { id: commandId, visible: true };
  if (sourceFamilyId === targetFamilyId) {
    const buttons = source.buttons.filter((item) => item.id !== commandId);
    const index = Math.max(0, Math.min(buttons.length, targetIndex));
    buttons.splice(index, 0, button);
    return { ...config, families: config.families.map((family) => (family.id === source.id ? { ...family, buttons } : family)) };
  }
  return {
    ...config,
    families: config.families.map((family) => {
      if (family.id === source.id) {
        // Predefined families keep a hidden entry so the command remains in
        // Add or Remove and a later registry normalization cannot resurrect it
        // as a visible button. A custom toolbar's membership is the list
        // itself, so the entry leaves with the command.
        return {
          ...family,
          buttons: family.custom
            ? family.buttons.filter((item) => item.id !== commandId)
            : family.buttons.map((item) => (item.id === commandId ? { ...item, visible: false } : item)),
          separators: family.separators.filter((id) => id !== commandId),
        };
      }
      if (family.id === target.id) {
        const buttons = family.buttons.filter((item) => item.id !== commandId);
        const index = Math.max(0, Math.min(buttons.length, targetIndex));
        buttons.splice(index, 0, button);
        return { ...family, buttons };
      }
      return family;
    }),
  };
}

export function setFamilyStyle(config: ToolbarWorkspaceConfig, familyId: string, style: ToolbarIconStyle): ToolbarWorkspaceConfig {
  return { ...config, families: config.families.map((family) => (family.id === familyId ? { ...family, style } : family)) };
}

export function renameButton(
  config: ToolbarWorkspaceConfig,
  familyId: string,
  commandId: string,
  label: string | null,
): ToolbarWorkspaceConfig {
  const clean = label?.trim().slice(0, 80) ?? "";
  return {
    ...config,
    families: config.families.map((family) => family.id === familyId
      ? {
        ...family,
        buttons: family.buttons.map((button) => {
          if (button.id !== commandId) return button;
          if (!clean) {
            const next = { ...button };
            delete next.label;
            return next;
          }
          return { ...button, label: clean };
        }),
      }
      : family),
  };
}

export function toggleSeparator(
  config: ToolbarWorkspaceConfig,
  familyId: string,
  commandId: string,
): ToolbarWorkspaceConfig {
  return {
    ...config,
    families: config.families.map((family) => {
      if (family.id !== familyId) return family;
      const present = family.separators.includes(commandId);
      return {
        ...family,
        separators: present
          ? family.separators.filter((id) => id !== commandId)
          : [...family.separators, commandId],
      };
    }),
  };
}

export function setToolbarsLocked(config: ToolbarWorkspaceConfig, locked: boolean): ToolbarWorkspaceConfig {
  return { ...config, locked };
}

export function resetFamily(config: ToolbarWorkspaceConfig, familyId: string): ToolbarWorkspaceConfig {
  const family = findToolbarFamily(config, familyId);
  if (!family) return config;
  if (family.custom) {
    return {
      ...config,
      families: config.families.map((item) => (item.id === familyId
        ? { ...item, buttons: [], separators: [], style: "icon" }
        : item)),
    };
  }
  const defaults = defaultFamilyState(familyId);
  return {
    ...config,
    families: config.families.map((item) => (item.id === familyId
      ? { ...defaults, rail: item.rail, visible: item.visible }
      : item)),
  };
}

export function resetAllToolbars(config: ToolbarWorkspaceConfig): ToolbarWorkspaceConfig {
  // Custom toolbars are user content; a reset restores the predefined families
  // and keeps custom definitions, emptied rather than deleted.
  const reset = defaultToolbarConfig();
  const custom = config.families.filter((family) => family.custom);
  return {
    locked: false,
    families: [...reset.families, ...custom.map((family) => ({ ...family, visible: true, buttons: [], separators: [], style: "icon" as ToolbarIconStyle }))],
  };
}

let customSequence = 0;

export function createCustomFamily(config: ToolbarWorkspaceConfig, name: string): { config: ToolbarWorkspaceConfig; familyId: string } {
  customSequence += 1;
  const clean = name.trim().slice(0, 80) || "Custom Toolbar";
  let id = `${CUSTOM_PREFIX}${Date.now().toString(36)}-${customSequence}`;
  while (config.families.some((family) => family.id === id)) id = `${CUSTOM_PREFIX}${Date.now().toString(36)}-${customSequence += 1}`;
  const family: ToolbarFamilyState = {
    id,
    rail: "floating",
    visible: true,
    style: "icon",
    buttons: [],
    separators: [],
    custom: true,
    name: clean,
  };
  return { config: { ...config, families: [...config.families, family] }, familyId: id };
}

export function renameCustomFamily(config: ToolbarWorkspaceConfig, familyId: string, name: string): ToolbarWorkspaceConfig {
  const clean = name.trim().slice(0, 80);
  if (!clean) return config;
  return {
    ...config,
    families: config.families.map((family) => (family.custom && family.id === familyId ? { ...family, name: clean } : family)),
  };
}

export function deleteCustomFamily(config: ToolbarWorkspaceConfig, familyId: string): ToolbarWorkspaceConfig {
  const family = findToolbarFamily(config, familyId);
  if (!family?.custom) return config;
  return { ...config, families: config.families.filter((item) => item.id !== familyId) };
}

/** Resolve the visible label for a family, including custom names. */
export function familyDisplayName(
  family: ToolbarFamilyState,
  translate: (english: string, persian: string) => string,
): string {
  if (family.custom) return family.name?.trim() || translate("Custom Toolbar", "نوار ابزار سفارشی");
  const definition = toolbarFamily(family.id);
  return definition ? translate(definition.label.en, definition.label.fa) : family.id;
}

/** Stable English/Persian pair for a registry family, used by the tab title. */
export function familyDefinitionLabel(familyId: string): { en: string; fa: string } {
  const definition = toolbarFamily(familyId);
  return definition ? definition.label : { en: familyId, fa: familyId };
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

// Re-exported so callers do not import the registry twice for a config action.
export { TOOLBAR_FAMILY_IDS, TOOLBAR_COMMANDS };
