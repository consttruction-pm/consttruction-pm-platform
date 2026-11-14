# P6 EPPM V26 vs P6 Professional V26 — Unifier, Gateway & Primavera Cloud Integration Matrix

**Status:** V26 documentary comparison of integration setup, exchange workflows and external version constraints  
**Scope:** Primavera Unifier Schedule/ Summary/Activity Sheets, Primavera Gateway, P6 Project Scheduled Services, P6 Professional exchange actions, Oracle Primavera Cloud integration, and Unifier 26.12 compatibility notes.  
**Out of scope:** Configuring Gateway, linking projects, sending/receiving data, changing synchronizations, or modifying any project/workspace.  
**Version rule:** P6 EPPM V26 Help and P6 Professional V26 User/Help sources. Unifier 26.12 Day One Impact is used only to state current Unifier-side lifecycle/deprecation constraints.

## 1. Executive findings

1. **Professional is not excluded from all Unifier exchange.** Professional V26 User Guide documents Schedule Sheet, Summary Sheet and Activity Sheet exchange actions. However, the Professional Help/Guide labels the initial Unifier project-link setup as **P6 EPPM only**; Professional requires P6 EPPM to be configured for Unifier integration and the project to be linked before it can exchange.
2. **Activity Sheet has a specific first-exchange rule.** The first exchange between P6 Professional and Unifier must be initiated from Unifier. After that, the exchange can be initiated from P6, P6 Professional or Unifier.
3. **Schedule Sheet and Summary Sheet have different orchestration.** Schedule Sheet integration can use P6 Project Scheduled Services for periodic sends. Summary Sheet periodic sends are configured by the Primavera Gateway administrator; P6 does not use the same Project Scheduled Service for Summary Sheets.
4. **The three sheet types are not interchangeable.** Schedule Sheets exchange project/WBS/resource-assignment/activity data; Summary Sheets exchange WBS hierarchy and summarized project/baseline/resource-assignment/expense data based on CBS; Activity Sheets exchange activity data and actual dates.
5. **P6 EPPM V26 has a broader web-side integration configuration surface.** EPPM documents application-level Gateway/Unifier settings, project preferences, CBS filters, and Project Scheduled Services. Professional can invoke supported exchange actions after EPPM setup; it is not the setup/administration surface.
6. **Oracle Primavera Cloud integration is explicitly marked P6 EPPM only in Professional V26 Help.** EPPM can send scope and enterprise risk data to Primavera Cloud and import scope/risk analysis results (including pessimistic pre/post-response activity dates). The Professional V26 Help TOC marks Gateway/OPC integration as P6 EPPM Only.
7. **Unifier 26.12 changes the supported sheet lifecycle.** Oracle's Unifier 25.10/26 Day One Impact states Schedule Manager and Resource Manager were removed from uDesigner; new Schedule Sheets cannot be created, existing ones can still be updated, and Oracle recommends moving to Activity Sheets. A P6 V26 integration comparison must include the Unifier version, not only the P6 version.
8. **Tested deployment has a database constraint.** P6 V26 system requirements state that Primavera Unifier 26.12 integration through Primavera Gateway is tested when P6 EPPM Web Services is configured with an Oracle database only. This is a tested-configuration constraint, not a general claim that other configurations can never work.

