/**
 * Canonical CUBI asset references for Desktop.
 * The binary/SVG source remains owned by the Web public asset family so
 * Desktop does not fork or redraw the approved mark.
 */
export const CUBI_BRAND_ASSETS = Object.freeze({
  light: "apps/web/public/cubi-platform-logo-primary.svg",
  dark: "apps/web/public/cubi-platform-logo-primary-dark.svg",
} as const);

export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;
