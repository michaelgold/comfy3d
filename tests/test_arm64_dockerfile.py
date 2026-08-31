import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARM64_DOCKERFILE = ROOT / "Docker" / "Dockerfile.arm64"
AMD64_DOCKERFILE = ROOT / "Docker" / "Dockerfile"
LOCKSET = ROOT / "utils" / "comfy3d_lockset.json"
UNIRIG_COMMIT = "cab707a2c0f69900df0c8577418441750a84e0db"


def test_arm64_image_installs_and_validates_bpy_5_2_1():
    dockerfile = ARM64_DOCKERFILE.read_text()
    normalized = " ".join(dockerfile.replace("\\\n", " ").split())

    assert "ARG BPY_VERSION=5.2.1" in dockerfile
    assert (
        'ARG BPY_ARM64_WHEEL_NAME="bpy-${BPY_VERSION}-cp313-cp313-manylinux_2_39_aarch64.whl"'
        in dockerfile
    )
    assert (
        "https://github.com/michaelgold/buildbpy/releases/download/"
        "v${BPY_VERSION}/${BPY_ARM64_WHEEL_NAME}"
        in dockerfile
    )
    assert "93ac058b264ccc847aacdb33ed460bff519dfb30f7c55fc477ca0b04ca81ff80" in dockerfile
    assert "sha256sum --check" in dockerfile
    bpy_checksum = dockerfile.index("sha256sum --check", dockerfile.index("ARG BPY_ARM64_SHA256"))
    bpy_install = dockerfile.index('uv pip install "/tmp/${BPY_ARM64_WHEEL_NAME}"')
    bpy_import = dockerfile.index("import bpy, platform")
    assert bpy_checksum < bpy_install < bpy_import
    assert "https://sh.rustup.rs" not in dockerfile
    assert "ARG RUSTUP_VERSION=1.28.2" in dockerfile
    assert "e3853c5a252fca15252d07cb23a1bdd9377a8c6f3efa01531109281ae47f841c" in dockerfile
    rust_checksum = dockerfile.index("sha256sum --check", dockerfile.index("ARG RUSTUP_SHA256"))
    rust_execute = dockerfile.index('/tmp/rustup-init -y --profile minimal')
    assert rust_checksum < rust_execute
    assert "import bpy, platform" in dockerfile
    assert "platform.machine() == 'aarch64'" in dockerfile
    assert "bpy.app.version == (5, 2, 1)" in dockerfile
    assert (
        "libgl1 libegl1 libopengl0 libglu1-mesa libxfixes3 libxi6 "
        "libxrender1 libxkbcommon0 libsm6 libxext6 libglib2.0-0 libtbbmalloc2"
        in normalized
    )
    assert UNIRIG_COMMIT in dockerfile
    assert "a117c477762f65fe29ed51738e2e83498c43eed7" in dockerfile
    assert "libharfbuzz0b" in dockerfile
    assert "Skipping bpy" not in dockerfile


def test_amd64_and_arm64_pin_the_same_accepted_unirig_commit():
    for path in (AMD64_DOCKERFILE, ARM64_DOCKERFILE):
        dockerfile = path.read_text()
        assert UNIRIG_COMMIT in dockerfile
        assert "4f2d5803dcd59ac0230623bb20871e176a1b650b" not in dockerfile
        assert "c68895bd9f4ad44451bec335be97f0b98ccddabd" not in dockerfile

    lockset = json.loads(LOCKSET.read_text())
    unirig = lockset["nodes"]["ComfyUI-UniRig"]
    assert unirig["repo"] == "https://github.com/michaelgold/ComfyUI-UniRig"
    assert unirig["ref"] == UNIRIG_COMMIT
