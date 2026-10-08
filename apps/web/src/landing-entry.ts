import { renderLandingPage } from "./landing.js";
import { resolveEntryRoute } from "./entry-routing.js";

const container = document.getElementById("app");
if (!container) {
  throw new Error("APP_ROOT_NOT_FOUND");
}

if (resolveEntryRoute(window.location.pathname) === "landing") {
  renderLandingPage(container);
} else {
  void import("./main.js");
}
