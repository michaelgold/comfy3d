#!/bin/bash
set -e

# Check if first argument is "init-workspace"
if [ "$1" = "init-workspace" ]; then
    echo "Initializing workspace volume setup..."
    
    # 1) Prepare persistent layout + symlinks
    WORK="/workspace"; [ -d /runpod-volume ] && WORK="/runpod-volume"
    migrate_link() {
      src="$1"; dst="$2"
      mkdir -p "$dst"
      if [ -d "$src" ] && [ ! -L "$src" ]; then
        shopt -s dotglob; mv "$src"/* "$dst"/ 2>/dev/null || true; shopt -u dotglob
        rm -rf "$src"
      fi
      ln -sfnT "$dst" "$src"
    }
    mkdir -p "$WORK"/{models,custom_nodes,manager,u2net,output,workflows,input} /app/comfy/user/default /root
    migrate_link /app/comfy/models "$WORK/models"
    migrate_link /app/comfy/custom_nodes "$WORK/custom_nodes"
    migrate_link /app/comfy/output "$WORK/output"
    migrate_link /app/comfy/input "$WORK/input"
    migrate_link /app/comfy/user/default/ComfyUI-Manager "$WORK/manager"
    rm -rf /root/.u2net || true; ln -sfnT "$WORK/u2net" /root/.u2net

    echo "Workspace initialization complete."
    # Shift arguments to remove "init-workspace" and continue with normal startup
    shift
fi

#activate venv
source /app/.venv/bin/activate

# echo "Downloading models if needed and starting ComfyUI" 
# python /app/utils/model_downloader.py /app/utils/model_config.json & \
# If no arguments provided, start the ComfyUI server (service mode)
if [ $# -eq 0 ]; then
    echo "Starting ComfyUI server..."
    exec comfy launch -- --listen 0.0.0.0 --port 8188 
else
    # Otherwise, run comfy with the provided arguments (CLI mode)
    echo "Running comfy command: $@"
    exec comfy "$@"
fi