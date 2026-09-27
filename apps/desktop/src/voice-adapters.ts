import { normalizeVoiceCapture, requireVoiceOutput, type VoiceInputAdapter, type VoiceOutputAdapter } from "../../client-sync/src/voice-provider-adapter.ts";
import type { VoiceCommand } from "../../client-sync/src/voice-command.ts";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";

export type DesktopVoiceAdapters = Readonly<{ input: VoiceInputAdapter; output: VoiceOutputAdapter }>;

export function createDesktopVoiceAdapters(adapters: DesktopVoiceAdapters): DesktopVoiceAdapters {
  return Object.freeze(adapters);
}

export function normalizeDesktopVoiceCapture(
  adapters: DesktopVoiceAdapters,
  capture: Awaited<ReturnType<VoiceInputAdapter["capture"]>>,
  aiLanguage: AILanguageContext,
  scope: VoiceCommand["scope"],
): VoiceCommand {
  if (!adapters.input.capabilities.input) throw new Error("VOICE_INPUT_UNAVAILABLE");
  return normalizeVoiceCapture(capture, aiLanguage, scope);
}

export function requireDesktopVoiceOutput(
  adapters: DesktopVoiceAdapters,
  language: string,
  scope: VoiceCommand["scope"],
): void {
  requireVoiceOutput(adapters.output, language, scope);
}
