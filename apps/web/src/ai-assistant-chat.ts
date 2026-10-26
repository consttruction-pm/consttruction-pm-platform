import type { ApiTransport, ProjectContext } from "./client.js";
import {
  AIActionClient,
  type AIAssistantHistoryMessage,
  type AIAssistantInputProvenance,
} from "./ai-action-client.js";
import {
  getWorkspaceLocaleDefinition,
  getWorkspaceLocaleDirection,
  translateWorkspaceText,
} from "./workspace-localization.js";
import type { VoiceCommand } from "../../client-sync/src/voice-command.js";
import {
  buildWebAILanguageContext,
  cancelWebVoiceInput,
  createWebVoiceAdapters,
  normalizeWebVoiceCapture,
  stopWebVoiceOutput,
  type WebVoiceAdapters,
} from "./voice-adapters.js";
import { createWebSpeechAdapters } from "./web-speech-provider.js";

type ChatLabels = {
  title: string;
  description: string;
  messageLabel: string;
  placeholder: string;
  send: string;
  sending: string;
  you: string;
  assistant: string;
  proposalNotice: string;
  requestFailed: string;
  serverUnavailable: string;
  staleRevision: string;
  empty: string;
  privacyNotice: string;
  translationsUnavailable: string;
  providerNotConfigured: string;
  connectionFailed: string;
  voiceStart: string;
  voiceStop: string;
  voiceListening: string;
  voiceCaptured: string;
  voiceUnavailable: string;
  voiceDenied: string;
  voiceFailed: string;
  voiceEmpty: string;
  voicePrivacyNotice: string;
  readAloud: string;
  stopReading: string;
  playReply: string;
  speaking: string;
  speechUnavailable: string;
  speechFailed: string;
};

type ChatMessage = AIAssistantHistoryMessage;

type ChatSession = {
  projectId: string;
  messages: ChatMessage[];
  lastProposalId: string | null;
};

export type AIAssistantChatOptions = Readonly<{
  /** Injectable browser speech adapters; production uses the real Web Speech capability. */
  voiceAdapters?: WebVoiceAdapters;
}>;

const sessions = new WeakMap<HTMLElement, ChatSession>();

const MAX_HISTORY_MESSAGES = 12;
const MAX_HISTORY_MESSAGE_CHARS = 4_000;
const MAX_HISTORY_TOTAL_CHARS = 12_000;
const MAX_MESSAGE_CHARS = 6_000;

let activeChatMount = 0;
let activeChatCleanup: (() => void) | null = null;

/** Keep the newest complete, individually valid messages within the server's documented bounds. */
export function boundedAIAssistantHistory(
  messages: readonly AIAssistantHistoryMessage[],
): AIAssistantHistoryMessage[] {
  const selected: AIAssistantHistoryMessage[] = [];
  let totalChars = 0;
  for (const message of [...messages].reverse()) {
    if (selected.length >= MAX_HISTORY_MESSAGES) break;
    const content = message.content.trim();
    if (!content || content.length > MAX_HISTORY_MESSAGE_CHARS) continue;
    if (totalChars + content.length > MAX_HISTORY_TOTAL_CHARS) continue;
    selected.push({ role: message.role, content });
    totalChars += content.length;
  }
  return selected.reverse();
}

