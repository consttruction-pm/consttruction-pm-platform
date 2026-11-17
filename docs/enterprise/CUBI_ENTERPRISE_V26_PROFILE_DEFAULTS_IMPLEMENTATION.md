# CUBI Enterprise — V26 Global and Project Security Profile Defaults

Status: implemented in this branch as a focused persistence/authorization foundation slice; not a claim of complete P6 EPPM V26 security parity.

## Normative Oracle HTML Help

- [Working with Security Profiles — V26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html)
- [Creating Global Security Profiles — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/35572.htm)
- [Creating Project Security Profiles — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/35278.htm)
- [Global Privileges Detail Window — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm)
- [Project Privileges Detail Window — V26](https://docs.oracle.com/cd/G48897_01/p6help/en/102786.htm)

## Required behavior

Oracle V26 defines two different default-profile scopes:

1. A Global Security Profile default is assigned to new users.
2. A Project Security Profile default is used when OBS access is assigned to a user.

Each scope has one active default profile. The defaults are independent: changing the Global default must not clear or revision-bump the Project default, and vice versa. The profile must be active before it can become default. A default profile cannot be deleted while it remains the default; an administrator must select a replacement first.

## Implementation in this slice

- Keeps both Global and Project profiles in the canonical `p6_security_profiles` table and their grants in `p6_security_profile_privileges`.
- Adds a tenant-scoped partial unique index for the Global default while retaining the independent Project default index.
- Removes the Project-only database check that previously rejected Global defaults.
- Uses a separate advisory lock per tenant and profile scope to serialize default changes.
- Revision-bumps and append-audits both the newly selected profile and the previously selected profile in the same scope.
- Exposes `get_default_global_profile` alongside the existing `get_default_project_profile`.
- Rejects deletion of a currently selected default profile.

## Acceptance evidence added

`tests/integration/test_security_profiles_postgres_live.py` covers:
- simultaneous Global and Project defaults for one tenant;
- switching each default independently;
- revision changes on the displaced default;
- retrieval of the current default by scope;
- deletion denial for either active default.

## Explicitly not claimed by this slice

This change does not yet wire automatic Global-default assignment into new-user provisioning or automatic Project-default assignment into OBS assignment. Those flows must use the same canonical repository and be covered in a separate exact-HTML-Help integration slice. It also does not introduce a second `p6_global_security_profiles` table or a second project-profile/OBS assignment authority.
