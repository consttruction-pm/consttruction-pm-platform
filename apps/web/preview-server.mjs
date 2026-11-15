import http from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { isAbsolute, join, normalize, relative, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const host = process.env.HOST || "0.0.0.0";
const port = Number(process.env.PORT || "4173");

const CONTENT_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
  [".otf", "font/otf"],
  [".ttf", "font/ttf"],
]);

function contentType(file) {
  const dot = file.lastIndexOf(".");
  return CONTENT_TYPES.get(dot >= 0 ? file.slice(dot).toLowerCase() : "") || "application/octet-stream";
}

function within(rootPath, candidate) {
  const rel = relative(rootPath, candidate);
  return rel === "" || (!rel.startsWith(".." + sep) && !isAbsolute(rel));
}

export function resolveRequestFile(requestPath) {
  const pathname = decodeURIComponent(requestPath.split("?")[0]);
  // Reject traversal syntax before normalization so "/../x" cannot be
  // silently normalized back inside the web root.
  if (pathname.split("/").some((segment) => segment === "..")) return null;
  const publicRoot = join(¶»§q«^