# Optional SkinTokens runtime

This is **opt-in runtime provisioning**. Existing rigging defaults remain unchanged.
SkinTokens runs in a separate Python process through `SkinTokensRigGLB` in the
maintained `michaelgold/ComfyUI-UniRig` fork. The node consumes `SKINTOKENS_ROOT`
and `SKINTOKENS_PYTHON`.

**Candidate build available; inference-unqualified:** both Dockerfiles and the
lockset now pin the maintained node to
`d53a0010f31106abf7dfe0822404cfe5d9a1b274`. Building these sources includes the
node; this does not claim that a published image has been rebuilt or validated.
Provisioning alone does **not** add the node to an older image. Before release,
verify the installed revision and `SkinTokensRigGLB` in `/object_info`, then run
a real GLB rigging smoke on each supported platform. GPU inference, texture
preservation, and deformation quality remain release gates.

## Pins and dependency boundaries

| Component | Immutable revision |
| --- | --- |
| VAST-AI-Research/SkinTokens source | `273b691d35989d71cd17ff2895fdc735097b92d1` |
| VAST-AI/SkinTokens model assets | `79736cad0fd84de384d5eede659b4ebd24effe33` |
| Qwen/Qwen3-0.6B configuration | `c1899de289a04d12100db370d81485cdf75e47ca` |

`utils/skintokens_runtime.py` clones/detaches the source, refuses changed tracked
files or a different revision, and creates a clean venv with **no system site
packages**. It never installs torch, bpy, or flash-attn automatically. Operators
must explicitly provision wheels/builds matching their Python ABI, CPU
architecture, CUDA toolkit/driver, GPU architecture, and Blender requirements.
All already installed distribution versions are constrained before inference
dependencies are installed, so conflicts fail instead of replacing that stack.
ComfyUI's interpreter and its transformers/diffusers versions are untouched.

The inference requirements pin the principal Python packages. NumPy/SciPy and
transitive dependencies are not a universal cross-platform lock; successful
installation records the actual complete environment in
`/opt/skintokens/installed-requirements.txt`. Keep that file with validation
results when qualifying a platform. This setup is not yet an inference-qualified
AMD64 or ARM64 release.

The pinned upstream demo really imports Gradio even in CLI mode, uses Lightning,
Transformers' Qwen3 implementation, Diffusers, and FlashAttention 2. Its Blender
server runs with the **same Python executable**. Its general `requirements.txt`
includes Open3D, but no file in the pinned CLI/server import graph imports it;
this inference-only profile omits Open3D. It does not silently replace
FlashAttention with another attention backend.

## Provision without rebuilding the image

From the Comfy3D checkout:

```sh
# For ARM64, substitute docker-compose.arm64.yml for docker-compose.yml.
docker compose -f docker-compose.yml -f docker-compose.skintokens.yml up -d

docker compose -f docker-compose.yml -f docker-compose.skintokens.yml exec comfy3d bash
# Remaining commands run inside the container:
cd /workspace
python utils/skintokens_runtime.py prepare --python python3.11
```

Choose an installed Python interpreter compatible with your **platform's** torch,
bpy, and flash-attn builds. The `prepare` command requires Python >= 3.11 plus
venv/ensurepip and git; it downloads source, not models or GPU packages. If the
image only provides another compatible Python, pass that executable instead.

For **Linux AMD64 / Python 3.11 only**, this is an explicit upstream-style starting
point (not an ARM64 recipe and not an inference certification):

```sh
P=/opt/skintokens/venv/bin/python
"$P" -m pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
  --index-url https://download.pytorch.org/whl/cu128
"$P" -m pip install numpy==1.26.4 bpy==4.2.0 packaging ninja setuptools wheel
# Install your validated flash-attn wheel matching this torch/CUDA/Python ABI:
"$P" -m pip install --no-deps /absolute/path/to/validated_flash_attn.whl
```

The last path must refer to an actual platform-qualified wheel. Building
FlashAttention from a reviewed pinned source is an alternative, requiring the
CUDA development toolkit and compiler; it can be expensive. Do not use an
unversioned auto-install into ComfyUI to bypass a missing wheel.

On **ARM64**, supply the corresponding torch, bpy and FlashAttention builds in
the isolated venv instead. The existing ARM64 image's bpy 5.2.1 wheel is CPython
3.13-specific; it cannot be installed in a Python 3.11 venv. Do not copy binaries
between environments or fall back to x86 wheels. Until the actual import/CUDA and
GLB tests pass on that ABI, ARM64 inference support remains unverified. If a
required wheel/build is unavailable, stop rather than modifying the working
ComfyUI environment.

Once the platform stack is installed:

```sh
python utils/skintokens_runtime.py install
python utils/skintokens_runtime.py download  # explicit multi-GB model download
python utils/skintokens_runtime.py validate
```

`install` requires torch, bpy, NumPy and importable flash-attn first, resolves
inference dependencies under immutable constraints for the preinstalled stack,
and runs `pip check`. `validate` verifies the source revision, required model
paths, Qwen3 config, dependency consistency, real demo/Blender-server imports,
and CUDA availability. It does **not** claim to load checkpoints or produce a
rig. Model presence validation checks nonempty files, not a full checkpoint
checksum. Only load trusted checkpoints: upstream deserializes PyTorch objects.

