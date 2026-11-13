# CUBI Subscription, Payment, and Website Administration Requirements

**Status:** Approved product requirements baseline; pricing and provider integration details remain open.  
**Scope:** Public website pricing/payment experience, subscription entitlements, payment-method administration, owner administration panel, and public-content/announcement management.  
**Out of scope for this decision:** On-premises, LAN, satellite, air-gapped, or customer-hosted deployments. No subscription prices are set in this document.

## 1. Product plans shown on the website

The public Plans / Subscription page must present four clear plan cards or sections: **Free**, **Pro**, **Team**, and **Enterprise Cloud**. Each plan must explain its intended audience, included capacity, storage, collaboration rules, and access boundaries. Do not imply that Team or Enterprise has a more powerful scheduling or engineering engine than Pro: all paid professional plans use the same CUBI professional workspace and shared engineering capabilities. Plan differences are capacity, organization, collaboration, storage, and administration.

### 1.1 Free

- Personal account: one personal project, up to 100 Activities, and 100 MB storage.
- Form Builder learning/experience allowance: up to 10 forms; create, save, edit, and preview.
- A Free personal account cannot send forms to other people or create operational workflows.
- A Free user may be invited into a Pro, Team, or Enterprise workflow as a limited participant. They may access only specifically assigned forms/reports, submit requested information, respond to assigned approvals (approve/reject/request correction only where authorized), and use relevant messages.
- Free workflow participants must not receive general project access, the professional workspace, Gantt, WBS/Activities, project-wide documents/search, resources/equipment, cost/financial data, or management dashboards.
- Free participants are outside paid professional-seat caps and may be invited without a fixed commercial participant limit, subject to abuse/rate controls.
- The Free landing/dashboard is an operational inbox for assigned forms, tasks, approvals, messages, and statuses—not a second professional workspace.

### 1.2 Pro

- Full professional CUBI project-management capabilities, including projects, WBS, Activities, scheduling/Gantt, relationships/CPM, calendars, resources, cost/progress, professional reports, documents, Form Builder/workflows, and the professional assistant capabilities that are available to the account.
- Standard storage allowance: 2 GB. Additional storage can be purchased as an add-on; package sizes and prices are pending.
- The owner can create/send forms, receive reports and submissions, define multi-step review/approval workflows, assign stage owners, receive approve/reject/correction outcomes, and communicate about those workflows.
- A Pro owner may invite Free form/workflow participants without a fixed commercial seat cap, subject to abuse/rate controls.
- A Pro subscriber invited into a Team or Enterprise organization may participate under the organization's explicit permissions and scope. Their personal Pro subscription does not itself grant access to organization data and does not consume an organization-paid seat.

### 1.3 Team

- For small and medium companies/contractors managing multiple projects.
- Base organization subscription includes **3 organization-paid professional members**.
- Organization-paid capacity can be increased from 4 through a maximum of **10 organization-paid professional seats**.
- Each additional organization-paid seat adds a charge based on the Pro seat price; the exact amount/formula is not set yet.
- Total professional membership may reach **20 people maximum**, counting organization-paid professional members and invited independent Pro subscribers together. Free form-only participants/readers/approvers are excluded from this 20-person cap.
- Invited independent Pro subscribers use their own Pro subscription and do not consume Team's organization-paid seat allowance.
- Initial shared organization storage: **5 GB**. Additional storage is purchasable; package sizes/prices are pending.
- Multiple projects and organization-level access control.
- Shared dynamic dashboard, with cards/data limited by role and authorized scope.

### 1.4 Enterprise Cloud

