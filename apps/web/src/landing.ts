type LandingLocale = string;
type Feature = { icon: string; title: string; body: string; assistantAvatar?: boolean };
type LandingCopy = {
  nav: string[]; eyebrow: string; title: string; accent: string; subtitle: string; body: string;
  primary: string; secondary: string; featuresEyebrow: string; featuresTitle: string; featuresBody: string; features: Feature[];
  techEyebrow: string; techTitle: string; techBody: string; techLink: string; techNodes: string[];
  industriesEyebrow: string; industriesTitle: string; industriesBody: string;
  ctaTitle: string; ctaBody: string; signIn: string; start: string; language: string;
  footerColumns: Array<{ title: string; links: string[] }>; footerNote: string;
  assistantTitle: string; assistantSubtitle: string; assistantDescription: string;
  assistantWorkspaceAction: string; assistantClose: string;
};
const copy: Partial<Record<LandingLocale, LandingCopy>> = {
  en: {
    nav: ["Home", "Platform", "Solutions", "Resources", "About Us", "Contact"],
    eyebrow: "CONSTRUCTION & BUILDING INTELLIGENCE",
    title: "Control every detail.", accent: "Build with confidence.",
    subtitle: "Plan. Control. Build Smarter.",
    body: "From buildings and infrastructure to oil, gas, petrochemical, energy and complex industrial facilities, CUBI connects project scope, schedules, progress, resources, cost and evidence in one disciplined project-controls environment. Give planners, cost engineers, site leaders and executives a clearer basis for the next decision.",
    primary: "Explore the Platform →", secondary: "See How It Works",
    featuresEyebrow: "ONE CONNECTED WORKFLOW",
    featuresTitle: "The information behind delivery, connected",
    featuresBody: "Bring plans, performance, people, records and decisions together across the project lifecycle—with clear ownership, traceable information and workflows shaped around the way your organization delivers work.",
    features: [
      { icon: "⌁", title: "Project Controls", body: "Track milestones, progress and performance signals in one project view." },
      { icon: "✧", assistantAvatar: true, title: "Engineering Intelligence", body: "Find relevant CUBI guidance, understand project context and prepare permission-aware next steps—with user approval before changes." },
      { icon: "↗", title: "Resources & Cost", body: "Connect resource plans, cost visibility and delivery performance." },
      { icon: "▤", title: "Documents & Contracts", body: "Keep project records and supporting evidence close to the workflow." },
      { icon: "◎", title: "Team Collaboration", body: "Give stakeholders a shared view of project status and actions." },
      { icon: "☁", title: "Cloud & Scalability", body: "Access a consistent project workspace as teams and projects grow." }
    ],
    techEyebrow: "BUILT FOR REAL PROJECTS",
    techTitle: "A connected foundation for better decisions",
    techBody: "CUBI connects project definition, WBS, activity networks, calendars, baselines, progress, resource and cost visibility, controlled documents, reporting and guided engineering assistance. Authoritative project services—not an assistant guess—remain the source of calculations and schedule outcomes.",
    techLink: "Explore platform capabilities →",
    techNodes: ["Project controls", "Engineering guidance", "Connected data", "Governed workflow"],
    industriesEyebrow: "FROM CIVIL WORKS TO COMPLEX PROCESS FACILITIES",
    industriesTitle: "One project-controls foundation. Many industries.",
    industriesBody: "CUBI is designed for building and infrastructure programs, oil and gas developments, pipelines, refineries, petrochemical facilities, power and utility projects, industrial plants and EPC delivery. Adapt project structures, calendars, roles and reporting to the work—not the other way around.",
    ctaTitle: "Bring your project into focus.",
    ctaBody: "Start with one connected view of schedules, costs, progress and decisions.",
    assistantTitle: "CUBI Engineering Intelligence Assistant",
    assistantSubtitle: "Project guidance, one step away",
    assistantDescription: "Find relevant product guidance and project-context support inside your workspace. Answers must respect your permissions, disclose knowledge gaps and request your approval before changing project records.",
    assistantWorkspaceAction: "Open project workspace →",
    assistantClose: "Close assistant panel",
    signIn: "Sign In", start: "Get Started", language: "فارسی",
    footerColumns: [
      { title: "Platform", links: ["Project Controls", "Planning & Scheduling", "Resources & Cost"] },
      { title: "Solutions", links: ["Construction Teams", "Project Leadership", "Project Delivery"] },
      { title: "Resources", links: ["Documentation", "Product Overview", "Contact"] }
    ],
    footerNote: "Plan. Control. Build Smarter."
  },
  fa: {
    nav: ["خانه", "پلتفرم", "راهکارها", "منابع", "درباره ما", "تماس"],
    eyebrow: "هوشمندی ساخت و مدیریت پروژه",
    title: "جزئیات را کنترل کنید؛", accent: "با اطمینان بسازید.",
    subtitle: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.",
    body: "از پروژه‌های ساختمانی و زیرساختی تا طرح‌های نفت، گاز، پتروشیمی، انرژی و تأسیسات صنعتی پیچیده، کوبی اطلاعات محدوده کار، ساختار شکست، زمان‌بندی، پیشرفت، منابع، هزینه و مستندات را در یک محیط منسجم کنترل پروژه به هم پیوند می‌دهد. از مهندسان برنامه‌ریزی و کنترل هزینه تا مدیران پروژه، مدیران کارگاه و مدیران ارشد، هر عضو تیم می‌تواند تصویر روشن‌تری از وضعیت کار و مبنای دقیق‌تری برای تصمیم بعدی داشته باشد.",
    primary: "کاوش پلتفرم ←", secondary: "نحوه کار را ببینید",
    featuresEyebrow: "جریان کاری یکپارچه",
    featuresTitle: "اطلاعات پشت اجرای پروژه، در یک جریان یکپارچه",
    featuresBody: "برنامه‌ها، عملکرد، افراد، سوابق و تصمیم‌ها را در چرخه عمر پروژه کنار هم قرار دهید؛ با مسئولیت‌پذیری روشن، اطلاعات قابل ردیابی و گردش کاری متناسب با روش اجرای سازمان شما.",
    features: [
      { icon: "⌁", title: "کنترل پروژه", body: "نقاط عطف، پیشرفت و شاخص‌های عملکرد را در یک نمای پروژه دنبال کنید." },
      { icon: "✧", assistantAvatar: true, title: "هوشمندی مهندسی و راهنمای هوشمند", body: "راهنمای مرتبط کوبی را پیدا کنید، اطلاعات پروژه را بهتر درک کنید و گام‌های بعدی را با رعایت سطح دسترسی و تأیید کاربر آماده سازید." },
      { icon: "↗", title: "منابع و هزینه", body: "برنامه منابع، شفافیت هزینه و عملکرد اجرا را به هم متصل کنید." },
      { icon: "▤", title: "اسناد و قراردادها", body: "سوابق و شواهد پشتیبان پروژه را در کنار جریان کار نگه دارید." },
      { icon: "◎", title: "همکاری تیمی", body: "نمای مشترک و روشنی از وضعیت پروژه و اقدامات در اختیار ذی‌نفعان قرار دهید." },
      { icon: "☁", title: "ابر و توسعه‌پذیری", body: "با رشد تیم‌ها و پروژه‌ها به فضای کاری یکپارچه دسترسی داشته باشید." }
    ],
    techEyebrow: "برای پروژه‌های واقعی",
    techTitle: "زیرساختی یکپارچه برای تصمیم‌های بهتر",
    techBody: "کوبی تعریف پروژه، ساختار شکست کار، شبکه فعالیت‌ها، تقویم‌ها، مبناها، پیشرفت، اطلاعات منابع و هزینه، اسناد کنترل‌شده، گزارش‌ها و راهنمایی مهندسی را به هم متصل می‌کند. محاسبات و نتایج زمان‌بندی باید از سرویس‌های معتبر پروژه به دست آیند، نه از حدس دستیار.",
    techLink: "مشاهده قابلیت‌های پلتفرم ←",
    techNodes: ["کنترل پروژه", "راهنمای مهندسی", "داده یکپارچه", "گردش کار کنترل‌شده"],
    industriesEyebrow: "از پروژه‌های عمرانی تا تأسیسات فرایندی پیچیده",
    industriesTitle: "یک بنیان کنترل پروژه؛ برای صنایع گوناگون",
    industriesBody: "کوبی برای پروژه‌های ساختمانی و زیرساختی، طرح‌های نفت و گاز، خطوط لوله، پالایشگاه‌ها، مجتمع‌های پتروشیمی، نیروگاه‌ها، خدمات عمومی، کارخانه‌های صنعتی و پروژه‌های EPC طراحی شده است. ساختار پروژه، تقویم، نقش‌ها و گزارش‌ها را با ماهیت کار هماهنگ کنید، نه برعکس.",
    ctaTitle: "تصویر روشنی از پروژه بسازید.",
    ctaBody: "با نمایی یکپارچه از زمان‌بندی، هزینه، پیشرفت و تصمیم‌ها شروع کنید.",
    assistantTitle: "دستیار هوشمندی مهندسی کوبی",
    assistantSubtitle: "راهنمای پروژه، یک گام با شما فاصله دارد",
    assistantDescription: "راهنمای محصول و پشتیبانی متناسب با اطلاعات پروژه را در فضای کاری پیدا کنید. پاسخ‌ها باید سطح دسترسی را رعایت کنند، کمبود دانش را آشکار سازند و پیش از تغییر سوابق پروژه تأیید شما را بگیرند.",
    assistantWorkspaceAction: "ورود به فضای کاری پروژه ←",
    assistantClose: "بستن پنل دستیار",
    signIn: "ورود", start: "شروع کنید", language: "EN",
    footerColumns: [
      { title: "پلتفرم", links: ["کنترل پروژه", "برنامه‌ریزی و زمان‌بندی", "منابع و هزینه"] },
      { title: "راهکارها", links: ["تیم‌های ساخت", "مدیریت پروژه", "تحویل پروژه"] },
      { title: "منابع", links: ["مستندات", "معرفی محصول", "تماس"] }
    ],
    footerNote: "برنامه‌ریزی. کنترل. ساخت هوشمندتر."
  },
  de: {
    nav:["Startseite","Plattform","Lösungen","Ressourcen","Kontakt"], eyebrow:"PROJEKTSTEUERUNG FÜR BAU, INFRASTRUKTUR UND INDUSTRIE",
    title:"Jedes Projektdetail im Blick.", accent:"Mit Sicherheit liefern.", subtitle:"Planen. Steuern. Besser bauen.",
    body:"Von Gebäuden und Infrastruktur bis zu Öl, Gas, Petrochemie, Energie und komplexen Industrieanlagen verbindet CUBI Projektumfang, Termine, Fortschritt, Ressourcen, Kosten und Nachweise in einer strukturierten Projektsteuerungsumgebung.",
    primary:"CUBI-Plattform entdecken →", secondary:"So funktioniert CUBI",
    featuresEyebrow:"EINE VERBUNDENE PROJEKTUMGEBUNG",featuresTitle:"Alle Informationen für eine verlässliche Projektabwicklung",featuresBody:"Verbinden Sie Planung, Leistung, Teams, Dokumente und Entscheidungen über den gesamten Projektlebenszyklus hinweg.",
    features:[
      {icon:"⌁",title:"Projektplanung & Terminsteuerung",body:"Strukturieren Sie den Leistungsumfang, Aktivitäten, Kalender, Verknüpfungen, Baselines und Terminfortschritt."},
      {icon:"✧",assistantAvatar:true,title:"Engineering Intelligence",body:"Finden Sie passende CUBI-Anleitungen und bereiten Sie kontextbezogene nächste Schritte vor – mit Berechtigungsprüfung und Freigabe."},
      {icon:"↗",title:"Ressourcen & Kosten",body:"Schaffen Sie Transparenz über Ressourcenbedarf, Zuordnungen, Budgets und Kostenentwicklung."},
      {icon:"▤",title:"Dokumente & Verträge",body:"Halten Sie Versionen, Projektunterlagen, Vertragskontext und Nachweise mit der Arbeit verknüpft."},
      {icon:"◎",title:"Team- und Baustellenkoordination",body:"Verbinden Sie Projektteams, Baustelleninformationen, offene Punkte und Entscheidungen."},
      {icon:"☁",title:"Berichte & Zusammenarbeit",body:"Arbeiten Sie mit nachvollziehbaren Projektinformationen, geregelten Rollen und gemeinsamen Berichten."}
    ],
    techEyebrow:"FÜR KOMPLEXE PROJEKTE ENTWICKELT",techTitle:"Eine vernetzte Grundlage für bessere Entscheidungen",
    techBody:"CUBI verbindet Projektdefinition, PSP, Vorgangsnetze, Kalender, Baselines, Fortschritt, Ressourcen- und Kostenübersicht, kontrollierte Dokumente und Berichte. Berechnungen und Terminresultate stammen aus maßgeblichen Projektdiensten – nicht aus Vermutungen eines Assistenten.",
    techLink:"Plattformfunktionen entdecken →",techNodes:["Projektsteuerung","Engineering-Leitfaden","Verbundene Daten","Geregelte Abläufe"],
    industriesEyebrow:"VOM TIEFBAU BIS ZUR PROZESSINDUSTRIE",industriesTitle:"Eine Projektsteuerungsbasis. Viele Branchen.",
    industriesBody:"CUBI ist für Hochbau und Infrastruktur, Öl- und Gasprojekte, Pipelines, Raffinerien, petrochemische Anlagen, Kraftwerke, Versorgungsunternehmen, Industrieanlagen und EPC-Projekte konzipiert. Passen Sie Projektstrukturen, Kalender, Rollen und Berichte an Ihre Aufgaben an.",
    ctaTitle:"Treffen Sie Ihre nächste Projektentscheidung mit Klarheit.",ctaBody:"Verbinden Sie Planung, Menschen, Zahlen und Nachweise über den gesamten Projektlebenszyklus.",
    assistantTitle:"CUBI Engineering Intelligence Assistant",assistantSubtitle:"Projektorientierte Unterstützung – direkt verfügbar",
    assistantDescription:"Finden Sie Produktanleitungen und Unterstützung im Projektkontext. Antworten müssen Berechtigungen beachten, Wissenslücken offenlegen und vor Änderungen an Projektdaten Ihre Freigabe einholen.",
    assistantWorkspaceAction:"Projektarbeitsbereich öffnen →",assistantClose:"Assistent schließen",signIn:"Anmelden",start:"Jetzt starten",language:"فارسی",
    footerColumns:[{title:"Plattform",links:["Projektsteuerung","Planung & Terminierung","Ressourcen & Kosten"]},{title:"Lösungen",links:["Bauteams","Projektleitung","Projektausführung"]},{title:"Ressourcen",links:["Dokumentation","Produktübersicht","Kontakt"]}],footerNote:"Planen. Steuern. Besser bauen."
  },
  fr: {
    nav:["Accueil","Plateforme","Solutions","Ressources","Contact"],eyebrow:"PILOTAGE DE PROJETS POUR LE BÂTIMENT, LES INFRASTRUCTURES ET L’INDUSTRIE",
    title:"Gardez chaque détail du projet en vue.",accent:"Livrez en toute confiance.",subtitle:"Planifier. Piloter. Construire plus intelligemment.",
    body:"Des bâtiments et infrastructures aux projets pétroliers, gaziers, pétrochimiques, énergétiques et industriels complexes, CUBI relie le périmètre, les plannings, l’avancement, les ressources, les coûts et les justificatifs dans un environnement structuré de pilotage de projet.",
    primary:"Découvrir la plateforme CUBI →",secondary:"Découvrir le fonctionnement",
    featuresEyebrow:"UN ENVIRONNEMENT DE PROJET CONNECTÉ",featuresTitle:"Les informations essentielles à la bonne réalisation des projets",featuresBody:"Reliez les plans, la performance, les équipes, les documents et les décisions tout au long du cycle de vie du projet.",
    features:[
      {icon:"⌁",title:"Planification & ordonnancement",body:"Structurez le périmètre, les activités, les calendriers, les liens logiques, les références et l’avancement."},
      {icon:"✧",assistantAvatar:true,title:"Intelligence d’ingénierie",body:"Trouvez les guides CUBI pertinents et préparez les prochaines étapes selon le contexte, les droits et votre validation."},
      {icon:"↗",title:"Ressources & coûts",body:"Améliorez la visibilité sur les besoins en ressources, les affectations, les budgets et les coûts."},
      {icon:"▤",title:"Documents & contrats",body:"Reliez les versions, dossiers, éléments contractuels et preuves aux activités concernées."},
      {icon:"◎",title:"Coordination des équipes",body:"Rapprochez les équipes projet, les informations de chantier, les points ouverts et les décisions."},
      {icon:"☁",title:"Rapports & collaboration",body:"Partagez des informations traçables avec des rôles, des validations et des rapports structurés."}
    ],
    techEyebrow:"CONÇU POUR LES PROJETS COMPLEXES",techTitle:"Une base connectée pour mieux décider",
    techBody:"CUBI relie la définition du projet, la structure de découpage, les réseaux d’activités, les calendriers, les références, l’avancement, la visibilité des ressources et des coûts, les documents contrôlés et les rapports. Les calculs et résultats d’ordonnancement proviennent des services projet de référence, jamais d’une supposition de l’assistant.",
    techLink:"Explorer les capacités de la plateforme →",techNodes:["Pilotage de projet","Guide d’ingénierie","Données connectées","Processus gouverné"],
    industriesEyebrow:"DU GÉNIE CIVIL AUX INSTALLATIONS DE PROCÉDÉ",industriesTitle:"Un socle de pilotage. De nombreux secteurs.",
    industriesBody:"CUBI est conçu pour le bâtiment et les infrastructures, le pétrole et le gaz, les pipelines, les raffineries, la pétrochimie, les centrales, les réseaux de services, les sites industriels et les projets EPC. Adaptez structures, calendriers, rôles et rapports à la réalité du projet.",
    ctaTitle:"Prenez votre prochaine décision avec une vision plus claire.",ctaBody:"Reliez le planning, les équipes, les chiffres et les justificatifs pendant tout le cycle de vie du projet.",
    assistantTitle:"Assistant d’intelligence d’ingénierie CUBI",assistantSubtitle:"Un accompagnement projet à portée de main",
    assistantDescription:"Trouvez des guides produit et une aide liée au contexte du projet. Les réponses respectent les autorisations, signalent les lacunes de connaissance et demandent votre validation avant toute modification.",
    assistantWorkspaceAction:"Ouvrir l’espace projet →",assistantClose:"Fermer l’assistant",signIn:"Se connecter",start:"Commencer",language:"فارسی",
    footerColumns:[{title:"Plateforme",links:["Pilotage de projet","Planification & ordonnancement","Ressources & coûts"]},{title:"Solutions",links:["Équipes de construction","Direction de projet","Réalisation de projet"]},{title:"Ressources",links:["Documentation","Présentation du produit","Contact"]}],footerNote:"Planifier. Piloter. Construire plus intelligemment."
  },
  zh: {
    nav:["首页","平台","解决方案","资源","联系"],eyebrow:"面向建筑、基础设施与工业领域的项目控制",
    title:"全面掌握项目每个细节。",accent:"自信交付。",subtitle:"规划 · 控制 · 更智慧地建设",
    body:"从建筑和基础设施，到油气、石化、能源及复杂工业设施，CUBI 将项目范围、进度计划、实际进展、资源、成本和项目凭证整合到统一、规范的项目控制环境中。",
    primary:"探索 CUBI 平台 →",secondary:"了解 CUBI 如何工作",
    featuresEyebrow:"统一互联的项目环境",featuresTitle:"连接项目交付所需的关键信息",featuresBody:"在项目全生命周期中连接计划、绩效、团队、文档与决策，并保持责任清晰、信息可追溯。",
    features:[
      {icon:"⌁",title:"项目规划与进度管理",body:"组织项目范围、工作分解结构、活动、日历、逻辑关系、基准计划和进度更新。"},
      {icon:"✧",assistantAvatar:true,title:"工程智能助手",body:"查找相关 CUBI 指南并结合项目上下文准备后续步骤；严格遵循权限并在修改前征求确认。"},
      {icon:"↗",title:"资源与成本",body:"提升对资源需求、分配、预算和成本表现的可视性。"},
      {icon:"▤",title:"文档与合同",body:"将受控版本、项目记录、合同信息和支持凭证关联到相关工作。"},
      {icon:"◎",title:"团队与现场协同",body:"连接项目团队、现场信息、待处理事项和管理决策。"},
      {icon:"☁",title:"报告与协作",body:"基于可追溯的项目数据、角色权限和规范流程开展协作。"}
    ],
    techEyebrow:"为复杂项目而构建",techTitle:"支持更好决策的互联基础",
    techBody:"CUBI 连接项目定义、工作分解结构、活动网络、日历、基准计划、进度、资源与成本信息、受控文档和报告。计算结果与进度日期由权威项目服务提供，而不是由助手猜测。",
    techLink:"查看平台能力 →",techNodes:["项目控制","工程指南","互联数据","受控流程"],
    industriesEyebrow:"从土木工程到复杂流程设施",industriesTitle:"统一的项目控制基础，服务多种行业。",
    industriesBody:"CUBI 面向建筑与基础设施、油气开发、管道、炼油厂、石化设施、电力与公用事业、工业厂房及 EPC 项目。让项目结构、日历、角色和报告适应实际工作需求。",
    ctaTitle:"以更清晰的项目全景做出下一项决策。",ctaBody:"在项目全生命周期中连接计划、人员、数据和凭证。",
    assistantTitle:"CUBI 工程智能助手",assistantSubtitle:"项目指导，触手可及",
    assistantDescription:"在工作空间中查找产品指南和项目上下文支持。回答必须遵守访问权限、说明知识缺口，并在更改项目记录前获得用户批准。",
    assistantWorkspaceAction:"打开项目工作空间 →",assistantClose:"关闭助手",signIn:"登录",start:"立即开始",language:"فارسی",
    footerColumns:[{title:"平台",links:["项目控制","规划与进度管理","资源与成本"]},{title:"解决方案",links:["施工团队","项目领导","项目交付"]},{title:"资源",links:["文档","产品概览","联系"]}],footerNote:"规划 · 控制 · 更智慧地建设"
  },
  ja: {
    nav:["ホーム","プラットフォーム","ソリューション","リソース","お問い合わせ"],eyebrow:"建設・インフラ・産業プロジェクトのプロジェクトコントロール",
    title:"プロジェクトの細部まで見える化。",accent:"確かな遂行へ。",subtitle:"計画する。管理する。よりスマートに建設する。",
    body:"建築・インフラから石油・ガス、石油化学、エネルギー、複雑な産業施設まで、CUBI はプロジェクト範囲、工程、進捗、リソース、コスト、証跡を統合されたプロジェクト管理環境につなぎます。",
    primary:"CUBI プラットフォームを見る →",secondary:"CUBI の仕組みを見る",
    featuresEyebrow:"つながるプロジェクト環境",featuresTitle:"プロジェクト遂行に必要な情報を一つに",featuresBody:"プロジェクトライフサイクル全体で計画、実績、チーム、文書、意思決定をつなぎ、責任と情報の追跡可能性を明確にします。",
    features:[
      {icon:"⌁",title:"プロジェクト計画・工程管理",body:"スコープ、WBS、アクティビティ、カレンダー、ロジック、ベースライン、進捗更新を管理します。"},
      {icon:"✧",assistantAvatar:true,title:"エンジニアリング・インテリジェンス",body:"適切な CUBI ガイドを検索し、権限を守りながら次の対応案を準備します。データ変更には利用者の承認が必要です。"},
      {icon:"↗",title:"リソース・コスト",body:"リソース需要、割当、予算、コスト実績の可視性を高めます。"},
      {icon:"▤",title:"文書・契約",body:"管理された版、プロジェクト記録、契約情報、根拠資料を関連作業に結び付けます。"},
      {icon:"◎",title:"チーム・現場連携",body:"プロジェクトチーム、現場情報、課題、意思決定をつなぎます。"},
      {icon:"☁",title:"レポート・コラボレーション",body:"追跡可能なプロジェクト情報と明確な権限・承認フローで協働します。"}
    ],
    techEyebrow:"複雑なプロジェクトのために",techTitle:"より良い意思決定を支える統合基盤",
    techBody:"CUBI はプロジェクト定義、WBS、アクティビティネットワーク、カレンダー、ベースライン、進捗、リソース・コスト情報、管理文書、レポートを連携します。計算と工程結果は正式なプロジェクトサービスを根拠とし、アシスタントの推測には依存しません。",
    techLink:"プラットフォーム機能を見る →",techNodes:["プロジェクト管理","技術ガイド","連携データ","統制された業務"],
    industriesEyebrow:"土木工事から複雑なプロセス設備まで",industriesTitle:"一つのプロジェクト管理基盤を多様な産業へ。",
    industriesBody:"CUBI は建築・インフラ、石油・ガス開発、パイプライン、製油所、石油化学設備、発電・公益事業、産業プラント、EPC プロジェクトを想定しています。構造、カレンダー、役割、レポートを実際の業務に合わせて設定できます。",
    ctaTitle:"次のプロジェクト判断を、より明確な情報で。",ctaBody:"計画、人、数値、証跡をプロジェクトライフサイクル全体でつなぎます。",
    assistantTitle:"CUBI エンジニアリング・インテリジェンス・アシスタント",assistantSubtitle:"プロジェクト支援をすぐそばに",
    assistantDescription:"製品ガイドとプロジェクト状況に沿った支援を利用できます。回答は権限を尊重し、知識不足を明示し、記録変更前に承認を求めます。",
    assistantWorkspaceAction:"プロジェクトワークスペースを開く →",assistantClose:"アシスタントを閉じる",signIn:"ログイン",start:"利用を開始",language:"فارسی",
    footerColumns:[{title:"プラットフォーム",links:["プロジェクト管理","計画・工程管理","リソース・コスト"]},{title:"ソリューション",links:["建設チーム","プロジェクト責任者","プロジェクト遂行"]},{title:"リソース",links:["ドキュメント","製品概要","お問い合わせ"]}],footerNote:"計画する。管理する。よりスマートに建設する。"
  },
  ko: {
    nav:["홈","플랫폼","솔루션","자료","문의"],eyebrow:"건설·인프라·산업 프로젝트를 위한 프로젝트 컨트롤",
    title:"프로젝트의 모든 세부사항을 한눈에.",accent:"확신 있게 완수하세요.",subtitle:"계획하고, 관리하고, 더 스마트하게 건설하세요.",
    body:"건축과 인프라부터 석유·가스, 석유화학, 에너지 및 복합 산업시설까지 CUBI는 프로젝트 범위, 일정, 진척, 자원, 비용과 증빙을 하나의 체계적인 프로젝트 관리 환경으로 연결합니다.",
    primary:"CUBI 플랫폼 살펴보기 →",secondary:"CUBI 작동 방식",
    featuresEyebrow:"연결된 프로젝트 환경",featuresTitle:"프로젝트 수행에 필요한 핵심 정보를 하나로",featuresBody:"프로젝트 전 주기에 걸쳐 계획, 성과, 팀, 문서와 의사결정을 연결하고 책임과 정보 추적성을 명확히 합니다.",
    features:[
      {icon:"⌁",title:"프로젝트 계획 및 일정관리",body:"범위, WBS, 활동, 달력, 논리관계, 기준선과 일정 업데이트를 관리합니다."},
      {icon:"✧",assistantAvatar:true,title:"엔지니어링 인텔리전스",body:"관련 CUBI 가이드를 찾고 권한을 준수하며 다음 조치를 준비합니다. 기록 변경 전 사용자 승인이 필요합니다."},
      {icon:"↗",title:"자원 및 비용",body:"자원 수요, 배정, 예산과 비용 성과를 더 명확하게 파악합니다."},
      {icon:"▤",title:"문서 및 계약",body:"관리되는 버전, 프로젝트 기록, 계약 정보와 증빙을 관련 업무에 연결합니다."},
      {icon:"◎",title:"팀 및 현장 협업",body:"프로젝트 팀, 현장 정보, 이슈와 의사결정을 연결합니다."},
      {icon:"☁",title:"보고 및 협업",body:"추적 가능한 프로젝트 정보와 명확한 권한·검토 절차를 바탕으로 협업합니다."}
    ],
    techEyebrow:"복잡한 프로젝트를 위해 설계",techTitle:"더 나은 의사결정을 위한 연결 기반",
    techBody:"CUBI는 프로젝트 정의, WBS, 활동 네트워크, 달력, 기준선, 진척, 자원·비용 정보, 통제 문서와 보고를 연결합니다. 계산과 일정 결과는 공식 프로젝트 서비스에서 제공하며 어시스턴트의 추측에 의존하지 않습니다.",
    techLink:"플랫폼 기능 보기 →",techNodes:["프로젝트 컨트롤","엔지니어링 가이드","연결된 데이터","통제된 업무 흐름"],
    industriesEyebrow:"토목 공사부터 복합 공정 설비까지",industriesTitle:"하나의 프로젝트 컨트롤 기반, 다양한 산업에.",
    industriesBody:"CUBI는 건설·인프라, 석유·가스 개발, 파이프라인, 정유소, 석유화학 시설, 발전 및 유틸리티, 산업 플랜트와 EPC 프로젝트를 위해 설계되었습니다. 프로젝트 구조, 달력, 역할과 보고를 실제 업무에 맞게 조정하세요.",
    ctaTitle:"더 명확한 정보로 다음 프로젝트 결정을 내리세요.",ctaBody:"프로젝트 전 주기에 걸쳐 계획, 인력, 수치와 증빙을 연결합니다.",
    assistantTitle:"CUBI 엔지니어링 인텔리전스 어시스턴트",assistantSubtitle:"프로젝트 가이드를 가까이에서",
    assistantDescription:"제품 가이드와 프로젝트 맥락에 맞는 지원을 이용하세요. 답변은 권한을 준수하고 지식의 공백을 밝히며 프로젝트 기록을 변경하기 전에 승인을 요청해야 합니다.",
    assistantWorkspaceAction:"프로젝트 작업공간 열기 →",assistantClose:"어시스턴트 닫기",signIn:"로그인",start:"시작하기",language:"فارسی",
    footerColumns:[{title:"플랫폼",links:["프로젝트 컨트롤","계획 및 일정관리","자원 및 비용"]},{title:"솔루션",links:["건설팀","프로젝트 리더십","프로젝트 수행"]},{title:"자료",links:["문서","제품 개요","문의"]}],footerNote:"계획하고, 관리하고, 더 스마트하게 건설하세요."
  },
  ru: {
    nav:["Главная","Платформа","Решения","Ресурсы","Контакты"],eyebrow:"УПРАВЛЕНИЕ ПРОЕКТАМИ В СТРОИТЕЛЬСТВЕ, ИНФРАСТРУКТУРЕ И ПРОМЫШЛЕННОСТИ",
    title:"Каждая деталь проекта — под контролем.",accent:"Уверенная реализация.",subtitle:"Планируйте. Контролируйте. Стройте умнее.",
    body:"От зданий и инфраструктуры до нефтегазовых, нефтехимических, энергетических и сложных промышленных объектов — CUBI объединяет объем работ, графики, ход выполнения, ресурсы, затраты и подтверждающие документы в единой дисциплинированной среде управления проектами.",
    primary:"Изучить платформу CUBI →",secondary:"Как работает CUBI",
    featuresEyebrow:"ЕДИНАЯ СВЯЗАННАЯ СРЕДА ПРОЕКТА",featuresTitle:"Ключевая информация для надежной реализации проекта",featuresBody:"Объединяйте планы, результаты, команды, документы и решения на протяжении всего жизненного цикла проекта.",
    features:[
      {icon:"⌁",title:"Планирование и календарное управление",body:"Структурируйте объем работ, WBS, операции, календари, логические связи, базовые планы и обновления графика."},
      {icon:"✧",assistantAvatar:true,title:"Инженерная интеллектуальная поддержка",body:"Находите подходящие руководства CUBI и готовьте следующие шаги с учетом прав доступа и обязательного подтверждения пользователя."},
      {icon:"↗",title:"Ресурсы и затраты",body:"Повышайте прозрачность потребности в ресурсах, назначений, бюджетов и динамики затрат."},
      {icon:"▤",title:"Документы и договоры",body:"Связывайте версии, проектные записи, договорную информацию и подтверждающие материалы с работами."},
      {icon:"◎",title:"Командная и площадочная координация",body:"Объединяйте проектные команды, данные площадки, открытые вопросы и решения."},
      {icon:"☁",title:"Отчетность и взаимодействие",body:"Работайте с прослеживаемыми данными, ролевым доступом и контролируемыми процессами."}
    ],
    techEyebrow:"ДЛЯ СЛОЖНЫХ ПРОЕКТОВ",techTitle:"Связанная основа для более обоснованных решений",
    techBody:"CUBI объединяет определение проекта, WBS, сети операций, календари, базовые планы, прогресс, сведения о ресурсах и затратах, контролируемые документы и отчеты. Расчеты и результаты календарного планирования формируются авторитетными проектными сервисами, а не предположениями помощника.",
    techLink:"Возможности платформы →",techNodes:["Управление проектом","Инженерное руководство","Связанные данные","Контролируемый процесс"],
    industriesEyebrow:"ОТ ГРАЖДАНСКОГО СТРОИТЕЛЬСТВА ДО СЛОЖНЫХ ТЕХНОЛОГИЧЕСКИХ ОБЪЕКТОВ",industriesTitle:"Единая основа управления проектами для разных отраслей.",
    industriesBody:"CUBI предназначена для строительства и инфраструктуры, нефтегазовых разработок, трубопроводов, НПЗ, нефтехимических комплексов, энергетики, коммунальных объектов, промышленных предприятий и EPC-проектов. Настраивайте структуры, календари, роли и отчеты под реальные задачи.",
    ctaTitle:"Принимайте следующие проектные решения, опираясь на ясную картину.",ctaBody:"Свяжите план, команды, показатели и подтверждающие материалы на всем жизненном цикле проекта.",
    assistantTitle:"Инженерный интеллектуальный помощник CUBI",assistantSubtitle:"Поддержка проекта — в одном шаге",
    assistantDescription:"Используйте руководства по продукту и помощь с учетом контекста проекта. Ответы должны учитывать права доступа, обозначать пробелы в знаниях и запрашивать подтверждение перед изменением проектных записей.",
    assistantWorkspaceAction:"Открыть рабочее пространство проекта →",assistantClose:"Закрыть помощника",signIn:"Войти",start:"Начать",language:"فارسی",
    footerColumns:[{title:"Платформа",links:["Управление проектом","Планирование и графики","Ресурсы и затраты"]},{title:"Решения",links:["Строительные команды","Руководство проектом","Реализация проекта"]},{title:"Ресурсы",links:["Документация","Обзор продукта","Контакты"]}],footerNote:"Планируйте. Контролируйте. Стройте умнее."
  },
  ar: {
    nav:["الرئيسية","المنصة","الحلول","الموارد","اتصل بنا"],eyebrow:"إدارة المشاريع لقطاعات البناء والبنية التحتية والصناعة",
    title:"اجعل كل تفاصيل المشروع واضحة.",accent:"ونفّذ بثقة.",subtitle:"خطّط. تحكّم. ابنِ بذكاء أكبر.",
    body:"من المباني والبنية التحتية إلى مشاريع النفط والغاز والبتروكيماويات والطاقة والمنشآت الصناعية المعقدة، تربط CUBI نطاق العمل والجداول والتقدم والموارد والتكاليف والأدلة ضمن بيئة منضبطة لإدارة المشاريع والتحكم بها.",
    primary:"استكشف منصة CUBI →",secondary:"تعرّف على طريقة العمل",
    featuresEyebrow:"بيئة مشروع مترابطة",featuresTitle:"المعلومات الأساسية لإنجاز المشروع بثقة",featuresBody:"اربط الخطط والأداء والفرق والوثائق والقرارات طوال دورة حياة المشروع، مع وضوح المسؤوليات وإمكانية تتبع المعلومات.",
    features:[
      {icon:"⌁",title:"تخطيط المشاريع والجدولة",body:"نظّم نطاق العمل وهيكل تقسيم العمل والأنشطة والتقاويم والعلاقات المنطقية والخطوط الأساسية وتحديثات الجدول."},
      {icon:"✧",assistantAvatar:true,title:"الذكاء الهندسي والإرشاد",body:"اعثر على إرشادات CUBI المناسبة وجهّز الخطوات التالية وفق الصلاحيات، مع طلب موافقة المستخدم قبل التغيير."},
      {icon:"↗",title:"الموارد والتكاليف",body:"عزّز وضوح احتياجات الموارد والتخصيصات والميزانيات وأداء التكلفة."},
      {icon:"▤",title:"الوثائق والعقود",body:"اربط الإصدارات والسجلات ومعلومات العقود والأدلة بالأعمال ذات الصلة."},
      {icon:"◎",title:"تنسيق الفرق والمواقع",body:"اربط فرق المشروع ومعلومات الموقع والمسائل المفتوحة والقرارات."},
      {icon:"☁",title:"التقارير والتعاون",body:"تعاون باستخدام معلومات مشروع قابلة للتتبع وأدوار واضحة وإجراءات مراجعة منضبطة."}
    ],
    techEyebrow:"مصممة للمشاريع المعقدة",techTitle:"أساس مترابط لاتخاذ قرارات أفضل",
    techBody:"تربط CUBI تعريف المشروع وهيكل تقسيم العمل وشبكات الأنشطة والتقاويم والخطوط الأساسية والتقدم ومعلومات الموارد والتكاليف والوثائق المضبوطة والتقارير. تصدر الحسابات ونتائج الجدولة عن خدمات المشروع المعتمدة، لا عن تخمين المساعد.",
    techLink:"استكشف إمكانات المنصة →",techNodes:["التحكم بالمشروع","الإرشاد الهندسي","بيانات مترابطة","سير عمل محكوم"],
    industriesEyebrow:"من الأعمال المدنية إلى المنشآت الصناعية المعقدة",industriesTitle:"أساس واحد للتحكم بالمشاريع عبر قطاعات متعددة.",
    industriesBody:"صُممت CUBI لمشاريع المباني والبنية التحتية والنفط والغاز وخطوط الأنابيب والمصافي ومجمعات البتروكيماويات ومحطات الطاقة والمرافق والمنشآت الصناعية ومشاريع EPC. خصّص هياكل المشاريع والتقاويم والأدوار والتقارير وفق طبيعة العمل.",
    ctaTitle:"اتخذ قرار مشروعك التالي بناءً على صورة أوضح.",ctaBody:"اربط الخطة والفرق والأرقام والأدلة طوال دورة حياة المشروع.",
    assistantTitle:"مساعد CUBI للذكاء الهندسي",assistantSubtitle:"إرشاد المشروع على بُعد خطوة",
    assistantDescription:"اعثر على إرشادات المنتج والدعم المرتبط بسياق المشروع. يجب أن تحترم الإجابات الصلاحيات وتوضح فجوات المعرفة وتطلب موافقتك قبل تغيير سجلات المشروع.",
    assistantWorkspaceAction:"افتح مساحة عمل المشروع →",assistantClose:"إغلاق المساعد",signIn:"تسجيل الدخول",start:"ابدأ الآن",language:"فارسی",
    footerColumns:[{title:"المنصة",links:["التحكم بالمشروع","التخطيط والجدولة","الموارد والتكاليف"]},{title:"الحلول",links:["فرق البناء","قيادة المشروع","تنفيذ المشروع"]},{title:"الموارد",links:["الوثائق","نظرة عامة على المنتج","اتصل بنا"]}],footerNote:"خطّط. تحكّم. ابنِ بذكاء أكبر."
  }
};

