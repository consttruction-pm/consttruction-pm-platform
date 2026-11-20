import type { WorkspaceLocale } from "./workspace-model.js";
import type { HelpResolutionLevel } from "./help-registry.js";

/**
 * Fixed labels for the contextual Help block. These are interface strings, not
 * help content: the topic titles and URLs always come from the Help registry in
 * the source language the official Help is published in.
 */
export type AssistantHelpCopy = {
  heading: string;
  level: Record<HelpResolutionLevel, string>;
  noTopic: string;
  internalDocs: string;
  pdfPage: string;
  feature: string;
};

const COPY: Record<string, AssistantHelpCopy> = {
  en: {
    heading: "Official Help",
    level: {
      direct: "For this page",
      parent: "For the parent screen",
      inherited: "For this environment",
      "internal-docs": "Internal documentation",
    },
    noTopic: "No official Help topic covers this page.",
    internalDocs: "Read the internal documentation",
    pdfPage: "PDF p.",
    feature: "Feature",
  },
  fa: {
    heading: "راهنمای رسمی",
    level: {
      direct: "برای همین صفحه",
      parent: "برای صفحهٔ والد",
      inherited: "برای این محیط",
      "internal-docs": "مستندات داخلی",
    },
    noTopic: "هیچ موضوع رسمی راهنما این صفحه را پوشش نمی‌دهد.",
    internalDocs: "مستندات داخلی را بخوانید",
    pdfPage: "صفحهٔ PDF",
    feature: "قابلیت",
  },
  de: {
    heading: "Offizielle Hilfe",
    level: {
      direct: "Für diese Seite",
      parent: "Für die übergeordnete Ansicht",
      inherited: "Für diese Umgebung",
      "internal-docs": "Interne Dokumentation",
    },
    noTopic: "Kein offizielles Hilfethemen deckt diese Seite ab.",
    internalDocs: "Interne Dokumentation lesen",
    pdfPage: "PDF S.",
    feature: "Funktion",
  },
  fr: {
    heading: "Aide officielle",
    level: {
      direct: "Pour cette page",
      parent: "Pour l'écran parent",
      inherited: "Pour cet environnement",
      "internal-docs": "Documentation interne",
    },
    noTopic: "Aucun sujet d'aide officiel ne couvre cette page.",
    internalDocs: "Lire la documentation interne",
    pdfPage: "PDF p.",
    feature: "Fonction",
  },
  zh: {
    heading: "官方帮助",
    level: {
      direct: "本页",
      parent: "上级界面",
      inherited: "当前环境",
      "internal-docs": "内部文档",
    },
    noTopic: "没有官方帮助主题涵盖此页面。",
    internalDocs: "阅读内部文档",
    pdfPage: "PDF 第",
    feature: "功能",
  },
  ar: {
    heading: "المساعدة الرسمية",
    level: {
      direct: "لهذه الصفحة",
      parent: "للشاشة الأعلى",
      inherited: "لهذه البيئة",
      "internal-docs": "الوثائق الداخلية",
    },
    noTopic: "لا يوجد موضوع مساعدة رسمي يغطي هذه الصفحة.",
    internalDocs: "اقرأ الوثائق الداخلية",
    pdfPage: "صفحة PDF",
    feature: "قدرة",
  },
  ja: {
    heading: "公式ヘルプ",
    level: {
      direct: "このページ",
      parent: "親画面",
      inherited: "この環境",
      "internal-docs": "内部ドキュメント",
    },
    noTopic: "このページを扱う公式ヘルプのトピックはありません。",
    internalDocs: "内部ドキュメントを読む",
    pdfPage: "PDF p.",
    feature: "機能",
  },
  ko: {
    heading: "공식 도움말",
    level: {
      direct: "이 페이지",
      parent: "상위 화면",
      inherited: "이 환경",
      "internal-docs": "내부 문서",
    },
    noTopic: "이 페이지를 다루는 공식 도움말 항목이 없습니다.",
    internalDocs: "내부 문서 읽기",
    pdfPage: "PDF p.",
    feature: "기능",
  },
  ru: {
    heading: "Официальная справка",
    level: {
      direct: "Для этой страницы",
      parent: "Для родительского экрана",
      inherited: "Для этого окружения",
      "internal-docs": "Внутренняя документация",
    },
    noTopic: "Ни один официальный раздел справки не описывает эту страницу.",
    internalDocs: "Открыть внутреннюю документацию",
    pdfPage: "PDF с.",
    feature: "Возможность",
  },
  tr: {
    heading: "Resmî Yardım",
    level: {
      direct: "Bu sayfa için",
      parent: "Üst ekran için",
      inherited: "Bu ortam için",
      "internal-docs": "İç dokümantasyon",
    },
    noTopic: "Bu sayfayı kapsayan resmî bir Yardım konusu yok.",
    internalDocs: "İç dokümantasyonu okuyun",
    pdfPage: "PDF s.",
    feature: "Özellik",
  },
};

/** Resolve the fixed Help labels for a locale, falling back to English. */
export function getAssistantHelpCopy(locale: WorkspaceLocale | string): AssistantHelpCopy {
  const base = (locale || "en").split("-")[0].toLowerCase();
  return COPY[base] ?? COPY.en;
}
