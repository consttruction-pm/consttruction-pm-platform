// French public site copy. Published routes: home, platform, features,
// solutions, pricing, resources, documentation, contact.
export default {
  code: "fr",
  htmlLang: "fr",
  dir: "ltr",
  prefix: "fr/",
  label: "Français",
  nav: {
    home: "Accueil",
    platform: "Plateforme",
    features: "Fonctionnalités",
    solutions: "Solutions",
    pricing: "Tarifs",
    resources: "Ressources",
    documentation: "Documentation",
    help: "Aide",
    about: "À propos",
    contact: "Contact",
    "faq": "FAQ",
    "integrations": "Intégrations",
    "security": "Sécurité",
    "get-started": "Démarrer",
    "privacy": "Confidentialité",
    "terms": "Conditions",
  },
  footer: {
    tagline: "© 2026 CUBI Platform · Planifier. Contrôler. Construire plus intelligemment.",
    groups: [
      { title: "Produit", links: [["features", "Fonctionnalités"], ["platform", "Plateforme"], ["pricing", "Tarifs"]] },
      { title: "Apprendre", links: [["documentation", "Documentation"], ["resources", "Ressources"]] },
      { title: "Entreprise", links: [["about", "À propos"], ["contact", "Contact"]] },
    ],
  },
  cta: { label: "Ouvrir l'espace CUBI", href: "/app/" },
  pages: [
    {
      id: "home",
      path: "",
      title: "CUBI | Planification et contrôle de projet réunis",
      description: "CUBI relie la planification, le contrôle de projet, les ressources, les coûts et les documents dans un espace de travail unique.",
      eyebrow: "PLATEFORME CUBI",
      h1: "La planification et le contrôle, connectés.",
      lead: "Un espace de travail pour les projets de construction : organiser le plan, suivre la livraison et rapprocher l'information de la décision.",
      sections: [
        {
          h2: "Ce que CUBI relie",
          p: "Toutes les fonctions lisent le même enregistrement de projet, de calendrier et d'activité.",
          cards: [
            { h3: "Planification", p: "Structure de découpage, activités, calendriers, relations et référence dans un seul flux." },
            { h3: "Contrôle de projet", p: "Jalons, statut et indicateurs issus du plan que l'équipe exécute." },
            { h3: "Ressources et coûts", p: "Demande, affectations et coûts visibles au niveau de l'activité concernée." },
          ],
        },
      ],
      cta: { title: "Mettez votre projet au centre.", text: "Découvrez le flux de travail connecté dans CUBI.", label: "Ouvrir l'espace", href: "/app/" },
    },
    {
      id: "platform",
      path: "platform/",
      title: "CUBI Plateforme | Contrôle de projet de construction",
      description: "La plateforme CUBI relie planification, contrôle, ressources, coûts, documents et assistance IA.",
      eyebrow: "PLATEFORME CUBI",
      h1: "Une plateforme de contrôle connectée",
      lead: "Les pages publiques présentent le produit ; les données de projet restent dans l'espace authentifié.",
      sections: [
        {
          h2: "Un projet, un enregistrement",
          p: "Chaque fonction travaille sur le même projet et les mêmes autorisations.",
          cards: [
            { h3: "Planification", p: "Structure, activités, calendriers et dépendances explicites." },
            { h3: "Contrôle", p: "Statut, jalons et indicateurs sans tableur parallèle." },
            { h3: "Accès", p: "L'environnement et les actions suivent les rôles vérifiés par le serveur." },
          ],
        },
      ],
      cta: { title: "Voir la plateforme", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace", href: "/app/" },
    },
    {
      id: "features",
      path: "features/",
      title: "CUBI Fonctionnalités | Planification, contrôle, coûts et IA",
      description: "Comment CUBI relie planification, contrôle, ressources, coûts, documents, risques, rapports et assistance IA.",
      eyebrow: "FONCTIONNALITÉS",
      h1: "Chaque fonction reliée au travail",
      lead: "La disponibilité dépend de l'environnement auquel votre compte est autorisé.",
      sections: [
        {
          h2: "Planifier et contrôler",
          p: "Un enregistrement commun rend chaque changement visible là où il compte.",
          cards: [
            { h3: "Planification", p: "Structure, activités, calendriers, relations, référence et avancement." },
            { h3: "Contrôle de projet", p: "Jalons, statut et indicateurs dans une vue cohérente." },
            { h3: "Documents et risques", p: "Les preuves restent près de l'activité qu'elles expliquent." },
          ],
        },
      ],
      cta: { title: "Voir la plateforme", text: "Chaque fonction dispose de sa propre page.", label: "Voir la plateforme", href: "/fr/platform/" },
    },
    {
      id: "solutions",
      path: "solutions/",
      title: "CUBI Solutions | Livraison de projets de construction",
      description: "CUBI pour les entreprises, maîtres d'ouvrage et équipes de contrôle qui veulent réunir le plan et les preuves.",
      eyebrow: "SOLUTIONS",
      h1: "Pour les équipes qui exécutent le plan",
      lead: "Les projets échouent rarement par manque de données, mais par des données séparées. CUBI les réunit.",
      sections: [
        {
          h2: "Rôles dans le projet",
          p: "Chaque rôle voit la partie dont il a besoin pour décider.",
          cards: [
            { h3: "Entreprises", p: "Plan, avancement et preuves pour leur propre périmètre." },
            { h3: "Maîtres d'ouvrage", p: "Statut et jalons par rapport au plan de référence convenu." },
            { h3: "Contrôle", p: "Indicateurs et écarts issus de la même base." },
          ],
        },
      ],
      cta: { title: "Votre scénario", text: "Parlez-nous de votre projet.", label: "Contact", href: "/fr/contact/" },
    },
    {
      id: "pricing",
      path: "pricing/",
      title: "CUBI Tarifs | Abonnement Pro",
      description: "CUBI Pro s'achète en unités mensuelles. Le serveur confirme le droit après un paiement vérifié.",
      eyebrow: "TARIFS",
      h1: "Une facturation claire",
      lead: "Douze mois signifient douze unités mensuelles, sans offre annuelle séparée. Sans fournisseur configuré, rien n'est débité.",
      sections: [
        {
          h2: "Comment fonctionne l'achat",
          p: "Vous choisissez les mois, vérifiez le total et poursuivez vers le paiement. La page ne prélève rien.",
          cards: [
            { h3: "Unités mensuelles", p: "Chaque unité est un mois, achetée avec les autres." },
            { h3: "Abonnement existant", p: "Un achat confirmé prolonge la date d'expiration existante." },
            { h3: "Pas de fournisseur, pas de paiement", p: "Sans fournisseur vérifié, le paiement ne démarre pas." },
          ],
        },
      ],
      cta: { title: "Acheter Pro", text: "Le paiement se fait sur la page anglaise.", label: "Aller au paiement", href: "/pricing/" },
    },
    {
      id: "resources",
      path: "resources/",
      title: "CUBI Ressources | Présentation et guides",
      description: "Guides et références sur les environnements, la configuration de projet, la planification, le contrôle et l'accès aux données.",
      eyebrow: "RESSOURCES",
      h1: "Des ressources pour le travail quotidien",
      lead: "Les ressources suivent le produit et indiquent l'environnement concerné.",
      sections: [
        {
          h2: "Démarrage et référence",
          p: "Choisissez le guide correspondant à votre rôle.",
          cards: [
            { h3: "Premiers pas", p: "Se connecter, choisir un environnement, ouvrir un projet autorisé." },
            { h3: "Environnement Engineering", p: "Planification, contrôle et rapports pour les équipes projet." },
            { h3: "Environnement Enterprise", p: "Rôles et surface de tâches pour les comptes autorisés." },
          ],
        },
      ],
      cta: { title: "Documentation", text: "Les guides complets sont disponibles.", label: "Ouvrir la documentation", href: "/fr/documentation/" },
    },
    {
      id: "documentation",
      path: "documentation/",
      title: "CUBI Documentation | Guides de la plateforme et de l'espace",
      description: "Guides sur les environnements, la configuration de projet, la planification, le contrôle et l'accès aux données.",
      eyebrow: "DOCUMENTATION",
      h1: "La documentation de votre travail",
      lead: "Chaque guide indique l'environnement auquel il s'applique.",
      sections: [
        {
          h2: "Choisissez votre entrée",
          p: "Le rôle et l'environnement déterminent le guide adapté.",
          cards: [
            { h3: "Premiers pas", p: "Connexion, choix de l'environnement, ouverture du projet." },
            { h3: "Données et API", p: "Comment les données sont délimitées, versionnées et lues." },
            { h3: "Sécurité", p: "Identité, sessions, rôles et appartenance au projet." },
          ],
        },
      ],
      cta: { title: "Besoin d'aide ?", text: "Le centre d'aide couvre les cas fréquents.", label: "Centre d'aide", href: "/help/" },
    },
    {
      id: "contact",
      path: "contact/",
      title: "Contacter CUBI | Compte et informations produit",
      description: "Contact pour l'accès au compte, les questions produit et les scénarios de projet.",
      eyebrow: "CONTACT",
      h1: "Parlons de votre projet",
      lead: "Pour l'accès au compte, indiquez l'adresse du compte ; pour un scénario, la taille du projet et l'environnement souhaité.",
      sections: [
        {
          h2: "Ce dont nous avons besoin",
          p: "Plus les informations sont précises, plus la réponse est rapide.",
          cards: [
            { h3: "Accès au compte", p: "L'e-mail du compte et l'environnement à ouvrir." },
            { h3: "Question projet", p: "Taille du projet, rôles et domaine concerné." },
            { h3: "Sécurité", p: "Signalez immédiatement tout problème de sécurité suspecté." },
          ],
        },
      ],
      cta: { title: "Entrée rapide", text: "Connectez-vous et ouvrez l'environnement autorisé.", label: "Se connecter", href: "/login?next=/environments/" },
    },
    {
      id: "features-scheduling",
      path: "features/scheduling/",
      title: "CUBI Planification | WBS, activités et calendriers",
      description:
        "Construisez des WBS, des activités, des calendriers, des relations, des références et un avancement dans un flux de travail orienté planning.",
      eyebrow: "Fonctions · Planification",
      h1: "Un planning auquel toute l'équipe se fie",
      lead:
        "Planifiez du WBS jusqu'à l'activité, gardez calendriers et relations explicites, et comparez l'avancement à une référence enregistrée.",
      sections: [
        {
          h2: "La structure avant le détail",
          p: "Le WBS, les activités et les relations partagent un seul registre de projet, si bien que la structure ne se sépare jamais du détail.",
          cards: [
            { h3: "Structure de découpage", p: "Organisez livrables et lots de travaux dans une hiérarchie que l'équipe peut parcourir." },
            { h3: "Activités et relations", p: "Définissez les activités avec durée, calendrier et dépendances qui reflètent la séquence réelle." },
            { h3: "Calendriers et temps de travail", p: "Gardez jours ouvrés, jours fériés et postes explicites pour calculer les dates sur un temps réel." },
          ],
        },
        {
          h2: "Référence et avancement",
          p: "Une référence enregistrée et un avancement daté rendent l'écart lisible, sans reconstruire l'historique de mémoire.",
          cards: [
            { h3: "Référence enregistrée", p: "Figez le planning accepté et comparez-y le travail réel." },
            { h3: "Avancement daté", p: "Enregistrez l'avancement à une date de référence et gardez la trace de chaque mise à jour." },
            { h3: "Vues partagées", p: "Le même enregistrement alimente le tableau, le calendrier et les rapports." },
          ],
        },
      ],
      cta: { title: "Voir la planification", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-project-controls",
      path: "features/project-controls/",
      title: "CUBI Contrôle de projet | Jalons, statut et actions",
      description:
        "Suivez les jalons, l'état du projet et les actions correctives dans un espace de contrôle partagé entre planning et livraison.",
      eyebrow: "Fonctions · Contrôle de projet",
      h1: "Le contrôle suit le travail, pas l'inverse",
      lead:
        "Reliez jalons, statut et actions au planning : chaque décision de contrôle s'appuie sur des données de projet réelles.",
      sections: [
        {
          h2: "État lisible en un regard",
          p: "Le statut du projet, les jalons et les écarts se lisent ensemble, sans tableur parallèle.",
          cards: [
            { h3: "Jalons", p: "Placez les jalons sur le planning et suivez leur franchissement par rapport à la référence." },
            { h3: "Statut consolidé", p: "Rassemblez l'avancement, les retards et les risques dans une vue de contrôle unique." },
            { h3: "Actions correctives", p: "Consignez qui fait quoi et quand, avec un lien vers le travail concerné." },
          ],
        },
        {
          h2: "Décider sur des faits",
          p: "Chaque relevé de contrôle est relié aux données du projet qui l'ont produit.",
          cards: [
            { h3: "Écarts expliqués", p: "Comparez prévu et réalisé sans perdre l'origine de l'écart." },
            { h3: "Responsabilités", p: "Les actions suivent les rôles vérifiés par le serveur." },
            { h3: "Historique", p: "Les relevés restent datés pour reconstituer une décision passée." },
          ],
        },
      ],
      cta: { title: "Voir le contrôle", text: "Consultez statut et jalons dans l'espace de travail.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-resources",
      path: "features/resources/",
      title: "CUBI Ressources | Affectations, disponibilité et charge",
      description:
        "Planifiez les affectations à partir des ressources et des calendriers, et voyez la charge réelle plutôt qu'une estimation isolée.",
      eyebrow: "Fonctions · Ressources",
      h1: "Des affectations fondées sur la disponibilité",
      lead:
        "Planifiez les personnes et les moyens depuis un registre de ressources commun, avec des calendriers qui expliquent chaque jour ouvré.",
      sections: [
        {
          h2: "Un registre commun",
          p: "Les ressources et les affectations partagent le même registre que le planning et la coûtenance.",
          cards: [
            { h3: "Registre de ressources", p: "Décrivez personnes, équipes et moyens une seule fois pour tout le projet." },
            { h3: "Affectations", p: "Affectez une ressource à une activité avec une période et une charge explicites." },
            { h3: "Disponibilité", p: "Les calendriers de ressources rendent les jours réellement disponibles lisibles." },
          ],
        },
        {
          h2: "Charge visible",
          p: "La charge se calcule à partir des affectations réelles, pas d'un total saisi à la main.",
          cards: [
            { h3: "Surcharge", p: "Repérez les périodes où une ressource est engagée au-delà de sa capacité." },
            { h3: "Équilibrage", p: "Déplacez ou ajustez une affectation et voyez l'effet sur le planning." },
            { h3: "Coûts reliés", p: "Les affectations alimentent la coûtenance sans double saisie." },
          ],
        },
      ],
      cta: { title: "Voir les ressources", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-cost",
      path: "features/cost/",
      title: "CUBI Coûts | Budget, engagements et suivi",
      description:
        "Reliez budget, affectations et engagement pour suivre le coût là où le travail se produit, avec un historique daté.",
      eyebrow: "Fonctions · Coûts",
      h1: "Le coût là où le travail se produit",
      lead:
        "Le budget, les affectations et les dépenses engagées partagent les mêmes données de projet, si bien que le coût ne se reconstitue pas après coup.",
      sections: [
        {
          h2: "Du budget au détail",
          p: "Le budget se décompose en postes reliés aux activités et aux ressources.",
          cards: [
            { h3: "Budget structuré", p: "Répartissez le budget par poste et rattachez-le au WBS." },
            { h3: "Coût dérivé", p: "Le coût prévu se calcule à partir des affectations et des tarifs saisis." },
            { h3: "Engagement", p: "Distinguez ce qui est engagé de ce qui est seulement prévu." },
          ],
        },
        {
          h2: "Comparer sans ambiguïté",
          p: "Prévu, engagé et réalisé restent des séries distinctes, comparables sur une même base.",
          cards: [
            { h3: "Écart lisible", p: "Comparez prévu et réalisé et gardez la raison de l'écart." },
            { h3: "Historique daté", p: "Chaque relevé de coût reste daté pour expliquer une décision passée." },
            { h3: "Devise unique", p: "Le projet tient une devise de référence explicite." },
          ],
        },
      ],
      cta: { title: "Voir les coûts", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-documents",
      path: "features/documents/",
      title: "CUBI Documents | Registre, versions et traçabilité",
      description:
        "Gardez les documents du projet dans un registre versionné et reliez-les au travail qu'ils autorisent.",
      eyebrow: "Fonctions · Documents",
      h1: "Un registre de projet qui reste vrai",
      lead:
        "Les documents vivent dans un registre partagé, avec des versions et un lien vers les activités concernées.",
      sections: [
        {
          h2: "Registre et versions",
          p: "Chaque document a une place, un propriétaire et un historique de versions.",
          cards: [
            { h3: "Registre", p: "Classez les documents par projet et par type, sans doublon." },
            { h3: "Versions", p: "Conservez les versions successives et sachez laquelle fait foi." },
            { h3: "Propriété", p: "Un document a un responsable identifié dans le projet." },
          ],
        },
        {
          h2: "Relié au travail",
          p: "Un document n'est pas une pièce isolée : il se rattache aux activités et aux inspections.",
          cards: [
            { h3: "Liens utiles", p: "Rattachez un document à une activité, un jalon ou une inspection." },
            { h3: "Traçabilité", p: "Retrouvez qui a produit ou validé un document et quand." },
            { h3: "Accès par rôle", p: "L'accès suit les rôles contrôlés côté serveur." },
          ],
        },
      ],
      cta: { title: "Voir le registre", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-risks",
      path: "features/risks/",
      title: "CUBI Risques | Registre, impact et réponse",
      description:
        "Tenez un registre des risques qui relie chaque risque à son impact sur le planning et aux actions de réponse.",
      eyebrow: "Fonctions · Risques",
      h1: "Un registre de risques qui agit",
      lead:
        "Chaque risque a un porteur, une probabilité, un impact et une réponse, et se relie au planning qu'il peut affecter.",
      sections: [
        {
          h2: "Décrire avant de réagir",
          p: "Un registre clair permet de comparer les risques sur la même échelle.",
          cards: [
            { h3: "Fiche de risque", p: "Décrivez le risque, son porteur et sa zone du projet." },
            { h3: "Probabilité et impact", p: "Évaluez chaque risque sur une échelle commune, sans notation cachée." },
            { h3: "Réponses", p: "Associez une réponse, un responsable et une échéance." },
          ],
        },
        {
          h2: "Relié au planning",
          p: "Un risque qui menace une activité ou un jalon se voit dans le contrôle du projet.",
          cards: [
            { h3: "Impact daté", p: "Rattachez le risque à l'activité ou au jalon qu'il menace." },
            { h3: "Suivi", p: "Un risque ouvert reste visible jusqu'à sa clôture explicite." },
            { h3: "Historique", p: "Les changements de statut restent datés." },
          ],
        },
      ],
      cta: { title: "Voir le registre", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-reporting",
      path: "features/reporting/",
      title: "CUBI Rapports | Avancement, coûts et charge",
      description:
        "Produisez des rapports à partir des données du projet, sans ressaisie ni copie de chiffres dans un document séparé.",
      eyebrow: "Fonctions · Rapports",
      h1: "Des rapports issus des données réelles",
      lead:
        "Les rapports lisent le planning, les coûts et les ressources là où ils sont stockés, si bien qu'un chiffre publié reste rattachable.",
      sections: [
        {
          h2: "Une source unique",
          p: "Un rapport ne recalcule pas le projet dans un tableur : il lit les données enregistrées.",
          cards: [
            { h3: "Avancement", p: "Montrez le travail achevé par rapport à une référence claire." },
            { h3: "Coûts", p: "Présentez prévu, engagé et réalisé sur la même base." },
            { h3: "Ressources", p: "Affichez la charge réelle issue des affectations." },
          ],
        },
        {
          h2: "Partage maîtrisé",
          p: "Un rapport publié garde la date et le périmètre de ses données.",
          cards: [
            { h3: "Périmètre", p: "Chaque rapport indique le projet et la période couverts." },
            { h3: "Cohérence", p: "Les chiffres restent cohérents avec ce que montre l'espace de travail." },
            { h3: "Accès", p: "Seuls les rôles autorisés voient les rapports du projet." },
          ],
        },
      ],
      cta: { title: "Voir les rapports", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "features-ai-assistant",
      path: "features/ai-assistant/",
      title: "CUBI Assistant | Aide contextuelle sur le produit",
      description:
        "Un assistant qui répond à partir de l'aide officielle et des capacités réelles du produit, sans inventer de fonctions.",
      eyebrow: "Fonctions · Assistant",
      h1: "Une aide qui reste dans le produit",
      lead:
        "L'assistant s'appuie sur l'aide officielle et le registre des capacités pour orienter vers l'écran et le rôle justes.",
      sections: [
        {
          h2: "Réponses sourcées",
          p: "L'assistant renvoie à l'aide officielle au lieu de décrire des fonctions qui n'existent pas.",
          cards: [
            { h3: "Aide officielle", p: "Les réponses s'appuient sur la documentation du produit publiée." },
            { h3: "Capacités réelles", p: "Le registre des capacités indique ce qui est disponible et pour quel rôle." },
            { h3: "Pas d'invention", p: "Quand l'information manque, l'assistant le dit au lieu de deviner." },
          ],
        },
        {
          h2: "Au bon endroit",
          p: "L'aide s'ouvre dans le contexte de l'écran où vous travaillez.",
          cards: [
            { h3: "Contexte", p: "L'aide se rattache à la page et à la tâche en cours." },
            { h3: "Rôles", p: "L'assistant tient compte des droits vérifiés par le serveur." },
            { h3: "Langues", p: "La documentation reste disponible dans les langues publiées." },
          ],
        },
      ],
      cta: { title: "Essayer l'assistant", text: "Ouvrez l'espace de travail avec votre compte.", label: "Ouvrir l'espace de travail", href: "/app/" },
    },
    {
      id: "integrations",
      path: "integrations/",
      title: "CUBI Intégrations | Échange de données de projet",
      description:
        "Échangez les données de projet par des points d'interface explicites, sans créer un second système de référence.",
      eyebrow: "Plateforme · Intégrations",
      h1: "Échanger les données sans dupliquer le système",
      lead:
        "Les intégrations lisent et écrivent par les interfaces du produit, et le projet reste la source de vérité.",
      sections: [
        {
          h2: "Interfaces explicites",
          p: "Les échanges passent par des points d'entrée documentés plutôt que par une copie de base.",
          cards: [
            { h3: "API de projet", p: "Les données de projet s'échangent par des interfaces documentées." },
            { h3: "Import et export", p: "Importez ou exportez des structures de projet sans casser la référence." },
            { h3: "Identité", p: "Les échanges respectent l'identité et les rôles du compte." },
          ],
        },
        {
          h2: "Pas de second système",
          p: "Une intégration ne crée pas un schéma parallèle : le projet reste unique.",
          cards: [
            { h3: "Source unique", p: "Le projet reste la référence, y compris après un échange." },
            { h3: "Traçabilité", p: "Les échanges restent identifiables dans l'historique." },
            { h3: "Accompagnement", p: "Décrivez votre besoin d'intégration à l'équipe." },
          ],
        },
      ],
      cta: { title: "Planifier une intégration", text: "Parlez-nous de vos systèmes.", label: "Nous contacter", href: "/fr/contact/" },
    },
    {
      id: "help",
      path: "help/",
      title: "CUBI Aide | Documentation et assistance",
      description:
        "Trouvez la documentation officielle, les guides de tâches et le contact d'assistance pour votre projet.",
      eyebrow: "Assistance",
      h1: "L'aide officielle, au même endroit",
      lead:
        "La documentation décrit les écrans et les tâches réels ; le contact d'assistance sert quand il faut une réponse sur votre compte.",
      sections: [
        {
          h2: "Commencer par la documentation",
          p: "La documentation officielle couvre les tâches du quotidien et les concepts du produit.",
          cards: [
            { h3: "Guides de tâches", p: "Suivez des étapes pour créer un projet, un WBS ou un rapport." },
            { h3: "Concepts", p: "Comprenez comment planning, coûts et ressources partagent les mêmes données." },
            { h3: "Langues", p: "La documentation suit les langues publiées du produit." },
          ],
        },
        {
          h2: "Contacter l'assistance",
          p: "Pour une question de compte ou un incident, le contact direct reste le plus rapide.",
          cards: [
            { h3: "Compte", p: "Indiquez l'adresse du compte et l'environnement concerné." },
            { h3: "Incident", p: "Décrivez l'écran, l'action et la date d'apparition." },
            { h3: "Sécurité", p: "Signalez immédiatement tout problème de sécurité suspecté." },
          ],
        },
      ],
      cta: { title: "Continuer", text: "Connectez-vous et ouvrez votre projet.", label: "Se connecter", href: "/login?next=/environments/" },
    },
    {
      id: "faq",
      path: "faq/",
      title: "CUBI FAQ | Questions fréquentes",
      description:
        "Réponses directes sur les comptes, les projets, les données et l'assistance du produit.",
      eyebrow: "Assistance · FAQ",
      h1: "Les questions qui reviennent",
      lead:
        "Des réponses courtes sur le compte, les projets et les données, avec un chemin clair vers l'assistance.",
      sections: [
        {
          h2: "Compte et accès",
          p: "Les accès suivent les rôles vérifiés par le serveur, pas un réglage local.",
          cards: [
            { h3: "Créer un compte", p: "Ouvrez l'espace de travail puis connectez-vous avec votre compte." },
            { h3: "Rôles", p: "Chaque rôle ouvre les écrans et les actions qui lui sont autorisés." },
            { h3: "Environnements", p: "Un compte ouvre les environnements auxquels il est rattaché." },
          ],
        },
        {
          h2: "Données et assistance",
          p: "Les données de projet restent dans le système du produit, pas dans un fichier séparé.",
          cards: [
            { h3: "Données de projet", p: "Un projet garde une seule source pour le planning, les coûts et les documents." },
            { h3: "Assistance", p: "Écrivez-nous avec l'adresse du compte et le projet concerné." },
            { h3: "Sécurité", p: "Signalez toute faille suspectée sans attendre." },
          ],
        },
      ],
      cta: { title: "Une autre question ?", text: "Écrivez-nous avec le compte et le projet.", label: "Nous contacter", href: "/fr/contact/" },
    },
    {
      id: "security",
      path: "security/",
      title: "CUBI Sécurité | Identité, rôles et données",
      description:
        "La sécurité repose sur une identité vérifiée, des rôles contrôlés côté serveur et des données de projet isolées.",
      eyebrow: "Plateforme · Sécurité",
      h1: "L'accès se décide côté serveur",
      lead:
        "Chaque requête passe par une identité authentifiée et un contrôle de rôle avant d'atteindre les données du projet.",
      sections: [
        {
          h2: "Identité et rôles",
          p: "L'application ne fait pas confiance à l'interface pour décider qui peut agir.",
          cards: [
            { h3: "Authentification", p: "Chaque requête porte une identité authentifiée." },
            { h3: "Autorisation", p: "Le serveur vérifie le rôle avant chaque action sur le projet." },
            { h3: "Isolation", p: "Les données d'un projet restent séparées de celles des autres." },
          ],
        },
        {
          h2: "Données et transparence",
          p: "Les secrets restent hors du code et des journaux.",
          cards: [
            { h3: "Secrets", p: "Les secrets de déploiement ne sont ni versionnés ni écrits dans les journaux." },
            { h3: "Journalisation", p: "Les actions sensibles laissent une trace exploitable." },
            { h3: "Signalement", p: "Les problèmes de sécurité se signalent directement à l'équipe." },
          ],
        },
      ],
      cta: { title: "Voir la sécurité", text: "Identité et accès sont détaillés dans la documentation.", label: "Documentation", href: "/fr/documentation/" },
    },
    {
      id: "payments",
      path: "payments/",
      title: "CUBI Paiements | Abonnement et facturation",
      description:
        "Comprendre l'abonnement, la facturation et le passage au plan payant sans ambiguïté sur le périmètre.",
      eyebrow: "Plateforme · Paiements",
      h1: "Un abonnement clair",
      lead:
        "Le plan choisi détermine les fonctions ouvertes au compte ; la facturation reste séparée des données de projet.",
      sections: [
        {
          h2: "Choisir un plan",
          p: "Les plans se comparent sur les fonctions réellement ouvertes.",
          cards: [
            { h3: "Plans", p: "Comparez les plans sur la page des tarifs." },
            { h3: "Périmètre", p: "Un plan ouvre un ensemble défini de fonctions du compte." },
            { h3: "Évolution", p: "Un changement de plan suit la procédure de facturation en vigueur." },
          ],
        },
        {
          h2: "Facturation",
          p: "La facturation concerne le compte, pas le contenu du projet.",
          cards: [
            { h3: "Paiement", p: "Le paiement s'effectue par le circuit de facturation du produit." },
            { h3: "Données", p: "Les informations de paiement ne sont pas stockées dans le projet." },
            { h3: "Question", p: "Pour une question de facturation, écrivez avec l'adresse du compte." },
          ],
        },
      ],
      cta: { title: "Passer à Pro", text: "Le paiement se fait sur la page des tarifs.", label: "Voir les tarifs", href: "/pricing/" },
    },
    {
      id: "get-started",
      path: "get-started/",
      title: "CUBI Démarrage | Premier projet",
      description:
        "Créer un compte, ouvrir un environnement et poser les premières bases d'un projet dans l'espace de travail.",
      eyebrow: "Démarrage",
      h1: "Votre premier projet, étape par étape",
      lead:
        "Connectez-vous, ouvrez un environnement autorisé, puis créez la structure du projet avant d'ajouter le détail.",
      sections: [
        {
          h2: "Les premières étapes",
          p: "Le parcours suit l'ordre du produit : compte, environnement, projet, structure.",
          cards: [
            { h3: "Se connecter", p: "Ouvrez la page de connexion et saisissez votre compte." },
            { h3: "Ouvrir un environnement", p: "Choisissez un environnement auquel votre compte est rattaché." },
            { h3: "Créer la structure", p: "Commencez par le WBS, puis ajoutez les activités." },
          ],
        },
        {
          h2: "Éviter les pièges",
          p: "Un projet se construit sur une source unique, pas sur des copies parallèles.",
          cards: [
            { h3: "Une source", p: "Gardez planning, coûts et documents dans le même projet." },
            { h3: "Rôles", p: "Donnez à chaque personne le rôle dont elle a besoin, pas plus." },
            { h3: "Assistance", p: "En cas de blocage, écrivez avec le compte et l'écran concernés." },
          ],
        },
      ],
      cta: { title: "Commencer", text: "Connectez-vous et ouvrez votre premier projet.", label: "Se connecter", href: "/login?next=/environments/" },
    },
    {
      id: "privacy",
      path: "privacy/",
      title: "CUBI Confidentialité | Données et respect",
      description:
        "Quelles données le produit traite, pourquoi, et comment exercer vos droits sur votre compte.",
      eyebrow: "Mentions · Confidentialité",
      h1: "Les données de projet restent dans le projet",
      lead:
        "Le produit traite les données nécessaires au compte et au projet, et rien de plus que ce que la fonction demande.",
      sections: [
        {
          h2: "Ce que nous traitons",
          p: "Les données servent le compte, le projet et l'assistance.",
          cards: [
            { h3: "Compte", p: "Les informations de compte servent l'authentification et les rôles." },
            { h3: "Projet", p: "Les données de projet servent le planning, les coûts et les documents." },
            { h3: "Journaux", p: "Les journaux techniques servent la sécurité et le diagnostic." },
          ],
        },
        {
          h2: "Vos droits",
          p: "Vous pouvez demander l'accès, la correction ou la suppression selon le contrat applicable.",
          cards: [
            { h3: "Accès", p: "Demandez une copie des données de votre compte." },
            { h3: "Correction", p: "Signalez une donnée inexacte pour correction." },
            { h3: "Contact", p: "Écrivez avec l'adresse du compte et l'objet de la demande." },
          ],
        },
      ],
      cta: { title: "Une question de confidentialité ?", text: "Écrivez-nous avec le compte et l'objet.", label: "Nous contacter", href: "/fr/contact/" },
    },
    {
      id: "terms",
      path: "terms/",
      title: "CUBI Conditions | Utilisation du service",
      description:
        "Les conditions d'utilisation du service, du compte et des données de projet.",
      eyebrow: "Mentions · Conditions",
      h1: "Les règles d'usage, sans détour",
      lead:
        "Les conditions décrivent ce que le service fournit, ce que le compte doit respecter et comment il peut évoluer.",
      sections: [
        {
          h2: "Usage du service",
          p: "Le service se fournit tel que décrit, avec les évolutions annoncées.",
          cards: [
            { h3: "Compte", p: "Le compte reste responsable de ses identifiants et de ses accès." },
            { h3: "Usage loyal", p: "Le service ne doit pas servir à contourner les contrôles d'accès." },
            { h3: "Disponibilité", p: "Les évolutions et interruptions sont annoncées selon le contrat." },
          ],
        },
        {
          h2: "Données et responsabilité",
          p: "Les données de projet appartiennent au client ; le produit les traite pour le service.",
          cards: [
            { h3: "Propriété", p: "Le client conserve la propriété de ses données de projet." },
            { h3: "Sauvegarde", p: "Les modalités de sauvegarde suivent le contrat applicable." },
            { h3: "Contact", p: "Pour une question juridique, écrivez avec l'objet concerné." },
          ],
        },
      ],
      cta: { title: "Une question sur les conditions ?", text: "Écrivez-nous avec le compte et l'objet.", label: "Nous contacter", href: "/fr/contact/" },
    },
    {
      id: "about",
      path: "about/",
      title: "CUBI À propos | La plateforme et l'équipe",
      description:
        "Ce que fait la plateforme CUBI et comment elle aborde le travail de projet.",
      eyebrow: "À propos",
      h1: "Une plateforme pour le travail de projet réel",
      lead:
        "CUBI réunit planning, contrôle, ressources, coûts et documents dans un espace de travail unique et traçable.",
      sections: [
        {
          h2: "Notre approche",
          p: "Un projet tient sur une source unique, pas sur des copies dispersées.",
          cards: [
            { h3: "Une source", p: "Planning, coûts et documents partagent les mêmes données de projet." },
            { h3: "Traçabilité", p: "Chaque chiffre publié se rattache aux données qui l'ont produit." },
            { h3: "Contrôle serveur", p: "Les rôles se vérifient côté serveur, pas dans l'interface." },
          ],
        },
        {
          h2: "Comment nous travaillons",
          p: "Les pages publiques décrivent ; les données de projet restent dans l'espace de travail authentifié.",
          cards: [
            { h3: "Rôles clairs", p: "L'accès suit les rôles contrôlés par le serveur." },
            { h3: "Preuves", p: "Chaque affirmation s'appuie sur des données réellement tenues par le produit." },
            { h3: "Contact", p: "Nous répondons directement aux questions de compte ou de projet." },
          ],
        },
      ],
      cta: { title: "Parlons-en", text: "Racontez-nous votre projet.", label: "Nous contacter", href: "/fr/contact/" },
    },
  ],
};