copy["zh-Hans"] = copy.zh!;
copy["zh-Hant"] = {
  ...copy.zh!,
  nav: ["首頁", "平台", "解決方案", "資源", "關於我們", "聯絡我們"],
  eyebrow: "面向建築、基礎設施與工業領域的專案控制",
  title: "全面掌握專案每個細節。", accent: "自信交付。",
  subtitle: "規劃 · 控制 · 更智慧地建設",
  body: "從建築與基礎設施，到油氣、石化、能源及複雜工業設施，CUBI 將專案範圍、進度計畫、實際進展、資源、成本與專案憑證整合於統一且規範的專案控制環境中。",
  primary: "探索 CUBI 平台 →", secondary: "了解 CUBI 如何運作",
  featuresEyebrow: "統一互聯的專案環境",
  featuresTitle: "連結專案交付所需的關鍵資訊",
  featuresBody: "在專案全生命週期中連結計畫、績效、團隊、文件與決策，並確保責任明確、資訊可追溯。",
  features: [
    { icon: "⌁", title: "專案規劃與進度管理", body: "管理專案範圍、工作分解結構、活動、日曆、邏輯關係、基準計畫與進度更新。" },
    { icon: "✧", assistantAvatar: true, title: "工程智慧助理", body: "查找相關 CUBI 指南，結合專案情境準備後續步驟；遵循權限規則，並在變更前取得使用者確認。" },
    { icon: "↗", title: "資源與成本", body: "提升資源需求、分派、預算與成本績效的可視性。" },
    { icon: "▤", title: "文件與合約", body: "將受控版本、專案紀錄、合約資訊與佐證資料連結至相關工作。" },
    { icon: "◎", title: "團隊與現場協作", body: "連結專案團隊、現場資訊、待處理事項與管理決策。" },
    { icon: "☁", title: "報告與協作", body: "依據可追溯的專案資料、角色權限與規範流程進行協作。" }
  ],
  techEyebrow: "為複雜專案而打造",
  techTitle: "支援更佳決策的互聯基礎",
  techBody: "CUBI 連結專案定義、工作分解結構、活動網路、日曆、基準計畫、進度、資源與成本資訊、受控文件及報告。計算結果與進度日期由權威專案服務提供，而非由助理猜測。",
  techLink: "查看平台功能 →",
  techNodes: ["專案控制", "工程指南", "互聯資料", "受控流程"],
  industriesEyebrow: "從土木工程到複雜流程設施",
  industriesTitle: "統一的專案控制基礎，服務多元產業。",
  industriesBody: "CUBI 適用於建築與基礎設施、油氣開發、管線、煉油廠、石化設施、電力與公用事業、工業廠房及 EPC 專案。讓專案結構、日曆、角色與報告配合實際工作需求。",
  ctaTitle: "以更清晰的專案全貌做出下一個決策。",
  ctaBody: "在專案全生命週期中連結計畫、人員、數據與佐證資料。",
  assistantTitle: "CUBI 工程智慧助理",
  assistantSubtitle: "專案指引，近在咫尺",
  assistantDescription: "在工作區中查找產品指南與專案情境支援。回答必須遵守存取權限、說明知識缺口，並在變更專案紀錄前取得使用者核准。",
  assistantWorkspaceAction: "開啟專案工作區 →",
  assistantClose: "關閉助理",
  signIn: "登入", start: "立即開始", language: "فارسی",
  footerColumns: [
    { title: "平台", links: ["專案控制", "規劃與進度管理", "資源與成本"] },
    { title: "解決方案", links: ["施工團隊", "專案領導", "專案交付"] },
    { title: "資源", links: ["文件", "產品概覽", "聯絡我們"] }
  ],
  footerNote: "規劃 · 控制 · 更智慧地建設"
};
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDirection, getWorkspaceLocaleDisplayName, translateWorkspaceText } from "./workspace-localization.js";
import { getLandingChromeCopy, normalizeLandingLocaleTag, type LandingChromeCopy } from "./landing-chrome.js";
import { cubiAssistantAvatarUrl, cubiPlatformLogoUrl } from "./cubi-brand-assets.js";
import { LANDING_LOCALE_STORAGE_KEY } from "./workspace-preferences.js";
/** The un-prefixed landing document is the default language route. */
export const DEFAULT_LANDING_LOCALE = "en";
/**
 * Locales that have complete, indexable public-site routes. A locale is not added
 * to this list until its homepage and every public marketing route (including
 * pricing) have translated documents, correct metadata and working twin links.
 */
