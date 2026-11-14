# P6 EPPM V26 vs P6 Professional V26 — Risk Model, Scoring & Response Plan Matrix

**Status:** Evidence-backed V26 comparison of two related but non-identical risk experiences  
**Scope:** Risk registers, risk categories, scoring thresholds/matrices, score algorithms, exposure calculations, UDFs, activity assignments, response plans/actions, status lifecycle, and API/data model.  
**Out of scope:** Running risk analysis, changing project risk records, configuring matrices, building response plans, or modifying any product/workspace.  
**Version rule:** EPPM Help/REST sources and Professional Help/User Guide sources are V26. Where the Professional Java API reference is older than V26, it is clearly marked as non-V26 supporting evidence only.

## 1. Executive findings

1. **Risk management is not absent from either product.** EPPM V26 has its own Project Risks register, enterprise risk data, risk scoring matrices, risk thresholds, risk UDFs, and response plans. Professional V26 has a desktop Risks view explicitly labelled “P6 Professional Only,” with risk records, categories, activity assignments, impact analysis, response selection, and UDFs.
2. **The two product experiences are not the same feature set.** Professional's V26 Risks Details UI uses fixed Probability, Schedule and Cost levels, a fixed score lookup table, one Response Type/Description and post-response fields. EPPM uses configurable enterprise thresholds, project-assigned scoring matrices, optional user-defined impacts, selectable scoring methods, and multiple alternative response plans with multiple action items.
3. **EPPM risk scoring is configurable.** Risk thresholds can be Probability, Tolerance, Schedule, Cost, Relative Schedule, Relative Cost or User Defined. Matrix dimensions depend on the number of levels in the selected thresholds. The scoring method can be Highest Impact, Average Impact or Average Individual Impact.
4. **Professional risk scoring is a fixed six-level model in the V26 desktop Help.** Probability, Schedule and Cost each have six enumerated levels. The overall impact is the higher of Cost and Schedule; the score is read from the fixed 6×6 table. The Professional V26 Help does not document the EPPM-style matrix designer or selectable scoring-method list.
5. **EPPM response planning is structurally richer in the V26 UI/API.** A risk can have multiple alternative response plans, exactly one active at a time; each plan can contain multiple response action items. Action items have owners, statuses, dates, impacts, costs and optional activity assignments. Professional V26 documents a single response section with a response type/description and post-response Probability/Schedule/Cost fields; no equivalent multi-plan/action-item UI is documented there.
6. **Do not confuse risk UDFs with user-defined impact thresholds.** Risk UDFs add descriptive/custom fields and do not themselves participate in scoring. User-defined impact thresholds in an EPPM scoring matrix are separate threshold dimensions and can contribute to the score.
7. **Risk statuses and threat/opportunity concepts overlap.** Both V26 products document Proposed, Open, Active, Rejected (Closed), Managed (Closed) and Impacted (Closed), and both distinguish threats from opportunities. The shared labels do not make the scoring or response model identical.
8. **The XER data map confirms distinct risk structures.** It marks Professional PRORISK and RISKTYPE tables as Professional-only; Oracle also warns that Professional risk rows imported into EPPM via XER are not visible in the EPPM risk UI and recommends XML for risk exchange.

