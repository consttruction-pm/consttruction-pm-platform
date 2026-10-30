import { renderLandingPage } from "./landing.js";
import { resolveEntryRoute } from "./entry-routing.js";
import { renderWorkspaceStartup } from "./workspace-startup.js";

const container = document.getElementById("app");
if (!container) {
  throw new Error("APP_ROOT_NOT_FOUND");
}

if (resolveEntryRoute(window.location.pathname) === "landing") {
  renderLandingPage(container);
} else {
  // Render a useful surface before the workspace entry is fetched.
  // The workspace is bundled into one request so slower mobile networks do not
  // have to fetch the entire unbundled module graph before startup can begin.
  const locale = document.documentElement.lang.toLowerCase().startsWith("fa")
    || navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  renderWorkspaceStartup(container, locale, "loading");
  const moduleTimer = window.setTimeout(() => {
    renderWorkspaceStartup(container, locale, "slow");
  }, 20000);

  const bundleUrl = new URL("./main.bundle.js", import.meta.url).href;
  void import(bundleUrl)
    .then(() => window.clearTimeout(moduleTimer))
    .catch((error: unknown) => {
      window.clearTimeout(moduleTimer);
      console.error("CUBI workspace entry failed to load", error);
      renderWorkspaceStartup(container, locale, "failed");
    });
}
