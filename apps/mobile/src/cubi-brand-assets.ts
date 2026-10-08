/**
 * Canonical CUBI asset references for Mobile.
 * The approved mark is not duplicated or locally redrawn.
 */
export const CUBI_BRAND_ASSETS = Object.freeze({
  light: "apps/web/public/cubi-platform-logo-primary.svg",
  dark: "apps/web/public/cubi-platform-logo-primary-dark.svg",
} as const);

export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;
