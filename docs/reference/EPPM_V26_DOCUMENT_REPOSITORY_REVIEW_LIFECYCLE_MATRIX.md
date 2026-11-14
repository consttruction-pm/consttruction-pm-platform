# P6 EPPM V26 vs P6 Professional V26 — Document Repository & Review Lifecycle Matrix

**Status:** V26 documentary comparison; optional repository dependency called out explicitly  
**Scope:** Work Product & Document records, file storage/reference, repository configuration, version history, check-in/out, document review lifecycle, security policies, assignments, and Web Services fields.  
**Out of scope:** Configuring a repository, uploading files, changing document records, implementing workflows, or touching any workspace/product feature.  
**Version rule:** EPPM Help and Web Services references are V26. Professional Help/User Guide references are V26. A Professional V26 API field-level equivalent was not located; do not infer API parity from matching UI labels.

## 1. Executive findings

1. **Both products have document/work-product records and activity/WBS associations.** This is not an EPPM-only capability.
2. **The critical distinction is the optional, configured EPPM Content Repository.** Without it, EPPM provides a limited project-document feature set (add, delete, relate, file path/URL). With it, EPPM adds repository-backed storage, check-in/out locks, automatic version/history records, folders, document templates, private documents, search/download, and document reviews.
3. **Professional V26 Work Products & Documents is primarily a metadata-and-location-reference model.** The project database stores the record and metadata; the actual file can remain on a network file server, configuration management system or website. Professional supports Public and Private location references, but the cited V26 Professional guide does not document the EPPM repository review lifecycle as a Professional-native workflow.
4. **Professional connected to an EPPM database can see repository-managed document records, but cannot manage/open the repository file from Professional.** Professional V26 Help explicitly says details are read-only and the document cannot be opened from P6 Professional if it was added via a P6 installation with a configured content repository.
5. **Document Status and Review Status are different fields/states.** Status is a configurable category (e.g. Not Started, In Progress, On Hold). Review Status belongs to the repository review process and can be Blank, In Review, Approved, Rejected or Terminated.
6. **Document review is conditional and security-sensitive.** It requires the optional content repository, an eligible document version, appropriate privileges, and a Shared or Read Only security policy. A Personal document cannot be started for review.
7. **Review types are distinct:** Anyone May Review, Everyone Must Review, and Everyone Must Review in Sequence. The first reviewer to reject can reject a multi-reviewer review; unanimous approval is required for Approved in the two everyone-must-review modes.
8. **EPPM Web Services expose document fields** such as ContentRepositoryDocumentInternalId, ObjectId, ParentObjectId, ProjectObjectId, PrivateLocation, PublicLocation, SecurityPolicy, ReviewStatus, RevisionDate, Version and Comments. The V26 Professional API field-level counterpart is not established here.

