# ---------- Stage 0: base build tools ----------
ARG CUDA_TAG=12.8.1-cudnn-devel-ubuntu24.04
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
ARG VERSION=v0.3.62

# Install uv
RUN wget -q https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    mkdir -p uv-extract && tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C uv-extract && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && rm -rf uv-extract *.tar.gz

ARG TORCH_CUDA=cu128
# Optional: copy constraints
COPY ./constraints.txt /tmp/constraints.txt
ENV UV_CONSTRAINT=/tmp/constraints.txt
ENV PIP_CONSTRAINT=/tmp/constraints.txt
ENV UV_NO_CACHE=1
ENV PIP_NO_CACHE_DIR=1

RUN uv pip install comfy-cli && \
    comfy --skip-prompt --workspace=/app/comfy install --nvidia --version $VERSION --fast-deps && \
    uv pip uninstall torch torchvision torchaudio xformers && \
    uv pip install torch torchvision torchaudio --force-reinstall --index-url https://download.pytorch.org/whl/${TORCH_CUDA}

RUN echo "Using ${TORCH_CUDA}" && \
    uv pip install --upgrade pip wheel setuptools && \
    # uv pip install xformers==0.0.32.post2 pyhocon==0.3.61 pccm==0.4.16 plotly==6.3.0 && \
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
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0;10.0;12.0"

WORKDIR /wheels

# Build each package in separate RUN commands for better caching
RUN git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    cd diff-gaussian-rasterization && \
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

RUN git clone -b v0.2.20  --recursive https://github.com/ashawkey/kiuikit.git && \
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

# RUN printf "scipy==1.16.1\nnumpy<2\n" > /req-constraints.txt

RUN git clone --recursive https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    uv pip install pybind11==2.13.6 && \ 
    pip wheel -r ComfyUI-Hunyuan3DWrapper/requirements.txt -w /wheels --no-build-isolation && \
    pip wheel ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer -w /wheels --no-build-isolation && \
    pip wheel ./ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer -w /wheels --no-build-isolation


ENV MAX_JOBS=4
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0;12.0"

# build flash-attn
RUN pip wheel flash-attn==2.8.2 -w /wheels --no-build-isolation --no-deps


ENV SPCONV_DISABLE_JIT="1"
ENV CUMM_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0;12.0"

ENV CUMM_CUDA_VERSION="12.8"
# ENV CUMM_DISABLE_JIT="1"