- For larger companies, organizations, and holding groups using the CUBI cloud service.
- Base organization subscription includes **10 organization-paid professional members**.
- Organization-paid capacity may increase above 10 with **no fixed upper seat limit**; incremental pricing and volume tiers are pending.
- Independent Pro subscribers may be invited without consuming organization-paid capacity and without a fixed commercial invitation cap; their access remains explicitly permission-scoped.
- Free form-only participants/readers/approvers are unlimited and excluded from paid professional-member capacity.
- Initial shared organization storage: **10 GB**. Additional storage is purchasable; package sizes/prices are pending.
- Multiple projects, company/EPS structures, and holding-level organization use.
- One shared dynamic dashboard engine. Authorized holding-level users may aggregate permitted information across multiple EPS structures, companies, and projects. Company, department, project, WBS, and professional-member views narrow according to role and scope permissions.
- This is **Enterprise Cloud** only for the current scope. Do not add On-Premises/LAN/satellite/private-server options to this page or implementation scope.

## 2. Dashboard and access explanation

Explain on the plan page that dashboard visibility follows role and scope, not merely subscription name:

- Holding-level authorized manager: permitted consolidated view across EPS structures, companies, and projects.
- Company manager: only their company's permitted EPS/projects.
- Unit/department manager: relevant unit and project scope.
- Project manager: permitted projects.
- WBS/section manager: permitted WBS and activities.
- Professional member: assigned projects/tasks and allowed information.
- Free workflow participant: assigned forms, submissions, approvals, messages, and status only.

Use one dynamic dashboard engine, not separate duplicated dashboard products. Enforce authorization in API/data access and report aggregation, not only by hiding interface cards. Initial cards can include project counts, progress/schedule status, overdue items, permitted cost/resource summaries, tasks requiring action, approvals, notifications, and storage/plan status. Advanced portfolio analytics and custom dashboards may be phased later.

## 3. Public payment page and payment channels

The website must provide a clear subscription selection and checkout flow. Pricing is intentionally **not defined yet**. Do not invent, hard-code, or publish prices until the pricing decision is approved. The plan cards and terms can be prepared now, with price values supplied later from managed plan configuration.

Payment channel choices required by the product owner:

1. **USD / WebMoney:** a dollar-denominated payment option using WebMoney.
2. **Cryptocurrency / WebMoney-mediated token flow:** a cryptocurrency payment route associated with WebMoney. After the payment is confirmed, the CUBI application activates/ issues the applicable subscription token or entitlement. Do not assume an unverified gateway/API or claim a crypto asset is directly accepted until the exact WebMoney route and settlement/confirmation mechanism are validated.
3. **Iranian Rial (IRR):** the normal local Rial payment option on the website, intended to become available when the Iranian Rial payment system is operational.
4. **Interim token activation:** before the normal IRR system is enabled, a token activated through the application after a confirmed payment may be used to activate the corresponding CUBI web-application subscription and, where the entitlement is configured to include it, cover the website subscription as well. The token is an entitlement/activation mechanism, not a reason to expose a payment method that the administrator has hidden.

The payment page must show only payment methods currently enabled by the site owner. If a method is hidden/disabled, remove the entire method option from the public page, including its title, logo/icon, explanatory text, instructions, badges, and related checkout controls. Do not leave a disabled card, placeholder, “coming soon” message, or residual explanation visible for a hidden method.

### 3.1 Admin-controlled payment method visibility

The owner/super-admin must be able to enable or hide each payment method independently from the administration panel:
- WebMoney USD;
- cryptocurrency / WebMoney-mediated token route;
- Iranian Rial;
- any future payment method added through an approved extension.

Visibility controls must be separate from provider configuration and operational status. Hiding a method must prevent new checkouts from selecting it; it must not corrupt or erase historical transactions, invoices, subscription records, or audit history. In-progress/paid transactions must be handled safely and consistently. All changes must be audited with actor, timestamp, old/new state, and reason.

Provider credentials, signing secrets, merchant identifiers, callback secrets, and private keys must be stored server-side in secret/configuration storage, never in browser code or public content. Payment callbacks must be authenticated and idempotent; repeated callbacks must not activate duplicate subscriptions or tokens. Keep payment, subscription entitlement, and token activation as separate auditable states. Never activate from a browser success redirect alone; require trusted server-side confirmation or an explicitly audited manual verification path.

