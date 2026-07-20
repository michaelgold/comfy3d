#!/usr/bin/env python3
"""Install a Blender add-on zip into the bpy module environment.

Designed for Comfy3D Docker builds where proprietary/customer-provided Blender
add-ons should not be committed to the public repository. Provide the zip as a
Docker BuildKit secret and install it into Blender's user scripts/addons path.
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


def extract_addon(zip_path: Path, addon_dir: Path, module_name: str) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if n and not n.startswith(IGNORED_PREFIXES)]
        roots = _zip_roots(names)
        if len(roots) != 1:
            raise RuntimeError(f"Expected a single addon root in {zip_path}, found: {sorted(roots)}")

        root = next(iter(roots))
        addon_dir.mkdir(parents=True, exist_ok=True)
        target = addon_dir / module_name
        if target.exists():
            shutil.rmtree(target)

        with tempfile.TemporaryDirectory(prefix="blender-addon-") as tmp:
            tmp_path = Path(tmp)
            archive.extractall(tmp_path, members=names)
            extracted_root = tmp_path / root
            if not (extracted_root / "__init__.py").exists():
                raise RuntimeError(f"{zip_path} root {root!r} is not a Blender add-on package")
            shutil.move(str(extracted_root), target)

    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--module", default="auto_rig_pro")
    parser.add_argument("--extract-only", action="store_true", help="verify zip/extraction without importing bpy")
    args = parser.parse_args()

    if not args.zip_path.exists():
        raise FileNotFoundError(args.zip_path)

    if args.extract_only:
        addon_dir = Path(tempfile.mkdtemp(prefix="blender-addon-verify-")) / "addons"
    else:
        import bpy  # type: ignore

        addon_dir = Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))

    target = extract_addon(args.zip_path, addon_dir, args.module)
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