## 2. V26 risk capability matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Risk-management availability | Project Risks register and risk enterprise data are documented in EPPM Help | Risks view and Risks Details are explicitly marked P6 Professional Only | Both have risk-management functionality, but separate product surfaces. CONFIRMED |
| 2 | Primary risk UI | Projects > Risks page; also add/manage from Activities and EPS contexts | Project > Risks desktop view; Risks Details dock | Different UI and workflow. CONFIRMED |
| 3 | Risk register scope | Risk register can show risks for open projects and group/filter by project | Risks view is for open project; with multiple projects, automatic assignment depends on current grouping | Different multi-project workflow. CONFIRMED |
| 4 | Threat/opportunity | Risk Type distinguishes threat (negative) and opportunity (positive) | Same distinction | Shared concept. CONFIRMED |
| 5 | Risk owner | Resource owner assigned to risk | Resource owner assigned to risk | Shared field concept. CONFIRMED |
| 6 | Risk categories | Enterprise Risk Categories are global across enterprise and used to analyze trends across projects | Risk Categories are hierarchical Admin Categories, managed under Admin > Admin Categories | Shared classification concept; different administration surface. CONFIRMED |
| 7 | Risk category assignment | A risk can be associated with one category | Risk has a category selected from hierarchy | Shared single-category model in documented UI/API. CONFIRMED |
| 8 | Risk status lifecycle | Proposed, Open, Active, Rejected (Closed), Managed (Closed), Impacted (Closed) | Same six values and descriptions | Shared lifecycle labels and meanings. CONFIRMED |
| 9 | Activity assignment | Risk can be assigned to activities from Risks page or Activities page; risks can also be added at EPS/project level | Risk can be assigned to multiple activities; activity can have multiple risks | Shared many-to-many activity association. CONFIRMED |
| 10 | Activity exposure dates | Exposure Start/Finish derive from assigned activities; otherwise project dates are used as fallback | Same fallback sequence based on assigned activities/project dates | Shared concept. CONFIRMED |
| 11 | Risk UDFs | Dedicated Risk UDF enterprise-data page; UDFs add information not in standard risk fields | Risks Details includes UDFs tab; Professional supports risk-specific UDFs | Both support risk UDFs; exact field-type/permission parity not fully compared. CONFIRMED |
| 12 | Risk UDFs vs scoring | Risk UDFs are descriptive/custom data; separate User Defined Impact Thresholds contribute to risk score | UDF tab adds risk data; Professional V26 fixed score uses Probability, Cost and Schedule only | Do not treat UDF fields as scoring dimensions. CONFIRMED |
| 13 | Risk scoring matrix object | Configurable Risk Scoring Matrices page; each matrix has name/description and assigned thresholds | Professional V26 Help presents fixed impact score table and does not document a matrix designer/assignment workflow | Material scoring architecture difference. CONFIRMED (UI scope) |
| 14 | Matrix assignment | Matrix is assigned to projects; without a matrix, general risk data can be entered but qualitative Probability/Schedule/Cost scoring fields are disabled | No matrix-assignment prerequisite in Professional V26 risk workflow; fixed scoring table is part of Risks Details | Different prerequisite/configuration model. CONFIRMED |
| 15 | Threshold object | Separate Risk Thresholds enterprise data | No corresponding V26 Professional threshold-definition page in the Risks Help workflow | EPPM configurable threshold architecture. CONFIRMED (documented UI) |
| 16 | Threshold types | Probability, Tolerance, Schedule, Cost, Relative Schedule, Relative Cost, User Defined | Probability, Schedule and Cost fields with fixed ranges | EPPM has more threshold types. CONFIRMED |
| 17 | Threshold level count | Threshold levels can be configured; REST schema says 2–9 levels | Six predefined levels for each Probability/Schedule/Cost dimension | Configurable vs fixed levels. CONFIRMED |
| 18 | Probability levels | Configurable ranges per Probability threshold | Very High ≥70%; High 50–70%; Medium 30–50%; Low 10–30%; Very Low up to 10%; Negligible | Different configurability; shared ordinal labels. CONFIRMED |
| 19 | Schedule impact levels | Configurable duration or relative percentage thresholds | Very High ≥20%; High 10–20%; Medium 5–10%; Low 1–5%; Very Low up to 1%; Negligible | Different configurability and units. CONFIRMED |
| 20 | Cost impact levels | Configurable monetary or relative percentage thresholds | Very High ≥40%; High 20–40%; Medium 10–20%; Low 1–10%; Very Low up to 1%; Negligible | Different configurability and units. CONFIRMED |
| 21 | Tolerance threshold | Required threshold in EPPM scoring matrix configuration; describes risk acceptability/manageability | No corresponding Tolerance threshold field in Professional V26 Impact tab | EPPM-specific scoring dimension. CONFIRMED |
| 22 | User-defined impact threshold | Optional EPPM scoring dimension; may be technical, safety, quality, environmental, etc. | Professional V26 fixed score table has no additional impact dimension beyond Cost and Schedule | EPPM can score custom impact dimensions. CONFIRMED |
| 23 | Relative schedule threshold | EPPM can define schedule impact as project-duration percentage or duration value | Professional uses fixed percentage ranges in Schedule field | EPPM supports custom relative/value thresholds. CONFIRMED |
| 24 | Relative cost threshold | EPPM can define cost impact as project-cost percentage or monetary value | Professional uses fixed percentage ranges for Cost impact and applies project cost in exposure calculation | Different cost-threshold model. CONFIRMED |
| 25 | Matrix dimensions | Probability levels × impact levels define matrix size; PID is visual representation | Fixed 6×6 score lookup table in V26 Help | Configurable vs fixed matrix. CONFIRMED |
| 26 | Scoring method: Highest Impact | Supported; overall impact is highest of all assigned impacts | Professional uses higher of Cost and Schedule as overall impact | Professional's documented logic is closest to EPPM Highest Impact. CONFIRMED |
| 27 | Scoring method: Average Impact | Supported; averages impact severity levels | Not selectable in Professional V26 Risks Details | EPPM-only documented scoring method. CONFIRMED |
| 28 | Scoring method: Average Individual Impact | Supported; scores each impact separately with probability, then averages scores | Not selectable in Professional V26 Risks Details | EPPM-only documented scoring method. CONFIRMED |
| 29 | Score calculation | Matrix score derives from probability and overall impact using selected scoring method and PID | Higher of Cost/Schedule plus Probability determines score from fixed 6×6 table | Same high-level concept, different algorithm/configurability. CONFIRMED |
| 30 | Professional fixed score example | EPPM result depends on assigned matrix and selected method | Probability High + overall impact Medium = score 14 in fixed table | Example confirms fixed lookup semantics. CONFIRMED |
| 31 | Pre-response exposure | Exposure = Probability midpoint × Cost midpoint; monetary threshold or relative threshold conversion applies | Exposure Cost = Planned/Budgeted Total Cost × (Probability midpoint × Cost midpoint) | Similar probabilistic logic but cost basis differs. CONFIRMED |
| 32 | Relative cost conversion | EPPM relative cost thresholds convert percentage bounds to monetary values using project Planned Total Cost before midpoint calculation | Professional uses project Planned/Budgeted Total Cost as a multiplier in exposure formula | Different model; do not compare displayed exposure without threshold units. CONFIRMED |
| 33 | Response type for threats | Accept, Avoid, Reduce, Transfer | Same four values | Shared response vocabulary. CONFIRMED |
| 34 | Response type for opportunities | Enhance, Exploit, Facilitate, Reject | Same four values | Shared response vocabulary. CONFIRMED |
| 35 | Response structure | Multiple response plans can be created per risk; one plan must always be active and only one can be active | Professional V26 Impact tab has one Response Type and Response Description section | Different response-planning structure. CONFIRMED |
| 36 | Response action items | Each EPPM response plan can contain multiple action items | No separate response-action-item grid is documented in Professional V26 Risk Details | EPPM richer action model. CONFIRMED (documented UI) |
| 37 | Response action item status | Proposed, Sanctioned, Rejected, In-Progress, Complete | Professional response is a type and description; no separate action-item status lifecycle documented | EPPM action workflow. CONFIRMED |
| 38 | Response action item owner | Owner resource is assigned to each action item | Professional risk owner is assigned to risk; response section has no separate action owner field documented | Different responsibility granularity. CONFIRMED |
| 39 | Response action item schedule | Action item has start/finish; assigned activity dates can drive these values | Professional post-response fields capture probability/schedule/cost impact, not a set of action-item dates | Different response execution model. CONFIRMED |
| 40 | Response action item cost | Planned, Actual and Remaining cost are tracked; rejected action items excluded from total cost | Professional has Pre/Post-Response Exposure Cost, not a separate action-item cost ledger | Different financial treatment. CONFIRMED |
| 41 | Assign activities to response actions | Existing project activities can be assigned to response action items; activity dates/costs feed response calculations | Professional risk is assigned to activities; no separate response action item assignment is documented | Risk-affected activity vs mitigation activity are distinct relationships. CONFIRMED |
| 42 | Post-response impacts | Each response action item can carry probability, schedule, cost and user-defined impact values; plan score is based on response actions | One set of Post-Response Probability, Schedule and Cost values mirrors Pre-Response | Different granularity. CONFIRMED |
| 43 | Active response plan | Exactly one response plan must be active for each EPPM risk | Professional has one response selection on the risk; no alternative plan selector documented | EPPM alternatives and active selection. CONFIRMED |
| 44 | Response Total Cost | EPPM risk register displays total cost of active response plan as Remaining Cost + Actual Cost across non-rejected actions | Professional shows Post-Response Exposure Cost based on risk probability/cost and project cost | These are not equivalent metrics. CONFIRMED |
| 45 | Risk response exposure | EPPM Exposure for risk/response plan/action uses probability and cost midpoints; action/plan exposure helps compare response effectiveness | Professional exposure cost includes project/assigned activity Planned/Budgeted Total Cost multiplier | Do not equate EPPM Exposure and Professional Exposure Cost. CONFIRMED |
| 46 | Risk API object | EPPM V26 REST has Risk, RiskCategory, RiskImpact, RiskMatrix, RiskMatrixScore, RiskMatrixThreshold, RiskResponsePlan, RiskResponseAction, RiskResponseActionImpact, RiskThreshold, RiskThresholdLevel | Professional V26 Help documents desktop risk UI; V26 Professional API field schema not located | EPPM API data model is explicitly decomposed into threshold/matrix/response objects. CONFIRMED |
| 47 | EPPM RiskResponsePlan API | V26 REST exposes CRUD and fields including IsActive, ResponseType, RiskObjectId, ProjectObjectId, Planned/Actual/Remaining Cost, dates and scores | Professional V26 UI exposes a single response section; Pro V24 Java API reference is not used as V26 proof | Strong EPPM API contract; Professional parity NOT VERIFIED |
| 48 | EPPM RiskThreshold API | V26 REST threshold object includes Name, Level count and ThresholdType values | No corresponding V26 Professional REST/API threshold object schema located | EPPM contract confirmed; Pro API parity NOT VERIFIED |
| 49 | EPPM RiskImpact API | Stores pre-response qualitative value for each risk and threshold; composite object ID uses RiskObjectId + RiskThresholdObjectId | Professional UI stores fixed Pre-Response Probability/Cost/Schedule values | Different API/UI model. CONFIRMED |
| 50 | XER risk structures | EPPM Project Risks use EPPM risk model; Professional XER PRORISK/RISKTYPE structures imported to EPPM are not visible in EPPM risk UI | XER map marks PRORISK and RISKTYPE tables Professional-only | Separate exchange structures; XML is Oracle-recommended for risk exchange. CONFIRMED |
| 51 | Risk UDF scoring semantics | UDFs are additional descriptive data; User Defined Impact Thresholds are the scoring inputs | Professional UDFs add fields; fixed score calculation remains Probability/Cost/Schedule | Avoid confusing metadata extension with scoring dimension. CONFIRMED |
| 52 | Risk register download | EPPM Risks page supports Excel download of hierarchical or flat risk data | Professional view supports export/reporting through desktop workflows | Similar reporting intent; export schema parity not assessed here. PARTIALLY VERIFIED |
| 53 | REST reference prose consistency | V26 endpoint summary prose for RiskResponseAction and RiskResponseActionImpact appears to describe the opposite business-object concepts; their actual field schemas distinguish action-item fields from threshold-impact fields | No equivalent V26 Professional REST schema to compare | Consumers must follow the concrete V26 field schemas, not rely on the swapped summary sentences. DOCUMENTATION INCONSISTENCY CONFIRMED |

