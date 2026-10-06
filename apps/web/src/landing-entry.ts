import { renderLandingPage } from "./landing.js";

const container = document.getElementById("app");
if (!container) {
  throw new Error("APP_ROOT_NOT_FOUND");
}

const pathname = window.location.pathname.replace(/\/+$/, "");
const isAppRoute = /\/app(?:\/index\.html)?$/.test(pathname);
const isLandingRoute = !isAppRoute && (
  pathname === "" ||
  pathname.endsWith("/index.html")
);

if (isLandingRoute) {
  renderLandingPage(container);
} else {
  void import("./main.js");
}
