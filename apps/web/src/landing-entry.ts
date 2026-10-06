import { renderLandingPage } from "./landing.js";

const container = document.getElementById("app");
if (!container) {
  throw new Error("APP_ROOT_NOT_FOUND");
}

const isLandingRoute = window.location.pathname === "/" || window.location.pathname === "/index.html";

if (isLandingRoute) {
  renderLandingPage(container);
} else {
  void import("./main.js");
}