## 2. Product and configuration matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Document record capability | Project documents are managed from Documents page and can be related to project entities | Work Products & Documents creates a project-database record before assignment | Shared base capability. CONFIRMED |
| 2 | Work product vs document | Documents can be related to activities and WBS; work-product/deliverable semantics exist | A document can be marked as a work product when assigned to an Activity or WBS | Shared concept; not EPPM-only. CONFIRMED |
| 3 | Base storage without repository | Project document can reference local file path or URL | Private and Public file-location references can point to external files | Both can track external file references without a managed repository. CONFIRMED |
| 4 | EPPM optional content repository | Optional component; advanced document management is available only when configured | Professional does not provide an equivalent native EPPM repository lifecycle | EPPM advanced capabilities are configuration-dependent. CONFIRMED |
| 5 | EPPM without content repository | Limited actions: add, delete, relate documents; file path or URL | Professional document record and file-location reference model | EPPM basic mode is closer to Professional than repository-enabled EPPM. CONFIRMED |
| 6 | Repository storage | Stores P6-created documents in a reserved P6 repository folder; can also access external documents in repository folders | Actual files may be on network file server, configuration management system or website | Managed repository vs external file reference. CONFIRMED |
| 7 | Project document audience | Available to users with access to the corresponding project, subject to document security policy | Public Location can be viewed by all project participants; private location is visible only to P6 Professional users | Similar audience idea, but different control object. CONFIRMED |
| 8 | Private documents | With repository, user can add private documents unrelated to a project; visible in My Documents portlet | Private Location is a private filename/reference on a project document record | Do not equate EPPM Private Document with Professional Private Location. CONFIRMED |
| 9 | Workgroup documents | V26 Help describes project and private document types; the current V26 topic does not list workgroup documents | No corresponding Workgroup document class in the V26 Professional topic | V26 published scope only; historical Workgroup references must not be assumed current. PARTIALLY VERIFIED |
| 10 | Document folders | Repository enables project folder hierarchy; folder security policy can be Personal, Read Only or Shared | V26 Professional document library supports document records/assignments; no corresponding repository folder hierarchy is documented | Repository-only hierarchy. CONFIRMED |
| 11 | Document templates | Repository supports document templates and copying documents from templates | Professional V26 guide documents document records and assignments; no matching repository-backed file template lifecycle identified | EPPM repository capability; Pro parity NOT VERIFIED |
| 12 | File upload | Upload document into content repository from local computer/network server | Set path/filename in Private or Public Location; not a repository upload | Different file handling. CONFIRMED |
| 13 | File types restriction | Application Settings can restrict allowed upload file types for repository | External file path/reference model | Repository-specific upload control. CONFIRMED |
| 14 | Check out | Repository checkout downloads a copy and locks document against simultaneous edits | No corresponding native repository check-out process documented in Professional V26 Work Products & Documents | EPPM repository lifecycle. CONFIRMED |
| 15 | Check-out visibility | While checked out, others can still view/download but cannot modify, delete or check out | Public/private location access rules do not create the same repository lock state | Not equivalent to Public/Private reference. CONFIRMED |
| 16 | Check in | User uploads updated file, can add comments, and check-in lifts lock | Professional users update the external file at its location; no EPPM repository check-in action documented | Different version-control mechanism. CONFIRMED |
| 17 | Undo check out | EPPM provides Undo Check Out | No matching repository undo-checkout workflow documented for Professional V26 | EPPM repository capability. CONFIRMED |
| 18 | Version history | Repository supports document history and version list | Professional Version and Revision Date are document-record metadata; the user can edit the Version field | Automatic repository history vs manually maintained metadata. CONFIRMED |
| 19 | Version 1 semantics | Repository Version 1 is original version; subsequent check-ins create version history | Professional Version field is a user-maintained version number | Do not treat Pro Version field as repository version history. CONFIRMED |
| 20 | Modified By/Date and comments | Repository version details include modified by/date and comments per version | Professional metadata includes Author, Revision Date and Description; no per-check-in history in the cited V26 Pro guide | Repository audit trail is richer. CONFIRMED |
| 21 | Virus scanning | Cloud only: upload/check-in scans for viruses; infected file/version is removed and user notified | No equivalent Professional file scanning feature documented in V26 User Guide | EPPM cloud repository control; not universal on-prem claim. CONFIRMED |
| 22 | Repository authentication | Single-user or multiple-user authentication; multiple-user is default and uses individual logins/audit fields | Professional file access relies on configured network/web locations and operating-system/application access | Different identity boundary. CONFIRMED |
| 23 | Security policy values | Personal, Read Only, Shared | Professional Public/Private Location references; not the same policy enumeration | Different security semantics. CONFIRMED |
| 24 | Personal policy | Only document owner can access; document is not available in other project users' list | Private Location restricts visibility of that file path to P6 Professional users; it does not mean the project document record itself is private | Similar words, different behavior. CONFIRMED |
| 25 | Read Only policy | Project team may view but cannot modify/delete | Public Location makes the file available to participants; no equivalent built-in read-only lock is documented by that field | Not a direct match. CONFIRMED |
| 26 | Shared policy | Project team may view, modify and delete document/folder subject to privileges | Public Location only describes file audience; it does not grant shared repository operations | Not a direct match. CONFIRMED |
| 27 | Document category | EPPM category is configured in P6 and associated with the document | Professional connected to EPPM DB uses P6 categories; connected to Professional DB uses Admin Categories | Category source depends on database context. CONFIRMED |
| 28 | Document Status | Web Services exposes DocumentStatusName values blank, Not Started, Under Review, In Progress, Completed and On Hold; status-code name/object ID are separate fields | Status designations are created through Admin Categories or P6 categories according to database context; examples include Not Started, In Progress and On Hold | Shared configurable metadata concept; do not confuse with Review Status. CONFIRMED |
| 29 | Review Status | Repository review lifecycle: Blank, In Review, Approved, Rejected, Terminated | Professional V26 WP & Docs guide documents Status and Version, not the same EPPM document-review workflow | EPPM repository-specific lifecycle. CONFIRMED |
| 30 | Review prerequisite | Optional content repository must be installed/configured | Professional V26 does not document a native Start Review workflow | EPPM-only documented review mechanism. CONFIRMED |
| 31 | Review-eligible security policy | Shared or Read Only documents can start a review | Professional Private/Public location fields do not implement this review gate | EPPM review prerequisite. CONFIRMED |
| 32 | Review type: Anyone May Review | Any one listed reviewer can approve or reject; first decision completes review | No equivalent Professional V26 review type | EPPM repository workflow. CONFIRMED |
| 33 | Review type: Everyone Must Review | All reviewers must respond; all must approve for approval; one rejection is enough to reject | No equivalent Professional V26 review type | EPPM repository workflow. CONFIRMED |
| 34 | Review type: Everyone Must Review in Sequence | Reviewers act in specified order; all must approve; one rejection completes as rejected | No equivalent Professional V26 review type | EPPM repository workflow. CONFIRMED |
| 35 | Reviewer list mutation | At least one reviewer required; additional reviewers cannot be added after review creation | No matching review-assignment list in Professional V26 WP & Docs | EPPM review workflow constraint. CONFIRMED |
| 36 | Review due date | Optional due date for all reviewers | Professional Status field can be set, but no due-date-based review workflow documented | EPPM review workflow. CONFIRMED |
| 37 | Review dashboard | Initiator sees My Reviews; reviewers receive Action Required / workflow portlet items; details show responses and pending reviewers | No equivalent EPPM Document Reviews dashboard in Professional V26 Help | EPPM dashboard workflow. CONFIRMED |
| 38 | Review cannot start conditions | Current/previous version in review or reviewed; checked out; Personal policy; no privilege; multiple docs selected; template open | No matching review lifecycle | Exact preconditions are EPPM repository-specific. CONFIRMED |
| 39 | Professional connected to EPPM repository | EPPM document record and repository file are managed by EPPM | Professional sees read-only detail fields and cannot open the document from Professional when added through configured EPPM content repository | Direct inter-product limitation. CONFIRMED |
| 40 | Professional standalone database context | EPPM category/status configuration is not the source | Professional database uses Admin Categories for document categories/statuses | Database-context distinction. CONFIRMED |
| 41 | Activity/WBS assignment | Documents can be related to activities/WBS; related items can include other entities | Work products/documents can be assigned from WP & Docs, Activities and WBS windows | Shared assignment capability. CONFIRMED |
| 42 | Work product indicator | EPPM document can be linked to an activity/WBS and identified as a work product/deliverable | Professional uses Work Product checkbox for an assigned document; deliverable flag also exists | Shared semantics with UI differences. CONFIRMED |
| 43 | Deleting a document record | With repository, delete behavior depends on privileges and security policy; document file is repository-managed | Professional supports deleting the work product/document record | Deleting record vs deleting underlying external file must be distinguished. PARTIALLY VERIFIED |
| 44 | EPPM Web Services Document contract | V26 Document fields include repository internal ID, ObjectId, ParentObjectId, ProjectObjectId, Private/Public Location, SecurityPolicy, ReviewStatus, Version, RevisionDate, Comments, etc. | No version-matched Professional V26 API Document field schema located | EPPM API surface confirmed; Professional API parity NOT VERIFIED |
| 45 | ReviewStatus API enum | Web Services field schema lists In Review, Approved and Rejected; UI Data Dictionary also lists Blank and Terminated | No V26 Professional review API equivalent identified | API field enumeration is narrower than UI status glossary; preserve this nuance. CONFIRMED |
| 46 | Document repository internal ID | EPPM Web Services exposes ContentRepositoryDocumentInternalId | Professional record/location reference model does not expose this same V26 repository field in its User Guide | Repository-specific identifier. CONFIRMED |
| 47 | Parent/child document hierarchy | EPPM Web Services exposes ParentObjectId and repository folders | Professional document records can be associated to Activities/WBS but no equivalent repository folder-parent contract is documented | Do not equate assignments with folder hierarchy. CONFIRMED |
| 48 | Content type and file format | EPPM repository stores document content and version metadata | Professional references external file locations and opens via Launch | Different file-content ownership. CONFIRMED |
| 49 | DocumentType API classification | V26 Web Services distinguishes Non-Collaboration Document, Collaboration Document and Repository Document | Professional V26 UI describes records and file locations but no matching V26 API enum | EPPM service contract distinguishes repository/collaboration document classes. CONFIRMED; Pro API parity NOT VERIFIED |