## 4. Subscription configuration and future pricing fields

Build the plan/payment page from managed configuration rather than hard-coded card text. Each plan configuration should support:
- plan key and public name;
- short description and target audience;
- feature list and exclusions;
- included organization-paid seats and maximums;
- total professional-member cap (where applicable);
- Free participant rules;
- included storage and purchasable storage add-ons;
- project and Activity/form limits;
- billing currency and price (pending approval);
- billing period (monthly initially; annual billing decision pending);
- seat-addition rule and any volume tiers;
- active/visible status;
- sort order and localized public copy.

Price, billing period, add-on rates, annual discount, prorating, mid-cycle seat changes, downgrade/cancellation/refund rules, and exact token validity/expiry remain **undecided**. Keep these configurable and do not assume defaults as final policy.

## 5. Owner / Super Admin panel

Design a dedicated, secure **Owner / Super Admin** panel for the site owner. It is separate from ordinary organization admin roles. Only the explicitly authorized site owner/super-admin may change global payment visibility, public-site content, plan catalog, global announcements, and other platform-wide settings. Organization admins must not inherit these global powers.

The owner panel should be easy to use without coding and include:

### 5.1 Payment and subscription management
- Enable/hide each payment method independently, with the complete public-page removal behavior specified above.
- Edit plan descriptions, feature lists, limits, included storage, seat rules, visibility, and ordering.
- Add/edit/hide storage add-on packages.
- Configure prices and currencies later, after approval.
- View transactions, payment confirmation status, subscription status, token issuance/activation status, renewals, failures, and audit history.
- Search/filter/export transaction records.
- Provide a safe manual verification/adjustment workflow with mandatory reason and audit record; no silent balance or entitlement changes.

### 5.2 Website content management (WordPress-like ease of use)

Provide a visual, block-based content editor for public website pages so the owner can add/edit content and images without coding or breaking page layout:
- edit public pages such as Home, About, Features, Plans, Help/FAQ, Contact, and news/updates;
- add a new page or article/news item;
- add/edit headings, paragraphs, lists, buttons, links, images, image captions/alt text, and reusable content sections;
- upload/replace/reorder images and manage a simple media library;
- preview responsive layouts before publishing;
- save drafts, schedule publication if supported, publish/unpublish, and preserve revision history;
- restore a previous published revision;
- use safe predefined page sections/templates and layout constraints so ordinary edits cannot accidentally break the website shell or global design;
- support the site's multilingual content structure and RTL/LTR presentation.

The content editor must not permit arbitrary unsafe scripts or untrusted HTML injection. Separate editable content from application layout/components.


### 5.4 Visual asset replacement with exact size guidance

The Owner / Super Admin panel must include a dedicated **Visual Assets / Brand & Media** area for safely replacing the website logo, photos, illustrations, banners, and icons without editing code.

For every editable image/logo/icon slot shown in the page editor or asset manager:
- Display the exact recommended pixel dimensions (width × height) beside that slot's **Replace / Upload** control. Where useful, also show the rendered display size, aspect ratio, supported file formats, maximum file size, and whether transparent background is supported.
- Show a thumbnail/preview of the currently published asset and a preview of the newly selected asset before saving.
- Provide a clearly labeled **Replace** button and a separate **Upload** action where a new asset is being added. The upload/replace control must be adjacent to the dimensions guidance so the owner can see the required size at the moment of selection.
- Validate dimensions, aspect ratio, format, file size, and image integrity before accepting the asset. Explain any mismatch in plain language; do not silently stretch, crop, or distort the image.
- Offer a safe crop/fit preview (contain/cover or approved focal-point crop) where the slot allows it. Preserve original uploads and generate optimized responsive derivatives; do not destructively overwrite the source file.
- Show where the asset is used (for example header logo, footer logo, hero banner, feature card, news thumbnail, app icon, favicon) so replacing it does not unexpectedly alter unrelated locations.
- Allow the owner to choose whether the replacement applies only to the selected page/slot or to all explicitly linked uses. Require a clear confirmation before global replacement.
- Support draft preview before publishing, and preserve asset revision history so the owner can restore the previous image/logo/icon.
- Provide alt text/accessibility description fields and localized asset metadata where relevant.
- If an asset is hidden/removed, ensure the public page uses an approved fallback or intentionally omits the slot; never show a broken-image placeholder.
- Protect the live published asset while an upload is incomplete or fails. Only publish a fully validated replacement after explicit owner confirmation.

