import test from "node:test";
import assert from "node:assert/strict";
import { renderP6LayoutPersistenceControls } from "./p6-layout-persistence-controls-view.js";

test("P6 layout persistence controls expose scope and actions", () => {
  const html = renderP6LayoutPersistenceControls("project", {
    title: "Layout Persistence",
    load: "Load layout",
    save: "Save layout",
    scope: "Scope",
  });

  assert.match(html, /data-p6-layout-load/);
  assert.match(html, /data-p6-layout-save/);
  assert.match(html, /project/);
});
