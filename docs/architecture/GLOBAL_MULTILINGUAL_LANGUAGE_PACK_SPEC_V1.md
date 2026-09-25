# Global Multilingual & Language Pack Specification v1.0

## Objective
Make the public website, Web application, Desktop application, Mobile applications and AI capabilities multilingual by design, while maximizing speed through local language resources.

## 1. Supported-language model
The product does not hard-code a fixed small language list. It uses a registry-driven model so new languages can be added without rewriting product logic.
Initial release languages are selected commercially, but the architecture remains open to any language for which a validated pack exists.

## 2. Website
- Detect browser language as a suggestion only.
- Allow explicit language selection and persist preference.
- Expose localized URLs and SEO metadata.
- Support RTL/LTR.
- Localize navigation, forms, legal pages, product terminology, structured metadata and error/help text.
- Use locale routes such as /fa, /en and additional BCP 47-compatible locale routes as languages are released.

## 3. Desktop and Mobile
Each client includes a Language Manager with installed languages, available downloads, version/status, preferred language, fallback language, pack size, last update and remove/restore controls.
A language pack can be downloaded before field use and then used without a network connection.

## 4. AI
AI language has four separate layers: UI translation; project-data language/presentation; AI text language; voice input/output.
Support multilingual questions, multilingual answers, translation of structured reports, Smart Guide in preferred language, voice input in installed language and permitted language conversion for generated reports/emails.

## 5. Offline model strategy
For capable devices, downloadable lightweight local AI/voice models can provide offline Smart Guide and voice workflows.
For constrained devices, deterministic multilingual UI/help remains fully offline; AI can fall back to online processing where policy/connectivity permits.
Capability metadata must prevent the UI from promising unavailable offline AI.

## 6. Speed requirements
- UI language switch from local pack should not require network.
- Startup should not download translation resources already installed.
- Packs use compressed artifacts and delta updates where practical.
- Common language resources should be cache/memory friendly.
- Pack verification happens before activation.
- Missing optional resources do not block core application startup.

## 7. Data integrity
Never localize stable IDs, database enum keys, activity/resource codes, internal status values, API property names or calculation units/values.
Localize only presentation-layer text and approved translatable project fields.

## 8. Governance
Language-pack release requires translation completeness, terminology review, RTL/LTR check, date/number/unit check, accessibility review, Web/Desktop/Mobile smoke tests, AI/voice capability declaration and package checksum/signature verification.
No language is release-ready solely because machine translation exists.