const fallbackLabels: Record<"en" | "fa", ChatLabels> = {
  en: {
    title: "AI Project Assistant",
    description: "Ask a project-controls question or request a supported change. Project actions are prepared as proposals and are never executed without your explicit approval.",
    messageLabel: "Your message",
    placeholder: "Describe the project question or requested change…",
    send: "Send",
    sending: "Thinking…",
    you: "You",
    assistant: "Assistant",
    proposalNotice: "A proposal was saved. Review it in the Actions panel below before approving or executing it.",
    requestFailed: "The request failed. Check the proposal list before sending the same request again.",
    serverUnavailable: "The assistant provider is not configured or is temporarily unavailable.",
    staleRevision: "The project changed. Refresh the workspace before sending this request again.",
    empty: "Your conversation appears here.",
    privacyNotice: "When enabled, your message and recent conversation context are sent to the server-configured AI provider. Do not include passwords, access tokens, or unrelated sensitive details.",
    translationsUnavailable: "Assistant chat is unavailable in this language because required UI translations are missing. Switch to English or Persian.",
    providerNotConfigured: "The AI provider is not configured on the server. A server administrator must set the provider configuration before the assistant can answer.",
    connectionFailed: "The server could not be reached. Check your connection and try again.",
    voiceStart: "Start speaking",
    voiceStop: "Stop listening",
    voiceListening: "Listening… Speak now.",
    voiceCaptured: "Speech recognized. Review the text, edit it if needed, then send it.",
    voiceUnavailable: "Voice input is not available in this browser. You can type your message instead.",
    voiceDenied: "Microphone access was denied or is unavailable. You can type your message instead.",
    voiceFailed: "Speech recognition failed. Try again or type your message.",
    voiceEmpty: "No speech was recognized. Try again or type your message.",
    voicePrivacyNotice: "Voice input uses your browser's speech-recognition service. Raw audio is not sent to the CUBI server; only the recognized text becomes your message.",
    readAloud: "Read replies aloud",
    stopReading: "Stop reading",
    playReply: "Play reply",
    speaking: "Reading the reply aloud…",
    speechUnavailable: "Spoken replies are not available in this browser.",
    speechFailed: "The reply could not be read aloud. You can read it in the conversation.",
  },
  fa: {
    title: "دستیار هوشمند پروژه",
    description: "پرسش کنترل پروژه را مطرح کنید یا تغییر پشتیبانی‌شده‌ای بخواهید. اقدامات فقط به‌صورت پیشنهاد آماده می‌شوند و بدون تأیید صریح شما اجرا نخواهند شد.",
    messageLabel: "پیام شما",
    placeholder: "پرسش پروژه یا تغییر درخواستی را توضیح دهید…",
    send: "ارسال",
    sending: "در حال پردازش…",
    you: "شما",
    assistant: "دستیار",
    proposalNotice: "پیشنهاد ذخیره شد. پیش از تأیید یا اجرا، آن را در پنل اقدامات بررسی کنید.",
    requestFailed: "درخواست ناموفق بود. پیش از ارسال دوباره، فهرست پیشنهادها را بررسی کنید.",
    serverUnavailable: "ارائه‌دهنده دستیار پیکربندی نشده یا موقتاً در دسترس نیست.",
    staleRevision: "پروژه تغییر کرده است. فضای کار را تازه‌سازی کنید و سپس درخواست را دوباره بفرستید.",
    empty: "گفت‌وگو در این قسمت نمایش داده می‌شود.",
    privacyNotice: "در صورت فعال بودن، پیام شما و بخش اخیر گفت‌وگو به ارائه‌دهنده هوش مصنوعی پیکربندی‌شده در سرور ارسال می‌شود. گذرواژه، کلید دسترسی یا اطلاعات حساس نامرتبط را وارد نکنید.",
    translationsUnavailable: "ترجمه‌های لازم برای دستیار در این زبان کامل نیست. زبان انگلیسی یا فارسی را انتخاب کنید.",
    providerNotConfigured: "ارائه‌دهنده هوش مصنوعی در سرور پیکربندی نشده است. مدیر سرور باید پیش از پاسخ‌گویی دستیار، پیکربندی ارائه‌دهنده را تنظیم کند.",
    connectionFailed: "دسترسی به سرور برقرار نشد. اتصال خود را بررسی کنید و دوباره تلاش کنید.",
    voiceStart: "شروع صحبت",
    voiceStop: "توقف شنیدن",
    voiceListening: "در حال شنیدن… صحبت کنید.",
    voiceCaptured: "گفتار تشخیص داده شد. متن را بررسی و در صورت نیاز اصلاح کنید، سپس آن را بفرستید.",
    voiceUnavailable: "ورودی صوتی در این مرورگر در دسترس نیست. می‌توانید پیام خود را تایپ کنید.",
    voiceDenied: "دسترسی به میکروفون رد شده یا در دسترس نیست. می‌توانید پیام خود را تایپ کنید.",
    voiceFailed: "تشخیص گفتار ناموفق بود. دوباره تلاش کنید یا پیام خود را تایپ کنید.",
    voiceEmpty: "گفتاری تشخیص داده نشد. دوباره تلاش کنید یا پیام خود را تایپ کنید.",
    voicePrivacyNotice: "ورودی صوتی از سرویس تشخیص گفتار مرورگر شما استفاده می‌کند. صدای خام به سرور CUBI ارسال نمی‌شود؛ فقط متن تشخیص‌داده‌شده پیام شما خواهد بود.",
    readAloud: "خواندن پاسخ‌ها با صدا",
    stopReading: "توقف خواندن",
    playReply: "پخش پاسخ",
    speaking: "در حال خواندن پاسخ با صدا…",
    speechUnavailable: "پاسخ صوتی در این مرورگر در دسترس نیست.",
    speechFailed: "خواندن پاسخ با صدا ممکن نشد. می‌توانید آن را در گفت‌وگو بخوانید.",
  },
};

