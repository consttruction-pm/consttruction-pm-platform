import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  createWorkspaceState,
  setControlSummary,
  setFieldAssurance,
  setFieldIssues,
  setFieldOperations,
  setSiteDailyLogs,
  setChangeClaimRecords,
  withActivities,
  type WorkspaceCalendarMode,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
