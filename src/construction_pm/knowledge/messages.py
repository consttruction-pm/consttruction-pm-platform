"""Localized assistant and workflow message templates.

Every user-visible sentence the assistant composes itself lives here. Source
quotations, card titles and official steps always come from the knowledge record
so the answer keeps its citation. When a localized card is not approved, the
assistant uses an explicit fallback sentence instead of pretending the content is
in the requested language.
"""

from __future__ import annotations

from typing import Mapping

from .locales import DEFAULT_LOCALE, canonical_locale

MESSAGES: Mapping[str, Mapping[str, str]] = {
    "en": {
        "answer_prefix": "Based on the official Version 26 reference, {title}: {summary}",
        "answer_fallback": "The {locale} translation of this card is not approved yet, so the official English source is shown. {title}: {summary}",
        "gap": "There is not enough published, validated knowledge to answer this question. No answer is generated rather than guessing.",
        "guide_start": "Step-by-step guide started for {title}. Step 1: {step}",
        "guide_step": "Step {index} of {total} — {title}: {step}",
        "no_guide": "No official step-by-step guide is recorded for {title}. {summary}",
        "workflow_start": "The project-creation workflow has started. Current step: organization and EPS. No project is created until the reviewed plan is approved and executed.",
        "workflow_unavailable": "The project-creation workflow is not available in this environment. No operation was executed.",
        "translation_missing": "No approved {locale} translation is available for this card; the official source language is shown and marked.",
        "source_note": "Source: official Version 26 reference, card {card_id}.",
        "step_titles": {
            "organization": "Organization and EPS",
            "discipline": "Discipline and project type",
            "identity": "Project name and unique identifier",
            "review": "Review and confirmation",
            "create": "Create the project",
            "settings": "Base project settings",
            "wbs": "Work breakdown structure",
            "activities": "Activities",
            "schedule": "Relationships, data date and calendar",
            "control": "Final control and verification",
        },
    },
    "fa": {
        "answer_prefix": "بر اساس منابع رسمی نسخه ۲۶، «{title}»: {summary}",
        "answer_fallback": "ترجمه فارسی این کارت هنوز تأیید نشده است؛ متن رسمی انگلیسی با نشانه‌گذاری نمایش داده می‌شود. «{title}»: {summary}",
        "gap": "دانش تأییدشده و منتشرشده کافی برای پاسخ به این پرسش در دسترس نیست. برای جلوگیری از پاسخ ساختگی، پاسخی ارائه نمی‌شود.",
        "guide_start": "راهنمای گام‌به‌گام «{title}» آغاز شد. گام ۱: {step}",
        "guide_step": "گام {index} از {total} — «{title}»: {step}",
        "no_guide": "برای «{title}» راهنمای گام‌به‌گام رسمی ثبت نشده است. {summary}",
        "workflow_start": "گردش کار ایجاد پروژه آغاز شد. گام کنونی: سازمان و گره EPS. هیچ پروژه‌ای تا تأیید بازبینی و اجرای واقعی ایجاد نمی‌شود.",
        "workflow_unavailable": "گردش کار ایجاد پروژه در این محیط در دسترس نیست. هیچ عملیاتی اجرا نشد.",
        "translation_missing": "ترجمه تأییدشده فارسی برای این کارت در دسترس نیست؛ متن زبان مبدأ نمایش داده و مشخص می‌شود.",
        "source_note": "منبع: مرجع رسمی نسخه ۲۶، کارت {card_id}.",
        "step_titles": {
            "organization": "سازمان و ساختار EPS",
            "discipline": "رشته و نوع پروژه",
            "identity": "نام و شناسه یکتای پروژه",
            "review": "بازبینی و تأیید",
            "create": "ایجاد پروژه",
            "settings": "تنظیمات پایه پروژه",
            "wbs": "شکست ساختاری کار",
            "activities": "فعالیت‌ها",
            "schedule": "روابط، تاریخ داده و تقویم",
            "control": "کنترل و راستی‌آزمایی نهایی",
        },
    },
    "de": {
        "answer_prefix": "Gemäß der offiziellen Version-26-Referenz, {title}: {summary}",
        "answer_fallback": "Die deutsche Übersetzung dieser Karte ist noch nicht freigegeben; daher wird die offizielle englische Quelle gekennzeichnet angezeigt. {title}: {summary}",
        "gap": "Es sind nicht genügend veröffentlichte und geprüfte Kenntnisse vorhanden. Statt einer Vermutung wird keine Antwort erzeugt.",
        "guide_start": "Die Schritt-für-Schritt-Anleitung für {title} wurde gestartet. Schritt 1: {step}",
        "guide_step": "Schritt {index} von {total} — {title}: {step}",
        "no_guide": "Für {title} ist keine offizielle Schritt-für-Schritt-Anleitung erfasst. {summary}",
        "workflow_start": "Der Projektanlage-Workflow wurde gestartet. Aktueller Schritt: Organisation und EPS. Ein Projekt wird erst nach Prüfung und Freigabe angelegt.",
        "workflow_unavailable": "Der Projektanlage-Workflow ist in dieser Umgebung nicht verfügbar. Es wurde kein Vorgang ausgeführt.",
        "translation_missing": "Für diese Karte ist keine freigegebene deutsche Übersetzung vorhanden; die offizielle Ausgangssprache wird gekennzeichnet angezeigt.",
        "source_note": "Quelle: offizielle Version-26-Referenz, Karte {card_id}.",
        "step_titles": {
            "organization": "Organisation und EPS",
            "discipline": "Fachbereich und Projekttyp",
            "identity": "Projektname und eindeutige Kennung",
            "review": "Prüfung und Bestätigung",
            "create": "Projekt anlegen",
            "settings": "Grundlegende Projekteinstellungen",
            "wbs": "Arbeitsgliederungsstruktur",
            "activities": "Aktivitäten",
            "schedule": "Beziehungen, Datenstichtag und Kalender",
            "control": "Abschließende Kontrolle und Verifikation",
        },
    },
    "zh-CN": {
        "answer_prefix": "根据官方第 26 版参考资料，{title}：{summary}",
        "answer_fallback": "此卡片的简体中文译文尚未批准，因此显示官方英文原文并加以标注。{title}：{summary}",
        "gap": "没有足够的已发布且经过验证的知识来回答此问题。为避免猜测，不生成答案。",
        "guide_start": "已启动 {title} 的分步指南。第 1 步：{step}",
        "guide_step": "第 {index} 步，共 {total} 步 — {title}：{step}",
        "no_guide": "未记录 {title} 的官方分步指南。{summary}",
        "workflow_start": "项目创建流程已启动。当前步骤：组织与 EPS。在审查计划获得批准并实际执行之前，不会创建项目。",
        "workflow_unavailable": "此环境中无法使用项目创建流程。未执行任何操作。",
        "translation_missing": "此卡片没有已批准的简体中文译文；将显示官方源语言并加以标注。",
        "source_note": "来源：官方第 26 版参考资料，卡片 {card_id}。",
        "step_titles": {
            "organization": "组织与 EPS",
            "discipline": "专业与项目类型",
            "identity": "项目名称与唯一标识",
            "review": "审查与确认",
            "create": "创建项目",
            "settings": "项目基础设置",
            "wbs": "工作分解结构",
            "activities": "活动",
            "schedule": "关系、数据日期与日历",
            "control": "最终控制与验证",
        },
    },
    "zh-TW": {
        "answer_prefix": "根據官方第 26 版參考資料，{title}：{summary}",
        "answer_fallback": "此卡片的繁體中文譯文尚未核准，因此顯示官方英文原文並加以標註。{title}：{summary}",
        "gap": "沒有足夠已發佈且經驗證的知識可回答此問題。為避免猜測，不產生答案。",
        "guide_start": "已啟動 {title} 的逐步指南。第 1 步：{step}",
        "guide_step": "第 {index} 步，共 {total} 步 — {title}：{step}",
        "no_guide": "未記錄 {title} 的官方逐步指南。{summary}",
        "workflow_start": "專案建立流程已啟動。目前步驟：組織與 EPS。在審查計畫獲得核准並實際執行之前，不會建立專案。",
        "workflow_unavailable": "此環境中無法使用專案建立流程。未執行任何操作。",
        "translation_missing": "此卡片沒有已核准的繁體中文譯文；將顯示官方來源語言並加以標註。",
        "source_note": "來源：官方第 26 版參考資料，卡片 {card_id}。",
        "step_titles": {
            "organization": "組織與 EPS",
            "discipline": "專業與專案類型",
            "identity": "專案名稱與唯一識別碼",
            "review": "審查與確認",
            "create": "建立專案",
            "settings": "專案基本設定",
            "wbs": "工作分解結構",
            "activities": "活動",
            "schedule": "關係、資料日期與行事曆",
            "control": "最終控制與驗證",
        },
    },
    "ar": {
        "answer_prefix": "استناداً إلى المرجع الرسمي للإصدار 26، {title}: {summary}",
        "answer_fallback": "لم تتم الموافقة على الترجمة العربية لهذه البطاقة بعد، لذلك يُعرض المصدر الإنجليزي الرسمي مع وضع علامة عليه. {title}: {summary}",
        "gap": "لا توجد معرفة منشورة ومُتحقق منها بما يكفي للإجابة عن هذا السؤال. لا يتم توليد إجابة بدلاً من التخمين.",
        "guide_start": "بدأ الدليل خطوة بخطوة لـ {title}. الخطوة 1: {step}",
        "guide_step": "الخطوة {index} من {total} — {title}: {step}",
        "no_guide": "لا يوجد دليل رسمي خطوة بخطوة مسجل لـ {title}. {summary}",
        "workflow_start": "بدأ سير عمل إنشاء المشروع. الخطوة الحالية: المؤسسة وEPS. لا يُنشأ أي مشروع حتى تتم الموافقة على الخطة وتنفيذها فعلياً.",
        "workflow_unavailable": "سير عمل إنشاء المشروع غير متاح في هذه البيئة. لم يتم تنفيذ أي عملية.",
        "translation_missing": "لا توجد ترجمة عربية معتمدة لهذه البطاقة؛ يتم عرض لغة المصدر الرسمية مع الإشارة إليها.",
        "source_note": "المصدر: المرجع الرسمي للإصدار 26، البطاقة {card_id}.",
        "step_titles": {
            "organization": "المؤسسة وEPS",
            "discipline": "التخصص ونوع المشروع",
            "identity": "اسم المشروع والمعرّف الفريد",
            "review": "المراجعة والتأكيد",
            "create": "إنشاء المشروع",
            "settings": "إعدادات المشروع الأساسية",
            "wbs": "هيكل تقسيم العمل",
            "activities": "الأنشطة",
            "schedule": "العلاقات وتاريخ البيانات والتقويم",
            "control": "التحكم النهائي والتحقق",
        },
    },
    "fr": {
        "answer_prefix": "D'après la référence officielle de la version 26, {title} : {summary}",
        "answer_fallback": "La traduction française de cette fiche n'est pas encore approuvée ; la source officielle anglaise est affichée et signalée. {title} : {summary}",
        "gap": "Il n'existe pas assez de connaissances publiées et validées pour répondre. Aucune réponse n'est générée plutôt que de deviner.",
        "guide_start": "Le guide pas à pas de {title} a démarré. Étape 1 : {step}",
        "guide_step": "Étape {index} sur {total} — {title} : {step}",
        "no_guide": "Aucun guide officiel pas à pas n'est enregistré pour {title}. {summary}",
        "workflow_start": "Le workflow de création de projet a démarré. Étape actuelle : organisation et EPS. Aucun projet n'est créé avant l'approbation et l'exécution du plan.",
        "workflow_unavailable": "Le workflow de création de projet n'est pas disponible dans cet environnement. Aucune opération n'a été exécutée.",
        "translation_missing": "Aucune traduction française approuvée n'est disponible pour cette fiche ; la langue source officielle est affichée et signalée.",
        "source_note": "Source : référence officielle de la version 26, fiche {card_id}.",
        "step_titles": {
            "organization": "Organisation et EPS",
            "discipline": "Discipline et type de projet",
            "identity": "Nom et identifiant unique du projet",
            "review": "Revue et confirmation",
            "create": "Créer le projet",
            "settings": "Paramètres de base du projet",
            "wbs": "Structure de découpage du projet",
            "activities": "Activités",
            "schedule": "Relations, date des données et calendrier",
            "control": "Contrôle et vérification finaux",
        },
    },
    "ja": {
        "answer_prefix": "公式バージョン 26 リファレンスに基づく {title}: {summary}",
        "answer_fallback": "このカードの日本語訳はまだ承認されていないため、公式の英語原文を明示して表示します。{title}: {summary}",
        "gap": "この質問に回答するための公開・検証済み知識が十分にありません。推測を避けるため、回答は生成しません。",
        "guide_start": "{title} のステップバイステップ ガイドを開始しました。ステップ 1: {step}",
        "guide_step": "ステップ {index}/{total} — {title}: {step}",
        "no_guide": "{title} の公式ステップバイステップ ガイドは記録されていません。{summary}",
        "workflow_start": "プロジェクト作成ワークフローを開始しました。現在のステップ: 組織と EPS。レビュー済み計画の承認と実際の実行まではプロジェクトは作成されません。",
        "workflow_unavailable": "この環境ではプロジェクト作成ワークフローを利用できません。操作は実行されていません。",
        "translation_missing": "このカードには承認済みの日本語訳がありません。公式のソース言語を明示して表示します。",
        "source_note": "出典: 公式バージョン 26 リファレンス、カード {card_id}。",
        "step_titles": {
            "organization": "組織と EPS",
            "discipline": "分野とプロジェクト種別",
            "identity": "プロジェクト名と一意の識別子",
            "review": "レビューと確認",
            "create": "プロジェクトを作成",
            "settings": "プロジェクトの基本設定",
            "wbs": "作業分解構成",
            "activities": "アクティビティ",
            "schedule": "関係、データ日付、カレンダー",
            "control": "最終管理と検証",
        },
    },
    "ko": {
        "answer_prefix": "공식 버전 26 참조 자료에 따르면 {title}: {summary}",
        "answer_fallback": "이 카드의 한국어 번역은 아직 승인되지 않았으므로 공식 영어 원문을 표시하고 명시합니다. {title}: {summary}",
        "gap": "이 질문에 답할 충분한 게시·검증 지식이 없습니다. 추측을 피하기 위해 답변을 생성하지 않습니다.",
        "guide_start": "{title} 단계별 안내를 시작했습니다. 1단계: {step}",
        "guide_step": "{total}단계 중 {index}단계 — {title}: {step}",
        "no_guide": "{title}에 대한 공식 단계별 안내가 등록되어 있지 않습니다. {summary}",
        "workflow_start": "프로젝트 생성 워크플로가 시작되었습니다. 현재 단계: 조직 및 EPS. 검토된 계획이 승인되고 실제 실행되기 전에는 프로젝트가 생성되지 않습니다.",
        "workflow_unavailable": "이 환경에서는 프로젝트 생성 워크플로를 사용할 수 없습니다. 어떤 작업도 실행되지 않았습니다.",
        "translation_missing": "이 카드에는 승인된 한국어 번역이 없습니다. 공식 원문 언어를 표시하고 명시합니다.",
        "source_note": "출처: 공식 버전 26 참조 자료, 카드 {card_id}.",
        "step_titles": {
            "organization": "조직 및 EPS",
            "discipline": "분야 및 프로젝트 유형",
            "identity": "프로젝트 이름 및 고유 식별자",
            "review": "검토 및 확인",
            "create": "프로젝트 생성",
            "settings": "프로젝트 기본 설정",
            "wbs": "작업 분류 체계",
            "activities": "활동",
            "schedule": "관계, 데이터 날짜 및 달력",
            "control": "최종 통제 및 검증",
        },
    },
    "ru": {
        "answer_prefix": "На основании официального справочника версии 26, {title}: {summary}",
        "answer_fallback": "Русский перевод этой карточки ещё не утверждён, поэтому показан официальный английский источник с пометкой. {title}: {summary}",
        "gap": "Опубликованных и проверенных знаний недостаточно для ответа на этот вопрос. Ответ не формируется, чтобы не догадываться.",
        "guide_start": "Пошаговое руководство по {title} начато. Шаг 1: {step}",
        "guide_step": "Шаг {index} из {total} — {title}: {step}",
        "no_guide": "Для {title} официальное пошаговое руководство не зарегистрировано. {summary}",
        "workflow_start": "Запущен процесс создания проекта. Текущий шаг: организация и EPS. Проект не создаётся до утверждения проверенного плана и фактического выполнения.",
        "workflow_unavailable": "Процесс создания проекта недоступен в этой среде. Никакие операции не выполнялись.",
        "translation_missing": "Для этой карточки нет утверждённого русского перевода; показан официальный исходный язык с пометкой.",
        "source_note": "Источник: официальный справочник версии 26, карточка {card_id}.",
        "step_titles": {
            "organization": "Организация и EPS",
            "discipline": "Дисциплина и тип проекта",
            "identity": "Название и уникальный идентификатор проекта",
            "review": "Проверка и подтверждение",
            "create": "Создание проекта",
            "settings": "Базовые настройки проекта",
            "wbs": "Структура разбиения работ",
            "activities": "Активности",
            "schedule": "Связи, дата данных и календарь",
            "control": "Финальный контроль и проверка",
        },
    },
}


def messages_for(locale: object) -> Mapping[str, str]:
    resolved = canonical_locale(locale, default=DEFAULT_LOCALE) or DEFAULT_LOCALE
    return MESSAGES.get(resolved, MESSAGES[DEFAULT_LOCALE])


def message(locale: object, key: str) -> str:
    return messages_for(locale).get(key, MESSAGES[DEFAULT_LOCALE][key])


def step_title(locale: object, step: str) -> str:
    titles = messages_for(locale).get("step_titles", {})
    return titles.get(step, MESSAGES[DEFAULT_LOCALE]["step_titles"].get(step, step))


def step_titles(locale: object) -> dict[str, str]:
    return dict(messages_for(locale).get("step_titles", MESSAGES[DEFAULT_LOCALE]["step_titles"]))


__all__ = ["MESSAGES", "message", "messages_for", "step_title", "step_titles"]
