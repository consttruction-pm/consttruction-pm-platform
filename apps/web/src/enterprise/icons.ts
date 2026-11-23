/**
 * Enterprise semantic icon registry.
 *
 * Every control registered for ENT-07 resolves to a real, drawn SVG from this
 * module. The shell's legacy `cubi-icon` spans are flat squares; they are kept
 * for pages that have not been rebuilt yet, but no control on this page may use
 * one. Paths are authored on a 24×24 grid with a single stroke weight so the
 * icons stay legible at 16px, in LTR and RTL, without an icon font or an
 * external dependency.
 */

export type EnterpriseIconName =
  | "nav-projects"
  | "projects-search"
  | "projects-filter-status"
  | "projects-sort"
  | "project-open"
  | "project-overview"
  | "project-engineering"
  | "project-resources"
  | "project-documents"
  | "project-risks"
  | "project-reports"
  | "action-refresh"
  | "top-help";

type Shape =
  | { kind: "path"; d: string }
  | { kind: "circle"; cx: number; cy: number; r: number }
  | { kind: "line"; x1: number; y1: number; x2: number; y2: number };

const SHAPES: Record<EnterpriseIconName, readonly Shape[]> = {
  "nav-projects": [
    // A layered project folder: the register is a container, not a generic tile.
    { kind: "path", d: "M3 8a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" },
    { kind: "path", d: "M3 11h18" },
  ],
  "projects-search": [
    { kind: "circle", cx: 10.5, cy: 10.5, r: 6.5 },
    { kind: "line", x1: 15.5, y1: 15.5, x2: 21, y2: 21 },
  ],
  "projects-filter-status": [
    { kind: "path", d: "M3 5h18l-7 8.2V20l-4 1.6v-8.4z" },
  ],
  "projects-sort": [
    { kind: "line", x1: 7, y1: 4, x2: 7, y2: 20 },
    { kind: "path", d: "M4 17l3 3 3-3" },
    { kind: "line", x1: 17, y1: 20, x2: 17, y2: 4 },
    { kind: "path", d: "M14 7l3-3 3 3" },
  ],
  "project-open": [
    { kind: "path", d: "M13 4h7v7" },
    { kind: "line", x1: 20, y1: 4, x2: 11, y2: 13 },
    { kind: "path", d: "M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" },
  ],
  "project-overview": [
    { kind: "path", d: "M4 4h7v6H4z" },
    { kind: "path", d: "M13 4h7v10h-7z" },
    { kind: "path", d: "M4 12h7v8H4z" },
    { kind: "path", d: "M13 16h7v4h-7z" },
  ],
  "project-engineering": [
    // A gear: the Engineering environment owns scheduling and calculation.
    { kind: "circle", cx: 12, cy: 12, r: 3.2 },
    { kind: "path", d: "M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.2 5.2l2.1 2.1M16.7 16.7l2.1 2.1M18.8 5.2l-2.1 2.1M7.3 16.7l-2.1 2.1" },
  ],
  "project-resources": [
    { kind: "circle", cx: 9, cy: 8, r: 3.2 },
    { kind: "path", d: "M3 20a6 6 0 0 1 12 0" },
    { kind: "circle", cx: 17.5, cy: 9.5, r: 2.4 },
    { kind: "path", d: "M15.5 20a5 5 0 0 1 5.5-4.7" },
  ],
  "project-documents": [
    { kind: "path", d: "M6 3h8l4 4v14H6z" },
    { kind: "path", d: "M14 3v4h4" },
    { kind: "line", x1: 9, y1: 12, x2: 15, y2: 12 },
    { kind: "line", x1: 9, y1: 16, x2: 15, y2: 16 },
  ],
  "project-risks": [
    { kind: "path", d: "M12 3.2 21 20H3z" },
    { kind: "line", x1: 12, y1: 9.5, x2: 12, y2: 14 },
    { kind: "circle", cx: 12, cy: 16.8, r: 0.7 },
  ],
  "project-reports": [
    { kind: "line", x1: 4, y1: 20, x2: 20, y2: 20 },
    { kind: "path", d: "M7 20v-7M11.5 20V9M16 20v-4.5" },
  ],
  "action-refresh": [
    { kind: "path", d: "M20 12a8 8 0 1 1-2.4-5.7" },
    { kind: "path", d: "M20 4v5h-5" },
  ],
  "top-help": [
    { kind: "circle", cx: 12, cy: 12, r: 9 },
    { kind: "path", d: "M9.4 9.2a2.7 2.7 0 1 1 3.7 2.5c-.7.3-1.1 1-1.1 1.8v.6" },
    { kind: "circle", cx: 12, cy: 17.2, r: 0.7 },
  ],
};

const SVG_NS = "http://www.w3.org/2000/svg";

/**
 * Build a real inline SVG icon. The caller supplies the localised accessible
 * name; when it is absent the graphic is decorative (the surrounding control
 * carries the label).
 */
export function enterpriseIcon(name: EnterpriseIconName, accessibleName?: string): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "cubi-svg-icon");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.6");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("focusable", "false");
  if (accessibleName) {
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", accessibleName);
  } else {
    svg.setAttribute("aria-hidden", "true");
  }
  for (const shape of SHAPES[name]) {
    const node =
      shape.kind === "path"
        ? document.createElementNS(SVG_NS, "path")
        : shape.kind === "circle"
          ? document.createElementNS(SVG_NS, "circle")
          : document.createElementNS(SVG_NS, "line");
    if (shape.kind === "path") node.setAttribute("d", shape.d);
    else if (shape.kind === "circle") {
      node.setAttribute("cx", String(shape.cx));
      node.setAttribute("cy", String(shape.cy));
      node.setAttribute("r", String(shape.r));
    } else {
      node.setAttribute("x1", String(shape.x1));
      node.setAttribute("y1", String(shape.y1));
      node.setAttribute("x2", String(shape.x2));
      node.setAttribute("y2", String(shape.y2));
    }
    svg.append(node);
  }
  return svg;
}

/** The registered icon names, in crosswalk order. Used by the registry test. */
export const ENTERPRISE_ICON_NAMES: readonly EnterpriseIconName[] = [
  "nav-projects",
  "projects-search",
  "projects-filter-status",
  "projects-sort",
  "project-open",
  "project-overview",
  "project-engineering",
  "project-resources",
  "project-documents",
  "project-risks",
  "project-reports",
  "action-refresh",
  "top-help",
];

/** Shape count per icon; every icon must draw something to be useful. */
export function enterpriseIconShapeCount(name: EnterpriseIconName): number {
  return SHAPES[name].length;
}
