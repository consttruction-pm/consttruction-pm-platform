import { createVisualDemoState, mountVisualDemo } from "./workspace-visual-demo.js";

const container = document.getElementById("app");
if (!container) throw new Error("APP_ROOT_NOT_FOUND");

const locale = navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
document.documentElement.lang = locale;
document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
document.title = locale === "fa"
  ? "محیط کار CUBI — پیش‌نمایش بصری"
  : "CUBI Workspace — visual preview";

container.className = "cp-vd-root";
mountVisualDemo(container, createVisualDemoState(locale));
