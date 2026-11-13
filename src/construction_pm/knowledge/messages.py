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
        "conflicting_sources": "Two published cards describe this subject differently, so no single answer is presented. Review the sources: {titles}.",
        "unpublished_knowledge": "Matching knowledge exists but is not published yet, so it is not used in an answer. It is waiting for review.",
        "insufficient_evidence": "The available evidence is too weak to answer this question reliably. No answer is generated rather than guessing.",
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
        "conflicting_sources": "دو کارت منتشرشده این موضوع را متفاوت توصیف می‌کنند؛ بنابراین پاسخ واحدی ارائه نمی‌شود. منابع را بررسی کنید: {titles}.",
        "unpublished_knowledge": "دانش مرتبط وجود دارد اما هنوز منتشر نشده است؛ بنابراین در پاسخ استفاده نمی‌شود و در انتظار بازبینی است.",
        "insufficient_evidence": "شواهد موجود برای پاسخ مطمئن به این پرسش کافی نیست. به‌جای حدس زدن، پاسخی تولید نمی‌شود.",
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
        "conflicting_sources": "Zwei veröffentlichte Karten beschreiben dieses Thema unterschiedlich, daher wird keine einzelne Antwort gegeben. Prüfen Sie die Quellen: {titles}.",
        "unpublished_knowledge": "Passendes Wissen ist vorhanden, aber noch nicht veröffentlicht und wird daher nicht als Antwort verwendet; es wartet auf die Prüfung.",
        "insufficient_evidence": "Die vorhandenen Belege reichen für eine verlässliche Antwort nicht aus. Statt zu raten wird keine Antwort erzeugt.",
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
    "zh-Hans": {
        "answer_prefix": "根据官方第 26 版参考资料，{title}：{summary}",
        "answer_fallback": "此卡片的简体中文译文尚未批准，因此显示官方英文原文并加以标注。{title}：{summary}",
        "gap": "没有足够的已发布且经过验证的知识来回答此问题。为避免猜测，不生成答案。",
        "conflicting_sources": "两张已发布的卡片对该主题描述不一致，因此不给出单一答案。请审阅来源：{titles}。",
        "unpublished_knowledge": "存在匹配的知识，但尚未发布，因此不会用于回答，正在等待审核。",
        "insufficient_evidence": "现有证据不足以可靠回答该问题。系统不会猜测，而是不生成答案。",
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
    "ar": {
        "answer_prefix": "استناداً إلى المرجع الرسمي للإصدار 26، {title}: {summary}",
        "answer_fallback": "لم تتم الموافقة على الترجمة العربية لهذه البطاقة بعد، لذلك يُعرض المصدر الإنجليزي الرسمي مع وضع علامة عليه. {title}: {summary}",
        "gap": "لا توجد معرفة منشورة ومُتحقق منها بما يكفي للإجابة عن هذا السؤال. لا يتم توليد إجابة بدلاً من التخمين.",
        "conflicting_sources": "توجد بطاقتان منشورتان تصفان هذا الموضوع بشكل مختلف، لذلك لا تُقدَّم إجابة واحدة. راجع المصادر: {titles}.",
        "unpublished_knowledge": "توجد معرفة مطابقة لكنها غير منشورة بعد، لذلك لا تُستخدم في الإجابة وهي بانتظار المراجعة.",
        "insufficient_evidence": "الأدلة المتاحة غير كافية للإجابة عن هذا السؤال بثقة. لا تُولِّد إجابة بدلًا من التخمين.",
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
        "conflicting_sources": "Deux fiches publiées décrivent ce sujet différemment ; aucune réponse unique n'est donc proposée. Vérifiez les sources : {titles}.",
        "unpublished_knowledge": "Des connaissances correspondantes existent mais ne sont pas encore publiées ; elles ne sont donc pas utilisées et attendent une révision.",
        "insufficient_evidence": "Les preuves disponibles sont trop faibles pour répondre de façon fiable. Aucune réponse n'est générée plutôt que de deviner.",
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
        "conflicting_sources": "公開済みのカードがこの主題を異なる内容で説明しているため、単一の回答は示しません。出典を確認してください: {titles}。",
        "unpublished_knowledge": "一致する知識はありますが未公開のため、回答には使用しません。レビュー待ちです。",
        "insufficient_evidence": "利用可能な根拠が不十分なため、確実な回答はできません。推測せず回答は生成しません。",
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
        "conflicting_sources": "게시된 카드 두 개가 이 주제를 다르게 설명하므로 단일 답변을 제공하지 않습니다. 출처를 검토하세요: {titles}.",
        "unpublished_knowledge": "일치하는 지식이 있지만 아직 게시되지 않아 답변에 사용하지 않으며 검토를 기다리고 있습니다.",
        "insufficient_evidence": "사용 가능한 근거가 부족하여 신뢰할 수 있는 답변을 제공할 수 없습니다. 추측 대신 답변을 생성하지 않습니다.",
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
        "conflicting_sources": "Две опубликованные карточки описывают эту тему по-разному, поэтому единый ответ не выдаётся. Проверьте источники: {titles}.",
        "unpublished_knowledge": "Подходящие знания есть, но они ещё не опубликованы, поэтому не используются в ответе и ожидают проверки.",
        "insufficient_evidence": "Доступных доказательств недостаточно для надёжного ответа. Вместо догадки ответ не формируется.",
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
