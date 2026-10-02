export function selectProjectId(
  projects: readonly { project_id: string }[],
  requestedProjectId: string | null,
): string {
  if (projects.length === 0) throw new Error("NO_PROJECTS_AVAILABLE");
  if (requestedProjectId !== null) {
    if (!projects.some((project) => project.project_id === requestedProjectId)) {
      throw new Error("PROJECT_NOT_AVAILABLE");
    }
    return requestedProjectId;
  }
  if (projects.length === 1) return projects[0]!.project_id;
  throw new Error("PROJECT_SELECTION_REQUIRED");
}
