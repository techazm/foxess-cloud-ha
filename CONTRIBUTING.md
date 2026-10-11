# Contributing

## Workflow

1. Branch from `main`: `feat/short-description`, `fix/…`, `chore/…`, `docs/…`.
2. Commit in small, focused steps using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: add booking reminders`, `fix(api): handle empty payload`, `chore(deps): bump express`.
   The body explains *why* the change is needed, not just what changed.
3. Open a pull request and fill in the template. The PR title must also be a
   Conventional Commit: it becomes the squash-merge commit on `main`.
4. Merge once the required checks are green. Branches are deleted automatically after merge.

`main` is protected by a ruleset: no direct pushes, force-pushes or deletion, and a
linear history (squash merges only).

## Required checks

| Check | What it does |
|---|---|
| `ci-ok` | Lint, test and build for this repo (see `.github/workflows/ci.yml`) |
| `gitleaks` | Fails if a secret appears anywhere in the git history |
| `pr-title` | PR title follows Conventional Commits |

## Local checks

```bash
pip install pre-commit && pre-commit install   # once per clone
python -m compileall -q custom_components
```

## Secrets and personal data

Never commit `.env` files, keys, certificates, Terraform state or customer data. Put
templates in `*.example` files. If something slips through, rotate it first, then
clean the history.

## Releases

Tag `main` with `vX.Y.Z` and use **Generate release notes** on GitHub; notes are
grouped by label (see `.github/release.yml`).
