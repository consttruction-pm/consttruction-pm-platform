export type LandingChromeCopy = {
  nav: readonly [string, string, string, string, string, string];
  pricing: string;
  company: string;
  about: string;
  brandAria: string;
  brandAlt: string;
  dashboardAria: string;
  dashboardSidebar: readonly [string, string, string, string, string];
  dashboardTitle: string;
  projectLabel: string;
  progressTrend: string;
  schedule: string;
  onTrack: string;
  aiInsight: string;
  reviewNextMilestone: string;
  projectProgress: string;
  plan: string;
  actual: string;
  platformBlocks: string;
  planning: string;
  projectData: string;
  aiLabel: string;
  connectedCapabilities: string;
  copyright: string;
};

const CHROME: Readonly<Record<string, LandingChromeCopy>> = {
  en: {
    nav: ["Home", "Platform", "Solutions", "Resources", "About Us", "Contact"],
    pricing: "Pricing", company: "Company", about: "About Us",
    brandAria: "CUBI Platform home", brandAlt: "CUBI Platform — Plan. Control. Build Smarter.",
    dashboardAria: "Illustrative CUBI project dashboard showing schedule, progress and performance",
    dashboardSidebar: ["Overview", "Schedule", "Cost control", "Resources", "Documents"],
    dashboardTitle: "Project Control Center", projectLabel: "PROJECT",
    progressTrend: "Progress trend", schedule: "Schedule", onTrack: "On track",
    aiInsight: "AI insight", reviewNextMilestone: "Review next milestone",
    projectProgress: "Project progress", plan: "Plan", actual: "Actual",
    platformBlocks: "Platform building blocks", planning: "Planning", projectData: "Project data",
    aiLabel: "AI", connectedCapabilities: "Connected platform capabilities",
    copyright: "All rights reserved."
  },
  fa: {
    nav: ["خانه", "پلتفرم", "راهکارها", "منابع", "درباره ما", "تماس"],
    pricing: "قیمت‌گذاری", company: "شرکت", about: "درباره ما",
    brandAria: "صفحه اصلی پلتفرم کوبی", brandAlt: "پلتفرم کوبی — برنامه‌ریزی، کنترل، ساخت هوشمندتر",
    dashboardAria: "نمای نمونه داشبورد پروژه کوبی شامل زمان‌بندی، پیشرفت و عملکرد",
    dashboardSidebar: ["نمای کلی", "زمان‌بندی", "کنترل هزینه", "منابع", "اسناد"],
    dashboardTitle: "مرکز کنترل پروژه", projectLabel: "پروژه",
    progressTrend: "روند پیشرفت", schedule: "زمان‌بندی", onTrack: "طبق برنامه",
    aiInsight: "بینش هوشمند", reviewNextMilestone: "بررسی نقطه عطف بعدی",
    projectProgress: "پیشرفت پروژه", plan: "برنامه", actual: "واقعی",
    platformBlocks: "اجزای اصلی پلتفرم", planning: "برنامه‌ریزی", projectData: "داده‌های پروژه",
    aiLabel: "هوش مصنوعی", connectedCapabilities: "قابلیت‌های یکپارچه پلتفرم",
    copyright: "تمام حقوق محفوظ است."
  },
  de: {
    nav: ["Startseite", "Plattform", "Lösungen", "Ressourcen", "Über uns", "Kontakt"],
    pricing: "Preise", company: "Unternehmen", about: "Über uns",
    brandAria: "CUBI-Plattform Startseite", brandAlt: "CUBI Platform — Planen. Steuern. Besser bauen.",
    dashboardAria: "Beispiel-Dashboard von CUBI mit Terminplan, Fortschritt und Leistung",
    dashboardSidebar: ["Übersicht", "Terminplan", "Kostenkontrolle", "Ressourcen", "Dokumente"],
    dashboardTitle: "Projektsteuerungszentrum", projectLabel: "PROJEKT",
    progressTrend: "Fortschrittsverlauf", schedule: "Terminplan", onTrack: "Im Plan",
    aiInsight: "KI-Einblick", reviewNextMilestone: "Nächsten Meilenstein prüfen",
    projectProgress: "Projektfortschritt", plan: "Plan", actual: "Ist",
    platformBlocks: "Plattformbausteine", planning: "Planung", projectData: "Projektdaten",
    aiLabel: "KI", connectedCapabilities: "Verbundene Plattformfunktionen",
    copyright: "Alle Rechte vorbehalten."
  },
  fr: {
    nav: ["Accueil", "Plateforme", "Solutions", "Ressources", "À propos", "Contact"],
    pricing: "Tarifs", company: "Entreprise", about: "À propos",
    brandAria: "Accueil de la plateforme CUBI", brandAlt: "CUBI Platform — Planifier. Piloter. Construire plus intelligemment.",
    dashboardAria: "Tableau de bord CUBI illustratif présentant le planning, l’avancement et la performance",
    dashboardSidebar: ["Vue d’ensemble", "Planning", "Contrôle des coûts", "Ressources", "Documents"],
    dashboardTitle: "Centre de pilotage du projet", projectLabel: "PROJET",
    progressTrend: "Tendance d’avancement", schedule: "Planning", onTrack: "Dans les délais",
    aiInsight: "Analyse IA", reviewNextMilestone: "Examiner le prochain jalon",
    projectProgress: "Avancement du projet", plan: "Prévu", actual: "Réel",
    platformBlocks: "Composants de la plateforme", planning: "Planification", projectData: "Données du projet",
    aiLabel: "IA", connectedCapabilities: "Capacités connectées de la plateforme",
    copyright: "Tous droits réservés."
  },
  "zh-Hans": {
    nav: ["首页", "平台", "解决方案", "资源", "关于我们", "联系"],
    pricing: "价格", company: "公司", about: "关于我们",
    brandAria: "CUBI 平台首页", brandAlt: "CUBI 平台 — 规划、控制、更智慧地建设",
    dashboardAria: "CUBI 项目仪表板示意图，展示进度计划、项目进展和绩效",
    dashboardSidebar: ["总览", "进度计划", "成本控制", "资源", "文档"],
    dashboardTitle: "项目控制中心", projectLabel: "项目",
    progressTrend: "进展趋势", schedule: "进度计划", onTrack: "按计划进行",
    aiInsight: "智能分析", reviewNextMilestone: "检查下一个里程碑",
    projectProgress: "项目进展", plan: "计划", actual: "实际",
    platformBlocks: "平台核心组成", planning: "规划", projectData: "项目数据",
    aiLabel: "人工智能", connectedCapabilities: "互联的平台能力",
    copyright: "保留所有权利。"
  },
  "zh-Hant": {
    nav: ["首頁", "平台", "解決方案", "資源", "關於我們", "聯絡我們"],
    pricing: "價格", company: "公司", about: "關於我們",
    brandAria: "CUBI 平台首頁", brandAlt: "CUBI 平台 — 規劃、控制、更智慧地建設",
    dashboardAria: "CUBI 專案儀表板示意圖，展示進度計畫、專案進展與績效",
    dashboardSidebar: ["總覽", "進度計畫", "成本控制", "資源", "文件"],
    dashboardTitle: "專案控制中心", projectLabel: "專案",
    progressTrend: "進展趨勢", schedule: "進度計畫", onTrack: "按計畫進行",
    aiInsight: "智慧分析", reviewNextMilestone: "檢視下一個里程碑",
    projectProgress: "專案進展", plan: "計畫", actual: "實際",
    platformBlocks: "平台核心組成", planning: "規劃", projectData: "專案資料",
    aiLabel: "人工智慧", connectedCapabilities: "互聯的平台功能",
    copyright: "保留所有權利。"
  },
  ja: {
    nav: ["ホーム", "プラットフォーム", "ソリューション", "リソース", "会社情報", "お問い合わせ"],
    pricing: "料金", company: "会社情報", about: "会社情報",
    brandAria: "CUBI プラットフォームのホーム", brandAlt: "CUBI Platform — 計画し、管理し、よりスマートに建設する",
    dashboardAria: "工程、進捗、パフォーマンスを示す CUBI プロジェクトダッシュボードのイメージ",
    dashboardSidebar: ["概要", "工程", "コスト管理", "リソース", "ドキュメント"],
    dashboardTitle: "プロジェクト管理センター", projectLabel: "プロジェクト",
    progressTrend: "進捗推移", schedule: "工程", onTrack: "計画どおり",
    aiInsight: "AI 分析", reviewNextMilestone: "次のマイルストーンを確認",
    projectProgress: "プロジェクト進捗", plan: "計画", actual: "実績",
    platformBlocks: "プラットフォームの構成要素", planning: "計画", projectData: "プロジェクトデータ",
    aiLabel: "AI", connectedCapabilities: "連携されたプラットフォーム機能",
    copyright: "無断転載を禁じます。"
  },
  ko: {
    nav: ["홈", "플랫폼", "솔루션", "자료", "회사 소개", "문의"],
    pricing: "요금", company: "회사", about: "회사 소개",
    brandAria: "CUBI 플랫폼 홈", brandAlt: "CUBI 플랫폼 — 계획하고 관리하며 더 스마트하게 건설하세요",
    dashboardAria: "일정, 진척 및 성과를 보여주는 CUBI 프로젝트 대시보드 예시",
    dashboardSidebar: ["개요", "일정", "비용 관리", "자원", "문서"],
    dashboardTitle: "프로젝트 컨트롤 센터", projectLabel: "프로젝트",
    progressTrend: "진척 추이", schedule: "일정", onTrack: "계획대로 진행",
    aiInsight: "AI 인사이트", reviewNextMilestone: "다음 마일스톤 검토",
    projectProgress: "프로젝트 진척", plan: "계획", actual: "실적",
    platformBlocks: "플랫폼 구성 요소", planning: "계획", projectData: "프로젝트 데이터",
    aiLabel: "AI", connectedCapabilities: "연결된 플랫폼 기능",
    copyright: "모든 권리 보유."
  },
  ar: {
    nav: ["الرئيسية", "المنصة", "الحلول", "الموارد", "من نحن", "اتصل بنا"],
    pricing: "الأسعار", company: "الشركة", about: "من نحن",
    brandAria: "الصفحة الرئيسية لمنصة CUBI", brandAlt: "منصة CUBI — خطّط وتحكّم وابنِ بذكاء أكبر",
    dashboardAria: "لوحة مشروع توضيحية من CUBI تعرض الجدول والتقدم والأداء",
    dashboardSidebar: ["نظرة عامة", "الجدول", "مراقبة التكلفة", "الموارد", "المستندات"],
    dashboardTitle: "مركز التحكم بالمشروع", projectLabel: "المشروع",
    progressTrend: "اتجاه التقدم", schedule: "الجدول", onTrack: "وفق الخطة",
    aiInsight: "رؤية ذكية", reviewNextMilestone: "مراجعة المعلم الرئيسي التالي",
    projectProgress: "تقدم المشروع", plan: "المخطط", actual: "الفعلي",
    platformBlocks: "مكونات المنصة الأساسية", planning: "التخطيط", projectData: "بيانات المشروع",
    aiLabel: "الذكاء الاصطناعي", connectedCapabilities: "قدرات المنصة المترابطة",
    copyright: "جميع الحقوق محفوظة."
  },
  ru: {
    nav: ["Главная", "Платформа", "Решения", "Ресурсы", "О нас", "Контакты"],
    pricing: "Цены", company: "Компания", about: "О нас",
    brandAria: "Главная страница CUBI Platform", brandAlt: "CUBI Platform — Планируйте. Контролируйте. Стройте эффективнее.",
    dashboardAria: "Иллюстративная панель проекта CUBI: график, ход выполнения и показатели",
    dashboardSidebar: ["Обзор", "Расписание", "Контроль затрат", "Ресурсы", "Документы"],
    dashboardTitle: "Центр управления проектом", projectLabel: "ПРОЕКТ",
    progressTrend: "Динамика выполнения", schedule: "Расписание", onTrack: "По плану",
    aiInsight: "Аналитика ИИ", reviewNextMilestone: "Проверить следующий этап",
    projectProgress: "Ход выполнения проекта", plan: "План", actual: "Факт",
    platformBlocks: "Основные компоненты платформы", planning: "Планирование", projectData: "Данные проекта",
    aiLabel: "ИИ", connectedCapabilities: "Связанные возможности платформы",
    copyright: "Все права защищены."
  }
};

export function normalizeLandingLocaleTag(value: string): string {
  const normalized = value.trim().replace(/_/g, "-").toLowerCase();
  if (["zh", "zh-cn", "zh-sg", "zh-hans", "zh-hans-cn", "zh-hans-sg"].includes(normalized)) return "zh-Hans";
  if (["zh-tw", "zh-hk", "zh-mo", "zh-hant", "zh-hant-tw", "zh-hant-hk"].includes(normalized)) return "zh-Hant";
  if (normalized === "fa-ir") return "fa";
  if (normalized === "ar-sa" || normalized === "ar-ae" || normalized === "ar-eg") return "ar";
  return normalized.split("-")[0];
}

export function getLandingChromeCopy(locale: string): LandingChromeCopy {
  const normalized = normalizeLandingLocaleTag(locale);
  const copy = CHROME[normalized] ?? CHROME.en;
  return copy;
}
