/** Single source of truth for the approved CUBI logo across Web, Desktop and Mobile. */
export const CUBI_BRAND_ASSET = "apps/web/public/cubi-platform-logo-primary.svg" as const;
export const CUBI_BRAND_ASSETS = Object.freeze({ light: CUBI_BRAND_ASSET, dark: CUBI_BRAND_ASSET } as const);
export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;
export function cubiBrandAsset(_variant: CubiBrandVariant): string { return CUBI_BRAND_ASSET; }