## 2. Integration capability matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Unifier integration availability | EPPM Help documents Schedule Sheet, Summary Sheet and Activity Sheet integrations | Professional V26 User Guide documents exchange actions for all three sheet types | Both participate; setup responsibility differs. CONFIRMED |
| 2 | Initial integration setup | Configure Gateway/Unifier application settings and project integration preferences in EPPM | Professional Help labels “Linking Primavera Unifier data” and “Link a project with a Primavera Unifier Project” as P6 EPPM Only | Professional is an exchange client after EPPM setup, not the setup surface. CONFIRMED |
| 3 | Professional project link prerequisite | EPPM links the P6 project to Unifier project/sheet and configures deployment | Professional exchange requires P6 EPPM configured for Unifier integration and the project already linked to a Unifier project | Explicit prerequisite. CONFIRMED |
| 4 | Activity Sheet first exchange | EPPM and Unifier exchange activity data; Unifier can send actual dates back to P6 | First exchange must be initiated from Unifier; subsequent exchange can be initiated from P6 Professional | Important exception to “Professional can initiate exchange”. CONFIRMED |
| 5 | Schedule Sheet exchange | P6 sends project, WBS, resource assignment and activity data to Unifier Schedule Sheet | Professional File > Exchange Data > Send to Schedule Sheet | Shared exchange action after EPPM setup. CONFIRMED |
| 6 | Summary Sheet exchange | P6 sends WBS hierarchy and summarized project/baseline/resource assignment/expense data based on CBS | Professional File > Exchange Data; select Summary and Spread data, optionally WBS Hierarchy and baselines | Shared exchange action after EPPM setup. CONFIRMED |
| 7 | Activity Sheet exchange | Unifier retrieves activity data from P6 and can send actual dates back to P6 | Professional File > Exchange Data > Activity Data; first exchange from Unifier, then either side | Shared exchange after initial handshake. CONFIRMED |
| 8 | Schedule Sheet data scope | Project, WBS, resource assignments and activities | Professional can send selected project data to the linked Schedule Sheet | Same broad data scope; mapping/field parity not exhaustively tested. CONFIRMED |
| 9 | Summary Sheet data scope | WBS hierarchy and summarized project, baseline, resource assignment and expense data; CBS generates Unifier CBS hierarchy | Professional can send Summary and Spread data, WBS hierarchy and selected baselines | Same broad data scope. CONFIRMED |
| 10 | Activity Sheet data scope | Activity data is exchanged; Unifier can send actual dates to P6 | Professional sends Activity Data | Shared activity-level scope. CONFIRMED |
| 11 | Cost Breakdown Structure (CBS) | P6 retrieves CBS from linked Unifier project regularly; activities, resource assignments and expenses can be filtered by assigned CBS | Professional exchange uses the CBS mapping configured through the linked EPPM/Unifier integration | CBS is a key mapping dimension. CONFIRMED |
| 12 | CBS filter | EPPM can send only activities, resource assignments or expenses with assigned CBS, or the entire project | Professional can choose exchange action, but filter setup is part of EPPM/Unifier configuration | EPPM configuration surface; Pro filter parity not fully established. PARTIALLY VERIFIED |
| 13 | Schedule Sheet mapping | Mappings must be defined in Unifier; Unifier includes a default mapping | Professional uses the configured integration mapping; cannot define the EPPM-side project link from Professional | Different setup responsibility. CONFIRMED |
| 14 | Summary Sheet Gateway configuration | Configure data flows, synchronizations, P6 Web Services URL and Unifier Provider URL in Gateway; configure Gateway tab in P6 | Professional exchange uses the configured Gateway integration; Gateway setup is not performed in Professional | EPPM/Gateway administration prerequisite. CONFIRMED |
| 15 | Activity Sheet Gateway configuration | Configure data flows, synchronizations, P6 Web Services URL and Unifier Provider URL in Gateway; configure Gateway tab | Professional can exchange activity data after initial setup and first exchange from Unifier | Shared Gateway runtime, different initiation. CONFIRMED |
| 16 | P6 Project Scheduled Services | Project Scheduled Service can send data to Unifier on a schedule for Schedule Sheet integration | Professional has an Exchange Data action; it does not configure the EPPM server-side Project Scheduled Service | EPPM server automation vs Professional client action. CONFIRMED |
| 17 | Summary Sheet scheduling | Gateway administrator configures periodic processes/synchronizations | Professional can manually initiate Summary Sheet exchange; periodic Gateway process is configured outside Professional | Different scheduling responsibility. CONFIRMED |
| 18 | Activity Sheet scheduling | EPPM Help describes activity exchange and Gateway synchronization; no same Project Scheduled Service Send to Activity Sheet action is documented | Professional can initiate after the first Unifier-originated exchange | Do not assume Schedule Sheet Project Scheduled Service supports Activity Sheets. CONFIRMED |
| 19 | Unifier integration privilege | Allow Integration with Primavera Unifier privilege required to change project Integration/Gateway settings | Exchange Project Data with Primavera Unifier privilege required to send data from Professional | Setup privilege vs exchange privilege. CONFIRMED |
| 20 | Application Settings privilege | Edit Application Settings privilege required to configure Gateway/Unifier application settings | Professional does not own the EPPM Application Settings setup page | EPPM configuration privilege. CONFIRMED |
| 21 | Project preferences | Project Integrations/Gateway settings select deployment and link project to Unifier sheet | Professional Help labels project-link setup P6 EPPM Only | Setup boundary. CONFIRMED |
| 22 | Template project linking | Template projects cannot be linked to Primavera Unifier | Same restriction applies to P6 Professional project-linking workflow | Shared limitation. CONFIRMED |
| 23 | Copy project behavior | Copying a project with Unifier links does not retain those links | Professional uses copied projects; do not expect copied project to retain EPPM/Unifier links | Shared limitation. CONFIRMED |
| 24 | Copy activity with CBS | Copying an activity with CBS does not preserve its CBS assignment | Same underlying project data limitation | Shared limitation. CONFIRMED |
| 25 | Reflection/baseline links | Creating a reflection or baseline does not preserve the Unifier link | Professional reflections/baselines do not inherit the source Unifier link | Shared limitation. CONFIRMED |
| 26 | Summary Sheet baseline export | EPPM can send selected baselines with summarized data and WBS hierarchy | Professional Summary Sheet export allows selecting baselines to send | Shared capability. CONFIRMED |
| 27 | Activity Sheet baseline export | EPPM activity-sheet integration is activity-focused | Professional Help says baseline data cannot be sent when using Activity Sheet integration | Explicit format-specific limitation. CONFIRMED |
| 28 | Wrong integration action risk | Oracle warns selecting the wrong integration type/action can corrupt data | Same caution is repeated in Professional V26 User Guide | Operators must know which sheet type is configured. CONFIRMED |
| 29 | Unifier 26.12 Schedule Sheet lifecycle | EPPM V26 Help still documents Schedule Sheet workflows, but Unifier 25.10/26.12 removed Schedule Manager creation capability | Professional V26 can send to existing Schedule Sheets if integration remains available; new Schedule Sheet creation is not available in Unifier 26.12 | P6 capability must be qualified by Unifier version. CONFIRMED |
| 30 | Unifier Activity Sheet recommendation | Oracle recommends transitioning to Activity Sheets after Schedule Manager/Schedule Sheet creation deprecation | Professional V26 has explicit Activity Sheet exchange workflow | Activity Sheets are the forward path. CONFIRMED |
| 31 | Unifier Summary Sheet 26.12 caveat | Unifier 25.10 Day One Impact notes new Summary Sheet integrations can fail if Role Attribute Form integration settings are not configured; Resource Manager no longer supports creating Role Attribute forms | Professional can invoke Summary Sheet export but cannot resolve Unifier-side form/synchronization configuration | External Unifier dependency; not a P6 product parity claim. CONFIRMED |
| 32 | Gateway version tested | P6 V26 tested configuration lists Primavera Gateway 21.12 | Professional Cloud Connect V26 is in the tested-configuration guide; Unifier integration test is anchored to P6 EPPM Web Services | Deployment compatibility is shared but service dependency is EPPM-side. CONFIRMED |
| 33 | Unifier version tested | P6 V26 system requirements list Unifier 26.12 | Professional V26 user guide uses the configured EPPM integration and Unifier deployment | Version pairing matters. CONFIRMED |
| 34 | Database restriction for tested Unifier integration | Integration of Unifier 26.12 through Gateway is tested when P6 EPPM Web Services is configured with Oracle database only | Professional exchange depends on P6 EPPM configured integration; SQL Server parity is not established by this tested configuration note | Tested support constraint; do not claim universal SQL Server parity. CONFIRMED |
| 35 | Primavera Cloud integration | EPPM can send scope and enterprise risk data to Primavera Cloud and import results, including pre/post-response pessimistic activity dates | Professional V26 Help marks Working with Oracle Primavera Cloud/Gateway exchange as P6 EPPM Only | EPPM-only documented integration. CONFIRMED |
| 36 | Primavera Cloud risk exchange | P6 EPPM sends risk register and three-point estimate data; receives pre/post-response pessimistic dates and displays them in columns/Gantt bars | No corresponding Professional V26 OPC integration page; Help labels OPC exchange EPPM Only | EPPM-specific documented workflow. CONFIRMED |
| 37 | Primavera Gateway role | Gateway connects P6 EPPM with Unifier and Oracle Primavera Cloud; data flows/synchronizations are configured in Gateway | Professional can invoke some Unifier exchanges through the configured integration but is not the Gateway deployment administrator | Gateway is an external integration product, not a P6 Professional feature. CONFIRMED |
| 38 | Project data exchange schedule vs ad hoc | EPPM supports ad hoc and server-scheduled Schedule Sheet exchange; Summary Sheet can use Gateway-managed scheduled processes | Professional supports client-side ad hoc exchange actions after project linking | Different orchestration. CONFIRMED |