## 3. Scoring model comparison

### 3.1 EPPM V26

EPPM's risk score is not tied to one universal six-level table. It is driven by the matrix assigned to the project:
- define threshold types and levels,
- choose matrix size,
- choose Probability and impact thresholds,
- optionally include user-defined impact thresholds,
- choose one of three scoring methods,
- assign the matrix to one or more projects.

The three scoring methods are not interchangeable:
- **Highest Impact:** overall impact is the highest assigned impact.
- **Average Impact:** average the impact severity levels, then use the matrix with Probability.
- **Average Individual Impact:** calculate a probability/impact score for each impact and average those scores.

The V26 REST schema represents these objects separately: RiskThreshold, RiskThresholdLevel, RiskMatrix, RiskMatrixThreshold, RiskMatrixScore and RiskImpact.

### 3.2 Professional V26

The Professional V26 Impact tab defines fixed levels:
- Probability: Very High ≥70%, High 50–70%, Medium 30–50%, Low 10–30%, Very Low up to 10%, Negligible.
- Schedule: Very High ≥20%, High 10–20%, Medium 5–10%, Low 1–5%, Very Low up to 1%, Negligible.
- Cost: Very High ≥40%, High 20–40%, Medium 10–20%, Low 1–10%, Very Low up to 1%, Negligible.

