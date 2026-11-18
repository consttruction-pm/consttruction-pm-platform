import assert from "node:assert/strict";
import test from "node:test";

import {
  ACTIVITY_CODE_API_VERSION,
  ACTIVITY_NOTEBOOK_API_VERSION,
  parseActivityCodeList,
  parseNotebookTopicList,
  parseActivityCode,
  parseNotebookTopic,
} from "./workspace-activity-children.js";

test("parses an activity code list and keeps record revisions", () => {
  const codes = parseActivityCodeList({
    contract_version: ACTIVITY_CODE_API_VERSION,
    kind: "p6_activity_code_list",
    activity_id: "A130",
    codes: [
      { assignment_id: "c1", activity_id: "A130", code_type: "AREA", code_value: "ZONE-1", description: "North", record_revision: 2 },
    ],
  });
  assert.equal(codes.length, 1);
  assert.equal(codes[0].recordRevision, 2);
  assert.equal(codes[0].description, "North");
});

test("rejects an activity code record without a positive record revision", () => {
  assert.throws(() => parseActivityCode({
    assignment_id: "c1", activity_id: "A130", code_type: "AREA", code_value: "Z", record_revision: 0,
  }), /INVALID_ACTIVITY_CODE/);
});

test("parses notebook topics with sanitised description and order", () => {
  const topics = parseNotebookTopicList({
    contract_version: ACTIVITY_NOTEBOOK_API_VERSION,
    kind: "p6_activity_notebook_list",
    activity_id: "A130",
    topics: [
      { topic_id: "n1", activity_id: "A130", topic_name: "Kickoff", description: "<p>Agreed</p>", sequence: 1, record_revision: 3, updated_at: "2026-11-18T09:00:00+00:00" },
    ],
  });
  assert.deepEqual(topics.map((item) => [item.topicName, item.sequence, item.recordRevision]), [["Kickoff", 1, 3]]);
  assert.equal(topics[0].description, "<p>Agreed</p>");
});

test("rejects a notebook topic without a name", () => {
  assert.throws(() => parseNotebookTopic({
    topic_id: "n1", activity_id: "A130", topic_name: "", sequence: 0, record_revision: 1,
  }), /INVALID_NOTEBOOK_TOPIC/);
});

test("both contract versions are fixed", () => {
  assert.equal(ACTIVITY_CODE_API_VERSION, "p6-activity-code-api.v1");
  assert.equal(ACTIVITY_NOTEBOOK_API_VERSION, "p6-activity-notebook-api.v1");
});