export const LANDING_LANGUAGE_ROUTES: readonly string[] = Object.freeze(["en", "fa"]);
/** Homepage copy is available in these locales; other public routes remain gated until translated. */
export const LANDING_HOMEPAGE_LOCALES: readonly string[] = Object.freeze(["en", "fa", "de", "zh-Hans", "zh-Hant", "ar", "fr", "ja", "ko", "ru"]);
let locale: LandingLocale = "en";

/** Locales the public site can actually serve as complete, indexable route trees. */
export function getLandingLanguageRoutes(available: readonly string[] = getAvailableWorkspaceLocales()): string[] {
  const shipped = LANDING_LANGUAGE_ROUTES.filter((code) => available.includes(code));
  return shipped.length ? shipped : [DEFAULT_LANDING_LOCALE];
}

/** Locales with complete homepage copy. This list does not imply translated subpages. */
export function getLandingHomepageLocales(available: readonly string[] = getAvailableWorkspaceLocales()): string[] {
  return LANDING_HOMEPAGE_LOCALES.filter((code) => available.includes(code) || (code.startsWith("zh-") && available.includes("zh")));
}

/**
 * A landing document may be served from a language route such as /fa/. The last
 * path segment is used so GitHub Pages project bases (/<repo>/fa/) resolve the
 * same way as a custom domain (/fa/).
 */