The application uses the higher of Cost and Schedule as overall impact, then looks up the score against Probability in the fixed table. This is closest to EPPM's Highest Impact method, but it does not provide the V26 EPPM matrix designer's configurable thresholds and alternative scoring methods in the Professional UI.

### 3.3 Exposure is not Score and Response Total Cost is not Exposure

- **Score** is a qualitative risk rating from probability and impact.
- **Exposure** estimates monetary risk exposure from probability and cost impact midpoints.
- **Professional Exposure Cost** explicitly multiplies Planned/Budgeted Total Cost by the probability and cost midpoints.
- **EPPM Response Total Cost** is a cost roll-up of actual plus remaining cost across active response action items, excluding rejected actions.

These metrics answer different questions and must not be substituted in reports or field mappings.

## 4. Risk response lifecycle comparison

| Lifecycle element | EPPM V26 | Professional V26 |
|---|---|---|
| Alternative response options | Multiple plans per risk | One response selection in the Risk Details Impact tab |
| Active selection | Exactly one plan active | No equivalent plan-level Active selector documented |
| Response actions | Multiple action items per plan | No separate action-item list documented |
| Action owner | Resource assigned to action item | Risk owner at risk level |
| Action status | Proposed, Sanctioned, Rejected, In-Progress, Complete | Risk status lifecycle remains on risk record |
| Action schedule | Start/finish dates; assigned activity can drive dates | Post-response values describe impact after response |
| Action cost | Planned, Actual, Remaining; rejected actions excluded | Exposure Cost calculated from risk/project cost |
| Mitigation impacts | Probability, Schedule, Cost and user-defined threshold values | Post-Response Probability, Schedule and Cost |
| Activity relationship | Activities can be assigned to response actions | Activities can be assigned to risk (impact relationship) |
| Plan score | Based on action outcomes; API documents score after all response actions complete | Score is based on post-response Probability/Cost/Schedule fields |

