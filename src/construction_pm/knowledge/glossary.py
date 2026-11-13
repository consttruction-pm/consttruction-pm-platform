"""CUBI-owned technical glossary for the product languages.

These entries are product terminology, not source content. Search may expand a
localized engineering term into the English term used by the official Version 26
reference; the assistant may attach the glossary to an answer so a user sees the
canonical project-control vocabulary in their own language. The glossary never
changes a citation or invents a procedure. The Russian block is retained so
legacy records keep their terminology; Russian is not a product target.
"""

from __future__ import annotations

from typing import Mapping

GLOSSARIES: Mapping[str, tuple[tuple[str, str], ...]] = {
    "fa": (
        ("پروژه", "Project — مجموعه‌ای از فعالیت‌ها برای تحقق یک هدف"),
        ("EPS", "Enterprise Project Structure — ساختار سازمانی پروژه‌ها"),
        ("WBS", "Work Breakdown Structure — شکست ساختاری کار"),
        ("فعالیت", "Activity — واحد کاری زمان‌بندی‌شده"),
        ("رابطه", "Relationship — وابستگی منطقی میان فعالیت‌ها"),
        ("تقویم", "Calendar — تقویم کاری و ساعات کاری"),
        ("منبع", "Resource — نیروی انسانی، ماشین یا ماده"),
        ("هزینه", "Cost — هزینه برنامه‌ریزی‌شده یا واقعی"),
        ("زمان‌بندی", "Schedule — محاسبه و به‌روزرسانی زمان‌ها"),
        ("تقدم", "Predecessor — فعالیت پیشین"),
        ("جانشین", "Successor — فعالیت پسین"),
        ("سطح‌بندی منابع", "Resource Leveling — توزیع متعادل منابع"),
        ("خط مبنا", "Baseline — نسخه مرجع برنامه"),
    ),
    "en": (
        ("Project", "A temporary endeavor with a defined scope and schedule"),
        ("EPS", "Enterprise Project Structure"),
        ("WBS", "Work Breakdown Structure"),
        ("Activity", "A time-scheduled unit of work"),
        ("Relationship", "A logical dependency between activities"),
        ("Calendar", "Working days and hours"),
        ("Resource", "Labor, equipment or material"),
        ("Cost", "Planned or actual project cost"),
        ("Schedule", "Calculated activity dates"),
        ("Predecessor", "An activity that must occur before another"),
        ("Successor", "An activity that follows another"),
        ("Resource Leveling", "Balancing resource demand over time"),
        ("Baseline", "A reference version of the plan"),
    ),
    "de": (
        ("Projekt", "Ein zeitlich begrenztes Vorhaben mit definiertem Umfang"),
        ("EPS", "Enterprise Project Structure — Projektstruktur des Unternehmens"),
        ("WBS", "Work Breakdown Structure — Arbeitsgliederungsstruktur"),
        ("Aktivität", "Activity — zeitlich geplante Arbeitseinheit"),
        ("Beziehung", "Relationship — logische Abhängigkeit zwischen Aktivitäten"),
        ("Kalender", "Calendar — Arbeitstage und Arbeitszeiten"),
        ("Ressource", "Resource — Personal, Gerät oder Material"),
        ("Kosten", "Cost — geplante oder tatsächliche Projektkosten"),
        ("Terminplan", "Schedule — berechnete Aktivitätsdaten"),
        ("Vorgänger", "Predecessor — vorangehende Aktivität"),
        ("Nachfolger", "Successor — nachfolgende Aktivität"),
        ("Ressourcenausgleich", "Resource Leveling — gleichmäßige Ressourcenverteilung"),
        ("Basisplan", "Baseline — Referenzversion des Plans"),
    ),
    "zh-Hans": (
        ("项目", "Project — 具有明确范围与进度目标的临时性工作"),
        ("EPS", "Enterprise Project Structure — 企业项目结构"),
        ("WBS", "Work Breakdown Structure — 工作分解结构"),
        ("活动", "Activity — 纳入进度安排的工作单元"),
        ("关系", "Relationship — 活动之间的逻辑依赖"),
        ("日历", "Calendar — 工作日与工作时间"),
        ("资源", "Resource — 人工、设备或材料"),
        ("成本", "Cost — 计划成本或实际成本"),
        ("进度计划", "Schedule — 计算后的活动日期"),
        ("紧前活动", "Predecessor — 前置活动"),
        ("紧后活动", "Successor — 后续活动"),
        ("资源平衡", "Resource Leveling — 均衡资源需求"),
        ("基准计划", "Baseline — 计划的参考版本"),
    ),
    "ar": (
        ("مشروع", "Project — عمل مؤقت له نطاق وجدول زمني محدد"),
        ("EPS", "Enterprise Project Structure — هيكل مشاريع المؤسسة"),
        ("WBS", "Work Breakdown Structure — هيكل تقسيم العمل"),
        ("نشاط", "Activity — وحدة عمل مجدولة زمنياً"),
        ("علاقة", "Relationship — تبعية منطقية بين الأنشطة"),
        ("تقويم", "Calendar — أيام وساعات العمل"),
        ("مورد", "Resource — عمالة أو معدات أو مواد"),
        ("تكلفة", "Cost — التكلفة المخططة أو الفعلية"),
        ("جدول زمني", "Schedule — تواريخ الأنشطة المحسوبة"),
        ("سلف", "Predecessor — النشاط السابق"),
        ("خلف", "Successor — النشاط اللاحق"),
        ("موازنة الموارد", "Resource Leveling — موازنة الطلب على الموارد"),
        ("خط الأساس", "Baseline — النسخة المرجعية للخطة"),
    ),
    "fr": (
        ("Projet", "Project — effort temporaire avec un périmètre et un calendrier"),
        ("EPS", "Enterprise Project Structure — structure des projets de l'entreprise"),
        ("WBS", "Work Breakdown Structure — structure de découpage du projet"),
        ("Activité", "Activity — unité de travail planifiée"),
        ("Relation", "Relationship — dépendance logique entre activités"),
        ("Calendrier", "Calendar — jours et heures ouvrés"),
        ("Ressource", "Resource — main-d'œuvre, équipement ou matériau"),
        ("Coût", "Cost — coût prévu ou réel"),
        ("Échéancier", "Schedule — dates d'activité calculées"),
        ("Prédécesseur", "Predecessor — activité précédente"),
        ("Successeur", "Successor — activité suivante"),
        ("Lissage des ressources", "Resource Leveling — équilibrage de la demande"),
        ("Référence", "Baseline — version de référence du plan"),
    ),
    "ja": (
        ("プロジェクト", "Project — 明確な範囲とスケジュールを持つ一時的な取り組み"),
        ("EPS", "Enterprise Project Structure — 企業プロジェクト構造"),
        ("WBS", "Work Breakdown Structure — 作業分解構成"),
        ("アクティビティ", "Activity — スケジュールされた作業単位"),
        ("関係", "Relationship — アクティビティ間の論理的な依存関係"),
        ("カレンダー", "Calendar — 稼働日と稼働時間"),
        ("リソース", "Resource — 労務、設備、材料"),
        ("コスト", "Cost — 計画コストまたは実績コスト"),
        ("スケジュール", "Schedule — 計算されたアクティビティ日付"),
        ("先行アクティビティ", "Predecessor — 前工程"),
        ("後続アクティビティ", "Successor — 後工程"),
        ("リソース平準化", "Resource Leveling — リソース需要の平準化"),
        ("基準計画", "Baseline — 計画の基準版"),
    ),
    "ko": (
        ("프로젝트", "Project — 명확한 범위와 일정을 가진 일시적 작업"),
        ("EPS", "Enterprise Project Structure — 기업 프로젝트 구조"),
        ("WBS", "Work Breakdown Structure — 작업 분류 체계"),
        ("활동", "Activity — 일정이 지정된 작업 단위"),
        ("관계", "Relationship — 활동 간의 논리적 종속성"),
        ("달력", "Calendar — 작업일과 작업 시간"),
        ("자원", "Resource — 인력, 장비 또는 자재"),
        ("비용", "Cost — 계획 또는 실제 프로젝트 비용"),
        ("일정", "Schedule — 계산된 활동 날짜"),
        ("선행 활동", "Predecessor — 이전 활동"),
        ("후속 활동", "Successor — 다음 활동"),
        ("자원 평준화", "Resource Leveling — 자원 수요 균형"),
        ("기준 계획", "Baseline — 계획의 기준 버전"),
    ),
    "ru": (
        ("Проект", "Project — временная деятельность с определёнными рамками и графиком"),
        ("EPS", "Enterprise Project Structure — структура проектов предприятия"),
        ("WBS", "Work Breakdown Structure — структура разбиения работ"),
        ("Активность", "Activity — единица работы с графиком"),
        ("Связь", "Relationship — логическая зависимость между активностями"),
        ("Календарь", "Calendar — рабочие дни и часы"),
        ("Ресурс", "Resource — трудовые ресурсы, оборудование или материалы"),
        ("Стоимость", "Cost — плановая или фактическая стоимость"),
        ("График", "Schedule — рассчитанные даты активностей"),
        ("Предшественник", "Predecessor — предшествующая активность"),
        ("Последователь", "Successor — последующая активность"),
        ("Выравнивание ресурсов", "Resource Leveling — балансировка потребности в ресурсах"),
        ("Базовый план", "Baseline — эталонная версия плана"),
    ),
}


def glossary_pairs(locale: str) -> tuple[tuple[str, str], ...]:
    return tuple(GLOSSARIES.get(locale, ()))


__all__ = ["GLOSSARIES", "glossary_pairs"]