The exact pixel dimensions must be defined per asset slot in the CMS design system and maintained as visible metadata, not left for the owner to guess. Include dimensions for desktop/tablet/mobile variants where responsive assets differ. The owner must be able to replace logos, photos, and icons directly from the relevant page/slot as well as from the central media library.

### 5.3 Announcements and group messaging

The owner panel must allow the owner to:
- create a platform announcement or news item;
- send an announcement/message to all users or a selected audience/segment;
- target by subscription plan (Free/Pro/Team/Enterprise), account status, language, or other approved non-sensitive operational criteria;
- preview the message, select delivery channels supported by the product (in-app notification and email/push only where configured), and publish/send;
- choose whether it appears as a site notice, in-app announcement, or both;
- view delivery/recipient counts and delivery outcomes;
- prevent accidental repeated sends and keep an immutable send/audit record;
- respect notification preferences, legal requirements, and unsubscribe controls for non-essential email.

Distinguish public news/articles from private targeted announcements. Never expose one user's private account or project information to another recipient.

## 6. Security, governance, and acceptance criteria

- Enforce owner-only authorization server-side for global settings and content publishing.
- Use MFA/strong re-authentication for sensitive payment/provider and owner-account actions where supported.
- Record append-only audit events for payment-method visibility, plan changes, price changes, content publication/rollback, announcement sends, manual payment verification, and token issuance/revocation.
- Keep payment records, subscription entitlements, and token lifecycle separately traceable and idempotent.
- Use tenant isolation and role/scope checks for organization data and aggregated dashboards.
- Public pricing/payment UI must be responsive and multilingual, with RTL/LTR correctness.
- Hiding a payment method must leave no visible trace of that method on the public checkout page.
- Draft edits must not affect the live website until explicitly published.
- A failed content edit or upload must not corrupt the previously published page.
- The plan page must explain the actual Free/Pro/Team/Enterprise Cloud conditions above and must not claim prices until approved.
- No implementation may weaken or duplicate the single approved CUBI Visual Workspace or introduce a second professional workspace/dashboard.
- No on-premises, LAN, satellite, or air-gapped deployment scope is introduced by this work.

## 7. Decisions deliberately deferred to the pricing/payment-design phase

The following are not approved yet and must be discussed before production pricing or full payment integration:
- Pro, Team, and Enterprise Cloud prices;
- additional Team seat rate and Enterprise volume tiers;
- storage add-on sizes and prices;
- annual billing and discount;
- mid-cycle prorating, seat removal, renewals, downgrade/cancellation/refund policy;
- exact WebMoney merchant/payment product and supported transaction flow;
- exact cryptocurrency asset/network and how WebMoney-mediated settlement/confirmation works;
- token format, validity, renewal, revocation, and whether a particular token entitlement covers app only or both app and website;
- IRR provider and go-live criteria;
- tax/VAT/invoice requirements for supported markets.

**Implementation instruction:** First integrate this specification into the product requirements and admin/payment-page design. Do not publish invented prices or enable unverified payment rails. The visible payment-method set must be controlled by the owner panel. Full provider integration should follow after the deferred payment decisions are approved.
