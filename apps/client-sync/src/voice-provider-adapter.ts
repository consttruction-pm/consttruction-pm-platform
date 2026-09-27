import {
  normalizeVoiceCommand,
  type VoiceCommand,
  type VoiceCommandSnapshot,
} from "./voice-command.ts";
import type { AILanguageContext } from "./ai-language-contract.ts";

export type VoiceProviderCapabilities = Readonly<{
  input: boolean;
  output: boolean;
}>;

export type VoiceInputCapture = Readonly<{
  snapshot: VoiceCommandSnapshot;
}>;

export interface VoiceInputAdapter {
  readonly capabilities: VoiceProviderCapabilities;
  capture(
    context: Readonly<{
      aiLanguage: AILanguageContext;
      expectedScope: VoiceCommand["scope"];
    }>,
  ): Promise<VoiceInputCapture>;
}

export interface VoiceOutputAdapter {
  readonly capabilities: VoiceProviderCapabilities;
  speak(
    text: string,
    context: Readonly<{
      language: string;
      scope: VoiceCommand["scope"];
    }>,
  ): Promise<void>;
}

export function normalizeVoiceCapture(
  capture: VoiceInputCapture,
  aiLanguage: AILanguageContext,
  expectedScope: VoiceCommand["scope"],
): VoiceCommand {
  if (!capture || !capture.snapshot) {
    throw new Error("INVALID_VOICE_CAPTURE");
  }
  return normalizeVoiceCommand(capture.snapshot, aiLanguage, expectedScope);
}

export function requireVoiceOutput(
  adapter: VoiceOutputAdapter,
  language: string,
  scope: VoiceCommand["scope"],
): void {
  if (!adapter.capabilities.output) {
    throw new Error("VOICE_OUTPUT_UNAVAILABLE");
  }
  if (!language.trim()) {
    throw new Error("INVALID_VOICE_OUTPUT_LANGUAGE");
  }
  if (!scope.tenant_id.trim() || !scope.project_id.trim()) {
    throw new Error("INVALID_VOICE_OUTPUT_SCOPE");
  }
}
