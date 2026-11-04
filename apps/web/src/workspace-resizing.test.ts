import assert from "node:assert/strict";
import test from "node:test";
import { clampResizePercent, resizedColumnWidth } from "./workspace-resizing.js";

test("split ratios clamp to usable pane bounds and keep a finite fallback", () => {
  assert.equal(clampResizePercent(20, 30, 70, 45), 30);
  assert.equal(clampResizePercent(85, 30, 70, 45), 70);
  assert.equal(clampResizePercent(52.5, 30, 70, 45), 52.5);
  assert.equal(clampResizePercent(Number.NaN, 30, 70, 45), 45);
  assert.equal(clampResizePercent(Number.POSITIVE_INFINITY, 30, 70, 45), 45);
});

test("column drag grows toward the physical trailing edge in LTR and RTL", () => {
  assert.equal(resizedColumnWidth(120, 200, 245, "ltr"), 165);
  assert.equal(resizedColumnWidth(120, 200, 245, "rtl"), 75);
  assert.equal(resizedColumnWidth(120, 200, 155, "rtl"), 165);
});

test("column drag enforces min/max widths without changing the source width", () => {
  assert.equal(resizedColumnWidth(120, 200, -500, "ltr"), 40);
  assert.equal(resizedColumnWidth(700, 200, 900, "ltr"), 720);
  assert.equal(resizedColumnWidth(120, 200, 200, "ltr"), 120);
});

test("resize binding safely ignores DOM-light renderer fixtures", async () => {
  const { bindWorkspaceResizeInteractions } = await import("./workspace-resizing.js");
  assert.doesNotThrow(() => {
    bindWorkspaceResizeInteractions({} as HTMLElement, {} as never, {} as never);
  });
});
