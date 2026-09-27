import { requireVoiceInput, type AILanguageContext } from "./ai-language-contract.ts";

export const VOICE_COMMAND_VERSION = "voice-command.v1" as const;
export const SCHEDULE_QUERY_VERSION = "schedule-query.v1" as const;

export type VoiceCommandSource = "microphone" | "imported_audio" | "manual_transcript";
export type ScheduleQueryKind = "fact" | "explanation" | "filter" | "scenario";

export type VoiceCommand = Readonly<{
  contract_version: typeof VOICE_COMMAND_VERSION;
  voice_command_id: string;
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  requested_by: string;
  input_language: string;
  transcript: string;
  query_kind: ScheduleQueryKind;
  captured_at: string;
  source: VoiceCommandSource;
  confidence: number | null;
  provenance: Readonly<Record<string, unknown>> | null;
}>;

export type ScheduleQueryRequest = Readonly<{
  contract_version: typeof SCHEDULE_QUERY_VERSION;
  query_id: string;
  scope: VoiceCommand["scope"];
  requested_by: string;
  query_text: string;
  kind: ScheduleQueryKind;
  language: string;
}>;

export type VoiceCommandSnapshot = {
  contract_version: typeof VOICE_COMMAND_VERSION;
  voice_command_id: string;
  scope: VoiceCommand["scope"];
  requested_by: string;
  input_language: string;
  transcript: string;
  query_kind: ScheduleQueryKind;
  captured_at: string;
  source: VoiceCommandSource;
  confidence?: number | null;
  provenance?: Record<string, unknown> | null;
};

export function normalizeVoiceCommand(
  snapshot: VoiceCommandSnapshot,
  aiLanguage: AILanguageContext,
  expectedScope: VoiceCommand["scope"],
): VoiceCommand {
  requireVoiceInput(aiLanguage);

  if (snapshot.contract_version !== VOICE_COMMAND_VERSION) {
    throw new Error("UNSUPPORTED_VOICE_COMMAND_CONTRACT");
  }
  validateScope(snapshot.scope);
  validateScope(expectedScope);
  if (
    snapshot.scope.tenant_id !== expectedScope.tenant_id ||
    snapshot.scope.project_id !== expectedScope.project_id ||
    snapshot.scope.project_revision !== expectedScope.project_revision
  ) {
    throw new Error("VOICE_COMMAND_SCOPE_MISMATCH");
  }
  if (
    !snapshot.voice_command_id.trim() ||
    !snapshot.requested_by.trim() ||
    !snapshot.input_language.trim() ||
    !snapshot.transcript.trim()
  ) {
    throw new Error("INVALID_VOICE_COMMAND");
  }
  if (!isQueryKind(snapshot.query_kind)) {
    throw new Error("INVALID_VOICE_COMMAND_QUERY_KIND");
  }
  if (!isSource(snapshot.source)) {
    throw new Error("INVALID_VOICE_COMMAND_SOURCE");
  }
  if (!isTimezoneAwareDateTime(snapshot.captured_at)) {
    throw new Error("INVALID_VOICE_COMMAND_TIMESTAMP");
  }
  if (
    snapshot.confidence !== undefined &&
    snapshot.confidence !== null &&
    (typeof snapshot.confidence !== "number" ||
      !Number.isFinite(snapshot.confidence) ||
      snapshot.confidence < 0 ||
      snapshot.confidence > 1)
  ) {
    throw new Error("INVALID_VOICE_COMMAND_CONFIDENCE");
  }

  return Object.freeze({
    contract_version: VOICE_COMMAND_VERSION,
    voice_command_id: snapshot.voice_command_id,
    scope: Object.freeze({ ...snapshot.scope }),
    requested_by: snapshot.requested_by,
    input_language: snapshot.input_language,
    transcript: snapshot.transcript.trim(),
    query_kind: snapshot.query_kind,
    captured_at: snapshot.captured_at,
    source: snapshot.source,
    confidence: snapshot.confidence ?? null,
    provenance: snapshot.provenance ? Object.freeze({ ...snapshot.provenance }) : null,
  });
}

export function voiceCommandToScheduleQuery(
  command: VoiceCommand,
  outputLanguage = command.input_language,
): ScheduleQueryRequest {
  if (!outputLanguage.trim()) {
    throw new Error("INVALID_SCHEDULE_QUERY_LANGUAGE");
  }

  return Object.freeze({
    contract_version: SCHEDULE_QUERY_VERSION,
    query_id: command.voice_command_id,
    scope: Object.freeze({ ...command.scope }),
    requested_by: command.requested_by,
    query_text: command.transcript,
    kind: command.query_kind,
    language: outputLanguage,
  });
}

function validateScope(scope: VoiceCommand["scope"]): void {
  if (
    !scope.tenant_id.trim() ||
    !scope.project_id.trim() ||
    !Number.isInteger(scope.project_revision) ||
    scope.project_revision < 0 ||
    scope.project_revision > 9_007_199_254_740_991
  ) {
    throw new Error("INVALID_VOICE_COMMAND_SCOPE");
  }
}

function isTimezoneAwareDateTime(value: string): boolean {
  return !Number.isNaN(Date.parse(value)) && /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

function isQueryKind(value: string): value is ScheduleQueryKind {
  return ["fact", "explanation", "filter", "scenario"].includes(value);
}

function isSource(value: string): value is VoiceCommandSource {
  return ["microphone", "imported_audio", "manual_transcript"].includes(value);
}