export function resolveLandingLocaleFromPath(pathname: string): LandingLocale | null {
  const normalized = pathname.replace(/index\.html$/, "").replace(/\/+$/, "");
  const lastSegment = normalized.split("/").filter(Boolean).pop() ?? "";
  return getLandingLanguageRoutes().includes(lastSegment) ? lastSegment : null;
}

/**
 * Resolve the document URL that carries the landing page in one language.
 * The locale segment is removed from the end of the route path rather than
 * searched for, so a repository base that happens to contain the same letters
 * (for example /cubi-fa-tools/fa/) still resolves to the real language root.
 */
export function resolveLandingLanguageHref(
  targetLocale: LandingLocale,
  pathname: string,
  defaultLocale: LandingLocale = DEFAULT_LANDING_LOCALE,
): string {
  const routePath = `${pathname.replace(/index\.html$/, "").replace(/\/+$/, "")}/`;
  const pathLocale = resolveLandingLocaleFromPath(pathname);
  const base = pathLocale
    ? routePath.slice(0, routePath.length - `${pathLocale}/`.length)
    : routePath;
  if (targetLocale === defaultLocale) return base;
  return `${base}${targetLocale}/`;
}

function restoreLandingLocale(): string | null {
  const routeLocale = resolveLandingLocaleFromPath(window.location.pathname);
  const saved = readSavedLandingLocale();
  if (routeLocale) {
    locale = routeLocale;
    if (saved !== routeLocale) persistLandingLocale();
    return null;
  }
  // Homepage-only locales are rendered in place and are not advertised as
  // translated, indexable subpage routes. The document lang/dir is updated
  // together with the selected homepage copy.
  locale = saved ?? DEFAULT_LANDING_LOCALE;
  if (saved && getLandingLanguageRoutes().includes(saved)) {
    return resolveLandingLanguageHref(saved, window.location.pathname);
  }
  return null;
}
function readSavedLandingLocale(): LandingLocale | null {
  try {
    const saved = window.localStorage.getItem(LANDING_LOCALE_STORAGE_KEY);
    return saved && getLandingHomepageLocales().includes(saved) ? saved : null;
  } catch {
    // Storage may be disabled; the homepage remains usable without storage.
    return null;
  }
}
function persistLandingLocale(): void {
  try {
    window.localStorage.setItem(LANDING_LOCALE_STORAGE_KEY, locale);
  } catch {
    // Keep the selected language for the current render even without storage.
  }
}
function setLandingDocumentLocale(): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = getWorkspaceLocaleDirection(locale);
  const localized = getLandingCopy(locale);
  document.title = `${localized.title} ${localized.accent} | CUBI Platform`;
  const description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (description) description.content = localized.body;
  const ogLocale = document.querySelector<HTMLMetaElement>('meta[property="og:locale"]');
  if (ogLocale) ogLocale.content = ({ en: "en_US", fa: "fa_IR", de: "de_DE", "zh-Hans": "zh_CN", "zh-Hant": "zh_TW", ar: "ar_SA", fr: "fr_FR", ja: "ja_JP", ko: "ko_KR", ru: "ru_RU" } as Record<string, string>)[locale] ?? "en_US";
}
function getLandingCopy(requestedLocale: LandingLocale): LandingCopy & { chrome: LandingChromeCopy } {
  const normalizedLocale = normalizeLandingLocaleTag(requestedLocale);
  const baseline = copy[normalizedLocale] ?? copy.en!;
  const chrome = getLandingChromeCopy(normalizedLocale);
  const availableLocales = getLandingHomepageLocales();
  const currentLocaleIndex = availableLocales.indexOf(normalizedLocale);
  const nextLocale = availableLocales[(currentLocaleIndex + 1) % availableLocales.length] ?? DEFAULT_LANDING_LOCALE;
  const translate = (key: string, fallback: string) => translateWorkspaceText(normalizedLocale, `landing.${key}`, fallback);
  const localized: LandingCopy & { chrome: LandingChromeCopy } = {
    ...baseline,
    chrome,
    nav: chrome.nav.map((value, index) => translate(`nav.${index}`, value)),
    eyebrow: translate("eyebrow", baseline.eyebrow),
    title: translate("title", baseline.title),
    accent: translate("accent", baseline.accent),
    subtitle: translate("subtitle", baseline.subtitle),
    body: translate("body", baseline.body),
    primary: translate("primary", baseline.primary),
    secondary: translate("secondary", baseline.secondary),
    featuresEyebrow: translate("featuresEyebrow", baseline.featuresEyebrow),
    featuresTitle: translate("featuresTitle", baseline.featuresTitle),
    featuresBody: translate("featuresBody", baseline.featuresBody),
    features: baseline.features.map((feature, index) => ({
      assistantAvatar: feature.assistantAvatar,
      icon: translate(`features.${index}.icon`, feature.icon),
      title: translate(`features.${index}.title`, feature.title),
      body: translate(`features.${index}.body`, feature.body),
    })),
    techEyebrow: translate("techEyebrow", baseline.techEyebrow),
    industriesEyebrow: translate("industriesEyebrow", baseline.industriesEyebrow),
    industriesTitle: translate("industriesTitle", baseline.industriesTitle),
    industriesBody: translate("industriesBody", baseline.industriesBody),
    techTitle: translate("techTitle", baseline.techTitle),
    techBody: translate("techBody", baseline.techBody),
    techLink: translate("techLink", baseline.techLink),
    techNodes: baseline.techNodes.map((value, index) => translate(`techNodes.${index}`, value)),
    ctaTitle: translate("ctaTitle", baseline.ctaTitle),
    ctaBody: translate("ctaBody", baseline.ctaBody),
    signIn: translate("signIn", baseline.signIn),
    start: translate("start", baseline.start),
    language: translate("language", normalizedLocale === "en" ? "فارسی" : normalizedLocale === "fa" ? "EN" : getWorkspaceLocaleDisplayName(nextLocale)),
    footerColumns: baseline.footerColumns.map((column, columnIndex) => ({
      title: translate(`footerColumns.${columnIndex}.title`, column.title),
      links: column.links.map((value, linkIndex) => translate(`footerColumns.${columnIndex}.links.${linkIndex}`, value)),
    })),
    footerNote: translate("footerNote", baseline.footerNote),
    assistantTitle: translate("assistant.title", baseline.assistantTitle),
    assistantSubtitle: translate("assistant.subtitle", baseline.assistantSubtitle),
    assistantDescription: translate("assistant.description", baseline.assistantDescription),
    assistantWorkspaceAction: translate("assistant.workspaceAction", baseline.assistantWorkspaceAction),
    assistantClose: translate("assistant.close", baseline.assistantClose),
  };
  return escapeLandingCopy(localized);
}

