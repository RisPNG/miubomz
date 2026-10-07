#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
builder_image=${MIUBOMZ_BUILDER_IMAGE:-miubomz-builder:0.1.0}
docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_command=(sudo -n docker)
fi
"${docker_command[@]}" run --rm --privileged \
    --mount "type=bind,src=$project_dir/.build,dst=/work" \
    "$builder_image" bash -eu -c '
        lb clean --purge
        rm -rf /work/config /work/auto /work/local-packages
    '
