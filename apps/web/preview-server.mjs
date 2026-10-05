import http from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const rootPrefix = root.endsWith(sep) ? root : `${root}${sep}`;
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
]);

function contentType(file) {
  const dot = file.lastIndexOf(".");
  return CONTENT_TYPES.get(dot >= 0 ? file.slice(dot).toLowerCase() : "") || "application/octet-stream";
}

function safePath(requestPath) {
  const pathname = decodeURIComponent(requestPath.split("?")[0]);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const file = normalize(join(root, relative));
  if (!file.startsWith(rootPrefix) && file !== root) return null;
  return file;
}

const server = http.createServer((req, res) => {
  try {
    const requested = safePath(req.url || "/");
    if (!requested) {
      res.writeHead(403);
      res.end("Forbidden");
      return;
    }

    // tsconfig.build.json intentionally keeps Web and client-sync sources under
    // one output tree. index.html uses the stable /dist/main.js browser path;
    // map that entry point to the emitted Web entry without adding a bundler.
    const distRoot = join(root, "dist");
    const distWebEntry = join(distRoot, "web", "src");
    const distClientSyncEntry = join(distRoot, "client-sync", "src");
    const distPrefix = distRoot.endsWith(sep) ? distRoot : `${distRoot}${sep}`;
    const clientSyncRoot = join(root, "..", "client-sync");
    const clientSyncPrefix = clientSyncRoot.endsWith(sep) ? clientSyncRoot : `${clientSyncRoot}${sep}`;
    const file = requested === join(distRoot, "main.js")
      ? join(distWebEntry, "main.js")
      : requested.startsWith(distPrefix)
        ? requested
        : requested.startsWith(clientSyncPrefix)
          ? join(distClientSyncEntry, requested.slice(clientSyncPrefix.length))
          : requested;

    if (!existsSync(file) || !statSync(file).isFile()) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }

    const type = contentType(file);
    res.writeHead(200, {
      "Content-Type": type,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });

    createReadStream(file).pipe(res);
  } catch {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Preview server error");
  }
});

server.listen(port, host, () => {
  console.log(`CUBI Web Preview listening on http://${host === "0.0.0.0" ? "localhost" : host}:${port}`);
});
