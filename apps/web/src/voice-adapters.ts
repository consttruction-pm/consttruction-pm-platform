import { normalizeVoiceCapture, requireVoiceOutput, type VoiceInputAdapter, type VoiceOutputAdapter } from "../../client-sync/src/voice-provider-adapter.ts";
import type { VoiceCommand } from "../../client-sync/src/voice-command.ts";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";

export type WebVoiceAdapters = Readonly<{ input: VoiceInputAdapter; output: VoiceOutputAdapter }>;
export function createWebVoiceAdapters(adapters: WebVoiceAdapters): WebVoiceAdapters { return Object.freeze(adapters); }

/** Speech-service languages are declared per supported assistant locale; the UI locale alone never implies one. */
export function webVoiceLanguage(locale: string): string | null {
  const tag = locale.trim();
  if (/^fa(?:-|$)/i.test(tag)) return tag.includes("-") ? tag : "fa-IR";
  if (/^en(?:-|$)/i.test(tag)) return tag.includes("-") ? tag : "en-US";
  return null;
}

/** Build the shared AI-language contract from the active UI locale and real adapter capabilities. */
export function buildWebAILanguageContext(
  locale: string,
  capabilities: Readonly<{ input: boolean; output: boolean }>,
): AILanguageContext {
  const voiceLanguage = webVoiceLanguage(locale);
  return {
    input_language: voiceLanguage ?? locale,
    output_language: locale,
    project_language: locale,
    terminology_profile: "construction-default",
    locale,
    voice_language: voiceLanguage,
    text_capable: true,
    voice_input_capable: Boolean(voiceLanguage && capabilities.input),
    voice_output_capable: Boolean(voiceLanguage && capabilities.output),
    offline_ai_capable: false,
  };
}

export function cancelWebVoiceInput(adapters: WebVoiceAdapters): void { adapters.input.cancel?.(); }
export function stopWebVoiceOutput(adapters: WebVoiceAdapters): void { adapters.output.stop?.(); }

export function normalizeWebVoiceCapture(adapters: WebVoiceAdapters, capture: Awaited<ReturnType<VoiceInputAdapter["capture"]>>, aiLanguage: AILanguageContext, scope: VoiceCommand["scope"]): VoiceCommand {
 if (!adapters.input.capabilities.input) throw new Error("VOICE_INPUT_UNAVAILABLE");
 return normalizeVoiceCapture(capture, aiLanguage, scope);
}
export function requireWebVoiceOutput(adapters: WebVoiceAdapters, language: string, scope: VoiceCommand["scope"]): void { requireVoiceOutput(adapters.output, language, scope); }
