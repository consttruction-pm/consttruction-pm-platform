/**
 * Preview runtime smoke test.
 *
 * CI and local runs share this file so a green CI check always corresponds to a
 * check that can be reproduced with `npm run preview:smoke`.
 */
import { startPreviewServer } from "./preview-server.mjs";

const expected = [
  ["http://127.0.0.1:4173/", "CUBI Platform"],
  ["http://127.0.0.1:4173/styles.css", "prefers-reduced-motion"],
  ["http://127.0.0.1:4173/login", "Choose working role"],
  ["http://127.0.0.1:4173/login", "role-picker"],
  ["http://127.0.0.1:4173/workbench", "Personal Workbench"],
  ["http://127.0.0.1:4173/workbench", "personal-workbench"],
  ["http://127.0.0.1:4173/enterprise", "The Enterprise environment is not ready"],
  ["http://127.0.0.1:4173/role-workbench.css", ".rw-card"],
  ["http://127.0.0.1:4173/dist/role-workbench-entry.bundle.js", "CUBI Enterprise"],
  ["http://127.0.0.1:4173/cubi-assistant-avatar.svg", "CUBI AI Project Assistant"],
  ["http://127.0.0.1:4173/client-sync/src/scheduling-adapter.js", "SCHEDULING_CONTRACT_VERSION"],
  ["http://127.0.0.1:4173/platform/", "Project planning and controls, connected."],
  ["http://127.0.0.1:4173/solutions/", "Built around how construction projects are delivered."],
  ["http://127.0.0.1:4173/resources/", "Understand the platform. Find the right next step."],
  ["http://127.0.0.1:4173/contact/", "Get to the right CUBI destination."],
  ["http://127.0.0.1:4173/pricing/", "Choose your Pro time."],
  ["http://127.0.0.1:4173/pricing/", "month-quantity"],
  // Persian i¶»§q«^