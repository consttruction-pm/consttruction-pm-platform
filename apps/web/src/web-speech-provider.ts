import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";
import type { VoiceCommand } from "../../client-sync/src/voice-command.ts";
import type { VoiceInputAdapter, VoiceOutputAdapter } from "../../client-sync/src/voice-provider-adapter.ts";

type BrowserSpeechResult = { readonly 0: { readonly transcript: string; readonly confidence: number } };
type BrowserSpeechEvent = { readonly results: { readonly 0: BrowserSpeechResult } };
type BrowserSpeechErrorEvent = { readonly error: string };

interface BrowserRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: BrowserSpeechEvent) => void) | null;
  onerror: ((event: BrowserSpeechErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

interface BrowserRecognitionConstructor {
  new (): BrowserRecognition;
}

interface BrowserSpeechSynthesis {
  speak(utterance: BrowserSpeechSynthesisUtterance): void;
}

interface BrowserSpeechSynthesisUtterance {
  lang: string;
  text: string;
  onerror: (() => void) | null;
}

interface BrowserWindowSpeech {
  readonly SpeechRecognition?: BrowserRecognitionConstructor;
  readonly webkitSpeechRecognition?: BrowserRecognitionConstructor;
  readonly speechSynthesis?: BrowserSpeechSynthesis;
}

type WebSpeechProviderOptions = Readonly<{
  now?: () => Date;
  createUtterance?: (text: string) => BrowserSpeechSynthesisUtterance;
}>;

function browserSpeech(): BrowserWindowSpeech {
  if (typeof window === "undefined") return {};
  return window as unknown as BrowserWindowSpeech;
}

export function createWebSpeechInputAdapter(
  options: WebSpeechProviderOptions = {},
): VoiceInputAdapter {
  const provider = browserSpeech();
  const Recognition = provider.SpeechRecognition ?? provider.webkitSpeechRecognition;
  return {
    capabilities: { input: Boolean(Recognition), output: false },
    capture: async ({ aiLanguage, expectedScope }) => {
      if (!Recognition || !aiLanguage.voice_input_capable || !aiLanguage.voice_language) {
        throw new Error("VOICE_INPUT_UNAVAILABLE");
      }
      return new Promise((resolve, reject) => {
        const recognition = new Recognition();
        recognition.lang = aiLanguage.voice_language;
        recognition.continuous = false;
        recognition.interimResults = false;
        let settled = false;
        const finish = (fn: () => void) => {
          if (settled) return;
          settled = true;
          fn();
        };
        recognition.onresult = (event) => finish(() => {
          const result = event.results[0][0];
          const capturedAt = (options.now ?? (() => new Date()))().toISOString();
          resolve({
            snapshot: {
              contract_version: "voice-command.v1",
              voice_command_id: `web-speech-${capturedAt}`,
              scope: expectedScope,
              requested_by: "client",
              input_language: aiLanguage.voice_language!,
              transcript: result.transcript.trim(),
              query_kind: "fact",
              captured_at: capturedAt,
              source: "microphone",
              confidence: Math.max(0, Math.min(1, result.confidence)),
            },
          });
        });
        recognition.onerror = (event) => finish(() => reject(new Error(`VOICE_INPUT_${event.error.toUpperCase()}`)));
        recognition.onend = () => finish(() => reject(new Error("VOICE_INPUT_ENDED_WITHOUT_RESULT")));
        try {
          recognition.start();
        } catch (error) {
          finish(() => reject(error instanceof Error ? error : new Error("VOICE_INPUT_START_FAILED")));
        }
      });
    },
  };
}

export function createWebSpeechOutputAdapter(
  options: WebSpeechProviderOptions = {},
): VoiceOutputAdapter {
  const provider = browserSpeech();
  return {
    capabilities: { input: false, output: Boolean(provider.speechSynthesis) },
    speak: async (text, context) => {
      if (!provider.speechSynthesis) throw new Error("VOICE_OUTPUT_UNAVAILABLE");
      if (!text.trim() || !context.language.trim()) throw new Error("INVALID_VOICE_OUTPUT");
      const utterance = (options.createUtterance ?? ((value) => new SpeechSynthesisUtterance(value)))(text);
      utterance.lang = context.language;
      await new Promise<void>((resolve, reject) => {
        utterance.onerror = () => reject(new Error("VOICE_OUTPUT_FAILED"));
        provider.speechSynthesis!.speak(utterance);
        resolve();
      });
    },
  };
}

export type WebSpeechAdapters = Readonly<{
  input: VoiceInputAdapter;
  output: VoiceOutputAdapter;
}>;

export function createWebSpeechAdapters(options: WebSpeechProviderOptions = {}): WebSpeechAdapters {
  return Object.freeze({
    input: createWebSpeechInputAdapter(options),
    output: createWebSpeechOutputAdapter(options),
  });
}
