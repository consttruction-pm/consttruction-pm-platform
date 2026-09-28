export type LanguageFontResource = {
  family: string;
  uri: string;
  format: "woff2" | "woff" | "ttf" | "otf";
  weight: number;
  style: "normal" | "italic" | "oblique";
  unicode_range?: string;
};

export function createFontFaceCss(resources: readonly LanguageFontResource[]): string {
  return resources.map((font) => {
    const unicodeRange = font.unicode_range ? `\n  unicode-range: ${sanitizeCssToken(font.unicode_range)};` : "";
    return `@font-face {
  font-family: "${sanitizeCssString(font.family)}";
  src: url("${sanitizeCssUrl(font.uri)}") format("${font.format}");
  font-weight: ${font.weight};
  font-style: ${font.style};${unicodeRange}
}`;
  }).join("\n");
}

function sanitizeCssString(value: string): string {
  return value.replace(/["\\]/g, "\\$&");
}

function sanitizeCssUrl(value: string): string {
  return value.replace(/["\\\r\n]/g, (character) => encodeURIComponent(character));
}

function sanitizeCssToken(value: string): string {
  if (!/^[A-Za-z0-9_,. -]+$/.test(value)) throw new Error("INVALID_FONT_UNICODE_RANGE");
  return value;
}