## 3. Lifecycle distinctions that must remain separate

### 3.1 Document Status vs Review Status

- **Document Status** is a configurable project-document classification (examples include Not Started, In Progress, On Hold, or Completed).
- **Review Status** is the repository review workflow result/state: Blank, In Review, Approved, Rejected, or Terminated.

A Professional status label such as “In Review” can be manually assigned as a status category; that does not create an EPPM document review, assign reviewers, or produce an approval trail.

### 3.2 EPPM without repository vs EPPM with repository

The repository is optional. Without it, P6 can still add project document references, relate documents to project objects, and manage limited metadata. With it, the application adds a managed file lifecycle (upload, check-out/check-in, version history, folder hierarchy, search, templates and review). Therefore, the accurate comparison is three-way:

1. EPPM without configured repository.
2. EPPM with configured repository.
3. Professional Work Products & Documents.

A two-column EPPM-vs-Professional matrix that ignores the repository configuration will overstate EPPM capabilities as universally available.

### 3.3 Professional connected to EPPM is not a repository client

Professional V26 Help explicitly says that if a document was added through an EPPM installation with configured content repository, its detail fields are read-only and the document cannot be opened from Professional. Professional is therefore not a full substitute for the EPPM Documents page/repository lifecycle.

### 3.4 Private Location is not Personal Security Policy

