/**
 * Interface chrome for the global assistant in the eight built-in locales that
 * are neither English nor Persian. The operational guidance itself is reproduced
 * from the official Help wording in its published language; only the fixed
 * interface sentences live here, so no instruction is paraphrased by a translator.
 *
 * Keys are the English source sentences the launcher uses as its fallback. A
 * missing entry returns the English string, never a raw key.
 */

export type AssistantChromeLocale = "de" | "zh" | "ar" | "fr" | "ja" | "ko" | "ru" | "tr";

const CHROME: Record<AssistantChromeLocale, Readonly<Record<string, string>>> = {
  de: {
    "CUBI AI Assistant": "CUBI-KI-Assistent",
    "Project help, one step away": "Projekthilfe, nur einen Schritt entfernt",
    "Close assistant panel": "Assistentenbereich schließen",
    "Open a project to use the assistant with its project context.":
      "Öffnen Sie ein Projekt, um den Assistenten mit seinem Projektkontext zu nutzen.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "Für projektspezifische Antworten oder Unterstützung beim Terminplan öffnen Sie Ihren Arbeitsbereich und wählen ein Projekt.",
    "Open assistant panel →": "Assistentenbereich öffnen →",
    "Open project workspace →": "Projektarbeitsbereich öffnen →",
    "Open or create a project to use the assistant.":
      "Öffnen oder erstellen Sie ein Projekt, um den Assistenten zu nutzen.",
    "Next steps": "Nächste Schritte",
  },
  zh: {
    "CUBI AI Assistant": "CUBI AI 助手",
    "Project help, one step away": "项目帮助，近在一步",
    "Close assistant panel": "关闭助手面板",
    "Open a project to use the assistant with its project context.":
      "打开项目，以便助手使用其项目上下文。",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "如需项目专属答案或进度计划支持，请打开工作区并选择项目。",
    "Open assistant panel →": "打开助手面板 →",
    "Open project workspace →": "打开项目工作区 →",
    "Open or create a project to use the assistant.": "打开或创建项目以使用助手。",
    "Next steps": "后续步骤",
  },
  ar: {
    "CUBI AI Assistant": "مساعد CUBI الذكي",
    "Project help, one step away": "مساعدة المشروع على بُعد خطوة",
    "Close assistant panel": "إغلاق لوحة المساعد",
    "Open a project to use the assistant with its project context.":
      "افتح مشروعًا ليستخدم المساعد سياقه.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "للحصول على إجابات خاصة بالمشروع أو دعم الجدولة، افتح مساحة العمل واختر مشروعًا.",
    "Open assistant panel →": "فتح لوحة المساعد ←",
    "Open project workspace →": "فتح مساحة عمل المشروع ←",
    "Open or create a project to use the assistant.": "افتح مشروعًا أو أنشئه لاستخدام المساعد.",
    "Next steps": "الخطوات التالية",
  },
  fr: {
    "CUBI AI Assistant": "Assistant IA CUBI",
    "Project help, one step away": "L’aide projet à portée de main",
    "Close assistant panel": "Fermer le panneau de l’assistant",
    "Open a project to use the assistant with its project context.":
      "Ouvrez un projet pour que l’assistant dispose de son contexte.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "Pour des réponses propres au projet ou une aide sur l’échéancier, ouvrez votre espace de travail et sélectionnez un projet.",
    "Open assistant panel →": "Ouvrir le panneau de l’assistant →",
    "Open project workspace →": "Ouvrir l’espace de travail du projet →",
    "Open or create a project to use the assistant.":
      "Ouvrez ou créez un projet pour utiliser l’assistant.",
    "Next steps": "Étapes suivantes",
  },
  ja: {
    "CUBI AI Assistant": "CUBI AI アシスタント",
    "Project help, one step away": "プロジェクトのヘルプをすぐそばに",
    "Close assistant panel": "アシスタントパネルを閉じる",
    "Open a project to use the assistant with its project context.":
      "プロジェクトを開くと、アシスタントがそのプロジェクトのコンテキストを利用できます。",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "プロジェクト固有の回答やスケジュールの支援には、ワークスペースを開いてプロジェクトを選択してください。",
    "Open assistant panel →": "アシスタントパネルを開く →",
    "Open project workspace →": "プロジェクトワークスペースを開く →",
    "Open or create a project to use the assistant.":
      "アシスタントを使用するには、プロジェクトを開くか作成してください。",
    "Next steps": "次のステップ",
  },
  ko: {
    "CUBI AI Assistant": "CUBI AI 어시스턴트",
    "Project help, one step away": "프로젝트 도움말을 한 걸음 앞에",
    "Close assistant panel": "어시스턴트 패널 닫기",
    "Open a project to use the assistant with its project context.":
      "프로젝트를 열면 어시스턴트가 해당 프로젝트 컨텍스트를 사용할 수 있습니다.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "프로젝트별 답변이나 일정 지원을 받으려면 작업 공간을 열고 프로젝트를 선택하십시오.",
    "Open assistant panel →": "어시스턴트 패널 열기 →",
    "Open project workspace →": "프로젝트 작업 공간 열기 →",
    "Open or create a project to use the assistant.":
      "어시스턴트를 사용하려면 프로젝트를 열거나 만드십시오.",
    "Next steps": "다음 단계",
  },
  ru: {
    "CUBI AI Assistant": "ИИ-помощник CUBI",
    "Project help, one step away": "Помощь по проекту — на расстоянии шага",
    "Close assistant panel": "Закрыть панель помощника",
    "Open a project to use the assistant with its project context.":
      "Откройте проект, чтобы помощник использовал его контекст.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "Для ответов по проекту или поддержки расписания откройте рабочую область и выберите проект.",
    "Open assistant panel →": "Открыть панель помощника →",
    "Open project workspace →": "Открыть рабочую область проекта →",
    "Open or create a project to use the assistant.":
      "Откройте или создайте проект, чтобы использовать помощника.",
    "Next steps": "Следующие шаги",
  },
  tr: {
    "CUBI AI Assistant": "CUBI Yapay Zekâ Asistanı",
    "Project help, one step away": "Proje yardımı bir adım ötede",
    "Close assistant panel": "Asistan panelini kapat",
    "Open a project to use the assistant with its project context.":
      "Asistanın proje bağlamını kullanması için bir proje açın.",
    "For project-specific answers or schedule support, open your workspace and select a project.":
      "Projeye özgü yanıtlar veya program desteği için çalışma alanınızı açın ve bir proje seçin.",
    "Open assistant panel →": "Asistan panelini aç →",
    "Open project workspace →": "Proje çalışma alanını aç →",
    "Open or create a project to use the assistant.":
      "Asistanı kullanmak için bir proje açın veya oluşturun.",
    "Next steps": "Sonraki adımlar",
  },
};

export const ASSISTANT_CHROME_SOURCES: readonly string[] = Object.freeze([
  "CUBI AI Assistant",
  "Project help, one step away",
  "Close assistant panel",
  "Open a project to use the assistant with its project context.",
  "For project-specific answers or schedule support, open your workspace and select a project.",
  "Open assistant panel →",
  "Open project workspace →",
  "Open or create a project to use the assistant.",
  "Next steps",
]);

export const ASSISTANT_CHROME_LOCALES: readonly AssistantChromeLocale[] = Object.freeze([
  "de",
  "zh",
  "ar",
  "fr",
  "ja",
  "ko",
  "ru",
  "tr",
]);

/** Translate one fixed assistant sentence, falling back to the English source. */
export function translateAssistantChrome(base: string, english: string): string {
  return CHROME[base as AssistantChromeLocale]?.[english] ?? english;
}
