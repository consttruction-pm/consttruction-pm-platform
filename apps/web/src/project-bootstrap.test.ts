import assert from "node:assert/strict";
import test from "node:test";
import type { ApiResult } from "./client.js";
import { ProjectBootstrap, type ProjectBootstrapDependencies } from "./project-bootstrap.js";
import type { ProjectSummary, Session, SessionApi } from "./session-api.js";
import type { ProjectContext } from "./client.js";
import type { WorkspaceState } from "./workspace-model.js";
import type { WorkspaceReadClient } from "./workspace-read-api.js";

const session: Session = {
  session_id: "s1",
  user_id: "u1",
  tenant_id: "t1",
  roles: ["member"],
  expires_at: "2099-01-01T00:00:00Z",
};

const projects: ProjectSummary[] = [
  { project_id: "p1", tenant_id: "t1", name: "Project 1", revision: 1 },
  { project_id: "p2", tenant_id: "t1", name: "Project 2", revision: 2 },
];

const workspace = { context: { tenant_id: "t-authoritative", project_id: "p-authoritative", revision: 9 } } as WorkspaceState;

function ok<T>(data: T): ApiResult<T> {
  return { ok: true, data };
}

function error(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: `error.${code.toLowerCase()}`, available_actions: [] },
  };
}

function deps(overrides: Partial<SessionApi> = {}): {
  dependencies: ProjectBootstrapDependencies;
  opened: string[];
  runtimeContexts: ProjectContext[];
} {
  const opened: string[] = [];
  const runtimeContexts: ProjectContext[] = [];

  const sessionApi: SessionApi = {
    getSession: async () => ok(session),
    listProjects: async () => ok({ projects: [projects[0]] }),
    openProject: async (projectId) => {
      opened.push(projectId);
      return ok({
        context: {
          tenant_id: "t-authoritative",
          project_id: "p-authoritative",
          revision: 9,
          user_id: "u1",
        },
      });
    },
    createProject: async () => ok({
      context: {
        tenant_id: "t1",
        project_id: "new",
        revision: 0,
        user_id: "u1",
      },
    }),
    ...overrides,
  };

  const syncRuntime = {
    openProject: (tenant_id: string, project_id: string, revision: number) => {
      runtimeContexts.push({ tenant_id, project_id, revision });
      return { tenant_id, project_id, revision };
    },
  } as ProjectBootstrapDependencies["syncRuntime"];

  const workspaceReadClient = {
    load: async (context: ProjectContext) => ok({
      context,
    } as WorkspaceState),
  } as unknown as WorkspaceReadClient;

  return {
    dependencies: { sessionApi, syncRuntime, workspaceReadClient },
    opened,
    runtimeContexts,
  };
}

test("one project opens and hydrates using authoritative open context", async () => {
  const setup = deps();
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "ready");
  assert.deepEqual(setup.opened, ["p1"]);
  assert.deepEqual(setup.runtimeContexts, [{
    tenant_id: "t-authoritative",
    project_id: "p-authoritative",
    revision: 9,
  }]);
});

test("multiple projects stop at selection", async () => {
  const setup = deps({ listProjects: async () => ok({ projects }) });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "selecting");
  assert.deepEqual(setup.opened, []);
});

test("zero projects returns explicit error", async () => {
  const setup = deps({ listProjects: async () => ok({ projects: [] }) });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "NO_PROJECTS_AVAILABLE");
});

test("project creation hydrates the authoritative created context without a second open call", async () => {
  const setup = deps({
    createProject: async (projectId, name) => {
      assert.equal(projectId, "new-project");
      assert.equal(name, "New Project");
      return ok({
        context: {
          tenant_id: "t-created",
          project_id: projectId,
          revision: 0,
          user_id: "u1",
        },
      });
    },
  });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.createProject("new-project", "New Project");

  assert.equal(state?.status, "ready");
  assert.deepEqual(setup.opened, []);
  assert.deepEqual(setup.runtimeContexts, [{
    tenant_id: "t-created",
    project_id: "new-project",
    revision: 0,
  }]);
  assert.deepEqual(state?.status === "ready" ? state.context : null, {
    tenant_id: "t-created",
    project_id: "new-project",
    revision: 0,
  });
});

