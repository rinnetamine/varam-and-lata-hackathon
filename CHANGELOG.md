# Changes since d8f003d

## Demonstration entry flow

- Added a larger, animated iPhone-style popup beside the demo panel on the homepage.
- Added phone status details, a clickable Gmail icon, a single fictional VSAA newborn email, and a link that closes the popup and opens the portal.
- Added Latvian/English phone content, back/close/reset behaviour and reduced-motion support.

## Applications and profile roadmap

- Added confirmation before simple benefit submissions, showing profile-derived applicant/child details and a masked payout account.
- Added the profile-data warning to applications with selectable options; tightened the confirmation layout and placed confirmation on the right, cancellation on the left.
- Added child support roadmaps showing submitted, available and future benefits, deadlines and child-specific VSAA links.
- Added expandable calculation previews and 12/24-month childcare and single-child family-state benefit scenarios.
- Income-based previews require a daily contribution wage and reuse existing formulas. Future rates, entitlement and payment dates are not guaranteed. Forecasts are not persisted.
- Documented forecast assumptions and sources in OPEN_DATA.md.

## VSAA presentation and filtering

- Made benefit columns consistent across rows, including long status labels, with responsive layouts.
- Child selection now refreshes benefits, applications and reminders together, updates the URL and survives refresh/language changes.
- Added child/benefit identifiers to first-birthday reminders so they can be filtered correctly.

## Service wording

- Replaced demo-oriented operational labels with normal service wording in Latvian and English: reminders, submissions, confirmations, bank instructions and personal-code fields.
- Reminder control reads “Sūtīt atgādinājumus uz e-pastu”. Delivery remains simulated in the portal inbox.
- Removed demo-panel references from normal bank instructions and technical server instructions from user-facing load errors.
- Retained prototype warnings, authentication disclosures, calculation limitations and the demonstration panel.

## Names and showcase databases

- Name generation uses gender-separated imported PMLP first-name statistics and matches the explicit parent roles, with gender-appropriate fictional surnames.
- Added a repair for mismatched names in the previous showcase, then replaced that showcase with the requested versioned v4 dataset.
- Accounts 1–2 are parents of one child born three days before seeding; accounts 3–4 are parents of two children with some benefits already granted; account 5 is a single mother of three; account 999 is the administrator.
- Seeded six children, five granted benefit applications, matching inbox confirmations/decisions, and one closed unpaid B sick-leave record for each parent.
- Updated the separate people, children and mock-bank databases and README scenario documentation. Startup preserves actions after the one-time dataset migration.
- Committed database snapshots exclude sessions. Runtime databases and ignored backups retain their local state.

## Administrator tools

- Allowed admin access to the shared calculator and provided admin navigation on calculator and data-source pages.
- Locked decision/refresh buttons while a status change is saving to prevent duplicate actions.
- Verified review, grant and rejection persistence and matching applicant inbox notifications, including duplicate notification suppression.

## Verification

JavaScript syntax and diff checks passed. Temporary DOM checks covered phone flow, confirmation cancellation, child/application/reminder filtering, language persistence and administrator tool navigation. Temporary database checks covered the v4 family counts, sick leaves, application lifecycle, inbox decisions, persistence and integrity of all three databases. Forecast boundary checks passed.

The existing `server/test_api.py` still assumes the previous seven-parent showcase and stops at its old account-count assertions. It needs its scenario fixtures updated. New verification scripts were run temporarily and were not added to the repository.
