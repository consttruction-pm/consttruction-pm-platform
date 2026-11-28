// English copy for the CUBI public site.
// Only routes rendered by the generator live here; the long-form pages that
// already ship as hand-written documents (home, platform, solutions, pricing,
// resources, contact, about, help) keep their existing files.
export default {
  code: "en",
  htmlLang: "en",
  dir: "ltr",
  prefix: "",
  label: "English",
  nav: {
    home: "Home",
    platform: "Platform",
    features: "Features",
    solutions: "Solutions",
    pricing: "Pricing",
    resources: "Resources",
    documentation: "Documentation",
    help: "Help Center",
    about: "About",
    contact: "Contact",
  },
  footer: {
    tagline: "© 2026 CUBI Platform · Plan. Control. Build Smarter.",
    groups: [
      { title: "Product", links: [["features", "Features"], ["platform", "Platform"], ["integrations", "Integrations"], ["pricing", "Pricing"]] },
      { title: "Learn", links: [["documentation", "Documentation"], ["help", "Help Center"], ["faq", "FAQ"], ["resources", "Resources"]] },
      { title: "Company", links: [["about", "About"], ["security", "Security"], ["terms", "Terms"], ["privacy", "Privacy"]] },
    ],
  },
  cta: { label: "Open CUBI workspace", href: "/app/" },
  pages: [
    {
      id: "features",
      path: "features/",
      title: "CUBI Features | Planning, Controls, Cost and AI Assistance",
      description:
        "See how CUBI connects planning and scheduling, project controls, resources, cost, documents, risks, reporting and AI project assistance inside one workspace.",
      eyebrow: "CUBI FEATURES",
      h1: "Every capability connected to the work",
      lead:
        "CUBI organises the plan, the evidence and the decisions in one project workspace. Feature availability depends on the environment your account is authorised for.",
      sections: [
        {
          h2: "Plan and control in one place",
          p: "Each capability shares the same project, calendar and activity record, so a change in the plan is visible to the controls that depend on it.",
          cards: [
            { h3: "Planning and scheduling", p: "Work breakdown structures, activities, calendars, relationships, baselines and progress in a schedule-centred workflow." },
            { h3: "Project controls", p: "Milestones, schedule status, performance indicators and decision points in one consistent operating view." },
            { h3: "Resources and cost", p: "Resource planning, assignments and cost visibility connected to the activities they belong to." },
          ],
        },
        {
          h2: "Evidence and insight",
          p: "Records stay close to the activities and decisions they inform, and reporting reads the same data the team works in.",
          cards: [
            { h3: "Documents and contracts", p: "Keep project records, contract information and supporting evidence next to the work they belong to." },
            { h3: "Risks and issues", p: "Track risks and issues against the activities and dates they threaten, without a separate register to maintain." },
            { h3: "AI project assistance", p: "Use project context to organise information and prepare summaries for user-directed work." },
          ],
        },
      ],
    },
    {
      id: "features-scheduling",
      path: "features/scheduling/",
      title: "CUBI Scheduling | Work Breakdown, Activities and Calendars",
      description:
        "Build work breakdown structures, activities, calendars, relationships, baselines and progress in a schedule-centred construction workflow.",
      eyebrow: "FEATURES · SCHEDULING",
      h1: "A schedule the whole team can trust",
      lead:
        "Plan work from the work breakdown structure down to the activity, keep calendars and relationships explicit, and compare progress against a stored baseline.",
      sections: [
        {
          h2: "Structure before detail",
          p: "The work breakdown structure, activities and relationships share one project record, so structure and detail never drift apart.",
          cards: [
            { h3: "Work breakdown structure", p: "Organise deliverables and work packages into a hierarchy the team can navigate." },
            { h3: "Activities and relationships", p: "Define activities with durations, calendars and dependencies that reflect how the work is actually sequenced." },
            { h3: "Calendars and working time", p: "Keep working days, holidays and shift patterns explicit so dates are calculated from real working time." },
          ],
        },
        {
          h2: "Baselines and progress",
          p: "Store a baseline before work starts, then record progress against it instead of editing history.",
          cards: [
            { h3: "Baselines", p: "Keep the approved plan intact and compare it with current dates and durations." },
            { h3: "Progress and status", p: "Record actual starts and finishes so status reflects what happened, not what was planned." },
            { h3: "Layouts and views", p: "Save the columns, grouping and layout each role needs without changing the underlying data." },
          ],
        },
      ],
    },
    {
      id: "features-project-controls",
      path: "features/project-controls/",
      title: "CUBI Project Controls | Milestones, Status and Performance",
      description:
        "Bring milestones, schedule status, performance indicators and decision points into one consistent project operating view.",
      eyebrow: "FEATURES · PROJECT CONTROLS",
      h1: "Controls that read the same plan",
      lead:
        "Project controls only work when they measure the plan the team actually executes. CUBI keeps status, milestones and indicators on the same project record.",
      sections: [
        {
          h2: "One operating view",
          p: "Milestones, status and indicators are derived from the schedule rather than maintained in a parallel spreadsheet.",
          cards: [
            { h3: "Milestones", p: "Track contractual and internal milestones against the activities that drive them." },
            { h3: "Schedule status", p: "See where the plan stands today against the baseline, by project and by work package." },
            { h3: "Performance indicators", p: "Review indicators built on the same dates and progress the team records." },
          ],
        },
        {
          h2: "Decisions with evidence",
          p: "Each control point links back to the activities, documents and records that explain it.",
          cards: [
            { h3: "Decision log", p: "Keep the reasoning behind a schedule or cost decision close to the record it changed." },
            { h3: "Thresholds and alerts", p: "Define the thresholds that matter and surface them before they become surprises." },
            { h3: "Reporting", p: "Produce reports from the same data the workspace uses, not from a re-keyed copy." },
          ],
        },
      ],
    },
    {
      id: "features-resources",
      path: "features/resources/",
      title: "CUBI Resources | Resource Planning and Assignments",
      description:
        "Plan resources, roles and assignments against real activities and calendars so demand and availability stay visible.",
      eyebrow: "FEATURES · RESOURCES",
      h1: "Resource demand tied to the plan",
      lead:
        "Resources, roles and assignments belong to the activities that need them, so demand and availability are read from the same schedule the team executes.",
      sections: [
        {
          h2: "From role to assignment",
          p: "Define what the work needs, then assign it to the people and equipment that can deliver it.",
          cards: [
            { h3: "Resources and roles", p: "Keep people, equipment and roles in one catalogue shared by every project." },
            { h3: "Assignments", p: "Attach resources to activities with the quantity and duration the work requires." },
            { h3: "Availability", p: "Read demand and availability together instead of reconciling two systems afterwards." },
          ],
        },
        {
          h2: "Planning against reality",
          p: "Assignment data follows the activity calendar, so an approved calendar change updates the demand it implies.",
          cards: [
            { h3: "Calendar-aware planning", p: "Calculate resource demand from real working time rather than nominal days." },
            { h3: "Role coverage", p: "See which roles are over-committed before the schedule is released." },
            { h3: "Links to cost", p: "Carry assignments into cost visibility without a second data entry step." },
          ],
        },
      ],
    },
    {
      id: "features-cost",
      path: "features/cost/",
      title: "CUBI Cost | Cost Visibility Connected to Activities",
      description:
        "Connect expenses and cost visibility to the activities, resources and progress they belong to, instead of a separate cost file.",
      eyebrow: "FEATURES · COST",
      h1: "Cost where the work happens",
      lead:
        "Cost information is most useful when it is attached to the activity that generated it. CUBI keeps expenses and cost records in the project they belong to.",
      sections: [
        {
          h2: "Expenses and records",
          p: "Record what was spent against the work item it belongs to, with the evidence attached.",
          cards: [
            { h3: "Expenses", p: "Capture project expenses against activities and work packages with a clear audit trail." },
            { h3: "Cost visibility", p: "Review cost by project, activity and work package from the same workspace." },
            { h3: "Supporting evidence", p: "Keep the document or record that justifies a cost next to the cost itself." },
          ],
        },
        {
          h2: "Connected to progress",
          p: "Cost and progress are read together, so an earned-value conversation starts from consistent data.",
          cards: [
            { h3: "Progress linkage", p: "Compare spend with recorded progress rather than with an outdated percentage." },
            { h3: "Currency clarity", p: "Record the currency and working price explicitly so totals are never guessed." },
            { h3: "Reporting", p: "Report cost from live project data, not a monthly re-keyed summary." },
          ],
        },
      ],
    },
    {
      id: "features-documents",
      path: "features/documents/",
      title: "CUBI Documents | Project Records and Contracts in Context",
      description:
        "Keep project documents, contract information and supporting evidence close to the activities and decisions they inform.",
      eyebrow: "FEATURES · DOCUMENTS",
      h1: "Records next to the work",
      lead:
        "A document is only useful when it can be found from the activity it explains. CUBI keeps records and evidence in the project context.",
      sections: [
        {
          h2: "A single project record",
          p: "Documents and contracts are attached to the project, work package or activity they belong to.",
          cards: [
            { h3: "Project documents", p: "Store and find the drawings, submittals and records a project depends on." },
            { h3: "Contracts", p: "Keep contract information next to the schedule and cost records it governs." },
            { h3: "Evidence", p: "Attach the evidence that supports progress, cost or a decision." },
          ],
        },
        {
          h2: "Findable and accountable",
          p: "Every record keeps its owner and history, so the team knows what it is looking at.",
          cards: [
            { h3: "Ownership", p: "Record who uploaded a document and when, with the project scope preserved." },
            { h3: "Version awareness", p: "Avoid acting on a superseded document by keeping its context visible." },
            { h3: "Access boundaries", p: "Document access follows the same project membership as the rest of the workspace." },
          ],
        },
      ],
    },
    {
      id: "features-risks",
      path: "features/risks/",
      title: "CUBI Risks | Risks and Issues Against the Plan",
      description:
        "Track risks and issues against the activities, dates and owners they affect, without maintaining a separate register.",
      eyebrow: "FEATURES · RISKS",
      h1: "Risks attached to real dates",
      lead:
        "A risk register that sits outside the schedule cannot show what a risk would delay. CUBI keeps risks and issues in the project record.",
      sections: [
        {
          h2: "Register in context",
          p: "Risks and issues reference the activities and milestones they threaten, so exposure is visible where it matters.",
          cards: [
            { h3: "Risk register", p: "Capture probability, impact, owner and response for each risk." },
            { h3: "Issues", p: "Track issues that have already happened, with the activity they affect." },
            { h3: "Ownership", p: "Give every risk and issue a named owner and a review date." },
          ],
        },
        {
          h2: "From exposure to action",
          p: "Link a response to the schedule or cost record it changes, so mitigation is more than a note.",
          cards: [
            { h3: "Responses", p: "Record the chosen response and the activities it modifies." },
            { h3: "Thresholds", p: "Escalate when exposure passes the threshold the project defined." },
            { h3: "Review history", p: "Keep the assessment history so a decision can be explained later." },
          ],
        },
      ],
    },
    {
      id: "features-reporting",
      path: "features/reporting/",
      title: "CUBI Reporting | Reports From Live Project Data",
      description:
        "Produce project reports from the same data the workspace uses, with saved layouts and consistent definitions.",
      eyebrow: "FEATURES · REPORTING",
      h1: "One definition, many reports",
      lead:
        "Reports are only comparable when they share definitions. CUBI builds reports from the project data the team works in every day.",
      sections: [
        {
          h2: "Report from the source",
          p: "No export-and-rekey step: reporting reads the project record directly.",
          cards: [
            { h3: "Saved layouts", p: "Keep the columns, grouping and filters each audience expects." },
            { h3: "Schedule reports", p: "Report dates, progress and variance from the calculated schedule." },
            { h3: "Cost and resource reports", p: "Report cost and demand alongside the activities that produced them." },
          ],
        },
        {
          h2: "Consistent by construction",
          p: "Shared definitions mean two reports of the same thing cannot disagree.",
          cards: [
            { h3: "Shared definitions", p: "One definition of progress and variance across every report." },
            { h3: "Period awareness", p: "Report a period knowing which records were valid at the time." },
            { h3: "Audience views", p: "Give each audience the view it needs without duplicating data." },
          ],
        },
      ],
    },
    {
      id: "features-ai-assistant",
      path: "features/ai-assistant/",
      title: "CUBI AI Assistant | Project-Aware Assistance",
      description:
        "Use project context to organise information, prepare summaries and support user-directed project workflows with a visible assistant.",
      eyebrow: "FEATURES · AI ASSISTANCE",
      h1: "An assistant that reads your project context",
      lead:
        "The CUBI assistant works with the project you have open. It helps organise information and prepare summaries; you stay in control of every decision and every write.",
      sections: [
        {
          h2: "Assistance, not autonomy",
          p: "The assistant proposes and drafts. Creating, changing or approving a project record remains a user action.",
          cards: [
            { h3: "Project context", p: "Answers are grounded in the project the session is authorised for." },
            { h3: "Summaries", p: "Turn long project records into a summary you can review." },
            { h3: "Navigation help", p: "Find the window, record or definition you need instead of hunting through menus." },
          ],
        },
        {
          h2: "Visible and bounded",
          p: "The assistant is a visible part of the workspace, bounded by the same permissions as the user.",
          cards: [
            { h3: "Same permissions", p: "The assistant never exceeds the access of the signed-in user." },
            { h3: "Transparent actions", p: "You see what is proposed before anything is written." },
            { h3: "No hidden data paths", p: "Assistance uses the project data and services the product already exposes." },
          ],
        },
      ],
    },
    {
      id: "integrations",
      path: "integrations/",
      title: "CUBI Integrations | Connect Project Data to Your Systems",
      description:
        "Understand how CUBI connects project data to the systems a construction organisation already runs, and what each integration requires.",
      eyebrow: "INTEGRATIONS",
      h1: "Project data that moves with your organisation",
      lead:
        "CUBI exposes project data through a versioned HTTP API and imports and exports the formats project teams exchange. Each integration states what it needs and what it does not do.",
      sections: [
        {
          h2: "How data moves",
          p: "Integrations are explicit: a channel, an owner and a scope. Nothing is synchronised silently.",
          cards: [
            { h3: "HTTP API", p: "A versioned project API for reading and writing project records under the same session and project permissions." },
            { h3: "Import and export", p: "Exchange schedules and project data in the formats your partners and clients expect." },
            { h3: "Documents and evidence", p: "Attach project documents to the records they support so the evidence travels with the data." },
          ],
        },
        {
          h2: "What an integration needs",
          p: "Every connection is scoped to a tenant and a project, and is authenticated like any other client.",
          cards: [
            { h3: "Authentication", p: "Session and credential handling follow the same identity rules as the workspace." },
            { h3: "Project scope", p: "A connection sees only the projects its account is authorised for." },
            { h3: "Change control", p: "Versioned writes and revision checks protect records from silent overwrites." },
          ],
        },
      ],
    },
    {
      id: "documentation",
      path: "documentation/",
      title: "CUBI Documentation | Guides for the Platform and Workspace",
      description:
        "Find the guides that explain environments, project setup, scheduling, controls and data access in CUBI.",
      eyebrow: "DOCUMENTATION",
      h1: "Documentation for the work you do",
      lead:
        "The documentation set follows the product: environments, project setup, scheduling, controls and data access. Each guide states which environment it applies to.",
      sections: [
        {
          h2: "Start here",
          p: "Choose the guide that matches your role and the environment your account can open.",
          cards: [
            { h3: "Getting started", p: "Sign in, choose an environment and open the project you are authorised for." },
            { h3: "Engineering environment", p: "Planning, scheduling, controls and reporting for project delivery teams." },
            { h3: "Enterprise environment", p: "Organisation-level access, roles and the task surface for authorised accounts." },
          ],
        },
        {
          h2: "Reference",
          p: "Reference material for the concepts the product relies on.",
          cards: [
            { h3: "Data and API", p: "How project data is scoped, versioned and read through the API." },
            { h3: "Security and access", p: "How identity, sessions, roles and project membership fit together." },
            { h3: "Glossary", p: "The project-controls terms CUBI uses, with one definition each." },
          ],
        },
      ],
    },
    {
      id: "faq",
      path: "faq/",
      title: "CUBI FAQ | Common Questions Answered",
      description:
        "Answers about environments, accounts, data, security, payments and support for the CUBI platform.",
      eyebrow: "FAQ",
      h1: "Questions we hear most",
      lead:
        "Short, direct answers about accounts, environments, data handling and payments.",
      sections: [
        {
          h2: "Accounts and environments",
          p: "",
          cards: [
            { h3: "Do I need two accounts?", p: "No. One account can open both environments when it carries the roles each environment requires." },
            { h3: "Why does Enterprise ask for a role?", p: "Enterprise exposes organisation-level surfaces. Access follows the role, and the server enforces it." },
            { h3: "Can I switch environment later?", p: "Yes. The environment selector is the entry point and shows only the environments your account is authorised for." },
          ],
        },
        {
          h2: "Data, security and payment",
          p: "",
          cards: [
            { h3: "Where is my project data stored?", p: "In the account's project database. Public marketing pages never hold project records." },
            { h3: "Who can see a project?", p: "Only accounts with membership of that project, within the same tenant." },
            { h3: "When is a payment taken?", p: "Only after a configured payment provider confirms it. If checkout cannot start, no payment is made." },
          ],
        },
      ],
    },
    {
      id: "security",
      path: "security/",
      title: "CUBI Security | Identity, Access and Data Boundaries",
      description:
        "How CUBI handles identity, sessions, project membership, data boundaries and the separation between public pages and project data.",
      eyebrow: "SECURITY",
      h1: "Security stated plainly",
      lead:
        "This page describes what the product actually does today. It is not a certification claim and it does not replace a security review of your own deployment.",
      sections: [
        {
          h2: "Identity and sessions",
          p: "Access starts with an authenticated account and a server-side session.",
          cards: [
            { h3: "Password handling", p: "Passwords are stored as salted scrypt hashes, never in plain text." },
            { h3: "Session handling", p: "Sessions use HttpOnly cookies with CSRF protection on state-changing requests." },
            { h3: "Sign-in throttling", p: "Repeated failed sign-in attempts are rate limited to slow credential guessing." },
          ],
        },
        {
          h2: "Data boundaries",
          p: "Project data is separated by tenant and project, and enforced on the server.",
          cards: [
            { h3: "Tenant and project scope", p: "Every project read and write is scoped to the account's tenant and membership." },
            { h3: "Role-based access", p: "Environment and action access follows the roles the server checks, not the buttons the client shows." },
            { h3: "Public and private surfaces", p: "Marketing pages are static; project records are only served by the authenticated runtime." },
          ],
        },
      ],
    },
    {
      id: "payments",
      path: "payments/",
      title: "CUBI Payments | Pro Subscription and Billing Clarity",
      description:
        "Understand how the CUBI Pro subscription works, what a purchase adds and when a payment is actually taken.",
      eyebrow: "PAYMENTS",
      h1: "Clear billing, no surprises",
      lead:
        "CUBI Pro is purchased in monthly units. The server, not the page, confirms and records the entitlement after a verified payment.",
      sections: [
        {
          h2: "How a purchase works",
          p: "You choose the number of months, review the estimated total and continue to checkout. Nothing is charged by the page itself.",
          cards: [
            { h3: "Monthly units", p: "Twelve months means twelve monthly units purchased together, not a separate annual plan." },
            { h3: "Existing subscriptions", p: "A confirmed purchase extends the existing future expiry date instead of starting over." },
            { h3: "No provider, no charge", p: "If no verified provider is configured, checkout cannot start and no payment is taken." },
          ],
        },
        {
          h2: "Clarity and records",
          p: "Prices and entitlements are recorded explicitly, so a later question can be answered from the record.",
          cards: [
            { h3: "Working price", p: "The configured working price is shown before you continue to checkout." },
            { h3: "Server-side entitlement", p: "Only the server records the entitlement; the browser cannot grant it." },
            { h3: "Refunds and questions", p: "Contact us with the account and payment reference for any billing question." },
          ],
        },
      ],
    },
    {
      id: "get-started",
      path: "get-started/",
      title: "Get Started with CUBI | Open Your First Project",
      description:
        "Sign in, choose the environment your account is authorised for, and open a project in the CUBI workspace.",
      eyebrow: "GET STARTED",
      h1: "Three steps to your first project",
      lead:
        "CUBI separates the public site from the authenticated workspace. Signing in is the only step that opens project data.",
      sections: [
        {
          h2: "The path in",
          p: "Each step is explicit, so you always know which environment and which project you are working in.",
          cards: [
            { h3: "1. Sign in", p: "Use your CUBI account. Failed attempts are throttled; a wrong password never opens a workspace." },
            { h3: "2. Choose an environment", p: "The selector shows Engineering and Enterprise only when your roles allow them." },
            { h3: "3. Open a project", p: "Choose a project you are a member of. The workspace opens scoped to that project." },
          ],
        },
        {
          h2: "If something is missing",
          p: "Access is data, not guesswork. Each missing item has a named cause.",
          cards: [
            { h3: "No project listed", p: "Your account is not a member of any project yet. Ask a project owner to add you." },
            { h3: "Enterprise disabled", p: "Your account lacks an enterprise role. An administrator can grant it." },
            { h3: "Need more detail", p: "The Help Center explains the common cases and how to reach support." },
          ],
        },
      ],
    },
    {
      id: "privacy",
      path: "privacy/",
      title: "CUBI Privacy | What We Collect and Why",
      description:
        "What the CUBI platform collects, why it is collected and how project and account data are separated.",
      eyebrow: "PRIVACY",
      h1: "Privacy in plain language",
      lead:
        "This page explains the data the product handles so you can decide what to share. It is a product description, not a legal opinion.",
      sections: [
        {
          h2: "Account data",
          p: "We keep what is needed to authenticate you and operate the workspace.",
          cards: [
            { h3: "Identity", p: "Account email, a salted password hash and the roles granted to the account." },
            { h3: "Sessions", p: "Session identifiers needed to keep you signed in, invalidated when you sign out." },
            { h3: "Operational logs", p: "Records used to secure the service and diagnose failures." },
          ],
        },
        {
          h2: "Project data",
          p: "Project records belong to the tenant that created them.",
          cards: [
            { h3: "Tenant isolation", p: "A tenant's project records are not served to another tenant's accounts." },
            { h3: "Membership", p: "Within a tenant, only project members can read or write a project's records." },
            { h3: "Public pages", p: "Marketing pages are static and hold no project records." },
          ],
        },
      ],
    },
    {
      id: "terms",
      path: "terms/",
      title: "CUBI Terms | Using the Platform",
      description:
        "The terms that describe acceptable use of the CUBI platform, account responsibility and service boundaries.",
      eyebrow: "TERMS",
      h1: "Terms of use",
      lead:
        "These terms describe how the platform may be used. They are written to be read, not to hide behind.",
      sections: [
        {
          h2: "Your account",
          p: "You are responsible for the account you use and the data you put into it.",
          cards: [
            { h3: "Account responsibility", p: "Keep your credentials private and tell us promptly if you suspect misuse." },
            { h3: "Authorised access", p: "Access only the projects and environments you have been granted." },
            { h3: "Accurate data", p: "Project decisions rely on the data entered, so enter records honestly." },
          ],
        },
        {
          h2: "The service",
          p: "The platform is provided as described, with limits stated where they exist.",
          cards: [
            { h3: "Availability", p: "We work to keep the service available and explain planned interruptions where we can." },
            { h3: "Changes", p: "Features may change; documentation states which environment a capability applies to." },
            { h3: "Ending use", p: "You may stop using the service at any time; your data remains governed by the privacy description." },
          ],
        },
      ],
    },
  ],
};