/** Returns the complete, non-route-gated homepage copy for localization QA. */
export function getLandingCopyForLocale(requestedLocale: string): LandingCopy & { chrome: LandingChromeCopy } {
  return getLandingCopy(requestedLocale);
}

export type LandingSecurityCard = { icon: string; title: string; body: string; status: string };
export type LandingSecurityCopy = { eyebrow: string; title: string; intro: string; cards: LandingSecurityCard[]; disclosure: string };

const securitySectionCopy: Record<string, LandingSecurityCopy> = {
  en: {
    eyebrow: "SECURITY & RELIABILITY",
    title: "Your Projects. Securely Connected. Reliably Protected.",
    intro: "Manage your projects in a secure and always-accessible environment. With cloud infrastructure, security capabilities, and backup services, CUBI helps you manage your project information and records with greater confidence.",
    cards: [
      { icon: "🔒", title: "Secure SSL Connection", status: "ACTIVE — HOST MANAGED", body: "Encrypted connection between your browser and CUBI." },
      { icon: "🛡", title: "Cloud Firewall Protection", status: "NOT VERIFIED", body: "No IP-based access restrictions are configured for the two connected web services. A separate application firewall rule set has not been verified; CUBI authentication remains a separate layer." },
      { icon: "◈", title: "DDoS Protection", status: "PROVIDER-PROVIDED", body: "Protection against attacks that disrupt service availability, provided by the hosting platform." },
      { icon: "☁", title: "Automatic Cloud Backup", status: "NOT CONFIGURED / VERIFIED", body: "Automatic backups reduce the risk of losing project information. No CUBI backup configuration has yet been verified; free web-service filesystems are ephemeral." },
      { icon: "⌁", title: "Infrastructure Monitoring", status: "PARTIAL", body: "Monitoring of infrastructure health and performance. Hosting logs and service events are available; independent alert coverage is not verified." },
      { icon: "↻", title: "Data Recovery", status: "NOT VERIFIED", body: "Recovery of information from available backup copies. No tested backup source or successful restore drill has been established." }
    ],
    disclosure: "CUBI lets you focus on project management while cloud infrastructure supports the protection of your information. Hosting audit: the connected workspace currently has two Free web services in Frankfurt and no managed PostgreSQL instance. IP-based access restrictions are not configured at the hosting layer. External databases or backup providers, if any, have not been verified. Free web services can spin down and their local filesystem is not persistent. Statuses will change only after configuration and evidence checks."
  },
  fa: {
    eyebrow: "امنیت و پایداری",
    title: "Your Projects. Securely Connected. Reliably Protected.",
    intro: "مدیریت پروژه‌های خود را به محیطی امن و همیشه در دسترس بسپارید.\nCUBI با بهره‌گیری از زیرساخت ابری، امکانات امنیتی و خدمات پشتیبان‌گیری، به شما کمک می‌کند اطلاعات و سوابق پروژه‌های خود را با اطمینان بیشتری مدیریت کنید.",
    cards: [
      { icon: "🔒", title: "Secure SSL Connection", status: "فعال — مدیریت‌شده توسط میزبان", body: "ارتباط امن و رمزنگاری‌شده با CUBI." },
      { icon: "🛡", title: "Cloud Firewall Protection", status: "تأیید نشده", body: "در دو سرویس وب متصل، محدودیت دسترسی مبتنی بر IP پیکربندی نشده است. پیکربندی جداگانه فایروال برنامه تأیید نشده و احراز هویت کوبی لایه‌ای مستقل است." },
      { icon: "◈", title: "DDoS Protection", status: "ارائه‌شده توسط میزبان", body: "محافظت در برابر حملات مختل‌کننده سرویس؛ این قابلیت توسط زیرساخت میزبان ارائه می‌شود." },
      { icon: "☁", title: "Automatic Cloud Backup", status: "پیکربندی یا تأیید نشده", body: "پشتیبان‌گیری خودکار برای کاهش خطر از دست رفتن اطلاعات. پیکربندی پشتیبان‌گیری کوبی هنوز تأیید نشده و فایل‌سیستم سرویس وب رایگان ماندگار نیست." },
      { icon: "⌁", title: "Infrastructure Monitoring", status: "محدود / جزئی", body: "پایش سلامت و عملکرد زیرساخت. لاگ‌ها و رخدادهای سرویس در داشبورد میزبان در دسترس‌اند؛ پوشش هشداردهی مستقل تأیید نشده است." },
      { icon: "↻", title: "Data Recovery", status: "تأیید نشده", body: "امکان بازیابی اطلاعات از نسخه‌های پشتیبان. منبع پشتیبان آزمایش‌شده و آزمون موفق بازیابی هنوز ثبت نشده است." }
    ],
    disclosure: "کوبی؛ تمرکز شما بر مدیریت پروژه، حفاظت از اطلاعات بر عهده زیرساخت ابری. نتیجه بررسی میزبانی: در فضای کاری متصل، دو سرویس وب رایگان در فرانکفورت و هیچ نمونه PostgreSQL مدیریت‌شده مشاهده نشد. در لایه میزبانی، محدودیت دسترسی مبتنی بر IP پیکربندی نشده است. دیتابیس یا ارائه‌دهنده پشتیبان خارجی احتمالی هنوز بررسی نشده است. سرویس‌های وب رایگان ممکن است متوقف شوند و فایل‌سیستم محلی آن‌ها ماندگار نیست. وضعیت‌ها فقط پس از پیکربندی و بررسی شواهد به‌روزرسانی می‌شوند."
  }

  de: {
    eyebrow: "SICHERHEIT & ZUVERLÄSSIGKEIT",
    title: "Ihre Projekte. Sicher verbunden. Zuverlässig geschützt.",
    intro: "Verwalten Sie Ihre Projekte in einer sicheren Umgebung. CUBI unterstützt Sie mit Cloud-Infrastruktur und Sicherheitsfunktionen; der tatsächliche Status jeder Schutzmaßnahme wird transparent ausgewiesen.",
    cards: [
      { icon: "🔒", title: "Sichere SSL-Verbindung", status: "AKTIV — HOSTVERWALTET", body: "Verschlüsselte Verbindung zwischen Ihrem Browser und CUBI über verwaltete TLS-Zertifikate und HTTPS-Weiterleitung." },
      { icon: "🛡", title: "Cloud-Firewall-Schutz", status: "NICHT BESTÄTIGT", body: "Für beide verbundenen Webdienste ist keine IP-basierte Zugriffsbeschränkung konfiguriert. Eine separate Anwendungsfirewall wurde nicht bestätigt; die CUBI-Authentifizierung ist eine eigene Sicherheitsebene." },
      { icon: "◈", title: "DDoS-Schutz", status: "DURCH HOSTER", body: "Der aktuelle Hosting-Anbieter dokumentiert automatischen DDoS-Schutz für gehostete Anwendungen, einschließlich kostenloser Dienste." },
      { icon: "☁", title: "Automatische Cloud-Sicherung", status: "NICHT EINGERICHTET / BESTÄTIGT", body: "Eine verwaltete PostgreSQL-Datenbank oder geprüfte Anwendungssicherung wurde im verbundenen Workspace nicht gefunden. Das Dateisystem kostenloser Webdienste ist flüchtig." },
      { icon: "⌁", title: "Infrastrukturüberwachung", status: "TEILWEISE", body: "Hosting-Protokolle und Ereignisse sind verfügbar. Unabhängige Verfügbarkeitsüberwachung und vollständige Alarmierung sind nicht bestätigt." },
      { icon: "↻", title: "Datenwiederherstellung", status: "NICHT BESTÄTIGT", body: "Eine getestete Sicherungsquelle und ein erfolgreicher Wiederherstellungstest liegen nicht vor." }
    ],
    disclosure: "Hosting-Prüfung: Der verbundene Workspace enthält zwei kostenlose Webdienste in Frankfurt und keine verwaltete PostgreSQL-Instanz. IP-basierte Zugriffsbeschränkungen sind auf Hosting-Ebene nicht konfiguriert. Externe Datenbanken und Sicherungsanbieter wurden nicht geprüft. Kostenlose Webdienste können inaktiv werden; ihr lokales Dateisystem ist nicht dauerhaft."
  },
  "zh-Hans": {
    eyebrow: "安全与可靠性",
    title: "您的项目，安全连接，可靠保护。",
    intro: "在安全的环境中管理项目。CUBI 提供云基础设施与安全能力，并透明展示每项保护措施当前是否已配置和验证。",
    cards: [
      { icon: "🔒", title: "安全 SSL 连接", status: "已启用 — 托管平台管理", body: "通过托管 TLS 证书和 HTTPS 重定向，在浏览器与 CUBI 之间建立加密连接。" },
      { icon: "🛡", title: "云防火墙保护", status: "尚未验证", body: "两个已连接的 Web 服务均未配置基于 IP 的访问限制。尚未确认独立的应用防火墙；CUBI 身份验证是单独的安全层。" },
      { icon: "◈", title: "DDoS 防护", status: "由托管平台提供", body: "当前托管服务商说明，其平台托管的应用（包括免费服务）会自动获得 DDoS 防护。" },
      { icon: "☁", title: "自动云备份", status: "未配置或未验证", body: "连接的工作区中未发现托管 PostgreSQL 数据库或经过验证的应用备份配置。免费 Web 服务的文件系统不是持久存储。" },
      { icon: "⌁", title: "基础设施监控", status: "部分可用", body: "可以查看托管日志和服务事件；独立运行时间监控及完整告警覆盖尚未验证。" },
      { icon: "↻", title: "数据恢复", status: "尚未验证", body: "尚未建立经过测试的备份来源，也没有成功的恢复演练。" }
    ],
    disclosure: "托管审查：连接的工作区在法兰克福有两个免费 Web 服务，没有托管 PostgreSQL 实例。托管层未配置基于 IP 的访问限制。外部数据库和备份服务尚未验证。免费 Web 服务可能休眠，其本地文件系统不具备持久性。"
  },
  ar: {
    eyebrow: "الأمان والموثوقية",
    title: "مشاريعك متصلة بأمان ومحميّة بموثوقية.",
    intro: "أدر مشاريعك ضمن بيئة آمنة. تعرض CUBI بوضوح حالة إعداد كل وسيلة حماية والتحقق منها في بيئة الاستضافة الحالية.",
    cards: [
      { icon: "🔒", title: "اتصال SSL آمن", status: "نشط — يديره مزود الاستضافة", body: "اتصال مشفّر بين المتصفح وCUBI باستخدام شهادات TLS مُدارة وإعادة توجيه HTTP إلى HTTPS." },
      { icon: "🛡", title: "حماية جدار الحماية السحابي", status: "غير مؤكد", body: "لا توجد قيود وصول معتمدة على عنوان IP للخدمتين المتصلتين. لم يتم التحقق من جدار حماية مستقل للتطبيق؛ ويظل تسجيل الدخول في CUBI طبقة منفصلة." },
      { icon: "◈", title: "الحماية من DDoS", status: "يوفرها مزود الاستضافة", body: "يوثق مزود الاستضافة الحالي حماية تلقائية من DDoS للتطبيقات المستضافة، بما فيها الخدمات المجانية." },
      { icon: "☁", title: "النسخ الاحتياطي السحابي التلقائي", status: "غير مُعد أو غير مؤكد", body: "لم يتم العثور على قاعدة PostgreSQL مُدارة أو إعداد نسخ احتياطي موثق للتطبيق. نظام ملفات خدمة الويب المجانية مؤقت." },
      { icon: "⌁", title: "مراقبة البنية التحتية", status: "جزئي", body: "تتوفر سجلات الاستضافة وأحداث الخدمة؛ ولم يتم التحقق من مراقبة مستقلة للتوافر أو تغطية التنبيهات." },
      { icon: "↻", title: "استعادة البيانات", status: "غير مؤكد", body: "لم يتم إثبات مصدر نسخ احتياطي مختبر أو اختبار استعادة ناجح." }
    ],
    disclosure: "مراجعة الاستضافة: تحتوي مساحة العمل المتصلة على خدمتي ويب مجانيتين في فرانكفورت ولا تحتوي على قاعدة PostgreSQL مُدارة. لا توجد قيود وصول قائمة على IP في طبقة الاستضافة. لم يتم التحقق من قواعد البيانات أو مزودي النسخ الاحتياطي الخارجيين. قد تتوقف الخدمات المجانية مؤقتاً ونظام ملفاتها المحلي غير دائم."
  },
  fr: {
    eyebrow: "SÉCURITÉ ET FIABILITÉ",
    title: "Vos projets. Connectés en sécurité. Protégés en toute transparence.",
    intro: "Gérez vos projets dans un environnement sécurisé. CUBI indique clairement quelles protections sont actives, partiellement disponibles ou encore à configurer.",
    cards: [
      { icon: "🔒", title: "Connexion SSL sécurisée", status: "ACTIVE — GÉRÉE PAR L’HÉBERGEUR", body: "Connexion chiffrée entre votre navigateur et CUBI grâce aux certificats TLS gérés et à la redirection HTTPS." },
      { icon: "🛡", title: "Protection par pare-feu cloud", status: "NON VÉRIFIÉE", body: "Aucune restriction d’accès par IP n’est configurée sur les deux services Web connectés. Un pare-feu applicatif distinct n’a pas été vérifié ; l’authentification CUBI reste une couche séparée." },
      { icon: "◈", title: "Protection DDoS", status: "FOURNIE PAR L’HÉBERGEUR", body: "L’hébergeur actuel documente une protection DDoS automatique pour les applications hébergées, y compris les services gratuits." },
      { icon: "☁", title: "Sauvegarde cloud automatique", status: "NON CONFIGURÉE / VÉRIFIÉE", body: "Aucune base PostgreSQL gérée ni sauvegarde applicative vérifiée n’a été trouvée dans l’espace connecté. Le système de fichiers des services gratuits est éphémère." },
      { icon: "⌁", title: "Surveillance de l’infrastructure", status: "PARTIELLE", body: "Les journaux et événements d’hébergement sont disponibles. La surveillance indépendante de disponibilité et la couverture des alertes ne sont pas vérifiées." },
      { icon: "↻", title: "Récupération des données", status: "NON VÉRIFIÉE", body: "Aucune source de sauvegarde testée ni restauration réussie n’a été établie." }
    ],
    disclosure: "Audit d’hébergement : l’espace connecté contient deux services Web gratuits à Francfort et aucune instance PostgreSQL gérée. Aucune restriction d’accès par IP n’est configurée au niveau de l’hébergement. Les bases de données et sauvegardes externes ne sont pas vérifiées. Les services gratuits peuvent s’endormir et leur système de fichiers local n’est pas persistant."
  },
  ja: {
    eyebrow: "セキュリティと信頼性",
    title: "プロジェクトを安全につなぎ、透明性をもって保護します。",
    intro: "安全な環境でプロジェクトを管理できます。CUBI は、各保護機能の設定状況と検証状況を明確に示します。",
    cards: [
      { icon: "🔒", title: "安全な SSL 接続", status: "有効 — ホスト管理", body: "管理 TLS 証明書と HTTPS リダイレクトにより、ブラウザーと CUBI 間の通信を暗号化します。" },
      { icon: "🛡", title: "クラウドファイアウォール保護", status: "未確認", body: "接続された 2 つの Web サービスには IP ベースのアクセス制限が設定されていません。独立したアプリケーションファイアウォールは未確認で、CUBI 認証は別の保護層です。" },
      { icon: "◈", title: "DDoS 保護", status: "ホスト提供", body: "現在のホスティング事業者は、無料サービスを含むホスト済みアプリに自動 DDoS 保護を提供すると説明しています。" },
      { icon: "☁", title: "自動クラウドバックアップ", status: "未設定／未確認", body: "接続されたワークスペースに管理 PostgreSQL データベースや検証済みバックアップ設定はありません。無料 Web サービスのファイルシステムは一時的です。" },
      { icon: "⌁", title: "インフラ監視", status: "一部", body: "ホスティングログとサービスイベントは利用できます。独立した稼働監視やアラート範囲は確認されていません。" },
      { icon: "↻", title: "データ復旧", status: "未確認", body: "テスト済みバックアップ元と復元テストの成功は確認されていません。" }
    ],
    disclosure: "ホスティング監査：接続されたワークスペースにはフランクフルトの無料 Web サービスが 2 つあり、管理 PostgreSQL インスタンスはありません。ホスティング層に IP アクセス制限は設定されていません。外部データベースやバックアップは未確認です。無料 Web サービスはスリープする場合があり、ローカルファイルシステムは永続的ではありません。"
  },
  ko: {
    eyebrow: "보안 및 안정성",
    title: "프로젝트를 안전하게 연결하고 투명하게 보호합니다.",
    intro: "안전한 환경에서 프로젝트를 관리하세요. CUBI는 각 보호 기능의 실제 구성 및 검증 상태를 명확히 공개합니다.",
    cards: [
      { icon: "🔒", title: "보안 SSL 연결", status: "활성 — 호스팅 제공업체 관리", body: "관리형 TLS 인증서와 HTTPS 리디렉션을 통해 브라우저와 CUBI 간 연결을 암호화합니다." },
      { icon: "🛡", title: "클라우드 방화벽 보호", status: "확인되지 않음", body: "연결된 두 웹 서비스에는 IP 기반 접근 제한이 설정되어 있지 않습니다. 별도의 애플리케이션 방화벽은 확인되지 않았으며 CUBI 인증은 독립적인 보안 계층입니다." },
      { icon: "◈", title: "DDoS 보호", status: "호스팅 제공업체 제공", body: "현재 호스팅 제공업체는 무료 서비스를 포함한 호스팅 앱에 자동 DDoS 보호를 제공한다고 안내합니다." },
      { icon: "☁", title: "자동 클라우드 백업", status: "구성 또는 확인되지 않음", body: "연결된 작업 공간에서 관리형 PostgreSQL 데이터베이스나 검증된 앱 백업 구성을 찾지 못했습니다. 무료 웹 서비스의 파일 시스템은 임시 저장소입니다." },
      { icon: "⌁", title: "인프라 모니터링", status: "부분 제공", body: "호스팅 로그와 서비스 이벤트는 확인할 수 있습니다. 독립 가동 시간 모니터링과 경보 범위는 검증되지 않았습니다." },
      { icon: "↻", title: "데이터 복구", status: "확인되지 않음", body: "테스트된 백업 원본과 성공적인 복구 훈련이 확인되지 않았습니다." }
    ],
    disclosure: "호스팅 점검 결과: 연결된 작업 공간에는 프랑크푸르트의 무료 웹 서비스 2개가 있으며 관리형 PostgreSQL 인스턴스는 없습니다. 호스팅 계층에 IP 접근 제한이 설정되어 있지 않습니다. 외부 데이터베이스와 백업 서비스는 확인되지 않았습니다. 무료 웹 서비스는 유휴 상태에서 중지될 수 있고 로컬 파일 시스템은 영구 저장소가 아닙니다."
  },
};

