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

function resolveRequestFile(requestPath) {
  const pathname = decodeURIComponent(requestPath.split("?")[0]);
  const publicRoot = join(root, "public");
  const distRoot = join(root, "dist");
  const distWebEntry = join(distRoot, "web", "src");
  const distClientSyncEntry = join(distRoot, "client-sync", "src");

  let candidate;

  if (pathname === "/") {
    candidate = join(root, "index.html");
  } else if (pathname.startsWith("/dist/")) {
    const rest = pathname.slice("/dist/".length);
    candidate = rest.startsWith("web/") || rest.startsWith("client-sync/")
      ? join(distRoot, rest)
      : join(distWebEntry, rest);
  } else if (pathname.startsWith("/client-sync/src/")) {
    candidate = join(distClientSyncEntry, pathname.slice("/client-sync/src/".length));
  } else {
    const relativePath = pathname.replace(/^\/+/, "");
    candidate = join(root, relativePath);
    if (!existsSync(candidate) || !statSync(candidate).isFile()) {
      candidate = join(publicRoot, relativePath);
    }
  }

  const normalized = normalize(candidate);
  if (!within(root, normalized) && !within(distRoot, normalized) && !within(publicRoot, normalized)) {
    return null;
  }
  return normalized;
}

export { resolveRequestFile };

export function createPreviewServer() {
  return http.createServer((req, res) => {
    try {
      const file = resolveRequestFile(req.url || "/");
      if (!file) {
        res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Forbidden");
        return;
      }

      if (!existsSync(file) || !statSync(file).isFile()) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Not Found");
        return;
      }

      res.writeHead(200, {
        "Content-Type": contentType(file),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      });

      createReadStream(file).pipe(res);
    } catch {
      res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Preview server error");
    }
  });
}

const isDirectExecution = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (isDirectExecution) {
  const server = createPreviewServer();
  server.listen(port, host, () => {
    console.log(`CUBI Web Preview listening on http://${host === "0.0.0.0" ? "localhost" : host}:${port}`);
  });
}
