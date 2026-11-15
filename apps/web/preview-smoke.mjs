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
  ["http://127.0.0.1:4173/cubi-assistant-avatar.svg", "CUBI AI Project Assistant"],
  ["http://127.0.0.1:4173/client-sync/src/scheduling-adapter.js", "SCHEDULING_CONTRACT_VERSION"],
  ["http://127.0.0.1:4173/platform/", "Project planning and controls, connected."],
  ["http://127.0.0.1:4173/solutions/", "Built around how construction projects are delivered."],
  ["http://127.0.0.1:4173/resources/", "Understand the platform. Find the right next step."],
  ["http://127.0.0.1:4173/contact/", "Get to the right CUBI destination."],
  ["http://127.0.0.1:4173/pricing/", "Choose your Pro time."],
  ["http://127.0.0.1:4173/pricing/", "month-quantity"],
  // Persian is served as its own documents and routes, not as a client-only repaint.
  ["http://127.0.0.1:4173/fa/", '<html lang="fa" dir="rtl">'],
  ["http://127.0.0.1:4173/fa/", "نرم‌افزار مدیریت پروژه و کنترل پروژه ساختمانی | کوبی"],
  ["http://127.0.0.1:4173/fa/platform/", "برنامه‌ریزی و کنترل پروژه، به‌صورت یکپارچه."],
  ["http://127.0.0.1:4173/fa/solutions/", "بر پایه شیوه تحویل پروژه‌های ساختمانی ساخته شده است."],
  ["http://127.0.0.1:4173/fa/resources/", "پلتفرم را بشناسید و گام بعدی را درست انتخاب کنید."],
  ["http://127.0.0.1:4173/fa/contact/", "به مسیر درست کوبی برسید."],
  ["http://127.0.0.1:4173/fa/pricing/", "مدت اشتراک Pro را انتخاب کنید."],
  ["http://127.0.0.1:4173/fa/pricing/", "month-quantity"],
  ["http://127.0.0.1:4173/fa/contact/", "global-assistant-launcher.bundle.js"],
];

const server = startPreviewServer();
await new Promise((resolve, reject) => {
  server.once("listening", resolve);
  server.once("error", reject);
});

try {
  for (const [url, marker] of expected) {
    const response = await fetch(url);
    if (!response.ok) throw new Error("HTTP " + response.status + " for " + url);
    const body = await response.text();
    if (!body.includes(marker)) {
      throw new Error("Expected " + marker + " in " + url);
    }
    console.log("smoke ok: " + url);
  }
  console.log(`CUBI preview smoke passed (${expected.length} checks).`);
} finally {
  await new Promise((resolve) => server.close(resolve));
}
