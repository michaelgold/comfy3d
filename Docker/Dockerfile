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


RUN echo "Using ${TORCH_CUDA}" && \
    uv pip install --upgrade pip wheel setuptools && \
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


ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 
RUN mkdir -p ${TORCH_EXTENSIONS_DIR}


# Copy and install pre-built wheels
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

# use the constraints in /app/constraints
COPY ./constraints.txt /app/constraints.txt
ENV UV_CONSTRAINT=/app/constraints.txt
ENV PIP_CONSTRAINT=/app/constraints.txt

# install diso dependency for comfy3dpack
RUN uv pip install diso --no-build-isolation 


# ---------- Stage 5: final runtime ----------
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS final

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


COPY ./constraints.txt /app/constraints.txt
ENV UV_CONSTRAINT=/app/constraints.txt
ENV PIP_CONSTRAINT=/app/constraints.txt



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

ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"
ARG TORCH_CUDA=cu126
ENV TORCH_CUDA=${TORCH_CUDA}


COPY ./utils /app/utils 

# Install version-locked comfy nodes
WORKDIR /app/comfy

RUN python /app/utils/node_install.py  https://github.com/rgthree/rgthree-comfy --version c5ffa43de4ddb17244626a65a30700a05dd6b67d 

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-KJNodes --version 9ea455afd61cc3814bbf8deb5e7e387336872466

RUN python /app/utils/node_install.py https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite --version 8e4d79471bf1952154768e8435a9300077b534fa

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-DepthAnythingV2 --version 047a4ecfd09a951944154c7f3e823566e586c2d5

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-WanVideoWrapper --version 2c854c53ee8c078069d9b95bf493bb44b25039ee

RUN python /app/utils/node_install.py https://github.com/Acly/comfyui-inpaint-nodes --version b9039c22de926919f26b7242cfa4da00d8b6fbec

RUN python /app/utils/node_install.py https://github.com/michaelgold/ComfyUI-HF-Model-Downloader --version e53962b646b7c05931d57873771611e52b8b1428

RUN python /app/utils/node_install.py https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch --version b432b2411cbb7d3192d35953bd3aafea05a0e245

RUN python /app/utils/node_install.py https://github.com/MrForExample/ComfyUI-3D-Pack --version 9ab02eb440b98cf7dea0c2de9379f45d99d160d5 --no-build-isolation

RUN python /app/utils/node_install.py https://github.com/cubiq/ComfyUI_essentials --version cb5c69c5715230ff6cc1402ddbb5a59473e23202 

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-Hunyuan3DWrapper --version 4a87c71089c5d5175035bc6f0de2a586d1fd2a08 

# Set workspace and install nodes with non-interactive flags
WORKDIR /app/comfy
RUN comfy --skip-prompt --workspace=/app/comfy tracking disable

# Copy workflows/inputs, scripts
COPY ./workflows /app/comfy/user/default/workflows
COPY ./input /app/comfy/input

RUN chmod a+x /app/utils/init.sh

EXPOSE 8188
ENTRYPOINT ["/app/utils/init.sh"]