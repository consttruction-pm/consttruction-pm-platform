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
  // Render a useful surface before the large workspace module graph is fetched.
  // The global assistant loads independently and must never be the only visible UI.
  const locale = document.documentElement.lang.toLowerCase().startsWith("fa")
    || navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
  renderWorkspaceStartup(container, locale, "loading");
  const moduleTimer = window.setTimeout(() => {
    renderWorkspaceStartup(container, locale, "slow");
  }, 15000);

  void import("./main.js")
    .then(() => window.clearTimeout(moduleTimer))
    .catch((error: unknown) => {
      window.clearTimeout(moduleTimer);
      console.error("CUBI workspace entry failed to load", error);
      renderWorkspaceStartup(container, locale, "failed");
    });
}
