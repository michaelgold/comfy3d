#!/usr/bin/env python3
"""Install a Blender add-on package into the bpy module environment.

Accepts either a Blender add-on zip or an extracted add-on package directory.
Comfy3D uses this to install Auto-Rig Pro into the same controlled Docker
runtime that provides Blender's Python module (`bpy`).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


IGNORED_PREFIXES = ("__MACOSX/",)


def _zip_roots(names: list[str]) -> set[str]:
    roots: set[str] = set()
    for name in names:
        if not name or name.startswith(IGNORED_PREFIXES):
            continue
        parts = Path(name).parts
        if parts:
            roots.add(parts[0])
    return roots


def _copy_package(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if not (source / "__init__.py").exists():
        raise RuntimeError(f"{source} is not a Blender add-on package directory")
    shutil.copytree(source, target)


def install_addon(source_path: Path, addon_dir: Path, module_name: str) -> Path:
    addon_dir.mkdir(parents=True, exist_ok=True)
    target = addon_dir / module_name

    if source_path.is_dir():
        _copy_package(source_path, target)
        return target

    with zipfile.ZipFile(source_path) as archive:
        names = [n for n in archive.namelist() if n and not n.startswith(IGNORED_PREFIXES)]
        roots = _zip_roots(names)
        if len(roots) != 1:
            raise RuntimeError(f"Expected a single addon root in {source_path}, found: {sorted(roots)}")

        root = next(iter(roots))
        with tempfile.TemporaryDirectory(prefix="blender-addon-") as tmp:
            tmp_path = Path(tmp)
            archive.extractall(tmp_path, members=names)
            _copy_package(tmp_path / root, target)

    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_path", type=Path, help="Blender add-on zip or extracted package directory")
    parser.add_argument("--module", default="auto_rig_pro")
    parser.add_argument("--extract-only", action="store_true", help="verify zip/directory extraction without importing bpy")
    args = parser.parse_args()

    if not args.source_path.exists():
        raise FileNotFoundError(args.source_path)

    if args.extract_only:
        addon_dir = Path(tempfile.mkdtemp(prefix="blender-addon-verify-")) / "addons"
    else:
        import bpy  # type: ignore

        addon_dir = Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))

    target = install_addon(args.source_path, addon_dir, args.module)
    print(f"Installed Blender add-on package at {target}")

    if args.extract_only:
        return

    import bpy  # type: ignore

    if str(addon_dir) not in sys.path:
        sys.path.append(str(addon_dir))
    bpy.ops.preferences.addon_enable(module=args.module)
    bpy.ops.wm.save_userpref()
    print(f"Enabled Blender add-on module {args.module}")


if __name__ == "__main__":
    main()
