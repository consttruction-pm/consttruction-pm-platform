import { mountEnterpriseWorkbench } from "./enterprise/app.js";

/**
 * Enterprise Workbench entry point.
 *
 * This bundle is served only from `/cubi/*` through `enterprise.html`. It is
 * independent of the Engineering workspace bundle so the two environments can
 * never mount into each other by accident.
 */
const root = document.getElementById("cubi-app");
if (!root) {
  throw new Error("CUBI_ENTERPRISE_ROOT_NOT_FOUND");
}

void mountEnterpriseWorkbench();
