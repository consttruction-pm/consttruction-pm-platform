import { execFileSync } from "node:child_process";
import { gunzipSync } from "node:zlib";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const patchDir = resolve(here, "../preview-patches");
const root = resolve(here, "../../..");
const files = readdirSync(patchDir).filter((name) => name.endsWith(".gz")).sort();
const webParts = files.filter((name) => name.startsWith("web-part-"));
const patches = files.filter((name) => !name.startsWith("web-part-")).map((name) => [name, gunzipSync(readFileSync(join(patchDir, name)))]);
if (webParts.length) patches.push(["web.patch", Buffer.concat(webParts.map((name) => gunzipSync(readFileSync(join(patchDir, name)))))]);
for (const [index, [name, patch]] of patches.entries()) {
  const patchPath = join(tmpdir(), `cubi-preview-source-${index}-${name.replace(/[^a-z0-9]/gi, "-")}.patch`);
  writeFileSync(patchPath, patch);
  execFileSync("git", ["-C", root, "apply", "--binary", "--whitespace=nowarn", patchPath], { stdio: "inherit" });
}
console.log("Applied the versioned CUBI preview source patches.");