# Build CUMM as a wheel (a dep for spconv)
COPY ./cumm_cuda_arch.patch /tmp/cumm_cuda_arch.patch
RUN git clone -b v0.7.13 https://github.com/FindDefinition/cumm.git && \
    cd cumm && \
    # Apply the CUDA architecture patch
    patch -p1 < /tmp/cumm_cuda_arch.patch && \
    echo "Applied CUDA architecture patch successfully" && \
    uv pip install -e . &&\
    python setup.py bdist_wheel && \
    cp dist/*.whl /wheels/

 
RUN git clone https://github.com/traveller59/spconv && \
    cd spconv && \
    sed -i 's/cumm-cu{}>=0.7.11, <0.8.0/cumm-cu{}>=0.7.11, <0.9.0/g' setup.py && \
    sed -i 's/cumm>=0.7.11, <0.8.0/cumm>=0.7.11, <0.9.0/g' setup.py && \
    cd .. && \
    uv pip install --no-index --find-links=/wheels --only-binary=:all: --no-deps \
     cumm_cu128 && \
    # uv pip show cumm_cu128 && \
    uv pip install pccm==0.4.16 && \
    pip wheel ./spconv -w /wheels --no-build-isolation 

# build xformers without flash attention
ENV XFORMERS_DISABLE_FLASH_ATTN=1
RUN pip wheel git+https://github.com/facebookresearch/xformers.git@v0.0.32.post2 \
      -w /wheels \
      --no-build-isolation


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
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0;12.0"


ENV TORCH_EXTENSIONS_DIR=/app/.venv/torch_extensions 
RUN mkdir -p ${TORCH_EXTENSIONS_DIR}

# build xformers without flash attention




# Copy and install pre-built wheels
# RUN --mount=from=wheel-builder,source=/wheels,target=/mnt/wheels,ro \
#     --mount=type=cache,target=/root/.cache/pip \
#     uv pip install --no-index --find-links=/mnt/wheels --only-binary=:all: --no-deps \
#       diff_gaussian_rasterization  pytorch3d torch_scatter nvdiffrast mesh_processor custom_rasterizer nvdiffrast spconv_cu128 flash-attn 



# ---------- Stage 4: ComfyUI + nodes ----------
FROM native-builder AS comfy-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libcairo2-dev && \ 
    apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# ARG CUDA_VERSION_FOR_COMFY=12.6
# ENV CUDA_VERSION_FOR_COMFY=${CUDA_VERSION_FOR_COMFY}
# ENV VERSION=${VERSION}
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# use the constraints in /app/constraints
COPY ./constraints.txt /app/constraints.txt
ENV UV_CONSTRAINT=/app/constraints.txt
ENV PIP_CONSTRAINT=/app/constraints.txt

COPY ./requirements.txt /app/requirements.txt
RUN uv pip install -r /app/requirements.txt
# install diso dependency for comfy3dpack
RUN uv pip install diso==0.1.4 --no-build-isolation 

# install onnx gpu runtime
RUN uv pip install onnxruntime-gpu==1.22.0 --no-build-isolation

# Install version-locked comfy nodes
COPY ./utils /app/utils 
WORKDIR /app/comfy

RUN python /app/utils/node_install.py  https://github.com/rgthree/rgthree-comfy --version 0fb1e239a903e93ef626a8c20589b38f46e39dff 

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-KJNodes --version 9d7af919b91838fb22e31ad0107a6ddcf8bd7f3f

RUN python /app/utils/node_install.py https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite --version 8e4d79471bf1952154768e8435a9300077b534fa

RUN python /app/utils/node_install.py https://github.com/Fannovel16/comfyui_controlnet_aux --version cc6b232f4a47f0cdf70f4e1bfa24b74bd0d75bf1

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-segment-anything-2  --version ebdb9869596b14babdaa83505e6863aad4618501

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-DepthAnythingV2 --version 047a4ecfd09a951944154c7f3e823566e586c2d5

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-WanVideoWrapper --version 2c854c53ee8c078069d9b95bf493bb44b25039ee

RUN python /app/utils/node_install.py https://github.com/Acly/comfyui-inpaint-nodes --version b9039c22de926919f26b7242cfa4da00d8b6fbec

RUN python /app/utils/node_install.py https://github.com/michaelgold/ComfyUI-HF-Model-Downloader --version a6bc77da07b99b8791a52d9a2f1a28d1eea1f00d

RUN python /app/utils/node_install.py https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch --version b432b2411cbb7d3192d35953bd3aafea05a0e245

RUN python /app/utils/node_install.py https://github.com/MrForExample/ComfyUI-3D-Pack --version 9ab02eb440b98cf7dea0c2de9379f45d99d160d5 --no-build-isolation && \
uv pip uninstall cumm-cu126 spconv_cu126 utils3d && \
uv pip install git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8


RUN python /app/utils/node_install.py https://github.com/cubiq/ComfyUI_essentials --version cb5c69c5715230ff6cc1402ddbb5a59473e23202 

RUN python /app/utils/node_install.py https://github.com/kijai/ComfyUI-Hunyuan3DWrapper --version 4a87c71089c5d5175035bc6f0de2a586d1fd2a08 

RUN uv pip uninstall xformers

RUN --mount=from=wheel-builder,source=/wheels,target=/mnt/wheels,ro \
    --mount=type=cache,target=/root/.cache/pip \
    uv pip install --no-index --find-links=/mnt/wheels --only-binary=:all: --no-deps \
      diff_gaussian_rasterization  pytorch3d torch_scatter nvdiffrast mesh_processor custom_rasterizer nvdiffrast cumm_cu128 spconv_cu128 flash_attn xformers

# fix for older nodes     
RUN uv pip install diffusers==0.34.0 transformers==4.56.0


# ---------- Stage 5: final runtime ----------
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 AS final

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libegl1 libopengl0 libglu1-mesa cuda-minimal-build-12-8 libcusparse-dev-12-8 libcublas-dev-12-8 libcusolver-dev-12-8 wget curl git \
    libglib2.0-0 libglib2.0-dev libgthread-2.0-0 \
    libtbbmalloc2 \
   libvorbis-dev libtheora-dev   libjpeg-dev libpng-dev libtiff-dev \
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
# Prevent spconv from switching algorithms at runtime

ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0;12.0"
ARG TORCH_CUDA=cu128
ENV TORCH_CUDA=${TORCH_CUDA}

# Version arguments for ComfyUI
ARG VERSION=v0.3.62
ARG UPDATE_VERSION=v0.3.62
ENV VERSION=${VERSION}
ENV UPDATE_VERSION=${UPDATE_VERSION}



# Set workspace and install nodes with non-interactive flags
WORKDIR /app/comfy
RUN comfy --skip-prompt --workspace=/app/comfy tracking disable

# Copy workflows/inputs, scripts
COPY ./workflows /app/comfy/user/default/workflows
COPY ./input /app/comfy/input

# Update ComfyUI to latest version if different from base
RUN if [ "$VERSION" != "$UPDATE_VERSION" ] && [ -n "$UPDATE_VERSION" ]; then \
        echo "Updating ComfyUI from $VERSION to $UPDATE_VERSION"; \
        cd /app/comfy && \
        git fetch origin && \
        git checkout -b "${UPDATE_VERSION}" $UPDATE_VERSION && \
        uv pip install -r requirements.txt; \
    else \
        echo "No update needed, VERSION=$VERSION UPDATE_VERSION=$UPDATE_VERSION"; \
    fi


RUN chmod a+x /app/utils/init.sh

# ENV CUDA_LAUNCH_BLOCKING=1
# ENV TORCH_SHOW_CPP_STACKTRACES=1

EXPOSE 8188
ENTRYPOINT ["/app/utils/init.sh"]
