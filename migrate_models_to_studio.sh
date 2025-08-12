#!/bin/bash

# Enhanced script to copy models from production Docker volume to studio setup
# This script manages container startup and ensures clean shutdown
# Usage: ./migrate_models_to_studio.sh [--interactive]

set -e  # Exit on any error

# Check for interactive flag
INTERACTIVE_MODE=false
if [ "$1" = "--interactive" ]; then
    INTERACTIVE_MODE=true
fi

PROD_VOLUME_NAME="comfy3d_comfyui-models"
TARGET_DIR="./models"
TEMP_CONTAINER="temp-models-extractor"
PROD_COMPOSE_FILE="docker-compose.yml"
STUDIO_COMPOSE_FILE="docker-compose.studio.yml"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    
    # Stop production containers if we started them
    if [ "$STARTED_PROD" = "true" ]; then
        print_status "Stopping production containers..."
        docker compose -f "$PROD_COMPOSE_FILE" down > /dev/null 2>&1 || true
    fi
    
    # Remove temp container if it exists
    docker rm -f "$TEMP_CONTAINER" > /dev/null 2>&1 || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Variables to track what we've started
STARTED_PROD=false

print_status "Starting model migration from production to studio setup..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running or not accessible"
    exit 1
fi

# Check if production volume exists, if not try to create it by starting prod containers
if ! docker volume inspect "$PROD_VOLUME_NAME" >/dev/null 2>&1; then
    print_warning "Production volume '$PROD_VOLUME_NAME' not found"
    print_status "Starting production containers to initialize volume..."
    
    docker compose -f "$PROD_COMPOSE_FILE" up -d
    STARTED_PROD=true
    
    print_status "Waiting for production containers to initialize (60 seconds)..."
    sleep 60
    
    # Check again if volume was created
    if ! docker volume inspect "$PROD_VOLUME_NAME" >/dev/null 2>&1; then
        print_error "Production volume '$PROD_VOLUME_NAME' still not found after starting containers"
        exit 1
    fi
fi

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"
TARGET_ABS_PATH=$(realpath "$TARGET_DIR")

print_status "Target directory: $TARGET_ABS_PATH"

# Check current size of target directory
if [ -d "$TARGET_DIR" ] && [ "$(ls -A "$TARGET_DIR")" ]; then
    print_warning "Target directory already contains files:"
    ls -la "$TARGET_DIR" | head -10
    echo ""
    
    if [ "$INTERACTIVE_MODE" = "true" ]; then
        read -p "Do you want to continue and potentially overwrite files? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Operation cancelled by user"
            exit 0
        fi
    else
        print_status "Auto-accepting overwrite (non-interactive mode)"
        print_status "Use --interactive flag if you want to be prompted"
    fi
fi

# Create temporary container to access the production volume
print_status "Creating temporary container to access production volume..."

# First, check what's in the volume
print_status "Checking contents of production volume..."
VOLUME_CONTENTS=$(docker run --rm \
    -v "$PROD_VOLUME_NAME":/volume_data \
    alpine:latest \
    sh -c "cd /volume_data && ls -la . 2>/dev/null || echo 'EMPTY_OR_ERROR'")

if [ "$VOLUME_CONTENTS" = "EMPTY_OR_ERROR" ]; then
    print_warning "Production volume appears to be empty or inaccessible"
    print_status "This could mean:"
    print_status "  1. Production containers have never downloaded models"
    print_status "  2. Models are stored elsewhere"
    print_status "  3. Volume permissions issue"
    exit 1
fi

print_success "Found content in production volume:"
echo "$VOLUME_CONTENTS"
echo ""

# Perform the actual copy
print_status "Copying models from production volume to studio directory..."
docker run --name "$TEMP_CONTAINER" \
    -v "$PROD_VOLUME_NAME":/volume_data \
    -v "$TARGET_ABS_PATH":/target \
    --rm \
    alpine:latest \
    sh -c "
        set -e
        cd /volume_data
        echo 'Source directory contents:'
        ls -la .
        echo ''
        echo 'Starting copy operation...'
        
        # Copy with detailed output
        if [ \"\$(ls -A .)\" ]; then
            cp -rv * /target/
            echo ''
            echo 'Copy completed. Target directory now contains:'
            ls -la /target/
            
            # Calculate sizes
            SOURCE_SIZE=\$(du -sh . | cut -f1)
            TARGET_SIZE=\$(du -sh /target | cut -f1)
            echo ''
            echo \"Source size: \$SOURCE_SIZE\"
            echo \"Target size: \$TARGET_SIZE\"
        else
            echo 'No files to copy'
            exit 1
        fi
    "

print_success "Model migration completed successfully!"
print_status "Models copied from production volume '$PROD_VOLUME_NAME' to '$TARGET_DIR'"

# Show final status
if [ -d "$TARGET_DIR" ]; then
    FINAL_SIZE=$(du -sh "$TARGET_DIR" | cut -f1)
    FILE_COUNT=$(find "$TARGET_DIR" -type f | wc -l)
    print_success "Final status:"
    print_success "  - Directory: $TARGET_DIR"
    print_success "  - Total size: $FINAL_SIZE"
    print_success "  - File count: $FILE_COUNT"
fi

echo ""
print_status "Next steps:"
print_status "1. Start studio environment: docker compose -f $STUDIO_COMPOSE_FILE up"
print_status "2. The studio setup will use local ./models directory"
print_status "3. Verify models loaded correctly in the ComfyUI interface"

echo ""
print_warning "Note: This script COPIES models. Original files remain in production volume."