test("project creation failure is surfaced without workspace hydration", async () => {
  const setup = deps({ createProject: async () => error("PROJECT_CREATE_FAILED") });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.createProject("new-project", "New Project");

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "PROJECT_CREATE_FAILED");
  assert.deepEqual(setup.runtimeContexts, []);
});

test("invalid project selection is rejected without opening", async () => {
  const setup = deps();
  const bootstrap = new ProjectBootstrap(setup.dependencies);
  await bootstrap.start();

  const state = await bootstrap.selectProject("missing");

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "PROJECT_NOT_AVAILABLE");
  assert.deepEqual(setup.opened, ["p1"]);
});

test("session failure is surfaced without project access", async () => {
  const setup = deps({ getSession: async () => error("SESSION_REQUIRED") });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "SESSION_REQUIRED");
  assert.deepEqual(setup.opened, []);
});

test("open failure is surfaced", async () => {
  const setup = deps({
    openProject: async () => error("OPEN_FAILED"),
    listProjects: async () => ok({ projects: [projects[0]] }),
  });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "OPEN_FAILED");
});

test("workspace read failure is surfaced", async () => {
  const setup = deps();
  setup.dependencies.workspaceReadClient = {
    load: async () => error("WORKSPACE_READ_FAILED"),
  } as unknown as WorkspaceReadClient;
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "WORKSPACE_READ_FAILED");
});

test("a stale bootstrap result cannot replace a newer selection", async () => {
  let resolveOpen: ((value: ApiResult<{ context: ProjectContext & { user_id: string } }>) => void) | undefined;
  const setup = deps({
    listProjects: async () => ok({ projects: [projects[0], projects[1]] }),
    openProject: async (projectId) => {
      if (projectId === "p1") {
        return await new Promise<ApiResult<{ context: ProjectContext & { user_id: string } }>>((resolve) => {
          resolveOpen = resolve;
        });
      }
      return ok({
        context: {
          tenant_id: "t2",
          project_id: "p2",
          revision: 2,
          user_id: "u1",
        },
      });
    },
  });

  const bootstrap = new ProjectBootstrap(setup.dependencies);
  const selecting = await bootstrap.start();
  assert.equal(selecting?.status, "selecting");

  const stale = bootstrap.selectProject("p1");
  const current = await bootstrap.selectProject("p2");

  assert.equal(current?.status, "ready");
  resolveOpen?.(ok({
    context: {
      tenant_id: "t1",
      project_id: "p1",
      revision: 1,
      user_id: "u1",
    },
  }));

  assert.equal(await stale, null);
});


test("P6 presentation loader runs after authoritative workspace hydration", async () => {
  const setup = deps();
  setup.dependencies.p6PresentationLoader = async (state) => ({
    ...state,
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "26 / 26.4",
      status: "seeded_not_certified",
      fields: [],
    },
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity",
      revision: 0,
      columns: [],
    },
  });
  const bootstrap = new ProjectBootstrap(setup.dependencies);

  const state = await bootstrap.start();

  assert.equal(state?.status, "ready");
  assert.equal(state?.status === "ready" ? state.workspace.p6FieldRegistry?.registry_version : "", "p6-field-registry.v1");
  assert.equal(state?.status === "ready" ? state.workspace.p6Layout?.view_id : "", "activity");
});


test("P6 presentation loader failure becomes bootstrap error", async () => {
  const setup = deps();
  setup.dependencies.p6PresentationLoader = async () => { throw new Error("INVALID_P6_LAYOUT_SCHEMA"); };
  const state = await new ProjectBootstrap(setup.dependencies).start();
  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "P6_PRESENTATION_LOAD_FAILED");
  assert.equal(state?.status === "error" ? state.error.retryable : true, false);
  assert.deepEqual(state?.status === "error" ? state.error.available_actions : [], ["refresh"]);
});

test("P6 network loader failure remains retryable", async () => {
  const setup = deps();
  setup.dependencies.p6PresentationLoader = async () => { throw new Error("NETWORK_ERROR"); };
  const state = await new ProjectBootstrap(setup.dependencies).start();
  assert.equal(state?.status, "error");
  assert.equal(state?.status === "error" ? state.error.code : "", "NETWORK_ERROR");
  assert.equal(state?.status === "error" ? state.error.retryable : false, true);
  assert.deepEqual(state?.status === "error" ? state.error.available_actions : [], ["retry"]);
});
