# ---------- Stage 0: base build tools ----------
ARG CUDA_TAG=12.6.3-cudnn-devel-ubuntu24.04
FROM nvidia/cuda:${CUDA_TAG} AS build-base

ENV DEBIAN_FRONTEND=noninteractive PIP_PREFER_BINARY=1 CMAKE_BUILD_PARALLEL_LEVEL=8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget git ninja-build \
    zlib1g-dev libssl-dev libbz2-dev libreadline-dev \
    sqlite3 libsqlite3-0 libsqlite3-dev libffi-dev liblzma-dev uuid-dev \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    ffmpeg ca-certificates 


# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# ---------- Stage 1: build Python ----------
ARG PYTHON_VER=3.11.10
FROM build-base AS python-builder
WORKDIR /tmp/python
ADD https://www.python.org/ftp/python/${PYTHON_VER}/Python-${PYTHON_VER}.tgz .
RUN tar xzf Python-${PYTHON_VER}.tgz && cd Python-${PYTHON_VER} && \
    ./configure --enable-shared --enable-optimizations --enable-loadable-sqlite-extensions && \
    make -j$(nproc) && make install && ldconfig 

RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python && \
    ln -sf /usr/local/bin/pip3 /usr/local/bin/pip
# Keep only what we need noted; we'll copy from this later

# ---------- Stage 2: venv + core deps (torch, xformers, etc.) ----------
FROM python-builder AS venv-builder
# Copy Python runtime from python-builder
ENV PATH=/usr/local/bin:$PATH
ENV VIRTUAL_ENV=/app/.venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ARG VERSION=v0.3.49

# Install uv
RUN wget -q https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    mkdir -p uv-extract && tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C uv-extract && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && rm -rf uv-extract *.tar.gz

ARG TORCH_CUDA=cu126
# Optional: copy constraints
COPY ./constraints.txt /tmp/constraints.txt
ENV PIP_CONSTRAINT=/tmp/constraints.txt
ENV UV_NO_CACHE=1
ENV PIP_NO_CACHE_DIR=1

RUN uv pip install comfy-cli && \
    comfy --skip-prompt --workspace=/app/comfy install --nvidia --version $VERSION

# use version of torch compatible with xformers
RUN uv pip install xformers torchvision torchaudio --index-url https://download.pytorch.org/whl/$TORCH_CUDA

RUN echo "Using ${TORCH_CUDA}" && \
    uv pip install --upgrade pip wheel setuptools && \
    # uv pip install torch torchvision torchaudio  && \
    # uv pip install -U xformers --force-reinstall --no-cache-dir && \
    uv pip install torchsde pyhocon==0.3.61 pccm==0.4.16 plotly && \
    uv pip install spconv-cu120==2.3.6 && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

# ---------- Stage 3: build CUDA-native wheels ----------
FROM venv-builder AS native-builder
ENV VIRTUAL_ENV="/app/.venv"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
ENV PYOPENGL_PLATFORM=egl
ENV FORCE_CUDA="1"
ENV CUDA_HOME="/usr/local/cuda"
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
ENV PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.6,max_split_size_mb:128"
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"

# Prebuild CUDA deps and prime nvdiffrast's torch extension cache
WORKDIR /app/deps_build

COPY ./utils /tmp/utils

ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 

# Make sure the dir exists
RUN mkdir -p ${TORCH_EXTENSIONS_DIR}

# 1) Clone
RUN git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \

