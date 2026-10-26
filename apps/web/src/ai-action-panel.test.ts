import assert from "node:assert/strict";
import test from "node:test";

import { actionErrorLabelKey, proposalStatusLabelKey } from "./ai-action-panel.js";

test("known pre-execution rejection is not presented as an uncertain outcome", () => {
  assert.equal(proposalStatusLabelKey("blocked"), "preconditionFailed");
  assert.equal(proposalStatusLabelKey("denied"), "permissionDenied");
  assert.equal(proposalStatusLabelKey("uncertain"), "noRetry");
  assert.equal(proposalStatusLabelKey("executing"), "executing");
});

test("activity update execution uses the update success message", () => {
  assert.equal(proposalStatusLabelKey("executed", "activity.update"), "activityUpdated");
  assert.equal(proposalStatusLabelKey("executed", "activity.create"), "activityCreated");
  assert.equal(proposalStatusLabelKey("executed"), "executed");
  assert.equal(proposalStatusLabelKey("unknown-status"), null);
});

test("revision and permission failures map to their explicit non-uncertain messages", () => {
  assert.equal(actionErrorLabelKey("AI_ACTION_ACTIVITY_REVISION_CONFLICT"), "preconditionFailed");
  assert.equal(actionErrorLabelKey("AI_ACTION_ACTIVITY_NOT_FOUND"), "preconditionFailed");
  assert.equal(actionErrorLabelKey("AI_ACTION_ACTIVITY_ALREADY_EXISTS"), "activityAlreadyExists");
  assert.equal(actionErrorLabelKey("AI_TOOL_NOT_PERMITTED"), "permissionDenied");
  assert.equal(actionErrorLabelKey("AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN"), "noRetry");
  assert.equal(actionErrorLabelKey("SOMETHING_ELSE"), null);
});