Professional Private Location means a private file path/reference visible only to Professional users. EPPM Personal policy controls access to the document record/content and hides it from other project participants. These controls are not interchangeable.

## 4. EPPM Web Services Document field surface

The V26 Web Services Reference Guide documents the following fields (representative list):
- `ActivityObjectID`, `ProjectObjectId`, `ResourceObjectId`, `ParentObjectId`, `ObjectId`
- `ContentRepositoryDocumentInternalId`
- `Title`, `Author`, `Description`, `ReferenceNumber`, `DocumentCategoryName`
- `PrivateLocation`, `PublicLocation`, `SecurityPolicy`
- `Version`, `RevisionDate`, `ReviewStatus`, `Comments`
- `CreateDate`, `CreateUser`, `LastUpdateDate`, `LastUpdateUser`, `Size`, `Deliverable`

Important field semantics:
- `SecurityPolicy` values: Personal, Read Only, Shared.
- `ReviewStatus` in the V26 Web Services field table is restricted to In Review, Approved, Rejected.
- `Version` is a document version string; do not assume it has the same lifecycle as a manually maintained Professional version number.
- `ContentRepositoryDocumentInternalId` is the internal repository document ID, not the P6 document ObjectId.
- `PrivateLocation` and `PublicLocation` are location references and should not be treated as repository storage keys.

A V26 Professional API counterpart was not established; this is not a claim that Professional has no document API.

## 5. Source register — Oracle primary sources

