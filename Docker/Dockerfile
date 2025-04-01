FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04 AS builder

ARG VERSION=v0.3.27
ARG TORCH_CUDA=cu126
ENV VERSION=${VERSION}
ENV TORCH_CUDA=${TORCH_CUDA}
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
SHELL ["/bin/bash", "-c"]

# Install deps + Python + uv
RUN apt-get update && apt-get install -y \
    build-essential curl ffmpeg git software-properties-common \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    ninja-build wget && \
    add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
    wget https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C /usr/local/bin --strip-components=1 && \
    chmod +x /usr/local/bin/uv && \
    python3 -m venv $VIRTUAL_ENV && \
    rm -rf /var/lib/apt/lists/* get-pip.py uv-x86_64-unknown-linux-gnu.tar.gz

# Clone ComfyUI and setup
RUN git clone --depth=1 --branch $VERSION https://github.com/comfyanonymous/ComfyUI /tmp/ComfyUI && \
    cp -a /tmp/ComfyUI/. /app && rm -rf /tmp/ComfyUI

# Install everything in one step
RUN source $VIRTUAL_ENV/bin/activate && \
    uv pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/${TORCH_CUDA} && \
    uv pip install --no-cache-dir -U xformers --index-url https://download.pytorch.org/whl/${TORCH_CUDA} && \
    uv pip install --no-cache-dir wheel setuptools ninja pybind11 pytest packaging plotly && \
    uv pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /app/custom_nodes && cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager && \
    git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    git clone --depth=1 https://github.com/MrForExample/ComfyUI-3D-Pack && \
    git clone --depth=1 https://github.com/michaelgold/ComfyUI-Hal.fun-Model-Downloader && \
    for d in ComfyUI-Manager ComfyUI_essentials ComfyUI-Hunyuan3DWrapper ComfyUI-3D-Pack ComfyUI-Hal.fun-Model-Downloader; do \
      uv pip install --no-cache-dir -r $d/requirements.txt || true; \
    done && \
    uv pip install --no-cache-dir ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer --no-build-isolation && \
    uv pip install --no-cache-dir ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer --no-build-isolation && \
    mkdir -p deps_build && cd deps_build && \
    git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \
    for d in *; do cd $d && python setup.py bdist_wheel && pip install dist/*.whl && cd ..; done && \
    cd /app && rm -rf deps_build && \
    find $VIRTUAL_ENV -name '__pycache__' -type d -exec rm -rf {} + && \
    find $VIRTUAL_ENV -name '*.dist-info' -type d -exec rm -rf {} + && \
    find $VIRTUAL_ENV -name '*.egg-info' -type d -exec rm -rf {} +

# ===== Runtime =====
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

ARG VERSION=v0.3.27
ENV VERSION=${VERSION}
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/custom_nodes /app/custom_nodes
COPY --from=builder /app/utils /app/utils
COPY --from=builder /app/ComfyUI.py /app/ComfyUI.py
COPY --from=builder /app/web /app/web
COPY --from=builder /app/workflows /app/user/default/workflows

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
ENV PYOPENGL_PLATFORM=egl
ENV FORCE_CUDA="1"
ENV CUDA_HOME="/usr/local/cuda"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:/usr/lib64:${LD_LIBRARY_PATH}"
ENV PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.6,max_split_size_mb:128"
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"

RUN chmod a+x /app/utils/init.sh
EXPOSE 8188
ENTRYPOINT ["/app/utils/init.sh"]
