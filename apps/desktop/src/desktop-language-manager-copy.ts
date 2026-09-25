export type DesktopLanguageManagerCopy = {
  title: string;
  ready: string;
  downloading: (language: string) => string;
  supportedLanguages: string;
  language: string;
  locale: string;
  direction: string;
  installed: string;
  offline: string;
  ai: string;
  voiceIn: string;
  voiceOut: string;
  offlineAi: string;
  selected: string;
  use: string;
  download: string;
  update: string;
  unavailable: string;
  remove: string;
  yes: string;
  no: string;
  missing: string;
  action: string;
  downloadProgress: string;
  rtl: string;
  ltr: string;
};

export const DEFAULT_ENGLISH_DESKTOP_LANGUAGE_MANAGER_COPY: DesktopLanguageManagerCopy = {
  title: "Language",
  ready: "Ready",
  downloading: (language) => "Downloading " + language + "…",
  supportedLanguages: "Supported languages",
  language: "Language",
  locale: "Locale",
  direction: "Direction",
  installed: "Installed",
  offline: "Offline",
  ai: "AI",
  voiceIn: "Voice In",
  voiceOut: "Voice Out",
  offlineAi: "Offline AI",
  selected: "Selected",
  use: "Use",
  download: "Download",
  update: "Update",
  unavailable: "Unavailable",
  remove: "Remove",
  yes: "Yes",
  no: "No",
  missing: "—",
  action: "Action",
  downloadProgress: "Language pack download progress",
  rtl: "RTL",
  ltr: "LTR",
};
