#!/usr/bin/env python3
"""Synchronize selected ComfyUI custom nodes to the checked-in Comfy3D lockset.

This is intentionally small and Docker-friendly: it updates an existing custom-node
checkout in place when present, or clones it when absent, then installs its
requirements. Use it after changing ComfyUI core refs so nodes that depend on
ComfyUI internals are re-pinned to known-compatible commits.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def node_dir_from_repo(repo: str) -> str:
    name = repo.rstrip("/").split("/")[-1]
    return name[:-4] if name.endswith(".git") else name


def sync_node(name: str, spec: dict, custom_nodes: Path) -> None:
    repo = spec["repo"]
    ref = spec["ref"]
    dirname = spec.get("directory") or node_dir_from_repo(repo)
    target = custom_nodes / dirname
    custom_nodes.mkdir(parents=True, exist_ok=True)

    print(f"==> Syncing {name}: {repo}@{ref} -> {target}", flush=True)
    if target.exists():
        if not (target / ".git").exists():
            raise SystemExit(f"{target} exists but is not a git checkout")
        run(["git", "remote", "set-url", "origin", repo], cwd=target)
        run(["git", "fetch", "--depth", "1", "origin", ref], cwd=target)
    else:
        run(["git", "clone", "--no-checkout", "--filter=blob:none", repo, str(target)])
        run(["git", "fetch", "--depth", "1", "origin", ref], cwd=target)

    run(["git", "checkout", "--force", "FETCH_HEAD"], cwd=target)
    run(["git", "submodule", "update", "--init", "--recursive", "--depth", "1"], cwd=target)

    requirements = target / "requirements.txt"
    if requirements.exists():
        cmd = ["uv", "pip", "install", "-r", str(requirements)]
        if spec.get("no_build_isolation"):
            cmd.append("--no-build-isolation")
        for ignored in spec.get("ignore_requirements", []):
            print(f"NOTE: ignore_requirements is documented but not applied by sync script: {ignored}")
        run(cmd)
    else:
        print(f"No requirements.txt for {name}; skipping dependency install", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lockset", type=Path, default=Path("/app/utils/comfy3d_lockset.json"))
    parser.add_argument("--custom-nodes", type=Path, default=Path("/app/comfy/custom_nodes"))
    parser.add_argument("--node", action="append", help="Node key to sync. Can be repeated. Defaults to all nodes in lockset.")
    args = parser.parse_args()

    data = json.loads(args.lockset.read_text())
    nodes = data.get("nodes", {})
    selected = args.node or sorted(nodes)
    missing = [name for name in selected if name not in nodes]
    if missing:
        raise SystemExit(f"Node(s) missing from lockset: {', '.join(missing)}")

    for name in selected:
        sync_node(name, nodes[name], args.custom_nodes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
