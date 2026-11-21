import assert from "node:assert/strict";
import test from "node:test";

import { recordsToCsv, sortRecords } from "./enterprise/pages/records.js";

type Row = Record<string, unknown>;

const rows: Row[] = [
  { record_id: "r-1", title: "Beta", status: "open", revision: 2 },
  { record_id: "r-2", title: "alpha", status: "closed", revision: 1 },
  { record_id: "r-3", title: "Gamma", status: "open", revision: 3 },
];

test("sortRecords uses the requested locale and direction without mutating input", () => {
  const original = [...rows];
  const ascending = sortRecords(rows, "title", 1, "en");
  assert.deepEqual(ascending.map((row) => row.record_id), ["r-2", "r-1", "r-3"]);
  const descending = sortRecords(rows, "title", -1, "en");
  assert.deepEqual(descending.map((row) => row.record_id), ["r-3", "r-1", "r-2"]);
  assert.deepEqual(rows, original, "the input array must not be mutated");
  assert.deepEqual(sortRecords(rows, null, 1, "en").map((row) => row.record_id), ["r-1", "r-2", "r-3"]);
});

test("sortRecords keeps missing values stable instead of fabricating an order", () => {
  const withGap: Row[] = [
    { record_id: "a", title: "Zulu" },
    { record_id: "b" },
    { record_id: "c", title: "Alfa" },
  ];
  const sorted = sortRecords(withGap, "title", 1, "en");
  assert.equal(sorted[0]?.record_id, "b");
  assert.deepEqual(sorted.slice(1).map((row) => row.record_id), ["c", "a"]);
});

test("recordsToCsv quotes every field and preserves commas, quotes and newlines", () => {
  const csv = recordsToCsv(rows, [
    ["Title", (item: Row) => String(item.title)],
    ["Status", (item: Row) => String(item.status)],
  ]);
  assert.ok(csv.startsWith("\uFEFF"), "Excel needs a BOM to read UTF-8");
  const lines = csv.slice(1).split("\r\n");
  assert.equal(lines[0], '"Title","Status"');
  assert.equal(lines[1], '"Beta","open"');

  const tricky = recordsToCsv(
    [{ title: 'A, "quoted"\nvalue' }],
    [["Title", (item: Row) => String(item.title)]],
  );
  assert.equal(tricky, '\uFEFF"Title"\r\n"A, ""quoted""\nvalue"');
});

test("recordsToCsv with no rows still returns the header row", () => {
  const csv = recordsToCsv([], [["Name", (item: Row) => String(item.name)]]);
  assert.equal(csv, '\uFEFF"Name"');
});
