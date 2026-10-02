import test from "node:test";
import assert from "node:assert/strict";
import { fetchP6ActivityUdfs } from "./p6-udf-http.js";

function response(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    async json() { return body; },
  };
}

test("requests the authenticated UDF route and preserves allowed values", async () => {
  const calls: Array<{ input: string; credentials?: string }> = [];
  const result = await fetchP6ActivityUdfs("p1", "p6-field-registry.v1", async (input, init) => {
    calls.push({ input, credentials: init?.credentials });
    return response({
      registry_version: "p6-field-registry.v1",
      udfs: [{
        udf_id: "activity.status",
        subject_area: "Activity",
        display_name: "Status",
        data_type: "enum",
        writable: true,
        nullable: false,
        unit: null,
        allowed_values: ["Planned", "In Progress", "Complete"],
      }],
    });
  });

  assert.equal(calls[0]?.input, "/api/projects/p1/p6/udfs/p6-field-registry.v1");
  assert.equal(calls[0]?.credentials, "include");
  assert.deepEqual(result.udfs[0]?.allowed_values, ["Planned", "In Progress", "Complete"]);
});

test("surfaces authenticated HTTP failures without inventing a fallback", async () => {
  await assert.rejects(
    () => fetchP6ActivityUdfs("p1", "p6-field-registry.v1", async () => response({}, false, 403)),
    /P6_UDF_HTTP_403/,
  );
});

test("rejects malformed UDF metadata", async () => {
  await assert.rejects(
    () => fetchP6ActivityUdfs("p1", "p6-field-registry.v1", async () => response({
      registry_version: "p6-field-registry.v1",
      udfs: [{ udf_id: "activity.bad", data_type: "unknown" }],
    })),
    /P6_UDF_RESPONSE_INVALID/,
  );
});
