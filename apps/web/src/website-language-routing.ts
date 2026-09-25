export type LocalizedRoute = {
  languageTag: string;
  path: string;
};

export type LocalizedSeoMetadata = {
  languageTag: string;
  title: string;
  description: string;
  canonicalPath: string;
  alternatePaths: readonly string[];
};

export function languagePath(
  pathname: string,
  languageTag: string,
): LocalizedRoute {
  const normalized = normalizePath(pathname);
  return {
    languageTag,
    path: "/" + languageTag + (normalized === "/" ? "" : normalized),
  };
}

export function languageFromPath(
  pathname: string,
  supportedLanguages: readonly string[],
): string | null {
  const normalized = normalizePath(pathname);
  const segment = normalized.split("/")[1];
  if (!segment) return null;
  return supportedLanguages.includes(segment) ? segment : null;
}

export function stripLanguagePrefix(
  pathname: string,
  supportedLanguages: readonly string[],
): string {
  const normalized = normalizePath(pathname);
  const parts = normalized.split("/");
  const first = parts[1];
  if (first && supportedLanguages.includes(first)) {
    const rest = "/" + parts.slice(2).join("/");
    return rest === "/" ? "/" : normalizePath(rest);
  }
  return normalized;
}

export function buildAlternateLanguagePaths(
  canonicalPath: string,
  supportedLanguages: readonly string[],
): readonly LocalizedRoute[] {
  const clean = stripLanguagePrefix(canonicalPath, supportedLanguages);
  return supportedLanguages.map((languageTag) => languagePath(clean, languageTag));
}

function normalizePath(pathname: string): string {
  if (!pathname || pathname === "/") return "/";
  const withSlash = pathname.startsWith("/") ? pathname : "/" + pathname;
  return withSlash.replace(/\/+$/, "") || "/";
}
