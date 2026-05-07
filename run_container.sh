#!/bin/bash
# Run the WhoDis container with build and restart logic

set -e

# Configuration variables
CONTAINER_NAME="${CONTAINER_NAME:-whodis}"
HOST_PORT="${HOST_PORT:-8000}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
IMAGE_TAG="${IMAGE_TAG:-whodis:latest}"
UPLOADS_DIR="${UPLOADS_DIR:-$(pwd)/uploads}"
DB_DIR="${DB_DIR:-$(pwd)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== WhoDis Container Runner ===${NC}"
echo "Container name: $CONTAINER_NAME"
echo "Host port: $HOST_PORT"
echo "Container port: $CONTAINER_PORT"
echo "Image: $IMAGE_TAG"
echo ""

# Stop and remove existing container if running
echo -e "${YELLOW}Checking for existing container...${NC}"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Stopping existing container: $CONTAINER_NAME${NC}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${YELLOW}Removing existing container: $CONTAINER_NAME${NC}"
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo -e "${GREEN}Existing container removed${NC}"
else
    echo -e "${GREEN}No existing container found${NC}"
fi

echo ""

# Build the image
echo -e "${YELLOW}Building Docker image: $IMAGE_TAG${NC}"
docker build -t "$IMAGE_TAG" .
echo -e "${GREEN}Build complete${NC}"

echo ""

# Create uploads directory if it doesn't exist
if [ ! -d "$UPLOADS_DIR" ]; then
    echo -e "${YELLOW}Creating uploads directory: $UPLOADS_DIR${NC}"
    mkdir -p "$UPLOADS_DIR"
fi

# Run the container
echo -e "${YELLOW}Starting container: $CONTAINER_NAME${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    -v "${UPLOADS_DIR}:/app/uploads" \
    -v "${DB_DIR}/whodis.db:/app/whodis.db" \
    --restart unless-stopped \
    "$IMAGE_TAG"

echo ""
echo -e "${GREEN}Container started successfully!${NC}"
echo "API available at: http://localhost:${HOST_PORT}"
echo ""
echo "View logs: docker logs -f $CONTAINER_NAME"
echo "Stop: docker stop $CONTAINER_NAME"
echo "Remove: docker rm $CONTAINER_NAME"
