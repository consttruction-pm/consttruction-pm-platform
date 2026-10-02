export type ProjectSelectionOption = {
  project_id: string;
  label: string;
};

export function getProjectSelectionOptions(
  projects: readonly { project_id: string; name: string }[],
): readonly ProjectSelectionOption[] {
  return projects.map((project) => ({
    project_id: project.project_id,
    label: project.name.trim() || project.project_id,
  }));
}

export function buildProjectSelectionUrl(currentUrl: string, projectId: string): string {
  const url = new URL(currentUrl);
  url.searchParams.set("project_id", projectId);
  return url.toString();
}

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
