#!/bin/bash
IMAGE_NAME="comfy3d-comfy3d"

echo "=== Image Overview ==="
docker images $IMAGE_NAME

echo -e "\n=== Layer Sizes ==="
docker history $IMAGE_NAME --human --format "table {{.Size}}\t{{.CreatedSince}}\t{{.CreatedBy}}" | head -200

echo -e "\n=== Total Layers ==="
docker history $IMAGE_NAME --quiet | wc -l

echo -e "\n=== Largest Layers ==="
docker history $IMAGE_NAME --human --format "{{.Size}}\t{{.CreatedBy}}" | sort -hr | head -100

echo -e "\n=== Top 10 Largest Layers (Detailed) ==="
docker history $IMAGE_NAME --human --no-trunc --format "{{.Size}}\t{{.CreatedBy}}" | sort -hr | head -11