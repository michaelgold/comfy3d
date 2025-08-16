# ---------- Stage 0: base build tools ----------
ARG CUDA_TAG=12.6.3-cudnn-devel-ubuntu24.04
FROM nvidia/cuda:${CUDA_TAG} AS build-base

ENV DEBIAN_FRONTEND=noninteractive PIP_PREFER_BINARY=1 CMAKE_BUILD_PARALLEL_LEVEL=8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget git ninja-build \
    zlib1g-dev libssl-dev libbz2-dev libreadline-dev \
    sqlite3 libsqlite3-0 libsqlite3-dev libffi-dev liblzma-dev uuid-dev \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    ffmpeg ca-certificates && \ 
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

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
FROM nvidia/cuda:${CUDA_TAG} AS venv-builder
# Copy Python runtime from python-builder

RUN apt-get update && apt-get install -y --no-install-recommends curl wget git ca-certificates && \ 
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /usr/local/bin/python* /usr/local/bin/
COPY --from=python-builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=python-builder /usr/local/lib/libpython3.11.so* /usr/local/lib/
COPY --from=python-builder /usr/local/include/python3.11 /usr/local/include/python3.11

ENV PATH=/usr/local/bin:$PATH
# Update library cache and add library path for shared Python libraries
RUN ldconfig


ENV VIRTUAL_ENV=/app/.venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ARG VERSION=v0.3.50

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
    comfy --skip-prompt --workspace=/app/comfy install --nvidia --version $VERSION --fast-deps

# use version of torch compatible with xformers
# RUN uv pip install xformers torchvision torchaudio --index-url https://download.pytorch.org/whl/$TORCH_CUDA

RUN echo "Using ${TORCH_CUDA}" && \
    uv pip install --upgrade pip wheel setuptools && \
    # uv pip install torch torchvision torchaudio  && \
    # uv pip install -U xformers --force-reinstall --no-cache-dir && \
    uv pip install xformers pyhocon==0.3.61 pccm==0.4.16 plotly spconv-cu120==2.3.6 && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

# ---------- Stage 3a: build individual wheels ----------
FROM venv-builder AS wheel-builder
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

WORKDIR /wheels

# Build each package in separate RUN commands for better caching
RUN git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    cd diff-gaussian-rasterization && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    cd kiuikit && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    cd pytorch3d && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \
    cd pytorch_scatter && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    cd nvdiffrast && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN printf "scipy==1.16.1\nnumpy<2\n" > /req-constraints.txt

RUN git clone --recursive https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    pip wheel -r ComfyUI-Hunyuan3DWrapper/requirements.txt -c /req-constraints.txt -w /wheels && \
    pip wheel ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer -c /req-constraints.txt -w /wheels --no-build-isolation && \
    pip wheel ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer -c /req-constraints.txt -w /wheels --no-build-isolation


# Keep the original req files for the final stage (no editing/merging)


# Install node requirements and local packages
# RUN uv pip install -r custom_nodes/ComfyUI-Hunyuan3DWrapper/requirements.txt && \
#     uv pip install -r custom_nodes/ComfyUI-3D-Pack/requirements.txt --no-build-isolation && \
#     uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer --no-build-isolation && \
#     uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer --no-build-isolation && \
#     cp -r /app/custom_nodes/* /app/comfy/custom_nodes && rm -rf /app/custom_nodes

# ---------- Stage 3b: install wheels  ----------
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

COPY ./utils /tmp/utils

ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 
RUN mkdir -p ${TORCH_EXTENSIONS_DIR}


# Copy and install pre-built wheels
# COPY --from=wheel-builder /wheels/*.whl /tmp/wheels/
# RUN uv pip install --no-cache-dir /tmp/wheels/*.whl

# # Clean up
# RUN rm -rf /tmp/wheels && \
#     find /app -type d -name '__pycache__' -exec rm -r {} + || true

