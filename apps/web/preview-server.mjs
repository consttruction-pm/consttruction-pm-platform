import http from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { lookup } from "node:mime-types";

const root = fileURLToPath(new URL(".", import.meta.url));
const host = process.env.HOST || "0.0.0.0";
const port = Number(process.env.PORT || "4173");

function safePath(requestPath) {
  const pathname = decodeURIComponent(requestPath.split("?")[0]);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const file = normalize(join(root, relative));
  if (!file.startsWith(root + sep) && file !== root) return null;
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
    const file = requested === join(root, "dist", "main.js")
      ? join(root, "dist", "web", "src", "main.js")
      : requested;

    if (!existsSync(file) || !statSync(file).isFile()) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not Found");
      return;
    }

    const type = lookup(file) || "application/octet-stream";
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
