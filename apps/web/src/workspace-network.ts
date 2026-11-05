import type { WorkspaceActivityRow, WorkspaceRelationshipRow, WorkspaceRelationshipType } from "./workspace-model.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

/**
 * Presentation-only Activity Network.
 *
 * The network is a projection of the activities and persisted relationships
 * already loaded into the workspace read model. It never calculates schedules,
 * never infers missing logic and never invents nodes or edges. Level assignment
 * is a deterministic longest-path layout over the stored predecessor/successor
 * pairs, so the same revision always renders the same diagram.
 */

export type ActivityNetworkNode = {
  id: string;
  name: string;
  level: number;
  row: number;
  critical: boolean;
  progressLabel: string;
};

export type ActivityNetworkEdge = {
  relationshipId: string;
  from: string;
  to: string;
  type: WorkspaceRelationshipType;
  lagValue: string;
  lagUnit: string;
  label: string;
};

export type ActivityNetworkModel = {
  nodes: readonly ActivityNetworkNode[];
  edges: readonly ActivityNetworkEdge[];
  levelCount: number;
  rowCount: number;
  cycleDetected: boolean;
  omittedActivities: number;
  omittedRelationships: number;
};

export const MAX_NETWORK_ACTIVITIES = 150;

const NODE_WIDTH = 190;
const NODE_HEIGHT = 62;
const COLUMN_GAP = 96;
const ROW_GAP = 18;
const PADDING = 26;

function lagLabel(edge: WorkspaceRelationshipRow): string {
  const numeric = Number(edge.lagValue);
  const amount = Number.isFinite(numeric) && numeric !== 0
    ? `${numeric > 0 ? "+" : ""}${edge.lagValue}${edge.lagUnit === "working-hour" ? "h" : "d"}`
    : "";
  return `${edge.type}${amount}`;
}