# RUN --mount=from=wheel-builder,source=/wheels,target=/mnt/wheels,ro \
#     --mount=type=cache,target=/root/.cache/pip \
#     uv pip install --no-cache-dir /mnt/wheels/*.whl
RUN --mount=from=wheel-builder,source=/wheels,target=/mnt/wheels,ro \
    --mount=type=cache,target=/root/.cache/pip \
    uv pip install --no-index --find-links=/mnt/wheels --only-binary=:all: --no-deps \
      diff_gaussian_rasterization  pytorch3d torch_scatter nvdiffrast mesh_processor custom_rasterizer nvdiffrast 


    # ---------- Stage 4: ComfyUI + nodes ----------
FROM native-builder AS comfy-builder

ARG CUDA_VERSION_FOR_COMFY=12.6
ENV CUDA_VERSION_FOR_COMFY=${CUDA_VERSION_FOR_COMFY}
ENV VERSION=${VERSION}
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"






RUN uv pip install diso "numpy<2" --no-build-isolation 

WORKDIR /app/custom_nodes
RUN git clone --depth 1 --branch v0.1.6 --recursive https://github.com/MrForExample/ComfyUI-3D-Pack && \
    cd ComfyUI-3D-Pack && \
    git checkout -b local && \
    cd .. && \
    uv pip install -r ComfyUI-3D-Pack/requirements.txt --no-build-isolation 

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






# force reinstall of numpy and fix pytorch compatibility issues







# ---------- Stage 5: final runtime ----------
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS final
# FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04 AS final

# ENV DEBIAN_FRONTEND=noninteractive \
#     NVIDIA_VISIBLE_DEVICES=all \
#     NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
#     PYOPENGL_PLATFORM=egl \
#     EGL_PLATFORM=surfaceless \
#     PYTHONUNBUFFERED=1 

# ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 

# # COPY --from=comfy-builder /opt/torch_extensions /opt/torch_extensions

# # Minimal runtime libs you actually need
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 wget curl \
#     git ca-certificates && rm -rf /var/lib/apt/lists/* && \
#     apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libegl1 cuda-minimal-build-12-6 libcusparse-dev-12-6 libcublas-dev-12-6 libcusolver-dev-12-6 wget curl git \
    && apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*


# # Bring in Python runtime and venv
COPY --from=python-builder /usr/local/bin/python* /usr/local/bin/
COPY --from=python-builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=python-builder /usr/local/lib/libpython3.11.so* /usr/local/lib/
COPY --from=python-builder /usr/local/include/python3.11 /usr/local/include/python3.11

# copy app directory from comfy-builder
COPY --from=comfy-builder /app /app

ENV PATH=/usr/local/bin:$PATH
# Update library cache and add library path for shared Python libraries
RUN ldconfig
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
# ENV PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.6,max_split_size_mb:128"
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"
ARG TORCH_CUDA=cu126
ENV TORCH_CUDA=${TORCH_CUDA}


# # Bring in ComfyUI workspace (and, if desired, models)
# COPY --from=comfy-builder /app/comfy /app/comfy
# COPY --from=comfy-builder /app/utils /app/utils
# Or: COPY --from=downloader /app/comfy/models /app/comfy/# after you copy the venv and workspace
# COPY --from=comfy-builder /root/.cache/torch_extensions /root/.cache/torch_extensions




WORKDIR /app/comfy
RUN comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-kjnodes  --version 1.1.3 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-videohelpersuite --version 1.7.4 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-depthanythingv2 --version 1.0.1 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install ComfyUI-WanVideoWrapper --version 1.2.8 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install rgthree-comfy --version 1.0.2508012353 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install hf-model-downloader --version 0.2.5 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-inpaint-nodes --version 1.0.4  && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-inpaint-cropandstitch --version 2.1.7 && \
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-hunyuan3dwrapper --version 1.0.6 && \ 
    comfy --skip-prompt --workspace=/app/comfy node registry-install comfyui-manager --version 3.36 

# Set workspace and install nodes with non-interactive flags
WORKDIR /app/comfy
RUN comfy --skip-prompt --workspace=/app/comfy tracking disable

# Copy workflows/inputs, scripts
COPY ./workflows /app/comfy/user/default/workflows
COPY ./input /app/comfy/input
COPY ./utils /app/utils
RUN chmod a+x /app/utils/init.sh

EXPOSE 8188
ENTRYPOINT ["/app/utils/init.sh"]
