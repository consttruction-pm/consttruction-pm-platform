import { mountWorkbench } from "./workbench/mount.js";

/**
 * CUBI AI Workbench entry point.
 *
 * Served only from `/ai-workbench` by the authenticated document boundary. It
 * is a separate bundle from the Engineering workspace so the Workbench shell
 * can never mount into another environment by accident.
 */
void mountWorkbench().catch((error: unknown) => {
  const root = document.getElementById("aiw-root");
  if (root) {
    root.textContent =
      error instanceof Error ? `AI_WORKBENCH_START_FAILED: ${error.message}` : "AI_WORKBENCH_START_FAILED";
  }
});