## 3. Sheet-type reconciliation

### 3.1 Schedule Sheet
- Sends project, WBS, resource assignment and activity data to Unifier.
- Requires Unifier mappings and P6 project linking.
- EPPM can send on demand or use Project Scheduled Services for periodic Schedule Sheet sending.
- Professional V26 can invoke File > Exchange Data > Send to Schedule Sheet after EPPM setup.
- Unifier 26.12 no longer supports creating new Schedule Sheets through Schedule Manager; existing Schedule Sheets can still be updated.

### 3.2 Summary Sheet
- Sends WBS hierarchy and summarized project/baseline/resource assignment/expense information based on CBS.
- EPPM setup requires Gateway data flows/synchronizations and Web Services/Unifier Provider URLs.
- Professional V26 can select Summary and Spread data, WBS Hierarchy and baselines in the exchange dialog after EPPM setup.
- Periodic Summary Sheet processing is configured by the Gateway administrator, not through the same EPPM Project Scheduled Service action as Schedule Sheets.
- Unifier 26.12 has Role Attribute Form prerequisites and deprecation caveats; new Summary Sheet integration may fail if the required Unifier-side integration settings are missing.

### 3.3 Activity Sheet
- Unifier retrieves activity data from P6 and can send actual dates back to P6.
- The first exchange must be initiated from Unifier.
- After the first exchange, P6 EPPM, P6 Professional or Unifier can initiate exchange.
- Professional V26 has a dedicated Exchange Data > Activity Data action.
- Baseline data cannot be sent through Activity Sheet integration.

