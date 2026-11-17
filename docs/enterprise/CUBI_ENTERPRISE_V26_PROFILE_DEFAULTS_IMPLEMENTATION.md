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
- Deliberately rejects Select Resources until CUBI has an enterprise-wide resource hierarchy with authoritative root/descendant resolution. The existing resource master is project/revision scoped and cannot safely be used as a substitute for the V26 global resource hierarchy.

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
- rejection of arbitrary selected-resource IDs while no enterprise-wide resource hierarchy exists.

## Explicitly not claimed by this slice

Automatic Global-default assignment is now wired to user insertion/reactivation and the operator bootstrap. Automatic Project-default assignment when OBS access is assigned is still open and must be implemented through the same canonical repository. Select Resources remains unavailable until the enterprise-wide resource hierarchy exists; do not treat the project-scoped resource master as an equivalent. The work does not introduce a second `p6_global_security_profiles` table or a second project-profile/OBS assignment authority.
