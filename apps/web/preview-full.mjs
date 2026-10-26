import { spawn } from "node:child_process";
import { delimiter, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(webRoot, "..", "..");
const forwarded = process.argv.slice(2);

const configured = process.env.CUBI_PYTHON?.trim();
const command = configured
  ? { executable: configured, prefix: [] }
  : process.platform === "win32"
    ? { executable: "py", prefix: ["-3"] }
    : { executable: "python3", prefix: [] };

const pythonPath = [join(repoRoot, "src"), process.env.PYTHONPATH]
  .filter((value) => value && value.length > 0)
  .join(delimiter);

const child = spawn(
  command.executable,
  [
    ...command.prefix,
    "-m",
    "construction_pm.preview",
    "--web-root",
    webRoot,
    ...forwarded,
  ],
  {
    cwd: repoRoot,
    env: { ...process.env, PYTHONPATH: pythonPath },
    stdio: "inherit",
  },
);

child.on("error", (error) => {
  console.error(
    "Unable to start the CUBI Python preview runtime. Set CUBI_PYTHON to a Python 3.11+ executable.",
  );
  console.error(String(error));
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    if (!child.killed) child.kill(signal);
  });
}
