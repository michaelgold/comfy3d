# Add build arguments with specific versions
ARG BASE_IMAGE=nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04
# Use the ARG in the FROM statement
FROM ${BASE_IMAGE} 
ARG TORCH_CUDA=cu126
ENV TORCH_CUDA=${TORCH_CUDA}
ARG PYTHON_VER=3.11.10

# Set TORCH_CUDA based on BASE_IMAGE

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /app

# Arguments for versioning
ARG VERSION=v0.3.43
ENV VERSION=${VERSION}



# Cuda environment
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

# Install system dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    software-properties-common \
    libegl1-mesa-dev libgl1-mesa-dev libglvnd-dev libsm6 libxext6 libxrender1 \
    ninja-build wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

#install python
WORKDIR /home/tmp/python
ADD https://www.python.org/ftp/python/$PYTHON_VER/Python-$PYTHON_VER.tgz Python.tgz
RUN tar xzf Python.tgz
WORKDIR /home/tmp/python/Python-$PYTHON_VER
RUN ./configure --enable-shared --enable-optimizations
RUN make install
RUN rm -rf "/home/tmp/python"
RUN ln -s /usr/local/bin/python3 /usr/local/bin/python
# RUN ln -s /usr/bin/python3 /usr/bin/python
RUN ldconfig


# Install uv
RUN wget https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    mkdir -p uv-extract && \
    tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C uv-extract && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && \
    rm -rf uv-extract uv-x86_64-unknown-linux-gnu.tar.gz

# Set up virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv $VIRTUAL_ENV

SHELL ["/bin/bash", "-c"]


# Install core Python dependencies
RUN source $VIRTUAL_ENV/bin/activate && \
    echo "TORCH_CUDA: $TORCH_CUDA" && \
    if [ "$TORCH_CUDA" = "cu126" ]; then \
        uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/${TORCH_CUDA}; \
    else \
        uv pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121; \
    fi && \
    uv pip install wheel setuptools ninja pybind11 pytest packaging && \
    uv pip install plotly && \
    uv pip install -U xformers --index-url https://download.pytorch.org/whl/${TORCH_CUDA} && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

# Install custom nodes
RUN mkdir -p /app/custom_nodes && cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager && \
    git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git && \
    git clone --depth=1 https://github.com/MrForExample/ComfyUI-3D-Pack 

RUN source $VIRTUAL_ENV/bin/activate && \
    uv pip install -r custom_nodes/ComfyUI-Manager/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI_essentials/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-Hunyuan3DWrapper/requirements.txt && \
    uv pip install -r custom_nodes/ComfyUI-3D-Pack/requirements.txt && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer --no-build-isolation && \
    ls -lah ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer && \
    du -sh ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer && \
    rm -rf ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer/build && \
    rm -rf ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer/custom_rasterizer.egg-info && \
    uv pip install ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer --no-build-isolation && \
    ls -lah ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer && \
    du -sh ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer && \
    rm -rf ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer/build && \
    rm -rf ./custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer/custom_rasterizer.egg-info &&\
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

# Native build dependencies
RUN mkdir -p deps_build && cd deps_build && \
    git clone --recursive https://github.com/traveller59/spconv.git && \
    git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \
    for d in spconv diff-gaussian-rasterization nvdiffrast kiuikit pytorch3d pytorch_scatter; do \
        cd $d && python setup.py bdist_wheel && pip install dist/*.whl && cd ..; \
    done && cd /app && rm -rf deps_build && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

COPY ./utils /app/utils
RUN chmod a+x /app/utils/init.sh
# fix for EGL
ENV EGL_PLATFORM=surfaceless

# fix for missing comfy3d deps
RUN uv pip install pyhocon==0.3.61

# Clone, check out, and install ComfyUI at specified version
RUN source $VIRTUAL_ENV/bin/activate && \
    git clone --depth=1 --branch $VERSION https://github.com/comfyanonymous/ComfyUI /tmp/ComfyUI && \
    cp -a /tmp/ComfyUI/. /app && rm -rf /tmp/ComfyUI && \
    uv pip install -r requirements.txt && \
    find /app -type d -name '__pycache__' -exec rm -r {} + || true

RUN source $VIRTUAL_ENV/bin/activate && \
    cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-KJNodes && \
    git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-DepthAnythingV2 && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-WanVideoWrapper && \
    cd /app/custom_nodes/ComfyUI-KJNodes && \
    uv pip install -r requirements.txt && \
    cd /app/custom_nodes/ComfyUI-VideoHelperSuite && \
    uv pip install -r requirements.txt && \
    cd /app/custom_nodes/ComfyUI-DepthAnythingV2 && \
    uv pip install -r requirements.txt && \
    cd /app/custom_nodes/ComfyUI-WanVideoWrapper && \
    uv pip install -r requirements.txt



# Update some of our custom nodes
RUN source $VIRTUAL_ENV/bin/activate && \
    rm -rf /app/custom_nodes/ComfyUI-HF-Model-Downloader && \
    cd /app/custom_nodes && \
    git clone --depth=1 https://github.com/michaelgold/ComfyUI-HF-Model-Downloader && \
    cd /app/custom_nodes/ComfyUI-HF-Model-Downloader && \
    uv pip install -r requirements.txt && \
    cd /app/custom_nodes/ComfyUI-Manager && \
    git pull && \
    uv pip install -r requirements.txt 
    

COPY ./workflows /app/user/default/workflows
COPY ./input /app/input
EXPOSE 8188

ENTRYPOINT ["/app/utils/init.sh"]
