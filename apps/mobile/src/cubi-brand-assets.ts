/** Single source of truth: consume the approved shared CUBI logo; never redraw or fork it. */
export const CUBI_BRAND_ASSET = "apps/web/public/cubi-platform-logo-primary.svg" as const;
export const CUBI_BRAND_ASSETS = Object.freeze({ light: CUBI_BRAND_ASSET, dark: CUBI_BRAND_ASSET } as const);
export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;
