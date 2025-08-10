#!/bin/bash
set -e

#activate venv
source /app/.venv/bin/activate


# echo "Downloading models if needed and starting ComfyUI" 
# python /app/utils/model_downloader.py /app/utils/model_config.json & \
# If no arguments provided, start the ComfyUI server (service mode)
if [ $# -eq 0 ]; then
    echo "Starting ComfyUI server..."
    exec comfy launch -- --listen 0.0.0.0 --port 8188 --front-end-version Comfy-Org/ComfyUI_frontend@latest
else
    # Otherwise, run comfy with the provided arguments (CLI mode)
    echo "Running comfy command: $@"
    exec comfy "$@"
fi