# Security policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Use **[Report a vulnerability](https://github.com/techazm/foxess-cloud-ha/security/advisories/new)** (private to the maintainers), or email **services@azmtech.com.au**.

Include what you found, how to reproduce it and the impact you expect. You will get an
acknowledgement within 3 business days and a fix or mitigation plan as soon as the
issue is confirmed.

## Supported versions

Only the latest release on `main` receives security fixes.

## How this repository is protected

- Secret scanning with gitleaks on every pull request, every push to `main` and weekly
  across the full history; the same check runs locally via `pre-commit`.
- Dependabot alerts, one bundled dependency update PR per day, and grouped security
  update PRs as soon as an advisory is published.
- All changes reach `main` through pull requests with required checks.