## 5. API and field-surface notes

### EPPM V26 REST object family

**API documentation note:** The summary prose on the RiskResponseAction and RiskResponseActionImpact endpoint pages appears reversed relative to their V26 request/response schemas. The concrete `RiskResponseAction` schema contains action-item fields (ActivityObjectId, ResourceObjectId, Status, dates and costs); the `RiskResponseActionImpact` schema contains RiskResponseActionObjectId plus RiskThresholdLevelObjectId. Use the field schema when mapping these objects.
- `Risk` — probabilistic event/condition, threat or opportunity; supports UDFs.
- `RiskCategory` — enterprise category, a risk can be associated with one category.
- `RiskThreshold` / `RiskThresholdLevel` — named threshold and its discrete levels.
- `RiskMatrix` / `RiskMatrixThreshold` / `RiskMatrixScore` — matrix definition, threshold association and PID scores.
- `RiskImpact` — pre-response value for each risk/threshold pair; composite object ID.
- `RiskResponsePlan` — alternative plan, IsActive, response type, cost/date/score fields.
- `RiskResponseAction` — response action item details (activity link, owner, status, dates, planned/actual/remaining cost and score).
- `RiskResponseActionImpact` — post-response qualitative value per action/threshold (threshold-level association).

### Professional V26 documented desktop model
- Risk fields include ID, Name, Category, Type, Owner, Status, Identified Date/By, Exposure Start/Finish, Pre-Response Exposure Cost and Post-Response Exposure Cost.
- Impact tab includes Pre-Response Probability/Schedule/Cost, Response Type/Description, Post-Response Probability/Schedule/Cost and Score.
- Activities tab links risks to activities; UDFs tab extends risk details.
- A version-matched V26 Professional API schema for all risk objects was not located. Older Professional Java API references are not sufficient evidence for exact V26 object/field parity.

## 6. Source register — Oracle primary sources

