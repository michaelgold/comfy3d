# Auto-Rig Pro bundled for Comfy3D

Source: local `~/auto_rig_pro-master-new.zip` provided for the SIGGRAPH Comfy3D build.

Detected version: 3.78.34 (`blender_manifest.toml` / `bl_info`).

Licensing from upstream `LICENSE.txt` and `blender_manifest.toml`:

- Add-on source code: GNU General Public License, version 3 / GPL-2.0-or-later as declared in the Blender manifest.
- Asset files such as icons and rig components in `.blend` format: Royalty Free license and CC0; see subfolder license files.
- Generated rigs are the sole property of the end user according to upstream `LICENSE.txt`.

This copy is installed into the Docker image using `utils/install_blender_addon_zip.py` so it runs inside the same controlled Python/Blender environment as Comfy3D's `bpy==5.0.1` install.