const requiredTranslationKeys = Object.keys(fallbackLabels.en).map(
  (key) => `aiAssistantChat.${key}`,
);

export function isAIAssistantChatLocaleSupported(locale: string): boolean {
  const normalized = locale.toLowerCase();
  if (normalized === "en" || normalized.startsWith("en-") ||
      normalized === "fa" || normalized.startsWith("fa-")) return true;
  const definition = getWorkspaceLocaleDefinition(locale);
  if (!definition) return false;
  return requiredTranslationKeys.every((key) =>
    typeof definition.translations[key] === "string" &&
    definition.translations[key].trim().length > 0
  );
}

function chatLabels(locale: string): ChatLabels {
  const base = fallbackLabels[locale.toLowerCase().startsWith("fa") ? "fa" : "en"];
  return Object.fromEntries(
    Object.entries(base).map(([key, fallback]) => [
      key,
      translateWorkspaceText(locale, `aiAssistantChat.${key}`, fallback),
    ]),
  ) as ChatLabels;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function makeButton(text: string, className: string): HTMLButtonElement {
  const node = element("button", className, text);
  node.type = "button";
  return node;
}

/** Mounts a session-only chat UI; server-side authorization remains authoritative. */
export function mountAIAssistantChatPanel(
  appShell: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  onProposalCreated: () => void = () => {},
  options: AIAssistantChatOptions = {},
): void {
  activeChatCleanup?.();
  activeChatCleanup = null;
  const mountId = ++activeChatMount;
  const isCurrent = (): boolean => activeChatMount === mountId;

  const previous = appShell.querySelector<HTMLDetailsElement>("#cp-ai-assistant-chat");
  const wasOpen = previous?.open ?? true;
  previous?.remove();

  let session = sessions.get(appShell);
  if (!session || session.projectId !== context.project_id) {
    session = { projectId: context.project_id, messages: [], lastProposalId: null };
    sessions.set(appShell, session);
  }

  const t = chatLabels(locale);
  const client = new AIActionClient(transport);
  const adapters: WebVoiceAdapters = options.voiceAdapters ??
    createWebVoiceAdapters(createWebSpeechAdapters());
  activeChatCleanup = () => {
    cancelWebVoiceInput(adapters);
    stopWebVoiceOutput(adapters);
  };
  const aiLanguage = buildWebAILanguageContext(locale, {
    input: adapters.input.capabilities.input,
    output: adapters.output.capabilities.output,
  });
  const voiceInputSupported = aiLanguage.voice_input_capable;
  const voiceOutputSupported = aiLanguage.voice_output_capable;
  const scope = (): VoiceCommand["scope"] => ({
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    project_revision: context.revision,
  });

  const details = element("details", "cp-ai-assistant-chat");
  details.id = "cp-ai-assistant-chat";
  details.open = wasOpen;
  details.dir = getWorkspaceLocaleDirection(locale);
  details.lang = locale;

  const summary = element("summary", "cp-ai-chat-summary", t.title);
  details.append(summary);
  const content = element("div", "cp-ai-chat-content");
  if (!isAIAssistantChatLocaleSupported(locale)) {
    content.append(element("p", "cp-ai-chat-status", t.translationsUnavailable));
    details.append(content);
    appShell.append(details);
    return;
  }
  content.append(
    element("p", "cp-ai-chat-description", t.description),
    element("p", "cp-ai-chat-privacy", t.privacyNotice),
  );
  if (voiceInputSupported) {
    content.append(element("p", "cp-ai-chat-privacy", t.voicePrivacyNotice));
  }

  const providerNotice = element("p", "cp-ai-chat-provider-notice");
  providerNotice.setAttribute("role", "status");
  providerNotice.hidden = true;
  const voiceSupport = element("p", "cp-ai-chat-voice-support");
  const missingVoiceCapabilities = [
    voiceInputSupported ? "" : t.voiceUnavailable,
    voiceOutputSupported ? "" : t.speechUnavailable,
  ].filter(Boolean);
  voiceSupport.textContent = missingVoiceCapabilities.join(" ");
  voiceSupport.hidden = missingVoiceCapabilities.length === 0;

  const transcript = element("div", "cp-ai-chat-transcript");
  transcript.setAttribute("role", "log");
  transcript.setAttribute("aria-live", "polite");
  transcript.setAttribute("aria-relevant", "additions text");
  const notice = element("p", "cp-ai-chat-notice");
  notice.setAttribute("role", "status");
  const status = element("p", "cp-ai-chat-status");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");

  const form = element("form", "cp-ai-chat-form");
  const label = element("label", "cp-ai-chat-label", t.messageLabel);
  const textarea = element("textarea", "cp-ai-chat-input");
  textarea.name = "message";
  textarea.required = true;
  textarea.maxLength = MAX_MESSAGE_CHARS;
  textarea.rows = 3;
  textarea.placeholder = t.placeholder;
  textarea.autocomplete = "off";
  textarea.setAttribute("aria-label", t.messageLabel);
  label.append(textarea);

  const controls = element("div", "cp-ai-chat-controls");
  const micButton = makeButton(
    voiceInputSupported ? t.voiceStart : `${t.voiceStart} — ${t.voiceUnavailable}`,
    "cp-ai-chat-voice",
  );
  micButton.setAttribute("aria-pressed", "false");
  micButton.disabled = !voiceInputSupported;
  const submit = makeButton(t.send, "cp-ai-chat-send");
  submit.type = "submit";
  controls.append(micButton, submit);

  const playbackControls = element("div", "cp-ai-chat-playback");
  const readAloudButton = makeButton(t.readAloud, "cp-ai-chat-toggle");
  readAloudButton.setAttribute("aria-pressed", "false");
  readAloudButton.disabled = !voiceOutputSupported;
  const stopReadingButton = makeButton(t.stopReading, "cp-ai-chat-stop-reading");
  stopReadingButton.disabled = true;
  playbackControls.append(readAloudButton, stopReadingButton);
  if (!voiceOutputSupported) playbackControls.hidden = true;

  form.append(label, controls);
  content.append(
    providerNotice,
    voiceSupport,
    transcript,
    notice,
    status,
    form,
    playbackControls,
  );
  details.append(content);
  appShell.append(details);

  let busy = false;
  let providerEnabled: boolean | null = null;
  let pendingVoiceCommand: VoiceCommand | null = null;
  let listening = false;
  let readAloud = false;
  let speechSequence = 0;

  const setSpeaking = (speaking: boolean): void => {
    stopReadingButton.disabled = !speaking;
  };

  const setBusy = (next: boolean): void => {
    busy = next;
    textarea.disabled = next;
    submit.disabled = next;
    micButton.disabled = next || !voiceInputSupported;
    submit.textContent = next ? t.sending : t.send;
  };

  const clearStatus = (): void => {
    status.textContent = "";
    status.dataset.kind = "";
  };

  const setStatus = (text: string, kind: "" | "error" | "success" | "info"): void => {
    status.textContent = text;
    status.dataset.kind = kind;
  };

  const stopSpeech = (): void => {
    speechSequence += 1;
    stopWebVoiceOutput(adapters);
    setSpeaking(false);
    if (status.dataset.kind === "info") clearStatus();
  };

  async function speakReply(text: string): Promise<void> {
    if (!voiceOutputSupported || !text.trim()) return;
    const sequence = ++speechSequence;
    adapters.output.stop?.();
    setSpeaking(true);
    setStatus(t.speaking, "info");
    try {
      await adapters.output.speak(text, {
        language: aiLanguage.voice_language ?? locale,
        scope: scope(),
      });
      if (!isCurrent() || sequence !== speechSequence) return;
      if (status.dataset.kind === "info") clearStatus();
    } catch {
      if (!isCurrent() || sequence !== speechSequence) return;
      setStatus(t.speechFailed, "error");
    } finally {
      if (isCurrent() && sequence === speechSequence) setSpeaking(false);
    }
  }

  const render = (): void => {
    transcript.replaceChildren();
    if (session!.messages.length === 0) {
      transcript.append(element("p", "cp-ai-chat-empty", t.empty));
    } else {
      for (const message of session!.messages) {
        const item = element("article", `cp-ai-chat-message cp-ai-chat-message-${message.role}`);
        const author = message.role === "user" ? t.you : t.assistant;
        item.append(element("div", "cp-ai-chat-author", author));
        item.append(element("p", "cp-ai-chat-text", message.content));
        if (message.role === "assistant" && voiceOutputSupported) {
          const actions = element("div", "cp-ai-chat-message-actions");
          const play = makeButton(t.playReply, "cp-ai-chat-play");
          play.setAttribute("aria-label", `${t.playReply}: ${message.content.slice(0, 80)}`);
          play.onclick = () => { void speakReply(message.content); };
          actions.append(play);
          item.append(actions);
        }
        transcript.append(item);
      }
    }
    notice.textContent = session!.lastProposalId
      ? `${t.proposalNotice} ID: ${session!.lastProposalId}`
      : "";
  };

  const friendlyError = (code: string): string => {
    if (code === "AI_ASSISTANT_PROVIDER_NOT_CONFIGURED") return t.providerNotConfigured;
    if (code === "ROUTE_NOT_FOUND" ||
        code === "AI_ASSISTANT_PROVIDER_UNAVAILABLE" ||
        code === "AI_ASSISTANT_PROVIDER_RATE_LIMITED" ||
        code === "AI_ASSISTANT_PROVIDER_CONFIGURATION_INVALID") return t.serverUnavailable;
    if (code === "AI_ASSISTANT_STALE_REVISION") return t.staleRevision;
    if (code === "NETWORK_ERROR") return t.connectionFailed;
    return `${t.requestFailed} (${code})`;
  };

  const friendlyVoiceError = (code: string): string => {
    if (code === "VOICE_INPUT_UNAVAILABLE") return t.voiceUnavailable;
    if (code === "VOICE_INPUT_NOT_ALLOWED" || code === "VOICE_INPUT_SERVICE_NOT_ALLOWED") {
      return t.voiceDenied;
    }
    if (code === "VOICE_INPUT_NO_SPEECH" || code === "VOICE_INPUT_ENDED_WITHOUT_RESULT") {
      return t.voiceEmpty;
    }
    return t.voiceFailed;
  };

  async function sendMessage(
    rawMessage: string,
    provenance: AIAssistantInputProvenance | null = null,
  ): Promise<void> {
    if (busy) return;
    const message = rawMessage.trim();
    if (!message || message.length > MAX_MESSAGE_CHARS) return;

    stopSpeech();
    const history = boundedAIAssistantHistory(session!.messages);
    session!.messages.push({ role: "user", content: message });
    if (session!.messages.length > 40) {
      session!.messages.splice(0, session!.messages.length - 40);
    }
    session!.lastProposalId = null;
    textarea.value = "";
    pendingVoiceCommand = null;
    setBusy(true);
    clearStatus();
    render();

    const result = await client.sendAssistantTurn(context, message, locale, history, provenance);
    if (!isCurrent()) return;
    setBusy(false);
    if (!result.ok) {
      textarea.value = message;
      setStatus(friendlyError(result.error.code), "error");
      render();
      textarea.focus();
      return;
    }

    session!.messages.push({ role: "assistant", content: result.data.message });
    if (session!.messages.length > 40) {
      session!.messages.splice(0, session!.messages.length - 40);
    }
    if (result.data.proposal) {
      session!.lastProposalId = result.data.proposal.proposal_id;
      onProposalCreated();
      setStatus(t.proposalNotice, "success");
    } else {
      clearStatus();
    }
    render();
    if (readAloud) void speakReply(result.data.message);
    textarea.focus();
  }

  const setListening = (next: boolean): void => {
    listening = next;
    micButton.textContent = next ? t.voiceStop : t.voiceStart;
    micButton.setAttribute("aria-pressed", String(next));
    micButton.dataset.listening = String(next);
    micButton.disabled = !voiceInputSupported || busy;
  };

  micButton.addEventListener("click", () => {
    if (!voiceInputSupported || busy) return;
    if (listening) {
      cancelWebVoiceInput(adapters);
      setListening(false);
      clearStatus();
      return;
    }
    const expectedScope = scope();
    setListening(true);
    setStatus(t.voiceListening, "info");
    void (async () => {
      try {
        const capture = await adapters.input.capture({
          aiLanguage,
          expectedScope,
        });
        if (!isCurrent()) return;
        const command = normalizeWebVoiceCapture(adapters, capture, aiLanguage, expectedScope);
        if (!command.transcript) {
          setStatus(t.voiceEmpty, "error");
          return;
        }
        pendingVoiceCommand = command;
        textarea.value = command.transcript;
        textarea.focus();
        setStatus(t.voiceCaptured, "success");
      } catch (error) {
        if (!isCurrent()) return;
        const code = error instanceof Error ? error.message : "VOICE_INPUT_FAILED";
        if (code !== "VOICE_INPUT_CANCELLED") {
          setStatus(friendlyVoiceError(code), "error");
        }
      } finally {
        if (isCurrent()) setListening(false);
      }
    })();
  });

  textarea.addEventListener("input", () => {
    if (pendingVoiceCommand && textarea.value.trim() !== pendingVoiceCommand.transcript) {
      pendingVoiceCommand = null;
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (busy) return;
    const message = textarea.value.trim();
    if (!message || message.length > MAX_MESSAGE_CHARS) return;
    const voice = pendingVoiceCommand && pendingVoiceCommand.transcript === message
      ? pendingVoiceCommand
      : null;
    const provenance: AIAssistantInputProvenance | null = voice === null
      ? null
      : {
          channel: "voice",
          source: voice.source,
          confidence: voice.confidence,
        };
    void sendMessage(message, provenance);
  });

  readAloudButton.addEventListener("click", () => {
    readAloud = !readAloud;
    readAloudButton.setAttribute("aria-pressed", String(readAloud));
    if (!readAloud) stopSpeech();
  });

  stopReadingButton.addEventListener("click", () => {
    stopSpeech();
  });

  render();
  void client.getAssistantCapabilities(context).then((result) => {
    if (!isCurrent() || !result.ok) return;
    providerEnabled = result.data.enabled;
    if (providerEnabled) {
      providerNotice.hidden = true;
      providerNotice.textContent = "";
    } else {
      providerNotice.textContent = t.providerNotConfigured;
      providerNotice.hidden = false;
    }
    setBusy(busy);
  });
}
