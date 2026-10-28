/** Single source of truth for the approved CUBI logo across Web, Desktop and Mobile. */
export const CUBI_BRAND_ASSET = "apps/web/public/cubi-platform-logo-primary.svg" as const;
export const CUBI_ASSISTANT_AVATAR_ASSET = "apps/web/public/cubi-assistant-avatar.svg" as const;

/** Resolve the shared public asset from the compiled Web module, preserving GitHub Pages base paths. */
export function cubiAssistantAvatarUrl(moduleUrl: string = import.meta.url): string {
  return new URL("../../../cubi-assistant-avatar.svg", moduleUrl).href;
}

/**
 * Resolve the canonical logo the same way as the avatar. Landing markup is
 * rendered by JavaScript, so a document-relative path would break on any page
 * that is not served from the site root (for example a Persian language route).
 */
export function cubiPlatformLogoUrl(moduleUrl: string = import.meta.url): string {
  return new URL("../../../cubi-platform-logo-primary.svg", moduleUrl).href;
}
export const CUBI_BRAND_ASSETS = Object.freeze({ light: CUBI_BRAND_ASSET, dark: CUBI_BRAND_ASSET } as const);
export type CubiBrandVariant = keyof typeof CUBI_BRAND_ASSETS;
export function cubiBrandAsset(_variant: CubiBrandVariant): string { return CUBI_BRAND_ASSET; }