### P6 EPPM V26
1. About the Document Content Repository: https://docs.oracle.com/cd/G48897_01/p6help/en/6639.htm
2. Working with Documents with a Content Repository: https://docs.oracle.com/cd/G48897_01/p6help/en/6676.htm
3. Working with Documents without the Content Repository: https://docs.oracle.com/cd/G48897_01/p6help/en/6675.htm
4. Adding Documents without the Content Repository: https://docs.oracle.com/cd/G48897_01/p6help/en/8007.htm
5. Adding Documents to a Project and Storing Them in the Content Repository: https://docs.oracle.com/cd/G48897_01/p6help/en/7956.htm
6. Checking Out Documents: https://docs.oracle.com/cd/G48897_01/p6help/en/7954.htm
7. Checking In Documents: https://docs.oracle.com/cd/G48897_01/p6help/en/7953.htm
8. Creating Document Folders: https://docs.oracle.com/cd/G48897_01/p6help/en/7834.htm
9. Creating Document Reviews: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/43862.htm
10. Start Review Dialog Box: https://docs.oracle.com/cd/G48897_01/p6help/en/6025.htm
11. Version Tab of Document Details: https://docs.oracle.com/cd/G48897_01/p6help/en/6026.htm
12. EPPM V26 Web Services Document Fields: https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_web_services_reference/42380.htm
13. EPPM V26 Data Dictionary — Review Status/Reviewers/Revision Date: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_data_dictionary/p6_eppm_data_dictionary.pdf

### P6 Professional V26
14. Adding and Assigning Work Products and Documents: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/addingandassigningworkproductsanddocuments.htm
15. Add a Work Product or Document Record: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/add_a_work_product_or_document_record.htm
16. Assign a Document Status or Category: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/assign_a_document_status_or_category.htm
17. Specify Work Product and Document Location References: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/specify_work_product_and_doc_location_references.htm
18. Identify a Document as a Work Product: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/identify_a_document_as_a_work_product.htm
19. Work Product and Document Details Dialog Box: https://docs.oracle.com/cd/G48902_01/client_help/en_US/work_product_and_document_details_dialog_box.htm
20. Files Tab — Work Product and Document Details: https://docs.oracle.com/cd/G48902_01/client_help/en_US/files_tab_-_work_product_and_document_details.htm
21. Professional V26 User Guide: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf

## 6. Remaining gaps — explicitly open

- Full comparison of all EPPM V26 Document Web Services operations (create/update/delete, check-in/out, review operations) against a V26 Professional API contract.
- Exact EPPM repository connector/version compatibility and feature matrix (Oracle's own Help warns that capabilities depend on repository type and unsupported features may be unavailable).
- Document-level privilege matrix for every security policy and repository configuration.
- Full document version history retention, concurrent checkout, stale checkout, force/undo checkout and failed check-in edge cases.
- Full review transition matrix, reviewer delegation, notifications, rejection/restart behavior, and review termination audit.
- EPPM repository file permissions vs P6 project security interaction, especially multiple-user authentication mode.
- Behavior of Professional document records when the underlying external file path is unavailable, changed or deleted.
- Whether any Professional V26 add-on/connector provides repository-backed review outside the core Professional Help described here.
- Physical schema and exact V26 API field mapping for Document, DocumentVersion, DocumentReview, DocumentFolder and repository metadata.
- Controlled test of Professional V26 connected to an EPPM database with repository enabled, versus standalone Professional database, and EPPM with/without repository.

## 7. Boundary and conclusion

This is a **documentation-only reference comparison**. No repository was configured, no document was uploaded or checked in/out, no review was initiated, and no document record or project data was changed. No CUBI workspace, product menu, feature, application code, database schema, data flow, or agent-owned task was modified.

**Conclusion:** Both products support Work Product/Document records, metadata, and project-object associations. Professional V26's documented model is centered on records plus public/private external file references and configurable status/category values. EPPM V26 can provide the same basic reference behavior without a repository, but a configured optional Content Repository adds a materially richer managed document lifecycle: upload, version history, check-in/out, folders, templates, security policies, review assignments and approval states. Professional connected to that EPPM database does not become a full repository client: its document detail fields are read-only and the file cannot be opened from Professional. This is the defensible distinction; “documents exist only in EPPM” and “Professional has the same document review workflow” are both incorrect.
