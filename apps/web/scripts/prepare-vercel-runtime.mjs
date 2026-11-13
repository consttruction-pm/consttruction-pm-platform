// Copy the runtime the Vercel Python functions import.
//
// The Vercel project is rooted at ``apps/web`` (the only directory Vercel
// reads for a project), so the function bundle cannot reach ``../../src``.
// This script stages an unmodified copy of the repository runtime inside the
// project root; nothing here is committed or edited by hand.
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const repoRoot = resolve(webRoot, "../..");
const runtime = join(webRoot, "vercel-runtime");

rmSync(runtime, { recursive: true, force: true });
mkdirSync(join(runtime, "src"), { recursive: true });

const repoSource = join(repoRoot, "src");
if (!existsSync(repoSource)) {
  // Vercel clones the whole repository before switching to the project root,
  // so this should not happen; keep the build observable if it does.
  console.warn("cubi: repository src is not reachable from " + webRoot);
} else {
  cpSync(repoSource, join(runtime, "src"), {
    recursive: true,
    filter: (source) =>
      !source.includes("__pycache__") && !source.endsWith(".pyc"),
  });
}

const requirements = join(repoRoot, "requirements.txt");
if (existsSync(requirements)) {
  cpSync(requirements, join(runtime, "requirements.txt"));
}

const webroot = join(runtime, "webroot");
mkdirSync(webroot, { recursive: true });
for (const file of ["index.html", "app.html", "login.html"]) {
  cpSync(join(webRoot, file), join(webroot, file));
}

console.log("cubi: staged runtime at " + runtime);
