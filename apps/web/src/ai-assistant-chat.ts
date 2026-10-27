import type { ApiTransport, ProjectContext } from "./client.js";
import { AIActionClient, type AIAssistantHistoryMessage } from "./ai-action-client.js";
import { getWorkspaceLocaleDefinition, translateWorkspaceText } from "./workspace-localization.js";
import { cubiAssistantAvatarUrl } from "./cubi-brand-assets.js";

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
  assistantNotConfigured: string;
  staleRevision: string;
  empty: string;
  privacyNotice: string;
  translationsUnavailable: string;
};

type ChatMessage = AIAssistantHistoryMessage;

type ChatSession = {
  projectId: string;
  messages: ChatMessage[];
  lastProposalId: string | null;
};

const sessions = new WeakMap<HTMLElement, ChatSession>();

const MAX_HISTORY_MESSAGES = 12;
const MAX_HISTORY_MESSAGE_CHARS = 4_000;
const MAX_HISTORY_TOTAL_CHARS = 12_000;

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
    assistantNotConfigured: "The assistant is not enabled in this environment. The server-side provider and authorized action runtime must be configured before retrying.",
    staleRevision: "The project changed. Refresh the workspace before sending this request again.",
    empty: "Your conversation appears here.",
    privacyNotice: "When enabled, your message and recent conversation context are sent to the server-configured AI provider. Do not include passwords, access tokens, or unrelated sensitive details.",
    translationsUnavailable: "Assistant chat is unavailable in this language because required UI translations are missing. Switch to English or Persian.",
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
    assistantNotConfigured: "دستیار در این محیط فعال نشده است. ابتدا ارائه‌دهنده هوش مصنوعی و محیط اجرای مجاز عملیات را در سمت سرور پیکربندی کنید.",
    staleRevision: "پروژه تغییر کرده است. فضای کار را تازه‌سازی کنید و سپس درخواست را دوباره بفرستید.",
    empty: "گفت‌وگو در این قسمت نمایش داده می‌شود.",
    privacyNotice: "در صورت فعال بودن، پیام شما و بخش اخیر گفت‌وگو به ارائه‌دهنده هوش مصنوعی پیکربندی‌شده در سرور ارسال می‌شود. گذرواژه، کلید دسترسی یا اطلاعات حساس نامرتبط را وارد نکنید.",
    translationsUnavailable: "ترجمه‌های لازم برای دستیار در این زبان کامل نیست. زبان انگلیسی یا فارسی را انتخاب کنید.",
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

function makeButton(text: string): HTMLButtonElement {
  const node = element("button", "cp-ai-chat-send", text);
  node.type = "submit";
  return node;
}

/** Mounts a session-only chat UI; server-side authorization remains authoritative. */
export function mountAIAssistantChatPanel(
  appShell: HTMLElement,
  transport: ApiTransport,
  context: ProjectContext,
  locale: string,
  onProposalCreated: () => void = () => {},
): void {
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
  const details = element("details", "cp-ai-assistant-chat");
  details.id = "cp-ai-assistant-chat";
  details.open = wasOpen;
  details.dir = locale.toLowerCase().startsWith("fa") ? "rtl" : "ltr";

  const summary = element("summary", "cp-ai-chat-summary");
  const avatar = element("img", "cp-ai-chat-avatar");
  avatar.src = cubiAssistantAvatarUrl();
  avatar.alt = "";
  avatar.setAttribute("aria-hidden", "true");
  avatar.width = 44;
  avatar.height = 44;
  avatar.decoding = "async";
  const summaryTitle = element("span", "cp-ai-chat-summary-title", t.title);
  summary.append(avatar, summaryTitle);
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
  textarea.maxLength = 6000;
  textarea.rows = 3;
  textarea.placeholder = t.placeholder;
  textarea.autocomplete = "off";
  textarea.setAttribute("aria-label", t.messageLabel);
  label.append(textarea);
  const submit = makeButton(t.send);
  form.append(label, submit);
  content.append(transcript, notice, status, form);
  details.append(content);
  appShell.append(details);

  const render = (): void => {
    transcript.replaceChildren();
    if (session!.messages.length === 0) {
      transcript.append(element("p", "cp-ai-chat-empty", t.empty));
    } else {
      for (const message of session!.messages) {
        const item = element("article", `cp-ai-chat-message cp-ai-chat-message-${message.role}`);
        const author = message.role === "user" ? t.you : t.assistant;
        const authorHeading = element("div", "cp-ai-chat-message-heading");
        if (message.role === "assistant") {
          const messageAvatar = element("img", "cp-ai-chat-message-avatar");
          messageAvatar.src = cubiAssistantAvatarUrl();
          messageAvatar.alt = "";
          messageAvatar.width = 28;
          messageAvatar.height = 28;
          messageAvatar.decoding = "async";
          messageAvatar.setAttribute("aria-hidden", "true");
          authorHeading.append(messageAvatar);
        }
        authorHeading.append(element("div", "cp-ai-chat-author", author));
        item.append(authorHeading, element("p", "cp-ai-chat-text", message.content));
        transcript.append(item);
      }
    }
    notice.textContent = session!.lastProposalId
      ? `${t.proposalNotice} ID: ${session!.lastProposalId}`
      : "";
  };

  const friendlyError = (code: string): string => {
    if (code === "AI_ASSISTANT_NOT_CONFIGURED") return t.assistantNotConfigured;
    if (code === "AI_ASSISTANT_PROVIDER_UNAVAILABLE" ||
        code === "AI_ASSISTANT_PROVIDER_RATE_LIMITED" ||
        code === "AI_ASSISTANT_PROVIDER_CONFIGURATION_INVALID") return t.serverUnavailable;
    if (code === "AI_ASSISTANT_STALE_REVISION") return t.staleRevision;
    return `${t.requestFailed} (${code})`;
  };

  render();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = textarea.value.trim();
    if (!message || message.length > 6000 || submit.disabled) return;

    const history = boundedAIAssistantHistory(session!.messages);
    session!.messages.push({ role: "user", content: message });
    if (session!.messages.length > 40) session!.messages.splice(0, session!.messages.length - 40);
    session!.lastProposalId = null;
    textarea.value = "";
    textarea.disabled = true;
    submit.disabled = true;
    submit.textContent = t.sending;
    status.textContent = "";
    status.dataset.kind = "";
    render();

    const result = await client.sendAssistantTurn(context, message, locale, history);
    textarea.disabled = false;
    submit.disabled = false;
    submit.textContent = t.send;
    if (!result.ok) {
      status.textContent = friendlyError(result.error.code);
      status.dataset.kind = "error";
      textarea.focus();
      return;
    }

    session!.messages.push({ role: "assistant", content: result.data.message });
    if (session!.messages.length > 40) session!.messages.splice(0, session!.messages.length - 40);
    if (result.data.proposal) {
      session!.lastProposalId = result.data.proposal.proposal_id;
      onProposalCreated();
      status.textContent = t.proposalNotice;
      status.dataset.kind = "success";
    } else {
      status.textContent = "";
      status.dataset.kind = "";
    }
    render();
    textarea.focus();
  });
}
