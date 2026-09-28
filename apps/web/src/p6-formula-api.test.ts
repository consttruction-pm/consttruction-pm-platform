import test from "node:test";
import assert from "node:assert/strict";
import { validateP6Formula, dependencyFieldIds } from "./p6-formula-api.js";

test("formula validation uses ProjectContext and authoritative API transport", async () => {
  const calls: Array<{ path: string; context: unknown }> = [];
  const transport = {
    async get() { throw new Error("not used"); },
    async post<TRequest, TResponse>(path: string, _request: TRequest, context: unknown): Promise<{ ok: true; data: TResponse }> {
      calls.push({ path, context });
      return {
        ok: true as const,
        data: {
          status: "valid" as const,
          message_key: null,
          result_type: "percentage",
          result_unit: "%",
          authoritative: true as const,
          dependencies: [{ field_id: "actual", dependency_type: "field" as const, subject_area: "activity" }],
        },
      };
    },
  };
  const result = await validateP6Formula(transport, { tenant_id: "t1", project_id: "p1", revision: 9 }, {
    expression: "actual / planned",
    subject_area: "activity",
  });
  assert.equal(result.ok, true);
  assert.equal(calls[0].path, "/api/v1/p6/formulas/validate");
  assert.deepEqual(calls[0].context, { tenant_id: "t1", project_id: "p1", revision: 9 });
  if (result.ok) assert.deepEqual(dependencyFieldIds(result.data), ["actual"]);
});