## 4. Primavera Cloud (OPC) reconciliation

EPPM V26 documents a separate Gateway/OPC workflow:
- send P6 project scope data to Primavera Cloud,
- send enterprise risk register and three-point estimate information for quantitative risk analysis,
- receive pre-response and post-response pessimistic activity dates,
- display pessimistic start/finish columns and bars in P6 Gantt views,
- use Primavera Cloud risk, scope, task and portfolio functionality with P6 execution data.

Professional V26 Help explicitly marks Working with Oracle Primavera Cloud and exchanging data through Gateway as P6 EPPM Only. Do not infer that the Professional Unifier Activity Sheet client workflow implies Professional can perform the EPPM-to-OPC integration.

## 5. Source register — Oracle primary sources

### P6 EPPM V26
1. Working With Primavera Unifier: https://docs.oracle.com/cd/G48897_01/p6help/en/78769.htm
2. Linking P6 and Primavera Unifier Projects and Activity Sheets: https://docs.oracle.com/cd/G48897_01/p6help/en/89593.htm
3. Linking P6 and Primavera Unifier Applications Using Schedule Sheets: https://docs.oracle.com/cd/G48897_01/p6help/en/79000.htm
4. Linking P6 and Primavera Unifier Applications Using Summary Sheets: https://docs.oracle.com/cd/G48897_01/p6help/en/88849_1.htm
5. Exchanging P6 data with Primavera Unifier: https://docs.oracle.com/cd/G48897_01/p6help/en/78809.htm
6. Working With Primavera Gateway: https://docs.oracle.com/cd/G48897_01/p6help/en/88492.htm
7. Working With Oracle Primavera Cloud: https://docs.oracle.com/cd/G48897_01/p6help/en/88851.htm
8. EPPM V26 Help TOC: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm

