// Shared route inventory for the public site generator.
// `id` is the stable key used by navigation, hreflang and the sitemap.
export const ROUTE_PATHS = {
  home: "",
  platform: "platform/",
  features: "features/",
  "features-scheduling": "features/scheduling/",
  "features-project-controls": "features/project-controls/",
  "features-resources": "features/resources/",
  "features-cost": "features/cost/",
  "features-documents": "features/documents/",
  "features-risks": "features/risks/",
  "features-reporting": "features/reporting/",
  "features-ai-assistant": "features/ai-assistant/",
  solutions: "solutions/",
  integrations: "integrations/",
  pricing: "pricing/",
  resources: "resources/",
  documentation: "documentation/",
  help: "help/",
  faq: "faq/",
  about: "about/",
  security: "security/",
  payments: "payments/",
  contact: "contact/",
  "get-started": "get-started/",
  privacy: "privacy/",
  terms: "terms/",
};

// Top navigation order. A locale links to its own translation when one is
// published and falls back to the English route otherwise.
export const NAV_KEYS = [
  "home",
  "platform",
  "features",
  "solutions",
  "pricing",
  "resources",
  "about",
  "contact",
];

// Routes that exist as hand-written long-form documents in English and Persian.
// They are not regenerated; the generator only adds their hreflang alternates.
export const HANDWRITTEN_ROUTES = new Set([
  "home",
  "platform",
  "solutions",
  "pricing",
  "resources",
  "contact",
  "about",
]);

export const REQUIRED_INDEXABLE_ROUTE_COUNT = Object.keys(ROUTE_PATHS).length;
