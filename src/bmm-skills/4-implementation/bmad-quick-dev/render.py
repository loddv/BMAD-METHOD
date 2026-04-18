#!/usr/bin/env python3
"""render.py — bmad-quick-dev template renderer.

Resolves compile-time {{.variable}} placeholders from _bmad/bmm/config.yaml,
bakes absolute paths for {project-root} into derived values, and writes
rendered .md files to {project-root}/_bmad/render/bmad-quick-dev/.

Runtime {variable} placeholders (single curly) pass through untouched for
the LLM to resolve during workflow execution.

Every invocation rebuilds from scratch — no hash, no cache.
Python 3 stdlib only. UTF-8 I/O.
"""

import os
import re
import sys


def find_project_root():
    """Walk up from cwd until a _bmad/ directory is found. Exit non-zero otherwise."""
    current = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(current, "_bmad")
        if os.path.isdir(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            print(
                f"render.py: no _bmad/ directory found walking up from {os.getcwd()}",
                file=sys.stderr,
            )
            sys.exit(1)
        current = parent


def load_flat_yaml(path):
    """Parse a flat key: value YAML file. Quotes stripped; indented values ignored.
    Returns {} if the file is missing (with a stderr warning)."""
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        print(
            f"render.py: config not found at {path}; using smart defaults",
            file=sys.stderr,
        )
        return result
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        if line.startswith(" ") or line.startswith("\t"):
            continue
        colon = stripped.find(":")
        if colon < 0:
            continue
        key = stripped[:colon].strip()
        value = stripped[colon + 1 :].strip().strip("'\"")
        if not key or not value:
            continue
        # Skip YAML inline dict/list literals (balanced braces/brackets)
        if (value.startswith("{") and value.endswith("}")) or (
            value.startswith("[") and value.endswith("]")
        ):
            continue
        result[key] = value
    return result


def render_template(content, vars_):
    """Resolve {{.var}} substitutions. Unresolved references emit an empty string
    (Go's missingkey=zero semantics)."""
    return re.sub(r"\{\{\.(\w+)\}\}", lambda m: vars_.get(m.group(1), ""), content)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_name = os.path.basename(script_dir)
    root = find_project_root()

    config_path = os.path.join(root, "_bmad", "bmm", "config.yaml")
    vars_ = load_flat_yaml(config_path)

    vars_.setdefault(
        "planning_artifacts", "{project-root}/_bmad-output/planning-artifacts"
    )
    vars_.setdefault(
        "implementation_artifacts",
        "{project-root}/_bmad-output/implementation-artifacts",
    )
    vars_.setdefault("communication_language", "English")

    for key in list(vars_.keys()):
        vars_[key] = vars_[key].replace("{project-root}", root)

    vars_["project_root"] = root
    vars_["main_config"] = os.path.join(root, "_bmad", "bmm", "config.yaml")
    vars_["sprint_status"] = os.path.join(
        vars_["implementation_artifacts"], "sprint-status.yaml"
    )
    vars_["deferred_work_file"] = os.path.join(
        vars_["implementation_artifacts"], "deferred-work.md"
    )

    out_dir = os.path.join(root, "_bmad", "render", skill_name)
    os.makedirs(out_dir, exist_ok=True)

    count = 0
    for fname in sorted(os.listdir(script_dir)):
        if not fname.endswith(".md") or fname == "SKILL.md":
            continue
        src = os.path.join(script_dir, fname)
        dst = os.path.join(out_dir, fname)
        with open(src, "r", encoding="utf-8") as fh:
            content = fh.read()
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(render_template(content, vars_))
        count += 1

    print(f"render.py: rendered {count} files -> {out_dir}")


if __name__ == "__main__":
    main()
