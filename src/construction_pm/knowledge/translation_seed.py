"""Seed translations for a small, explicit set of core Knowledge Cards.

These records exist so every product translation target can demonstrate the
complete per-locale content model (title, summary, steps, glossary, source note)
without pretending that the whole card corpus has been translated. They are
stored as ``translated`` with ``review_status=pending``; no seed is approved or
published. A human reviewer must approve each locale through the normal API.

Chinese is seeded under the canonical ``zh-Hans`` code. The older ``zh-CN`` /
``zh-TW`` seeds were consolidated because the product exposes one Chinese
translation slot. A Russian seed is retained only as legacy data; Russian is
not a product target and does not count toward product coverage.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Mapping

from .locales import language_code
from .model import (
    CardStatus,
    KnowledgeCard,
    ReviewStatus,
    TranslationRecord,
    TranslationSource,
    TranslationStatus,
    translation_content_hash,
    utc_now,
)
from .store import KnowledgeStore


def _content(
    *,
    title: str,
    summary: str,
    steps: list[str],
    glossary: list[tuple[str, str]],
    source_note: str,
    prerequisites: list[str] | None = None,
    warnings: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, object]:
    return {
        "title": title,
        "summary": summary,
        "body": "\n".join(steps),
        "steps": steps,
        "prerequisites": prerequisites or [],
        "warnings": warnings or [],
        "limitations": limitations or [],
        "technical_glossary": glossary,
        "source_note": source_note,
    }


SEED_TRANSLATIONS: Mapping[str, Mapping[str, Mapping[str, object]]] = {
    "Create a project": {
        "fa": _content(
            title="ایجاد یک پروژه",
            summary="برای ایجاد یک پروژه جدید در CUBI از این مسیر رسمی استفاده کنید.",
            steps=[
                "File و سپس New را انتخاب کنید تا ویزارد Create a New Project باز شود.",
                "گره EPS مورد نظر برای افزودن پروژه جدید را انتخاب کنید.",
                "شناسه و نام پروژه جدید را وارد کنید.",
                "تاریخ شروع برنامه‌ریزی‌شده و در صورت نیاز تاریخ must finish by را مشخص کنید. با تعیین تاریخ پایان اجباری، تقویم به تاریخ و ساعت پایان پروژه تنظیم می‌شود؛ در صورت خالی بودن، تاریخ و ساعت جاری سیستم مبنا قرار می‌گیرد.",
                "مدیر مسئول را انتخاب کنید. عنصر OBS انتخاب‌شده در بالای OBS پروژه جدید قرار می‌گیرد.",
                "نوع نرخ پیش‌فرض پروژه را برای تخصیص منابع و نقش‌های جدید انتخاب کنید.",
                "روی Finish کلیک کنید.",
            ],
            glossary=[
                ("پروژه", "Project — واحد کاری با محدوده و زمان‌بندی مشخص"),
                ("EPS", "Enterprise Project Structure — ساختار پروژه‌های سازمان"),
                ("OBS", "Organizational Breakdown Structure — ساختار شکست سازمانی"),
            ],
            source_note="ترجمه از مرجع رسمی نسخه ۲۶؛ نیازمند بازبینی انسانی پیش از انتشار.",
        ),
        "de": _content(
            title="Ein Projekt anlegen",
            summary="Verwenden Sie diesen offiziellen Ablauf, um ein neues Projekt in CUBI anzulegen.",
            steps=[
                "Wählen Sie Datei und dann Neu, um den Assistenten Neues Projekt anlegen zu öffnen.",
                "Wählen Sie den EPS-Knoten, dem das neue Projekt hinzugefügt werden soll.",
                "Geben Sie eine Projektkennung und einen Projektnamen ein.",
                "Legen Sie ein geplantes Startdatum und bei Bedarf ein Muss-Enddatum fest. Mit einem Muss-Enddatum übernimmt der Kalender Datum und Uhrzeit des Projektendes; ohne Eintrag gilt das aktuelle Systemdatum.",
                "Wählen Sie einen verantwortlichen Manager. Das gewählte OBS-Element erscheint oben im OBS des neuen Projekts.",
                "Wählen Sie den Standard-Satztyp für neue Ressourcen- und Rollenzuweisungen.",
                "Klicken Sie auf Fertig stellen.",
            ],
            glossary=[
                ("Projekt", "Project — Vorhaben mit definiertem Umfang und Terminplan"),
                ("EPS", "Enterprise Project Structure — Projektstruktur des Unternehmens"),
                ("OBS", "Organizational Breakdown Structure — Organisationsstruktur"),
            ],
            source_note="Übersetzt aus der offiziellen Version-26-Referenz; vor Veröffentlichung menschlich zu prüfen.",
        ),
        "zh-Hans": _content(
            title="创建项目",
            summary="使用此官方流程在 CUBI 中创建新项目。",
            steps=[
                "选择“文件”，然后选择“新建”，启动“创建新项目”向导。",
                "选择要将新项目添加到的 EPS 节点。",
                "输入新项目的项目 ID 和项目名称。",
                "指定项目计划开始日期，必要时指定“必须完成日期”。设置必须完成日期后，日历默认采用项目完成日期和时间；留空时采用当前系统日期和时间。",
                "选择负责经理。此处选择的 OBS 元素将显示在新项目 OBS 的顶部。",
                "选择项目用于新资源与角色分配的默认费率类型。",
                "单击“完成”。",
            ],
            glossary=[
                ("项目", "Project — 具有明确范围与进度的临时性工作"),
                ("EPS", "Enterprise Project Structure — 企业项目结构"),
                ("OBS", "Organizational Breakdown Structure — 组织分解结构"),
            ],
            source_note="译自官方第 26 版参考资料；发布前需人工复核。",
        ),
        "ar": _content(
            title="إنشاء مشروع",
            summary="استخدم هذا المسار الرسمي لإنشاء مشروع جديد في CUBI.",
            steps=[
                "اختر ملف ثم جديد لفتح معالج إنشاء مشروع جديد.",
                "حدد عقدة EPS التي تريد إضافة المشروع الجديد إليها.",
                "أدخل معرّف المشروع واسم المشروع الجديد.",
                "حدد تاريخ البدء المخطط، وعند الحاجة تاريخ الإنجاز الإلزامي. عند إدخال تاريخ إنجاز إلزامي يعتمد التقويم على تاريخ ووقت انتهاء المشروع، وعند تركه فارغاً يعتمد على تاريخ ووقت النظام الحالي.",
                "اختر المدير المسؤول. يظهر عنصر OBS المحدد في أعلى OBS المشروع الجديد.",
                "اختر نوع السعر الافتراضي للمشروع لإسنادات الموارد والأدوار الجديدة.",
                "انقر فوق إنهاء.",
            ],
            glossary=[
                ("مشروع", "Project — عمل مؤقت له نطاق وجدول زمني محدد"),
                ("EPS", "Enterprise Project Structure — هيكل مشاريع المؤسسة"),
                ("OBS", "Organizational Breakdown Structure — هيكل التنظيم"),
            ],
            source_note="مترجم من المرجع الرسمي للإصدار 26؛ يتطلب مراجعة بشرية قبل النشر.",
        ),
        "fr": _content(
            title="Créer un projet",
            summary="Utilisez ce parcours officiel pour créer un nouveau projet dans CUBI.",
            steps=[
                "Choisissez Fichier puis Nouveau pour lancer l'assistant de création d'un projet.",
                "Sélectionnez le nœud EPS auquel ajouter le nouveau projet.",
                "Saisissez un identifiant et un nom pour le nouveau projet.",
                "Indiquez une date de début planifiée et, si nécessaire, une date de fin impérative. La date de fin impérative initialise le calendrier sur la date et l'heure de fin du projet ; si elle est vide, la date et l'heure système sont utilisées.",
                "Sélectionnez un chef de projet responsable. L'élément OBS choisi apparaît en haut de l'OBS du nouveau projet.",
                "Sélectionnez le type de taux par défaut pour les nouvelles affectations de ressources et de rôles.",
                "Cliquez sur Terminer.",
            ],
            glossary=[
                ("Projet", "Project — effort temporaire avec un périmètre et un calendrier"),
                ("EPS", "Enterprise Project Structure — structure des projets de l'entreprise"),
                ("OBS", "Organizational Breakdown Structure — structure organisationnelle"),
            ],
            source_note="Traduit de la référence officielle version 26 ; à réviser par un humain avant publication.",
        ),
        "ja": _content(
            title="プロジェクトを作成する",
            summary="CUBI で新しいプロジェクトを作成するための公式手順です。",
            steps=[
                "「ファイル」→「新規」を選択し、「新規プロジェクトの作成」ウィザードを起動します。",
                "新しいプロジェクトを追加する EPS ノードを選択します。",
                "新しいプロジェクトのプロジェクト ID とプロジェクト名を入力します。",
                "プロジェクトの計画開始日を指定し、必要に応じて「必着日」を指定します。必着日を設定すると、カレンダーはプロジェクトの終了日時を既定値とし、未設定の場合は現在のシステム日時を使用します。",
                "責任マネージャを選択します。ここで選択した OBS 要素が新しいプロジェクトの OBS の最上位に表示されます。",
                "新しい資源とロールの割り当てに使用する既定のレート タイプを選択します。",
                "「完了」をクリックします。",
            ],
            glossary=[
                ("プロジェクト", "Project — 明確な範囲とスケジュールを持つ一時的な取り組み"),
                ("EPS", "Enterprise Project Structure — 企業プロジェクト構造"),
                ("OBS", "Organizational Breakdown Structure — 組織分解構造"),
            ],
            source_note="公式バージョン 26 リファレンスからの翻訳。公開前に人によるレビューが必要です。",
        ),
        "ko": _content(
            title="프로젝트 생성",
            summary="CUBI에서 새 프로젝트를 생성하는 공식 절차입니다.",
            steps=[
                "파일 > 새로 만들기를 선택하여 새 프로젝트 만들기 마법사를 시작합니다.",
                "새 프로젝트를 추가할 EPS 노드를 선택합니다.",
                "새 프로젝트의 프로젝트 ID와 프로젝트 이름을 입력합니다.",
                "프로젝트 계획 시작 날짜를 지정하고 필요한 경우 필수 완료 날짜를 지정합니다. 필수 완료 날짜를 입력하면 달력이 프로젝트 완료 날짜와 시간을 기본값으로 사용하며, 비어 있으면 현재 시스템 날짜와 시간을 사용합니다.",
                "책임 관리자를 선택합니다. 여기서 선택한 OBS 요소가 새 프로젝트 OBS의 맨 위에 표시됩니다.",
                "새 자원 및 역할 배정에 사용할 기본 요율 유형을 선택합니다.",
                "마침을 클릭합니다.",
            ],
            glossary=[
                ("프로젝트", "Project — 명확한 범위와 일정을 가진 일시적 작업"),
                ("EPS", "Enterprise Project Structure — 기업 프로젝트 구조"),
                ("OBS", "Organizational Breakdown Structure — 조직 분류 체계"),
            ],
            source_note="공식 버전 26 참조 자료에서 번역됨. 게시 전에 사람 검토가 필요합니다.",
        ),
        "ru": _content(
            title="Создание проекта",
            summary="Официальная процедура создания нового проекта в CUBI.",
            steps=[
                "Выберите «Файл», затем «Создать», чтобы запустить мастер создания нового проекта.",
                "Выберите узел EPS, в который нужно добавить новый проект.",
                "Введите идентификатор и название нового проекта.",
                "Укажите плановую дату начала и при необходимости обязательную дату завершения. При указании обязательной даты завершения календарь принимает дату и время завершения проекта; если поле пустое, используются текущие системные дата и время.",
                "Выберите ответственного руководителя. Выбранный элемент OBS отображается в верхней части OBS нового проекта.",
                "Выберите тип ставки по умолчанию для новых назначений ресурсов и ролей.",
                "Нажмите «Готово».",
            ],
            glossary=[
                ("Проект", "Project — временная деятельность с определёнными рамками и графиком"),
                ("EPS", "Enterprise Project Structure — структура проектов предприятия"),
                ("OBS", "Organizational Breakdown Structure — организационная структура"),
            ],
            source_note="Перевод из официального справочника версии 26; перед публикацией требуется проверка человеком.",
        ),
    },
}


def seed_translations(
    store: KnowledgeStore,
    *,
    now: datetime | None = None,
    card_titles: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
) -> dict[str, int]:
    """Insert the seed records that have a matching card, without publishing."""

    moment = now or utc_now()
    catalog = card_titles or SEED_TRANSLATIONS
    written = 0
    skipped = 0
    cards_by_title: dict[str, KnowledgeCard] = {}
    for card in store.list_cards(
        scope="central",
        publication_statuses=[
            CardStatus.DRAFT.value,
            CardStatus.VALIDATED.value,
            CardStatus.PUBLISHED.value,
        ],
    ):
        cards_by_title.setdefault(card.title.casefold(), card)
    for title, locales in catalog.items():
        card = cards_by_title.get(title.casefold())
        if card is None:
            skipped += len(locales)
            continue
        for locale, content in locales.items():
            existing = store.get_translation(card.card_id, locale)
            if existing is not None and existing.translation_status is not TranslationStatus.MISSING:
                skipped += 1
                continue
            record = TranslationRecord(
                card_id=card.card_id,
                locale=locale,
                language_code=language_code(locale),
                source_language="en",
                title=str(content["title"]),
                summary=str(content["summary"]),
                body=str(content["body"]),
                steps=tuple(str(item) for item in content["steps"]),
                prerequisites=tuple(str(item) for item in content.get("prerequisites", [])),
                warnings=tuple(str(item) for item in content.get("warnings", [])),
                limitations=tuple(str(item) for item in content.get("limitations", [])),
                relations=tuple(card.relations),
                glossary=tuple(
                    (str(term), str(definition))
                    for term, definition in content.get("technical_glossary", [])
                ),
                source_note=str(content["source_note"]),
                translation_status=TranslationStatus.TRANSLATED,
                review_status=ReviewStatus.PENDING,
                translation_version=1,
                published_language_version=None,
                translation_source=TranslationSource.CUBI_AUTHORED,
                machine_translated=False,
                localization_metadata={
                    "seed": True,
                    "requires_human_review": True,
                    "source_title": card.title,
                    "source_version": card.source_version,
                },
                content_hash="",
                updated_at=moment,
            )
            record = replace(record, content_hash=translation_content_hash(record))
            record.validate()
            store.save_translation(record)
            written += 1
    return {"written": written, "skipped": skipped}


__all__ = ["SEED_TRANSLATIONS", "seed_translations"]
