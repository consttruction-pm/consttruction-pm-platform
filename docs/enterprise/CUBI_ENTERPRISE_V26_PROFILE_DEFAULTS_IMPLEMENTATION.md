# CUBI Enterprise — V26 Global and Project Security Profile Defaults

Status: implemented in this branch as a focused persistence/authorization foundation slice; not a claim of complete P6 EPPM V26 security parity.

## Normative Oracle HTML Help

- [Working with Security Profiles — V26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html)
- [Creating Global Security Profiles — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/35572.htm)
- [Creating Project Security Profiles — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm)
- [Global Privileges Detail Window — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm)
- [Project Privileges Detail Window — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm)
- [Users Page — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm)
- [Assigning Module Access — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/8118.htm)
- [Assigning Resource Access — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/7793.htm)
- [Project Access Detail Window — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/6186.htm)
- [Assigning OBS Elements to Users — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/35460.htm)
- [Assigning Global Security Profiles — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/8117.htm)

## Required behavior

Oracle V26 defines two different default-profile scopes:

1. A Global Security Profile default is assigned to new users.
2. A Project Security Profile default is used when OBS access is assigned to a user.

Each scope has one active default profile. The defaults are independent: changing the Global default must not clear or revision-bump the Project default, and vice versa. The profile must be active before it can become default. A default profile cannot be deleted while it remains the default; an administrator must select a replacement first. A tenant must retain one Global default because each new user requires a Global profile.

## Implementation in this slice

- Keeps both Global and Project profiles in the canonical `p6_security_profiles` table and their grants in `p6_security_profile_privileges`.
- Adds a tenant-scoped partial unique index for the Global default while retaining the independent Project default index.
- Removes the Project-only database check that previously rejected Global defaults.
- Uses a separate advisory lock per tenant and profile scope to serialize default changes.
- Revision-bumps and append-audits both the newly selected profile and the previously selected profile in the same scope.
- Exposes `get_default_global_profile` alongside the existing `get_default_project_profile`.
- Rejects deletion of a currently selected default profile.
- Requires the current assignment revision when replacing a user's Global profile, updates the single assignment in place, and preserves the last-Admin-Superuser guard.
- Keeps reserved built-in profile identities immutable; No Global Privileges may be selected as the safe Global default, but Admin Superuser and Project Superuser cannot become defaults.
- On first operator bootstrap, provisions No Global Privileges as the tenant Global default if no safe Global default exists, assigns it to existing active users without a Global assignment, and grants the bootstrap administrator the immutable Admin Superuser profile.
- Installs a database trigger so newly inserted or reactivated users receive the current Global default in the same canonical assignment table; changing the default affects future users, not existing assignments.
- Stores Module Access and Resource Access on the same `p6_security_profile_assignments` row as the Global profile; it does not create `p6_user_global_security` or a second profile assignment store.
- Validates the V26 module list and Contributor exclusivity; the bilingual administration UI edits module access. Server-side project and global resource authorization checks the corresponding module access.
- Uses No Resources as the default Resource Access mode; All Resources is supported, and Admin Superuser always receives all-resource access.
- Applies the Users Page visibility boundary: Admin Superuser can see all tenant users; a user with Add/Edit/Delete Users but without All Resources can see only their own account. Cross-user profile assignment, account activation/deactivation, and user-access reads require All Resources until selected-resource ancestry is available.
- Deactivating an account clears its Module Access on the same canonical Global assignment and records a revisioned audit event; reactivation does not silently restore removed modules. The database default-profile trigger does not override an existing assignment.
- Admin Superuser still obeys independent Module Access for project/resource modules; its Global profile does not re-enable modules removed by user deactivation.
- Deliberately rejects Select Resources until CUBI has an enterprise-wide resource hierarchy with authoritative root/descendant resolution. The existing resource master is project/revision scoped and cannot safely be used as a substitute for the V26 global resource hierarchy.
- During operator bootstrap, provisions a protected, read-only `p6-default-project-readonly` profile as the Project default when a tenant has not selected one.
- Adds a canonical OBS assignment operation: assigning an OBS without an explicit Project profile resolves the current Project default and records the profile in `p6_security_profile_assignments`; the operation shares the Project-default advisory lock so a concurrent default change cannot race the assignment.
- Enforces one Project profile per user/OBS with a partial unique index. Replacing a profile is revision-guarded and audited in place; it does not accumulate additive grants.
- Adds a tenant-scoped OBS options endpoint and a bilingual selector/form in the Enterprise access UI. The selector reads `p6_obs_node`, not the duplicate `enterprise_user_obs_assignments` store.
- Preserves V26 Responsible OBS behavior across EPS ancestry: a root-EPS Responsible OBS applies to descendant projects, while the nearest explicit WBS Responsible OBS takes precedence for WBS-scoped operations.

## Acceptance evidence added

`tests/integration/test_security_profiles_postgres_live.py` covers:
- simultaneous Global and Project defaults for one tenant;
- switching each default independently;
- revision changes on the displaced default;
- retrieval of the current default by scope;
- deletion denial for either active default;
- current-revision enforcement when replacing Global assignments and protection of the final Admin Superuser assignment;
- automatic safe Global-default assignment for existing/new users and bootstrap Admin module/resource settings;
- Module Access normalization, Contributor exclusivity, revisioned updates, immutable audit, and project-module authorization gating;
- rejection of arbitrary selected-resource IDs while no enterprise-wide resource hierarchy exists;
- Resource Access-based user-directory visibility, cross-user administration guard, and module removal on deactivation;
- safe Project default bootstrap, automatic default profile application on OBS assignment, single user/OBS profile enforcement, and revisioned replacement.

## Remaining V26 Users Page parity

This focused slice is not a claim that the entire V26 Users Page has been replicated. The following Help-defined areas remain open:
- Associated Resource field and resource-to-user association.
- Select Resources dialog with up to five resource roots and recursive descendant visibility; it remains disabled/fail-closed until the canonical enterprise-wide resource hierarchy is implemented.
- User Interface View assignment and copy-user-settings behavior.
- Full V26 dialog, toolbar, context-menu, hierarchy and keyboard interaction parity for the User Access and Security Profiles administration surfaces.
- Full integrated mainline acceptance after #1974, #1983 and #1984 are reconciled into one authority.

## Explicitly not claimed by this slice

Automatic Global-default assignment is wired to user insertion/reactivation and the operator bootstrap. Automatic Project-default assignment is wired through the canonical Enterprise user-access endpoint and UI; however, the existing #1983 branch still contains a second project-profile/OBS assignment store and must be reconciled before E0 can merge. Select Resources remains unavailable until the enterprise-wide resource hierarchy exists; do not treat the project-scoped resource master as an equivalent. The work does not introduce a second `p6_global_security_profiles` table or a second project-profile/OBS assignment authority.
