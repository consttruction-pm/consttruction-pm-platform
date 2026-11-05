#!/usr/bin/env node
/**
 * Starts the same real preview runtime used by the E2E suite, runs the desktop
 * journey audit against it, then stops the runtime. This keeps the audit
 * reproducible without a manually managed server or database.
 */
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { startManagedRuntime } from "./preview-e2e.mjs";

const runtime = await startManagedRuntime();
const audit = fileURLToPath(new URL("./audit-workspace.mjs", import.meta.url));
const child = spawn(process.execPath, [audit], {
  env: { ...process.env, CUBI_AUDIT_URL: runtime.baseUrl },
  stdio: "inherit",
});
const code = await new Promise((resolve) => child.on("exit", resolve));
await runtime.stop();
process.exitCode = typeof code === "number" ? code : 1;
