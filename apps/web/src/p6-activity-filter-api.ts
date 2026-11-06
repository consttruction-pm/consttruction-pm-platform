import type { ApiTransport, ProjectContext } from "./client.js";

export type ActivityFilterConnector = "where" | "and" | "or";
export type ActivityFilterOperator =
  | "equals" | "not-equals" | "contains" | "not-contains" | "starts-with" | "ends-with"
  | "greater-than" | "greater-than-or-equal" | "less-than" | "less-than-or-equal"
  | "between" | "not-between" | "is-empty" | "is-not-empty";

export type ActivityFilterCriterion = {
  connector: ActivityFilterConnector;
  field_id: string;
  operator: ActivityFilterOperator;
  value: string | number | boolean | null;
  high_value?: string | number | boolean | null;
};

export type SavedActivityFilter = {
  filter_id: string;
  name: string;
  category: "layout" | "user-defined";
  owner_id: string;
  revision: number;
  criteria: readonly ActivityFilterCriterion[];
  match_mode: "all" | "any";
};

export type ActivityFilterRegister = {
  contract_version: "p6-activity-filter-api.v1";
  kind: "activity_filter_register";
  filters: SavedActivityFilter[];
};

export type ActivityFilterSaveRequest = {
  filter_id: string;
  name: string;
  category: "layout" | "user-defined";
  expected_revision: number;
  match_mode: "all" | "any";
  criteria: readonly ActivityFilterCriterion[];
};

function activityFilterPath(context: ProjectContext): string {
  return "/api/projects/" + encodeURIComponent(context.project_id) + "/p6/activity-filters";
}

export function createP6ActivityFilterClient(transport: ApiTransport, context: ProjectContext) {
  return {
    async list(): Promise<readonly SavedActivityFilter[]> {
      const result = await transport.get<ActivityFilterRegister>(activityFilterPath(context), context);
      if (!result.ok) throw new Error(result.error.code || "P6_ACTIVITY_FILTER_LIST_FAILED");
      if (result.data.contract_version !== "p6-activity-filter-api.v1" ||
          result.data.kind !== "activity_filter_register" ||
          !Array.isArray(result.data.filters)) {
        throw new Error("INVALID_ACTIVITY_FILTER_REGISTER_RESPONSE");
      }
      return result.data.filters;
    },
    async save(request: ActivityFilterSaveRequest): Promise<SavedActivityFilter> {
      const result = await transport.post<ActivityFilterSaveRequest, {
        contract_version: string;
        filter: SavedActivityFilter;
      }>(activityFilterPath(context), request, context);
      if (!result.ok) throw new Error(result.error.code || "P6_ACTIVITY_FILTER_SAVE_FAILED");
      if (result.data.contract_version !== "p6-activity-filter-api.v1" || !result.data.filter) {
        throw new Error("INVALID_ACTIVITY_FILTER_SAVE_RESPONSE");
      }
      return result.data.filter;
    },
    async delete(filterId: string, expectedRevision: number): Promise<void> {
      if (!transport.delete) throw new Error("DELETE_TRANSPORT_UNAVAILABLE");
      const url = activityFilterPath(context) + "/" + encodeURIComponent(filterId) +
        "?expected_revision=" + encodeURIComponent(String(expectedRevision));
      const result = await transport.delete<Record<string, never>, {
        contract_version: string;
        deleted: boolean;
        filter_id: string;
      }>(url, {}, context);
      if (!result.ok) throw new Error(result.error.code || "P6_ACTIVITY_FILTER_DELETE_FAILED");
      if (!result.data.deleted || result.data.filter_id !== filterId) {
        throw new Error("INVALID_ACTIVITY_FILTER_DELETE_RESPONSE");
      }
    },
  };
}