The overlay mounts a persistent runtime volume at `/opt/skintokens`. Source
`experiments/` and `models/` are symlinks into
`/app/comfy/models/skintokens`, which the base Compose file already bind-mounts
under `./models`. The downloader requests only two pinned checkpoints and the
Qwen3 `config.json`; it does not fetch datasets or the Qwen LLM weights. Hub cache
lives at `models/skintokens/huggingface`. Downloads accept the normal `HF_TOKEN`
environment variable; never bake tokens into images or commit them. Existing
non-symlink source model directories are refused, not overwritten.

Never reuse a venv volume across architectures, Python ABI changes, or
incompatible base images. Re-provision a new runtime volume instead; preserve
the separate model cache. Normal startup never installs or downloads anything.

## Native paths and final smoke

Outside Docker, provide writable absolute paths on **every** command:

```sh
python utils/skintokens_runtime.py prepare \
  --prefix "$HOME/skintokens-runtime" --cache "$HOME/models/skintokens" \
  --python python3.11
# Provision platform dependencies into $HOME/skintokens-runtime/venv, then run
# install, download, and validate with the same --prefix and --cache options.
. "$HOME/skintokens-runtime/env.sh"
# Start ComfyUI from this environment only after the maintained node is installed.
```

Upstream hardcodes `experiments/.../grpo_1400.ckpt`, uses the VAE path stored in
the checkpoint, and looks for `models/Qwen3-0.6B` relative to its **working
directory**. The node must run the subprocess with `cwd=SKINTOKENS_ROOT`, not the
ComfyUI directory. The symlinks preserve upstream's expected layout without
patching source.

**Do not launch the upstream demo directly as a smoke test.** It starts an
unauthenticated Blender service on `0.0.0.0:59876` that deserializes arbitrary
PyTorch/pickle payloads. Omitting Docker port publication is insufficient:
other containers on the same bridge can still reach it.

The maintained worker binds only to loopback, checks readiness and child exit,
rejects occupied port ownership and concurrent jobs, and reaps its Blender child
on ordinary completion or failure. The node owns process-group cleanup for
cancellation/timeouts. Loopback is not authentication: run only in a trusted
single-user/container network namespace, never with host networking or untrusted
local processes. Provisioning and import validation do not start this service.

After building the candidate image and provisioning/validating its isolated
runtime, a direct worker smoke can run **inside the container**:

```sh
set -eu
. /opt/skintokens/env.sh
NODE=/app/comfy/custom_nodes/ComfyUI-UniRig
test "$(git -C "$NODE" rev-parse HEAD)" = d53a0010f31106abf7dfe0822404cfe5d9a1b274
WORKER=/app/comfy/custom_nodes/ComfyUI-UniRig/nodes/skintokens_worker.py
test -f "$WORKER"
# Keep artifacts unique so stale output cannot satisfy the smoke.
OUT=$(mktemp -d /app/comfy/output/skintokens-smoke.XXXXXX)
cd "$SKINTOKENS_ROOT"
# GNU timeout owns the whole process group, including the Blender child.
# Do not add --foreground, which would disable group-wide timeout cleanup.
timeout --signal=TERM --kill-after=10s 1800s \
  "$SKINTOKENS_PYTHON" -u "$WORKER" \
  --input "$SKINTOKENS_ROOT/examples/giraffe.glb" \
  --output "$OUT/giraffe.glb" --num_beams 10 --use_transfer --use_postprocess
test -s "$OUT/giraffe.glb"
printf 'Inspect smoke artifact: %s\n' "$OUT/giraffe.glb"
```

A timeout/nonzero exit is a failed smoke even if a file exists. Do not kill only
the worker PID; terminate its process group (or stop the dedicated container)
on external cancellation. On native POSIX systems, substitute the maintained
custom-node checkout path, runtime `env.sh`, and writable output directory.

Also verify `SkinTokensRigGLB` in ComfyUI `/object_info` and run this example
through the node with texture transfer enabled to qualify the ComfyUI path.
The direct worker smoke does not prove node registration or artifact delivery.
Record the worker revision, platform stack and logs alongside the result;
a provisioning-only test is not an inference smoke.

Upstream documents an NVIDIA GPU with at least 14 GB VRAM. A nonempty GLB is only
a first smoke; inspect bones, skin weights, mesh, texture and a deformation pose
before qualifying the backend. **Never publish port 59876** or run the service
on an untrusted shared network. No CPU or concurrent-inference
support is claimed here.

## Provisioning regression tests

```sh
uv run --with pytest --with pyyaml python -m pytest tests -q
```

Tests exercise real local Git checkout/idempotency/dirty-source refusal, cache
layout, isolation failures, pinned download arguments, platform constraints,
environment quoting and the opt-in Compose contract. Model download calls are
stubbed in unit tests; these tests are not GPU inference evidence.