### P6 EPPM V26
1. EPPM V26 Help TOC (Risks and Risk Enterprise Data): https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
2. Working with Risks Enterprise Data: https://docs.oracle.com/cd/G48897_01/p6help/es/43249_1.htm
3. Risk Scoring Matrices Page: https://docs.oracle.com/cd/G48897_01/p6help/en/17928.htm
4. Creating Risk Scoring Matrices (V26): https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/32334.htm
5. Risk Scoring Method Description: https://docs.oracle.com/cd/G48897_01/p6help/en/44763.htm
6. Risks Page: https://docs.oracle.com/cd/G48897_01/p6help/en/14409.htm
7. Response Plans Detail Window: https://docs.oracle.com/cd/G48897_01/p6help/en/14416.htm
8. Risk Exposure (Pre-response): https://docs.oracle.com/cd/G48897_01/p6help/en/48516.htm
9. Assigning a Risk to an Activity (V26): https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/32502_1.htm
10. EPPM V26 REST Risk endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-risk.html
11. EPPM V26 REST RiskThreshold endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-riskthreshold.html
12. EPPM V26 REST RiskMatrix endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-riskmatrix.html
13. EPPM V26 REST RiskResponsePlan endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-riskresponseplan.html
14. EPPM V26 REST RiskResponseAction endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-riskresponseaction.html
15. EPPM V26 REST RiskImpact endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-riskimpact.html
16. EPPM V26 REST RiskThresholdLevel schema: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-riskthresholdlevel-put.html
17. EPPM V26 REST RiskResponsePlan schema: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-riskresponseplan-put.html

### P6 Professional V26
18. Professional V26 Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
19. Risks (P6 Professional Only): https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm
20. Risks View (P6 Professional Only): https://docs.oracle.com/cd/G48902_01/client_help/en_US/project_risks_window.htm
21. Risks Details (P6 Professional Only): https://docs.oracle.com/cd/G48902_01/client_help/en_US/project_risk_details.htm
22. General tab — Risks Details: https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_project_risk_details.htm
23. Impact tab — Risks Details: https://docs.oracle.com/cd/G48902_01/client_help/en_US/48931.htm
24. Admin Categories (P6 Professional Only): https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_admin/toc.htm
25. Professional V26 User Guide: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf

### Explicitly version-limited Professional API support
26. Professional API FieldSummary (Release 24): https://docs.oracle.com/cd/F88968_01/English/Integration/p6_pro_api_reference/FieldSummary.html
This reference is not treated as a V26 API contract.

## 7. Remaining gaps — explicitly open

- Exact V26 Professional Java API risk classes and field-level schemas (Risk, RiskImpact, RiskResponsePlan, RiskResponseAction, RiskCategory, RiskThreshold).
- Whether any V26 Professional API operation exposes response-plan/action-item objects not represented in the V26 Professional desktop Help.
- Full UDF type/field-length/permission comparison for Risk UDFs across products.
- Complete EPPM V26 threshold/matrix default values and all matrix scoring edge cases.
- Numerical score parity test for identical Probability/Cost/Schedule inputs under EPPM Highest Impact and Professional fixed table.
- Numerical exposure parity tests for monetary vs relative thresholds and different project cost bases.
- Risk response action cost/date roll-up behavior under assigned activities, rejected actions, multiple actions with same finish date and multiple active/alternative plans.
- Full XML import/export risk mapping and exact behavior for Professional PRORISK vs EPPM ProjectRisk objects.
- EPPM risk matrix sharing with Oracle Primavera Cloud and any impact on P6 scores.
- Risk lifecycle permissions and security at field level for both product surfaces.
- Controlled runtime tests with the same risk scenarios in EPPM V26 and Professional V26, including both Professional standalone and EPPM-connected contexts.

## 8. Boundary and conclusion

This is a **documentation-only reference comparison**. No risk record, category, matrix, threshold, response plan or action item was created or changed. No product feature, CUBI workspace, application code, schema, menu, data flow or agent-owned task was modified.

**Conclusion:** The correct comparison is not “risk management is only in Professional” or “risk management is only in EPPM.” Both have risk-management capabilities, but the V26 documented experiences differ materially. Professional provides a desktop risk register and fixed three-factor qualitative score/response UI. EPPM provides a project risk register backed by configurable enterprise thresholds/matrices, selectable scoring methods, user-defined impact dimensions, and multi-plan/multi-action response management. The shared threat/opportunity labels, status names and risk UDF concept should not hide these differences.