export function getLandingSecurityCopyForLocale(requestedLocale: string): LandingSecurityCopy {
  const normalizedLocale = normalizeLandingLocaleTag(requestedLocale);
  const resolvedLocale = normalizedLocale === "zh-Hant" ? "zh-Hans" : normalizedLocale;
  return securitySectionCopy[resolvedLocale] ?? { ...securitySectionCopy.en!, eyebrow: "SECURITY & RELIABILITY" };
}

function escapeLandingCopy<T>(value: T): T {
  if (typeof value === "string") return escapeHtml(value) as T;
  if (Array.isArray(value)) return value.map((item) => escapeLandingCopy(item)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, escapeLandingCopy(item)])) as T;
  }
  return value;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"\']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"' : "&quot;", "\'": "&#39;" })[character]!);
}

function renderLanding(container: HTMLElement): void {
  const t = getLandingCopy(locale);
  const security = getLandingSecurityCopyForLocale(locale);
  const c = t.chrome;
  setLandingDocumentLocale();
  // Language routes live one level below the site root, so workspace and
  // product links must be resolved against the root instead of the page.
  const siteRootHref = resolveLandingLocaleFromPath(window.location.pathname) ? "../" : "./";
  const workspaceHref = `${siteRootHref}app/`;
  const publicRootHref = resolveLandingLanguageHref("en", window.location.pathname);
  const publicLocaleRootHref = locale === "fa" ? resolveLandingLanguageHref("fa", window.location.pathname) : publicRootHref;
  const publicPageHref = (route: string) => `${publicLocaleRootHref}${route}/`;
  const pricingHref = publicPageHref("pricing");
  const aboutLocale = locale === "zh-Hant" ? "zh-Hans" : locale;
  const aboutPageHref = ["en", "fa", "de", "zh-Hans", "ar", "fr", "ja", "ko"].includes(aboutLocale)
    ? `${resolveLandingLanguageHref(aboutLocale, window.location.pathname)}about/`
    : `${publicRootHref}about/`;
  container.innerHTML = `
    <div class="cubi-reference-home cubi-exact-home" id="home">
      <header class="cubi-exact-header">
        <a class="cubi-exact-brand" href="./" aria-label="${c.brandAria}"><img src="${cubiPlatformLogoUrl()}" width="180" height="60" alt="${c.brandAlt}" /></a>
        <nav class="cubi-exact-nav" aria-label="${c.primaryNavigation}">
          <a class="is-active" href="#home">${t.nav[0]}</a><a href="${publicPageHref("platform")}">${t.nav[1]}</a><a href="${publicPageHref("solutions")}">${t.nav[2]}</a><a href="${pricingHref}">${c.pricing}</a><a href="${publicPageHref("resources")}">${t.nav[3]}</a><a href="${aboutPageHref}">${t.nav[4]}</a><a href="${publicPageHref("contact")}">${t.nav[5]}</a>
        </nav>
        <div class="cubi-exact-actions">
          <label class="cubi-language-picker"><span class="sr-only">${c.changeLanguage}</span><select class="cubi-exact-language" id="cubi-language" aria-label="${c.changeLanguage}">${getLandingHomepageLocales().map((code) => { const names: Record<string, string> = { "zh-Hans": "简体中文", "zh-Hant": "繁體中文" }; return `<option value="${code}"${code === locale ? " selected" : ""}>${names[code] ?? getWorkspaceLocaleDisplayName(code)}</option>`; }).join("")}</select></label>
          <a href="${workspaceHref}" class="cubi-exact-signin">${t.signIn}</a><a href="${workspaceHref}" class="cubi-exact-start">${t.start} →</a>
        </div>
      </header>
      <main>
        <section class="cubi-exact-hero" aria-labelledby="cubi-hero-title">
          <div class="cubi-exact-hero-copy">
            <p class="cubi-exact-eyebrow">${t.eyebrow}</p><h1 id="cubi-hero-title">${t.title}<span>${t.accent}</span></h1><h2>${t.subtitle}</h2><p>${t.body}</p>
            <div class="cubi-exact-hero-actions"><a class="cubi-exact-primary" href="${workspaceHref}">${t.primary}</a><a class="cubi-exact-demo" href="#technology"><span class="play" aria-hidden="true">▶</span>${t.secondary}</a></div>
          </div>
          <div class="cubi-exact-dashboard" role="img" aria-label="${c.dashboardAria}">
            <aside class="cubi-dash-sidebar"><img src="${cubiPlatformLogoUrl()}" width="110" height="32" alt="CUBI Platform" /><span>${c.dashboardSidebar[0]}</span><span>${c.dashboardSidebar[1]}</span><span>${c.dashboardSidebar[2]}</span><span>${c.dashboardSidebar[3]}</span><span>${c.dashboardSidebar[4]}</span></aside>
            <div class="cubi-dash-main"><div class="cubi-dash-title"><strong>${c.dashboardTitle}</strong><span>${c.projectLabel} / 026</span></div>
              <div class="cubi-gantt" aria-hidden="true"><i style="width:76%"></i><i style="width:58%"></i><i style="width:82%"></i><i style="width:49%"></i><i style="width:67%"></i><i style="width:38%"></i></div>
              <div class="cubi-dash-bottom"><div class="cubi-mini-chart"><b>${c.progressTrend}</b><div class="cubi-line-chart"></div></div><div class="cubi-ring-card"><b>${c.schedule}</b><div class="cubi-ring"><strong>78%</strong></div><small>${c.onTrack}</small></div><div class="cubi-ai-card"><b>${c.aiInsight}</b><div class="cubi-ai-bubble" aria-hidden="true"><img src="${cubiAssistantAvatarUrl()}" width="31" height="31" alt="" /></div><small>${c.reviewNextMilestone}</small></div></div>
            </div>
            <aside class="cubi-progress-card"><div class="cubi-progress-ring"><strong>84%</strong></div><b>${c.projectProgress}</b><div><span>${c.plan}</span><span>${c.actual}</span></div></aside>
          </div>
        </section>
        <section class="cubi-exact-features" id="capabilities">
          <div class="cubi-exact-section-head"><p class="cubi-kicker">${t.featuresEyebrow}</p><h2>${t.featuresTitle}</h2><p>${t.featuresBody}</p></div>
          <div class="cubi-exact-feature-grid">${t.features.map((f) => `<article><div class="cubi-feature-icon${f.assistantAvatar ? " cubi-feature-icon-assistant" : ""}" aria-hidden="true">${f.assistantAvatar ? `<img src="${cubiAssistantAvatarUrl()}" width="50" height="50" alt="" />` : f.icon}</div><h3>${f.title}</h3><p>${f.body}</p></article>`).join("")}</div>
        </section>
        <section class="cubi-exact-features cubi-security-section" id="security" aria-labelledby="cubi-security-title">
          <div class="cubi-exact-section-head"><p class="cubi-kicker">${security.eyebrow}</p><h2 id="cubi-security-title">${security.title}</h2><p>${security.intro}</p></div>
          <div class="cubi-exact-feature-grid cubi-security-grid">${security.cards.map((card) => `<article><div class="cubi-feature-icon" aria-hidden="true">${card.icon}</div><h3>${card.title}</h3><p class="cubi-security-status"><strong>${card.status}</strong></p><p>${card.body}</p></article>`).join("")}</div>
          <p class="cubi-security-disclosure">${security.disclosure}</p>
        </section>
        <section class="cubi-exact-features cubi-exact-industries" id="industries" aria-labelledby="cubi-industries-title"><div class="cubi-exact-section-head"><p class="cubi-kicker">${t.industriesEyebrow}</p><h2 id="cubi-industries-title">${t.industriesTitle}</h2><p>${t.industriesBody}</p></div></section>
        <section class="cubi-exact-tech" id="technology" aria-labelledby="cubi-tech-title">
          <div class="cubi-tech-copy"><p class="cubi-kicker">${t.techEyebrow}</p><h2 id="cubi-tech-title">${t.techTitle}</h2><p>${t.techBody}</p>
            <div class="cubi-tech-badges" aria-label="${c.platformBlocks}"><b class="plan">PL</b><span>${c.planning}</span><b class="pg">▦</b><span>${c.projectData}</span><b class="ai" aria-hidden="true"><img src="${cubiAssistantAvatarUrl()}" width="29" height="29" alt="" /></b><span>${c.aiLabel}</span></div>
            <a class="cubi-exact-outline" href="${workspaceHref}">${t.techLink}</a>
          </div>
          <div class="cubi-tech-diagram" aria-label="${c.connectedCapabilities}"><div class="cubi-stack" aria-hidden="true"><i></i><i></i><i></i><b>C</b></div>
            <div class="cubi-tech-node n1"><span>${t.techNodes[0]}</span></div><div class="cubi-tech-node n2"><span>${t.techNodes[1]}</span></div><div class="cubi-tech-node n3"><span>${t.techNodes[2]}</span></div><div class="cubi-tech-node n4"><span>${t.techNodes[3]}</span></div>
          </div>
        </section>
        <section class="cubi-exact-cta" id="resources"><div><h2>${t.ctaTitle}</h2><p>${t.ctaBody}</p></div><div class="cubi-cta-actions"><a class="cubi-exact-primary" href="${workspaceHref}">${t.primary}</a><a class="cubi-exact-demo" href="#capabilities">${t.secondary}</a></div></section>
      </main>
      <footer class="cubi-exact-footer">
        <div class="cubi-footer-brand"><img src="${cubiPlatformLogoUrl()}" width="160" height="45" alt="${c.brandAlt}" /></div>
        ${t.footerColumns.map((col, columnIndex) => { const targets = [["platform/#project-controls", "platform/#scheduling", "platform/#resources-cost"], ["solutions/#construction-teams", "solutions/#project-leadership", "solutions/#project-delivery"], ["resources/#documentation", "resources/#overview", "contact/"]]; return `<div class="cubi-footer-col"><b>${col.title}</b>${col.links.map((link, linkIndex) => `<a href="${publicLocaleRootHref}${targets[columnIndex]?.[linkIndex] ?? ""}">${link}</a>`).join("")}</div>`; }).join("")}<div class="cubi-footer-col"><b>${c.company}</b><a href="${aboutPageHref}">${c.about}</a><a href="#security">${locale === "fa" ? "امنیت و پایداری" : "Security & Reliability"}</a></div>
        <div class="cubi-footer-social"><small>© 2026 CUBI Platform. ${c.copyright}</small></div>
      </footer>
      </div>`;
  document.getElementById("cubi-language")?.addEventListener("change", (event) => {
    const selected = (event.currentTarget as HTMLSelectElement).value;
    const next = normalizeLandingLocaleTag(selected);
    if (!getLandingHomepageLocales().includes(next)) return;
    locale = next;
    persistLandingLocale();
    renderLanding(container);
    setLandingDocumentLocale();
    // Only English and Persian have complete public subpage routes. Keep
    // homepage-only locales on the root homepage instead of routing them into
    // a Persian or English subpage by accident.
    const targetHome = resolveLandingLanguageHref(next === "fa" ? "fa" : "en", window.location.pathname);
    if (targetHome !== window.location.pathname) window.location.assign(targetHome);
  });
}
export function renderLandingPage(container: HTMLElement): void {
  let preferredLanguageRoute: string | null = null;
  if (container.dataset.localeInitialized !== "true") {
    preferredLanguageRoute = restoreLandingLocale();
    container.dataset.localeInitialized = "true";
  }
  renderLanding(container);
  // A stored preference is honored by moving to the document that describes it,
  // so the rendered copy, the URL and the localized metadata always agree.
  if (preferredLanguageRoute && preferredLanguageRoute !== window.location.pathname) {
    window.location.replace(preferredLanguageRoute);
  }
}
