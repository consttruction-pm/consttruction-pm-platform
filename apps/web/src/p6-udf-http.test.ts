import test from "node:test";
import assert from "node:assert/strict";
import { fetchP6ActivityUdfs, fetchP6ActivityUdfValues, saveP6ActivityUdfValue } from "./p6-udf-http.js";

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

test("rejects a UDF response from the wrong registry version", async () => {
  await assert.rejects(
    () => fetchP6ActivityUdfs("p1", "p6-field-registry.v1", async () => response({
      registry_version: "p6-field-registry.v2",
      udfs: [],
    })),
    /P6_UDF_RESPONSE_INVALID/,
  );
});

const UDF_VALUE = {
  udf_id: "activity.contract_status",
  subject_area: "Activity",
  display_name: "Contract Status",
  data_type: "enum" as const,
  writable: true,
  nullable: true,
  unit: null,
  allowed_values: ["draft", "signed"],
  value: "signed",
};

test("reads activity UDF values through the revision-scoped route", async () => {
  const calls: string[] = [];
  const result = await fetchP6ActivityUdfValues(
    "p1",
    "p6-field-registry.v1",
    "activity",
    "A 100",
    async (input) => {
      calls.push(input);
      return response({ object_type: "activity", object_id: "A 100", values: [UDF_VALUE] });
    },
  );

  assert.equal(
    calls[0],
    "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity/A%20100",
  );
  assert.equal(result.values[0]?.value, "signed");
  assert.deepEqual(result.values[0]?.allowed_values, ["draft", "signed"]);
});

test("writes one typed activity UDF value with PUT and preserves the request body", async () => {
  const calls: Array<{ input: string; method?: string; body?: string }> = [];
  const saved = await saveP6ActivityUdfValue(
    "p1",
    "p6-field-registry.v1",
    "activity",
    "A-100",
    "activity.contract_status",
    "signed",
    async (input, init) => {
      calls.push({ input, method: init?.method, body: init?.body });
      return response(UDF_VALUE);
    },
  );

  assert.equal(
    calls[0]?.input,
    "/api/projects/p1/p6/udf-values/p6-field-registry.v1/activity/A-100/activity.contract_status",
  );
  assert.equal(calls[0]?.method, "PUT");
  assert.deepEqual(JSON.parse(calls[0]?.body ?? "{}"), { value: "signed" });
  assert.equal(saved.value, "signed");
});

test("surfaces the authoritative UDF value error code", async () => {
  await assert.rejects(
    () => saveP6ActivityUdfValue(
      "p1",
      "p6-field-registry.v1",
      "activity",
      "A-100",
      "activity.contract_status",
      "unknown",
      async () => response({ code: "INVALID_ENUM_VALUE" }, false, 400),
    ),
    /INVALID_ENUM_VALUE/,
  );
});

test("rejects malformed UDF value payloads", async () => {
  await assert.rejects(
    () => fetchP6ActivityUdfValues(
      "p1",
      "p6-field-registry.v1",
      "activity",
      "A-100",
      async () => response({ object_type: "activity", object_id: "A-100", values: [{ udf_id: "x" }] }),
    ),
    /P6_UDF_VALUE_RESPONSE_INVALID/,
  );
});
