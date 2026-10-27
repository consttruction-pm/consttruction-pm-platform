import assert from "node:assert/strict";
import test from "node:test";

import { isAIAssistantChatLocaleSupported } from "./ai-assistant-chat.js";
import { registerWorkspaceLocale } from "./workspace-localization.js";

test("assistant chat is supported for its fully supplied initial language baselines", () => {
  assert.equal(isAIAssistantChatLocaleSupported("en"), true);
  assert.equal(isAIAssistantChatLocaleSupported("en-GB"), true);
  assert.equal(isAIAssistantChatLocaleSupported("fa"), true);
  assert.equal(isAIAssistantChatLocaleSupported("fa-IR"), true);
});

test("assistant chat is not advertised with missing translated labels", () => {
  registerWorkspaceLocale({
    locale: "de",
    displayName: "Deutsch",
    direction: "ltr",
    translations: {
      "aiAssistantChat.title": "Projektassistent",
      "aiAssistantChat.send": "Senden",
    },
  });
  assert.equal(isAIAssistantChatLocaleSupported("de"), false);
});

test("assistant chat accepts a language only when every required label has a translation", () => {
  const keys = [
    "title", "description", "messageLabel", "placeholder", "send", "sending",
    "you", "assistant", "proposalNotice", "requestFailed", "serverUnavailable",
    "assistantNotConfigured", "staleRevision", "empty", "privacyNotice", "translationsUnavailable",
  ];
  registerWorkspaceLocale({
    locale: "de-DE",
    displayName: "Deutsch",
    direction: "ltr",
    translations: Object.fromEntries(keys.map((key) => [
      `aiAssistantChat.${key}`, `Übersetzt: ${key}`,
    ])),
  });
  assert.equal(isAIAssistantChatLocaleSupported("de-DE"), true);
});


import { boundedAIAssistantHistory } from "./ai-assistant-chat.js";

test("assistant history skips oversized messages and stays within server bounds", () => {
  const messages = [
    { role: "user" as const, content: "older" },
    { role: "user" as const, content: "x".repeat(4001) },
    { role: "assistant" as const, content: "a".repeat(4000) },
    { role: "user" as const, content: "b".repeat(4000) },
    { role: "assistant" as const, content: "c".repeat(4000) },
  ];
  const history = boundedAIAssistantHistory(messages);
  assert.deepEqual(history.map((entry) => entry.content[0]), ["a", "b", "c"]);
  assert.ok(history.length <= 12);
  assert.ok(history.every((entry) => entry.content.length <= 4000));
  assert.ok(history.reduce((total, entry) => total + entry.content.length, 0) <= 12000);
});
