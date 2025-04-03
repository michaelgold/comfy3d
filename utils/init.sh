#!/bin/bash
set -e

# echo "Bootstrapping missing custom nodes from template if not present..."

# for dir in /app/_custom_nodes_template/*; do
#   name=$(basename "$dir")
#   if [ ! -d "/app/custom_nodes/$name" ]; then
#     echo "Copying $name..."
#     cp -r "$dir" "/app/custom_nodes/$name"
#   fi
# done

#activate venv
source /app/.venv/bin/activate


# echo "Downloading models if needed and starting ComfyUI" 
# python /app/utils/model_downloader.py /app/utils/model_config.json & \

python /app/main.py --listen 0.0.0.0 --port 8188