# ===== Builder Stage =====
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04 AS builder

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    software-properties-common \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    ninja-build wget && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    wget https://bootstrap.pypa.io/get-pip.py && python3 get-pip.py && \
    rm get-pip.py && rm -rf /var/lib/apt/lists/*

# Install uv
RUN wget https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    mkdir -p uv-extract && \
    tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C uv-extract && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && \
    rm -rf uv-extract uv-x86_64-unknown-linux-gnu.tar.gz

# Create and activate virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv $VIRTUAL_ENV

SHELL ["/bin/bash", "-c"]

# Clone ComfyUI and check out pinned version
RUN git clone https://github.com/comfyanonymous/ComfyUI . && \
    git checkout v0.3.27

# Install core dependencies
RUN source $VIRTUAL_ENV/bin/activate && \
    uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126 && \
    uv pip install wheel setuptools ninja pybind11 pytest packaging && \
    uv pip install plotly && \
    uv pip install -U xformers --index-url https://download.pytorch.org/whl/cu126 && \
    uv pip install -r requirements.txt

# Install custom nodes and extensions
RUN mkdir -p /app/custom_nodes && cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager && \
    git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    git clone --depth=1 https://github.com/MrForExample/ComfyUI-3D-Pack && \
    git clone --depth=1 https://github.com/michaelgold/ComfyUI-Hal.fun-Model-Downloader

RUN source $VIRTUAL_ENV/bin/activate && \
    uv pip install -r custom_nodes/ComfyUI-Manager/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI_essentials/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-Hunyuan3DWrapper/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-3D-Pack/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-Hal.fun-Model-Downloader/requirements.txt && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer --no-build-isolation && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer --no-build-isolation

# Build and install native dependencies
RUN mkdir -p deps_build && cd deps_build && \
    git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \
    for d in diff-gaussian-rasterization nvdiffrast kiuikit pytorch3d pytorch_scatter; do \
        cd $d && python setup.py bdist_wheel && pip install dist/*.whl && cd ..; \
    done && cd /app && rm -rf deps_build

# ===== Runtime Stage =====
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

WORKDIR /app

# Copy runtime app and venv from builder
COPY --from=builder /app /app

# Runtime ENV variables
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"
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
ENV VERSION=v0.3.27

COPY ./utils /app/utils
RUN chmod a+x /app/utils/init.sh
COPY ./workflows /app/user/default/workflows

EXPOSE 8188

ENTRYPOINT ["/app/utils/init.sh"]