export function buildActivityNetwork(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
): ActivityNetworkModel {
  const visible = activities.slice(0, MAX_NETWORK_ACTIVITIES);
  const order = new Map(visible.map((activity, index) => [activity.id, index]));
  const known = new Set(order.keys());

  const edges: ActivityNetworkEdge[] = [];
  let omittedRelationships = 0;
  for (const relationship of relationships) {
    if (!known.has(relationship.predecessorId) || !known.has(relationship.successorId)) {
      omittedRelationships += 1;
      continue;
    }
    if (relationship.predecessorId === relationship.successorId) {
      omittedRelationships += 1;
      continue;
    }
    edges.push({
      relationshipId: relationship.id,
      from: relationship.predecessorId,
      to: relationship.successorId,
      type: relationship.type,
      lagValue: relationship.lagValue,
      lagUnit: relationship.lagUnit,
      label: lagLabel(relationship),
    });
  }

  const indegree = new Map<string, number>();
  const outgoing = new Map<string, ActivityNetworkEdge[]>();
  for (const id of known) {
    indegree.set(id, 0);
    outgoing.set(id, []);
  }
  for (const edge of edges) {
    indegree.set(edge.to, (indegree.get(edge.to) ?? 0) + 1);
    outgoing.get(edge.from)?.push(edge);
  }

  const levels = new Map<string, number>();
  for (const id of known) levels.set(id, 0);
  const queue = visible.filter((activity) => (indegree.get(activity.id) ?? 0) === 0).map((activity) => activity.id);
  const processed = new Set<string>();
  while (queue.length) {
    const id = queue.shift();
    if (id === undefined) break;
    if (processed.has(id)) continue;
    processed.add(id);
    for (const edge of outgoing.get(id) ?? []) {
      const candidate = (levels.get(id) ?? 0) + 1;
      if (candidate > (levels.get(edge.to) ?? 0)) levels.set(edge.to, candidate);
      const remaining = (indegree.get(edge.to) ?? 0) - 1;
      indegree.set(edge.to, remaining);
      if (remaining === 0) queue.push(edge.to);
    }
  }

  let cycleDetected = false;
  let maxLevel = 0;
  for (const level of levels.values()) maxLevel = Math.max(maxLevel, level);
  const unprocessed = visible.filter((activity) => !processed.has(activity.id));
  if (unprocessed.length) {
    // A persisted cycle is a data defect, not something to hide. Keep the
    // nodes visible in a terminal column and let the caller show a notice.
    cycleDetected = true;
    maxLevel += 1;
    for (const activity of unprocessed) levels.set(activity.id, maxLevel);
  }

  const rowsByLevel = new Map<number, number>();
  const nodes: ActivityNetworkNode[] = visible.map((activity) => {
    const level = levels.get(activity.id) ?? 0;
    const row = rowsByLevel.get(level) ?? 0;
    rowsByLevel.set(level, row + 1);
    return {
      id: activity.id,
      name: activity.name,
      level,
      row,
      critical: activity.gantt?.critical === true,
      progressLabel: activity.gantt ? `${activity.gantt.progressPercent}%` : "",
    };
  });

  const levelCount = nodes.reduce((count, node) => Math.max(count, node.level + 1), 0);
  const rowCount = nodes.reduce((count, node) => Math.max(count, node.row + 1), 0);

  return {
    nodes,
    edges,
    levelCount,
    rowCount,
    cycleDetected,
    omittedActivities: Math.max(0, activities.length - visible.length),
    omittedRelationships,
  };
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, Math.max(0, max - 1))}…` : value;
}

function nodeX(level: number): number {
  return PADDING + level * (NODE_WIDTH + COLUMN_GAP);
}

function nodeY(row: number): number {
  return PADDING + row * (NODE_HEIGHT + ROW_GAP);
}

function edgePath(from: ActivityNetworkNode, to: ActivityNetworkNode): string {
  const sx = nodeX(from.level) + NODE_WIDTH;
  const sy = nodeY(from.row) + NODE_HEIGHT / 2;
  const tx = nodeX(to.level);
  const ty = nodeY(to.row) + NODE_HEIGHT / 2;
  if (tx > sx + 12) {
    const middle = sx + (tx - sx) / 2;
    return `M ${sx} ${sy} H ${middle} V ${ty} H ${tx}`;
  }
  // Back edge (cycle) or same column: curve around so it stays visible.
  return `M ${sx} ${sy} C ${sx + 48} ${sy}, ${tx - 48} ${ty}, ${tx} ${ty}`;
}

export function renderActivityNetwork(
  activities: readonly WorkspaceActivityRow[],
  relationships: readonly WorkspaceRelationshipRow[],
  locale: string,
  selectedActivityId: string | null,
): string {
  const model = buildActivityNetwork(activities, relationships);
  const t = (en: string, fa: string): string => translateWorkspaceUiText(locale, en, fa);

  if (!activities.length) {
    return `<section class="cp-p6-network" data-network-view><div class="cp-empty">${escapeHtml(t(
      "No activities are loaded, so no activity network can be drawn.",
      "فعالیتی بارگذاری نشده است؛ بنابراین شبکهٔ فعالیت قابل ترسیم نیست.",
    ))}</div></section>`;
  }

  const width = PADDING * 2 + Math.max(1, model.levelCount) * NODE_WIDTH + Math.max(0, model.levelCount - 1) * COLUMN_GAP;
  const height = PADDING * 2 + Math.max(1, model.rowCount) * NODE_HEIGHT + Math.max(0, model.rowCount - 1) * ROW_GAP;
  const nodesById = new Map(model.nodes.map((node) => [node.id, node]));

  const edgeMarkup = model.edges
    .filter((edge) => nodesById.has(edge.from) && nodesById.has(edge.to))
    .map((edge) => {
      const from = nodesById.get(edge.from);
      const to = nodesById.get(edge.to);
      if (!from || !to) return "";
      const sx = nodeX(from.level) + NODE_WIDTH;
      const sy = nodeY(from.row) + NODE_HEIGHT / 2;
      const tx = nodeX(to.level);
      const ty = nodeY(to.row) + NODE_HEIGHT / 2;
      const labelX = tx > sx + 12 ? sx + (tx - sx) / 2 + 4 : Math.max(sx, tx) + 14;
      const labelY = (sy + ty) / 2 - 5;
      return `<g class="cp-network-edge-group${from.critical && to.critical ? " is-critical" : ""}" data-relationship-id="${escapeHtml(edge.relationshipId)}"><path class="cp-network-edge" d="${edgePath(from, to)}" marker-end="url(#cp-network-arrowhead)" /><text class="cp-network-edge-label" x="${labelX}" y="${labelY}">${escapeHtml(edge.label)}</text></g>`;
    })
    .join("");

  const nodeMarkup = model.nodes.map((node) => {
    const x = nodeX(node.level);
    const y = nodeY(node.row);
    const selected = selectedActivityId === node.id;
    return `<g class="cp-network-node${node.critical ? " is-critical" : ""}${selected ? " is-selected" : ""}" data-gantt-activity-id="${escapeHtml(node.id)}" role="button" tabindex="0" aria-pressed="${selected ? "true" : "false"}" aria-label="${escapeHtml(`${node.id} — ${node.name}`)}"><title>${escapeHtml(`${node.id} — ${node.name}`)}</title><rect class="cp-network-node-surface" x="${x}" y="${y}" width="${NODE_WIDTH}" height="${NODE_HEIGHT}" rx="8" /><rect class="cp-network-node-accent" x="${x}" y="${y}" width="4" height="${NODE_HEIGHT}" rx="2" /><text class="cp-network-node-id" x="${x + 14}" y="${y + 22}">${escapeHtml(node.id)}</text><text class="cp-network-node-name" x="${x + 14}" y="${y + 43}">${escapeHtml(truncate(node.name, 30))}</text>${node.progressLabel ? `<text class="cp-network-node-status" x="${x + NODE_WIDTH - 12}" y="${y + 22}" text-anchor="end">${escapeHtml(node.progressLabel)}</text>` : ""}</g>`;
  }).join("");

  const notices: string[] = [];
  if (!model.edges.length) {
    notices.push(t(
      "No persisted relationships are loaded; only activity nodes are shown.",
      "هیچ رابطهٔ ذخیره‌شده‌ای بارگذاری نشده است؛ فقط گره‌های فعالیت نمایش داده می‌شوند.",
    ));
  }
  if (model.cycleDetected) {
    notices.push(t(
      "A circular dependency exists in the persisted relationships. The affected activities are grouped in the final column and no schedule was recalculated here.",
      "در روابط ذخیره‌شده وابستگی چرخه‌ای وجود دارد. فعالیت‌های متأثر در ستون پایانی گروه‌بندی شده‌اند و هیچ زمان‌بندی در اینجا بازمحاسبه نشد.",
    ));
  }
  if (model.omittedActivities || model.omittedRelationships) {
    notices.push(t(
      "The diagram is limited to 150 activities; some nodes or relationships are not drawn.",
      "نمودار به ۱۵۰ فعالیت محدود شده است؛ برخی گره‌ها یا روابط ترسیم نشده‌اند.",
    ));
  }

  return `<section class="cp-p6-network" data-network-view data-network-levels="${model.levelCount}" data-network-nodes="${model.nodes.length}" data-network-edges="${model.edges.length}">
    <header class="cp-p6-network-head">
      <div>
        <h2>${escapeHtml(t("Activity Network", "شبکهٔ فعالیت‌ها"))}</h2>
        <span>${escapeHtml(t(
          `${model.nodes.length} activities · ${model.edges.length} relationships`,
          `${model.nodes.length} فعالیت · ${model.edges.length} رابطه`,
        ))}</span>
      </div>
      <span class="cp-p6-network-note">${escapeHtml(t(
        "Projection of the persisted plan logic. Dates are read from the shared scheduling result and are not recalculated in this view.",
        "نمایشی از منطق ذخیره‌شدهٔ برنامه. تاریخ‌ها از نتیجهٔ زمان‌بندی هستهٔ مشترک خوانده می‌شوند و در این نما بازمحاسبه نمی‌شوند.",
      ))}</span>
    </header>
    ${notices.map((notice) => `<p class="cp-register-notice">${escapeHtml(notice)}</p>`).join("")}
    <div class="cp-network-scroll" dir="ltr">
      <svg class="cp-network-svg" role="img" dir="ltr" aria-label="${escapeHtml(t("Activity Network diagram", "نمودار شبکهٔ فعالیت‌ها"))}" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <defs><marker id="cp-network-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M 0 0 L 8 4 L 0 8 Z" class="cp-network-arrow" /></marker></defs>
        <g class="cp-network-edges">${edgeMarkup}</g>
        <g class="cp-network-nodes">${nodeMarkup}</g>
      </svg>
    </div>
  </section>`;
}
