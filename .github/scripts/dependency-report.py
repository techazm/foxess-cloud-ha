#!/usr/bin/env python3
"""List dependencies with a new MAJOR version, for every ecosystem in the repo.

Dependabot only proposes patch/minor updates (see .github/dependabot.yml), so this
report is how new majors get noticed. Standard library only.

  python3 .github/scripts/dependency-report.py [--npm DIR ...]

Checks: GitHub Actions (workflow `uses:` pins), npm (`npm outdated`, needs installed
node_modules), Docker official images (FROM lines), Terraform providers, and Python
packages (pyproject.toml / requirements*.txt). Prints a Markdown table, or nothing.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(".")
SKIP = {
    "node_modules",
    ".git",
    ".terraform",
    ".venv",
    "venv",
    "dist",
    "build",
    "Library",
}
rows = []


def get(url, token=None):
    req = urllib.request.Request(
        url, headers={"User-Agent": "dependency-report", "Accept": "application/json"}
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:  # report but never fail the whole run on one lookup
        print(f"warning: {url}: {e}", file=sys.stderr)
        return None


def major(v):
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else None


def files(pattern):
    for p in ROOT.rglob(pattern):
        if not SKIP.intersection(p.parts):
            yield p


def add(eco, where, name, current, latest):
    if (
        major(current) is not None
        and major(latest) is not None
        and major(latest) > major(current)
    ):
        rows.append((eco, where, name, str(current), str(latest)))


def github_actions():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    seen = {}
    for wf in list(files(".github/workflows/*.yml")) + list(
        files(".github/workflows/*.yaml")
    ):
        for m in re.finditer(
            r"uses:\s*([\w.-]+/[\w.-]+)(?:/[\w./-]+)?@\S+(?:\s*#\s*(v?[\d.]+))?",
            wf.read_text(encoding="utf-8"),
        ):
            repo, ver = m.group(1), m.group(2)
            if ver and repo not in seen:
                seen[repo] = ver
    for repo, ver in sorted(seen.items()):
        rel = get(f"https://api.github.com/repos/{repo}/releases/latest", token)
        if rel and rel.get("tag_name"):
            add("github-actions", ".github/workflows", repo, ver, rel["tag_name"])


def npm(dirs):
    for d in dirs:
        r = subprocess.run(
            ["npm", "outdated", "--json", "--long"],
            cwd=d,
            capture_output=True,
            text=True,
        )
        for name, v in json.loads(r.stdout or "{}").items():
            add("npm", d, name, v.get("current"), v.get("latest"))


def docker():
    for df in (
        list(files("Dockerfile"))
        + list(files("Dockerfile.*"))
        + list(files("*.Dockerfile"))
    ):
        for m in re.finditer(
            r"^FROM\s+(?:--platform=\S+\s+)?([a-z0-9._-]+):(\d+)(?:\.\d+)*(-[\w.-]+)?",
            df.read_text(encoding="utf-8"),
            re.M,
        ):
            image, cur, suffix = m.group(1), int(m.group(2)), m.group(3) or ""
            data = get(
                f"https://hub.docker.com/v2/repositories/library/{image}/tags?page_size=100&name={suffix.lstrip('-')}"
            )
            if not data:
                continue
            pat = re.compile(rf"^(\d+)(?:\.\d+)*{re.escape(suffix)}$")
            best = max(
                (
                    int(pm.group(1))
                    for t in data.get("results", [])
                    if (pm := pat.match(t["name"]))
                ),
                default=None,
            )
            if best and best > cur:
                note = " (use an LTS line)" if image == "node" and best % 2 else ""
                rows.append(
                    (
                        "docker",
                        str(df),
                        image,
                        f"{cur}{suffix}",
                        f"{best}{suffix}{note}",
                    )
                )


def terraform():
    for tf in files("*.tf"):
        text = tf.read_text(encoding="utf-8")
        for m in re.finditer(
            r'source\s*=\s*"([\w-]+/[\w-]+)"\s*\n\s*version\s*=\s*"([^"]+)"', text
        ):
            src, constraint = m.group(1), m.group(2)
            data = get(f"https://registry.terraform.io/v1/providers/{src}")
            if data and data.get("version"):
                add("terraform", str(tf.parent), src, constraint, data["version"])


def python():
    specs = []
    for pp in files("pyproject.toml"):
        block = re.search(
            r"^dependencies\s*=\s*\[(.*?)\]",
            pp.read_text(encoding="utf-8"),
            re.S | re.M,
        )
        if block:
            specs += [(str(pp), s) for s in re.findall(r'"([^"]+)"', block.group(1))]
    for rq in files("requirements*.txt"):
        specs += [
            (str(rq), line.strip())
            for line in rq.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith(("#", "-"))
        ]
    for where, spec in specs:
        m = re.match(
            r"([A-Za-z0-9_.-]+)(?:\[[^\]]*\])?\s*(?:[<>=~!]=?\s*([\d.]+))?", spec
        )
        if not m or not m.group(2):
            continue
        data = get(f"https://pypi.org/pypi/{m.group(1)}/json")
        if data:
            add("python", where, m.group(1), m.group(2), data["info"]["version"])


ap = argparse.ArgumentParser()
ap.add_argument("--npm", nargs="*", default=[])
args = ap.parse_args()
github_actions()
npm(args.npm)
docker()
terraform()
python()
if rows:
    print(
        "| Ecosystem | Where | Dependency | Current | Latest |\n|---|---|---|---|---|"
    )
    for r in sorted(rows):
        print(
            "| "
            + " | ".join(f"`{x}`" if i in (1,) else x for i, x in enumerate(r))
            + " |"
        )
