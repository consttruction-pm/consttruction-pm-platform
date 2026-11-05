# CUBI Product Surface Architecture — One Canonical Visual Workspace

**Status:** Product-owner decision / mandatory architecture principle  
**Decision date:** 2026-11-04  
**Acceptance issue:** [#1712](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1712)

## 1. Non-negotiable product identity

CUBI has exactly one main product environment: the **Visual Workspace**. This is the actual product interface, not a demo, optional mode, secondary route or alternative to a dashboard.

There is no separate authenticated dashboard, generic SaaS app, second workspace shell or parallel product environment. Do not create one.

## 2. Website information architecture

The public website and authenticated product are distinct layers in one site:

1. **Home** — public homepage and primary product introduction.
2. **Normal public pages** — Platform, Solutions, Resources, Pricing, Contact and other approved informational/marketing pages.
3. **Single product entry** — one clear Login / Open Workspace entry leading to the Visual Workspace.

The public pages remain conventional website pages. They are not alternate product environments. The site must not expose a second app/dashboard entry.

## 3. Authentication and navigation

- Successful login opens the Visual Workspace by default.
- If the user requested an authorized deep link before login, restore that destination as a window/page inside the same workspace shell.
- Logout returns to the public Home page.
- Refresh, direct URL entry and session restoration must preserve the same workspace shell and authorized project/window context.
- No route may open a second authenticated shell or generic dashboard.

## 4. Where product capabilities live

Every authenticated capability belongs inside the Visual Workspace, using its existing persistent shell:
- global menus, nested menus and toolbars;
- project windows, page tabs and navigation tree;
- engineering engines, scheduling, resource, cost, progress and quality controls;
- reports, charts, forms and document tools;
- administration, preferences, audit and security;
- dialogs, drawers, contextual panels and page-specific Details.

New capabilities extend this workspace. They do not become a separate app.

## 5. Visual no-regression rules

- Preserve the approved visual workspace as the primary post-login screen.
- Preserve existing page dimensions, window proportions, Gantt sizing, toolbar placement, navigation and page-specific Details layouts unless a separate explicit approval authorizes a change.
- Do not move the visual workspace behind a Help route, demo route, secondary menu or generic dashboard.
- Do not remove or replace existing workspace functionality while enforcing this entry flow.
- Any controls not yet connected must communicate their truthful state; no fake success.

## 6. Acceptance evidence

The rule is considered implemented only when the running website demonstrates:
1. Home and ordinary public pages work as public routes.
2. Exactly one product entry leads to authentication / workspace.
3. Login opens the Visual Workspace by default.
4. Logout returns to Home.
5. Direct workspace links and refresh remain inside the same shell.
6. All product tools and engineering engines open within that shell.
7. No competing dashboard, second app shell or visual-demo route is exposed.
8. Browser E2E tests cover the full journey, deep links, session restoration and permissions.

Documentation or a route catalogue alone is not implementation proof. Keep issue #1712 open until runtime evidence passes.