### P6 Professional V26
9. Professional V26 User Guide — Linking Primavera Unifier data (P6 EPPM only): https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm
10. Exchanging data with Primavera Unifier using Schedule Sheet Integration: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/89608.htm
11. Exchanging data with Primavera Unifier using Summary Sheet Integration: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/89609.htm
12. Exchanging data with Primavera Unifier using Activity Sheet Integration: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/89610.htm
13. Professional V26 Help TOC (Unifier/OPC scope labels): https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm

### External compatibility dependencies
14. P6 V26 Other Primavera Applications / tested configurations: https://docs.oracle.com/cd/G48902_01/English/client_system_requirements/99016.htm
15. Unifier V26 Day One Impact Guide: https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/day-one-impact/unifier-day-one-impact.pdf
16. Unifier 25.10 Removal of Resource Manager and Schedule Manager from uDesigner: https://docs.oracle.com/en/industries/construction-engineering/primavera-unifier/26/day-one-impact/2510removalofresourcemanagerandschedulemanagerfromudesigner-10318880a.html

## 6. Remaining gaps — explicitly open

- Full row/field mapping for Schedule Sheet, Summary Sheet and Activity Sheet synchronization payloads.
- Exact P6 Professional V26 behavior for each import action and direction (P6-to-Unifier vs Unifier-to-P6) across all sheet types.
- Exact CBS code mapping, hierarchy, cost account, WBS and baseline behavior under each Unifier form/sheet configuration.
- Unifier 26.12 compatibility matrix for every Gateway deployment, authentication mode, Oracle/SQL Server DB and P6 EPPM Web Services configuration.
- Detailed behavior of existing Schedule Sheets after Unifier Schedule Manager deprecation, including updates, configuration packages and permissions.
- Exact Summary Sheet Role Attribute Form prerequisites and error conditions after Resource Manager deprecation.
- Current Activity Sheet synchronization field inventory and supported operations in Unifier 26.12.
- Full Primavera Cloud Gateway import/export field mapping and Professional V26 API parity.
- Independent round-trip test for each sheet type using P6 EPPM V26, Professional V26 and Unifier 26.12.
- Full source-topic census for all Unifier/Gateway/OPC topics in both V26 Help trees.

## 7. Boundary and conclusion

This is a **documentation-only reference comparison**. No Gateway deployment, Unifier connection, synchronization, schedule sheet, summary sheet, activity sheet, Primavera Cloud transfer, project link or exchange was created or modified. No product feature, CUBI workspace, code, schema, menu, data flow or agent-owned task was changed.

**Conclusion:** P6 Professional V26 is a supported Unifier exchange client for Schedule Sheets, Summary Sheets and Activity Sheets, but its initial linking/configuration is explicitly P6 EPPM-only. Activity Sheet exchange has a first-run-from-Unifier rule; after that, Professional can initiate exchange. EPPM owns the broader setup and server-side orchestration surface, including Project Scheduled Services and Gateway configuration. Primavera Cloud integration is explicitly EPPM-only in Professional V26 Help. Current Unifier 26.12 deprecations and the tested Oracle-database-only Gateway configuration are material external constraints that must be included in any deployment or compatibility statement.
