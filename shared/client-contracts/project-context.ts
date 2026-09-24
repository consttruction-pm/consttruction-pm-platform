/**
 * Shared client-side types derived from shared/contracts/client-parity.schema.json.
 *
 * This module contains transport/context shapes only; scheduling and other
 * authoritative calculations remain in the Shared Core.
 */

export type ClientId = "web" | "desktop" | "mobile";

export type ProjectContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
};

export type ClientCapabilities = {
  scheduling: "shared-core";
  progress_evm: "shared-core";
  resource_cost: "shared-core";
  offline: boolean;
  localization: string[];
};

export type ClientParityContract = {
  contract_version: "1.0";
  client: ClientId;
  project_context: ProjectContext;
  capabilities: ClientCapabilities;
};

export function validateProjectContext(context: ProjectContext): void {
  if (!context.tenant_id || !context.project_id || !Number.isInteger(context.revision) || context.revision < 0) {
    throw new Error("INVALID_PROJECT_CONTEXT");
  }
}
