import { normalizeVoiceCapture, requireVoiceOutput, type VoiceInputAdapter, type VoiceOutputAdapter } from "../../client-sync/src/voice-provider-adapter.ts";
import type { VoiceCommand } from "../../client-sync/src/voice-command.ts";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";

export type MobileVoiceAdapters = Readonly<{ input: VoiceInputAdapter; output: VoiceOutputAdapter }>;

export function createMobileVoiceAdapters(adapters: MobileVoiceAdapters): MobileVoiceAdapters {
  return Object.freeze(adapters);
}

export function normalizeMobileVoiceCapture(
  adapters: MobileVoiceAdapters,
  capture: Awaited<ReturnType<VoiceInputAdapter["capture"]>>,
  aiLanguage: AILanguageContext,
  scope: VoiceCommand["scope"],
): VoiceCommand {
  if (!adapters.input.capabilities.input) throw new Error("VOICE_INPUT_UNAVAILABLE");
  return normalizeVoiceCapture(capture, aiLanguage, scope);
}

export function requireMobileVoiceOutput(
  adapters: MobileVoiceAdapters,
  language: string,
  scope: VoiceCommand["scope"],
): void {
  requireVoiceOutput(adapters.output, language, scope);
}
