/** Canonical CUBI Platform asset family shared by every client surface. */
export const CUBI_BRAND_ASSETS = Object.freeze({
  light: "apps/web/public/cubi-platform-logo-primary.svg",
  dark: "apps/web/public/cubi-platform-logo-primary-dark.svg",
} as const);

export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;

export function cubiBrandAsset(variant: CubiBrandVariant): string {
  return CUBI_BRAND_ASSETS[variant];
}
