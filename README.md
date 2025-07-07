# Comfy3D

**Comfy3D** is a GPU-accelerated containerized environment for advanced 3D workflows using [ComfyUI](https://github.com/comfyanonymous/ComfyUI), enhanced with real-time diffusion models like Hunyuan3D, FLUX, and various 3D/ControlNet extensions. 

This setup provides out-of-the-box workflows for generating character sheets, textured meshes, and multi-view renders, all within a reproducible and customizable Docker environment. 

Docker containers are deployed to [https://hub.docker.com/r/michaelgold/comfy3d](https://hub.docker.com/r/michaelgold/comfy3d)

<a target="_blank" href="https://lightning.ai/gold/studios/comfy3d">
  <img src="https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/studio-badge.svg" alt="Open In Studio"/>
</a>

---

## ✨ Features

- 📦 **Prebuilt Docker Environment** with CUDA 12.1 and 12.6 support
- 🧱 **Custom Nodes**:
  - [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)
  - [Hunyuan3D Wrapper](https://github.com/kijai/ComfyUI-Hunyuan3DWrapper)
  - [ComfyUI-3D-Pack](https://github.com/MrForExample/ComfyUI-3D-Pack)
  - [ControlNet Extensions](https://github.com/cubiq/ComfyUI_essentials)
- 🧠 **Included Models**:
  - Tencent's `Hunyuan3D-2` (`hy3dgen`)
  - FLUX for stylized 3D character generation
- 🧪 Ready-to-use **workflows** for:
  - Character generation (`characeter_flux.json`)
  - 3D mesh reconstruction (`hy3d.json`)
  - Multi-view + texture baking (`hy3d_multiview.json`)

---

## 🐳 Getting Started

### Prerequisites

- Docker with NVIDIA GPU support
- NVIDIA GPU with CUDA >= 12.1
- (Optional) VS Code with Dev Containers support

---

### 🏗️ Build & Run Locally

#### Development (hot-reload, volumes mapped):

```bash
docker compose -f docker-compose.dev.yml up --build
```

#### Production:

```bash
docker compose up -d
```
The app runs at http://localhost:8188

#### 🧬 Structure

├── Docker/                # Dockerfile and build logic
├── .devcontainer/         # VS Code container dev config
├── workflows/             # JSON workflows for ComfyUI
├── input/                 # Sample input images
├── output/                # Output directory (mounted)
├── utils/
│   ├── init.sh            # Container entrypoint
│   ├── model_downloader.py
│   └── model_config.json  # Model download config
├── docker-compose.yml     # Production stack
├── docker-compose.dev.yml # Development stack

#### 🧠 Models
The following models can be downloaded at runtime with the included [ComfyUI-HF-Model-Downloader](https://github.com/michaelgold/ComfyUI-HF-Model-Downloader) addon:

- Hunyuan3D-2 Turbo: tencent/Hunyuan3D-2
- ControlNet/FLUX Models (via mounted models/ folder)

####  🧪 Sample Workflows
1. Character Sheet (Flux)
workflows/characeter_flux.json

Generates a 1980s video game-style wrestler character from a single image and prompt using FLUX guidance.

2. Single-view Mesh (hy3d.json)
From 1 image (e.g., wrestler-front.png), generates a textured GLB mesh and multiview renders.

3. Multi-view Mesh (hy3d_multiview.json)
From 4 directional views, generates consistent textured 3D mesh with advanced postprocessing and export.

#### 🛠️ VS Code Dev Container
If using VS Code:

Open in container (Dev Containers extension)

Auto-runs utils/init.sh

Installs ComfyUI, custom nodes, and all Python deps in a virtualenv

#### 📤 Output
All images and GLB files are saved to the output/ directory, which is volume-mounted and shared across builds.

#### 📜 License
MIT License. Third-party model licenses may apply.

####  📬 Contact
Maintained by [@michaelgold](https://x.com/michaelgold)
For issues or ideas, please [open an Issue](https://github.com/michaelgold/comfy3d/issues/new).
