FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu24.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    git \
    software-properties-common \
    # TODO not sure all of this is required, remove unnnecessary
    libegl1 \
    libegl1-mesa-dev \
    libgl1 \
    libglib2.0-0 \
    libgl1-mesa-dev \
    libgl1 \
    libglx0 \
    libegl1 \
    libgles2 \
    libgles2-mesa-dev \
    libglib2.0-0 \
    libglvnd-dev \
    libglvnd0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ninja-build \
    wget && rm -rf /var/lib/apt/lists/*

# Install Python 3.11
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --set python3 /usr/bin/python3.11 && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py && \
    rm -rf /var/lib/apt/lists/*

# Install uv directly to /usr/local/bin
RUN wget https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz && \
    mkdir -p uv-extract && \
    tar -xzf uv-x86_64-unknown-linux-gnu.tar.gz -C uv-extract && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    cp uv-extract/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx && \
    rm -rf uv-extract uv-x86_64-unknown-linux-gnu.tar.gz


# Set CUDA environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility,graphics

# Default pyopengl to EGL for good headless rendering support
ENV PYOPENGL_PLATFORM egl
ENV FORCE_CUDA="1"
ENV CUDA_HOME="/usr/local/cuda"


ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:/usr/lib64:${LD_LIBRARY_PATH}"
ENV PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,garbage_collection_threshold:0.6,max_split_size_mb:128"
ENV TORCH_CUDA_ARCH_LIST="6.1;7.0;7.5;8.0;8.6;8.9;9.0"

RUN git clone https://github.com/comfyanonymous/ComfyUI .

# Make a virtual environment
RUN python3.11 -m venv /app/.venv

# Activate virtual environment for all subsequent RUN commands
SHELL ["/bin/bash", "-c"]
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN source /app/.venv/bin/activate
ENV PIP_NO_CACHE_DIR=1

# Install PyTorch with uv
RUN uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# Verify CUDA setup
RUN python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda); print('CUDA devices:', torch.cuda.device_count())" || echo "CUDA setup incomplete - will be verified at runtime with proper GPU access"

# Install comfyui dependencies
RUN uv pip install wheel setuptools ninja pybind11 pytest pytest-runner packaging


# Install comfyui manager
WORKDIR /app/custom_nodes/
RUN git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager
WORKDIR /app/custom_nodes/ComfyUI-Manager
RUN uv pip install -r requirements.txt

# Install comfyui essentials
WORKDIR /app/custom_nodes/
RUN git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials
WORKDIR /app/custom_nodes/ComfyUI_essentials
RUN uv pip install -r requirements.txt

# Install comfyui hunyuan3d wrapper
WORKDIR /app/custom_nodes/
RUN git clone --depth=1 https://github.com/kijai/ComfyUI-Hunyuan3DWrapper.git
WORKDIR /app/custom_nodes/ComfyUI-Hunyuan3DWrapper
RUN uv pip install -r requirements.txt
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV CUDACXX="/usr/local/cuda/bin/nvcc"
ENV CUDA_PATH="/usr/local/cuda"
ENV CUDA_TOOLKIT_ROOT_DIR="/usr/local/cuda"
WORKDIR /app/custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer
RUN uv pip install . --no-build-isolation
WORKDIR /app/custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/differentiable_renderer
RUN uv pip install . --no-build-isolation

# Install comfy3d
WORKDIR /app/custom_nodes/
RUN git clone --depth=1 https://github.com/MrForExample/ComfyUI-3D-Pack
WORKDIR /app/custom_nodes/ComfyUI-3D-Pack
RUN uv pip install -r requirements.txt

# Create build directory and clone/build dependencies
RUN mkdir -p deps_build && \
    cd deps_build && \
    # Clone all repositories
    git clone --recursive https://github.com/ashawkey/diff-gaussian-rasterization.git && \
    git clone --recursive https://github.com/NVlabs/nvdiffrast.git && \
    git clone --recursive https://github.com/ashawkey/kiuikit.git && \
    git clone --recursive https://github.com/facebookresearch/pytorch3d.git && \
    git clone --recursive https://github.com/rusty1s/pytorch_scatter.git && \
    # Build and install each one
    cd diff-gaussian-rasterization && python setup.py bdist_wheel && pip install dist/*.whl && cd .. && \
    cd nvdiffrast && python setup.py bdist_wheel && pip install dist/*.whl && cd ..  && \
    cd kiuikit && python setup.py bdist_wheel && pip install dist/*.whl && cd .. && \
    cd pytorch3d && python setup.py bdist_wheel && pip install dist/*.whl && cd .. && \
    cd pytorch_scatter && python setup.py bdist_wheel && pip install dist/*.whl && cd .. && cd .. && \
    rm -rf deps_build

# Install plotly
RUN uv pip install plotly

# Install xformers for cuda 12.6
RUN uv pip install -U xformers --index-url https://download.pytorch.org/whl/cu126


ENV BUILD_DATE = 2025-03-31-02-50

WORKDIR /app/custom_nodes/
RUN git clone --depth=1 https://github.com/michaelgold/ComfyUI-Hal.fun-Model-Downloader
WORKDIR /app/custom_nodes/ComfyUI-Hal.fun-Model-Downloader
RUN uv pip install -r requirements.txt

# Save a copy of the fully set-up custom nodes (before volume mounts mask them)
# RUN mkdir -p /app/_custom_nodes_template && \
#     cp -r /app/custom_nodes/* /app/_custom_nodes_template/

WORKDIR /app

RUN git pull 
ENV VERSION=v0.3.27

RUN git checkout $VERSION -b $VERSION

RUN uv pip install -r ./requirements.txt


COPY ./utils /app/utils
RUN chmod a+x /app/utils/init.sh

COPY ./workflows /app/user/default/workflows

EXPOSE 8188

ENTRYPOINT ["/app/utils/init.sh"]