// Build the Vercel project rooted at ``apps/web``.
//
// 1. Build the TypeScript client.
// 2. Assemble the public site that Vercel serves (the same artifact the
//    Pages workflow validates), without redirecting ``/app`` to Render.
// 3. Remove the static ``app/`` mirror: ``/app`` is served by the
//    session-gated WSGI function.
// 4. Stage the Python runtime the API functions import.
import { spawnSync } from "node:child_process";
import { cpSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const site = join(webRoot, "vercel-site");

function run(command, args, env = {}) {
  const result = spawnSync(command, args, {
    cwd: webRoot,
    stdio: "inherit",
    env: { ...process.env, ...env },
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

run("npm", ["run", "build"]);

const baseUrl =
  process.env.SITE_BASE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "") ||
  (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "") ||
  "https://cubi-web-preview.vercel.app";

run(process.execPath, ["scripts/assemble-pages-site.mjs", site], {
  SITE_BASE_URL: baseUrl,
  // The workspace is served from this origin now. Never keep the retired
  // Render preview as the /app destination.
  CUBI_WORKSPACE_URL: "",
});

// ``/app`` and ``/app/`` belong to the session-gated function; leaving the
// static mirror in place would make routing order decide whether the gate
// runs.
rmSync(join(site, "app"), { recursive: true, force: true });

// The login document is static: it contains no user data and must load
// without a session.
cpSync(join(webRoot, "login.html"), join(site, "login.html"));

run(process.execPath, ["scripts/prepare-vercel-runtime.mjs"]);

console.log("cubi: assembled " + site + " for " + baseUrl);