# 2) Build wheels for the libs that ship proper extension wheels
    for d in diff-gaussian-rasterization kiuikit pytorch3d pytorch_scatter; do \
      cd $d && python setup.py bdist_wheel && pip install --no-cache-dir dist/*.whl && cd ..; \
    done && \

# 3) Build/install nvdiffrast IN-TREE (it uses torch.cpp_extension under the hood)
    cd nvdiffrast && pip install --no-build-isolation . && cd .. && \


# 5) Clean
    cd /app && rm -rf /app/deps_build && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

# Prime the torch extension cache (compiles into $TORCH_EXTENSIONS_DIR)
# PRIME the torch extension cache now (this triggers the cpp_extension build)

    # ---------- Stage 4: ComfyUI + nodes ----------
FROM native-builder AS comfy-builder

ARG CUDA_VERSION_FOR_COMFY=12.6
ENV CUDA_VERSION_FOR_COMFY=${CUDA_VERSION_FOR_COMFY}
ENV VERSION=${VERSION}
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app


# # Force reinstall of torch
# RUN echo "Using ${TORCH_CUDA}" && \
#     uv pip install --upgrade pip wheel setuptools && \
#     uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/${TORCH_CUDA} && \
#     uv pip uninstall nvidia-cufile-cu12 nvidia-cufft-cu12 nvidia-cusparse-cu12 nvidia-cusolver-cu12 nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12 nvidia-cuda-cupti-cu12 nvidia-nvjitlink-cu12 nvidia-curand-cu12 nvidia-nvtx-cu12 nvidia-cuda-runtime-cu12 || true && \
#     uv pip install -U xformers --index-url https://download.pytorch.org/whl/${TORCH_CUDA} --force-reinstall --no-cache-dir && \
#     uv pip install torchsde pyhocon==0.3.61 pccm==0.4.16 plotly && \
#     uv pip install spconv-cu120==2.3.6 && \
#     find /app -type d -name '__pycache__' -exec rm -r {} + || true


# # Add custom nodes (git clones)


RUN mkdir -p /app/custom_nodes && cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    git clone --depth=1 https://github.com/MrForExample/ComfyUI-3D-Pack

# Install node requirements and local packages
RUN uv pip install -r custom_nodes/ComfyUI-Hunyuan3DWrapper/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-3D-Pack/requirements.txt --no-build-isolation && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer --no-build-isolation && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer --no-build-isolation && \
    cp -r /app/custom_nodes/* /app/comfy/custom_nodes && rm -rf /app/custom_nodes

# Copy workflows/inputs, scripts
COPY ./workflows /app/comfy/user/default/workflows
COPY ./input /app/comfy/input
COPY ./utils /app/utils
RUN chmod a+x /app/utils/init.sh

WORKDIR /app/comfy
RUN comfy --skip-prompt --workspace=/app/comfy node install https://github.com/cubiq/ComfyUI_essentials && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/kijai/ComfyUI-KJNodes && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/kijai/ComfyUI-DepthAnythingV2 && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/kijai/ComfyUI-WanVideoWrapper && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/rgthree/rgthree-comfy && \
    comfy --skip-prompt --workspace=/app/comfy node install https://github.com/michaelgold/ComfyUI-HF-Model-Downloader

# force reinstall of numpy and fix pytorch compatibility issues
RUN uv pip install diso "numpy<2" --force-reinstall --no-build-isolation 





# ---------- Stage 5: final runtime ----------
# FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS final
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04 AS final

ENV DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    PYOPENGL_PLATFORM=egl \
    EGL_PLATFORM=surfaceless \
    PYTHONUNBUFFERED=1 

ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 

# COPY --from=comfy-builder /opt/torch_extensions /opt/torch_extensions

# Minimal runtime libs you actually need
RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    git ca-certificates && rm -rf /var/lib/apt/lists/*

RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Bring in Python runtime and venv
COPY --from=python-builder /usr/local/ /usr/local/

ENV PATH=/usr/local/bin:$PATH
# Update library cache and add library path for shared Python libraries
RUN ldconfig
COPY --from=comfy-builder /app/.venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
ENV PYOPENGL_PLATFORM=egl
ENV FORCE_CUDA="1"
ENV CUDA_HOME="/usr/local/cuda"
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
ENV PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.6,max_split_size_mb:128"
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"
ARG TORCH_CUDA=cu126
ENV TORCH_CUDA=${TORCH_CUDA}


# Bring in ComfyUI workspace (and, if desired, models)
COPY --from=comfy-builder /app/comfy /app/comfy
COPY --from=comfy-builder /app/utils /app/utils
# Or: COPY --from=downloader /app/comfy/models /app/comfy/# after you copy the venv and workspace
# COPY --from=comfy-builder /root/.cache/torch_extensions /root/.cache/torch_extensions



# Set workspace and install nodes with non-interactive flags
WORKDIR /app/comfyanonymous
RUN comfy --skip-prompt --workspace=/app/comfy tracking disable

EXPOSE 8188
ENTRYPOINT ["/app/utils/init.sh"]
