from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARM64_DOCKERFILE = ROOT / "Docker" / "Dockerfile.arm64"


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
    assert "4f2d5803dcd59ac0230623bb20871e176a1b650b" in dockerfile
    assert "a117c477762f65fe29ed51738e2e83498c43eed7" in dockerfile
    assert "libharfbuzz0b" in dockerfile
    assert "Skipping bpy" not in dockerfile
