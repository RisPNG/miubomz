#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"

builder_image=${MIUBOMZ_BUILDER_IMAGE:-miubomz-builder:0.1.0}
mkdir -p .build/logs .cache/miubomz artifacts

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_command=(sudo -n docker)
fi

"${docker_command[@]}" build --tag "$builder_image" builder

run_options=(
    --rm --privileged
    --memory "${MIUBOMZ_BUILD_MEMORY:-4g}"
    --cpus "${MIUBOMZ_BUILD_JOBS:-4}"
    --mount "type=bind,src=$project_dir,dst=/src,readonly"
    --mount "type=bind,src=$project_dir/.build,dst=/work"
    --mount "type=bind,src=$project_dir/.cache/miubomz,dst=/cache"
    --mount "type=bind,src=$project_dir/artifacts,dst=/artifacts"
    --env "MIUBOMZ_BUILD_JOBS=${MIUBOMZ_BUILD_JOBS:-4}"
    --env "MIUBOMZ_SQUASHFS_MEMORY=${MIUBOMZ_SQUASHFS_MEMORY:-1G}"
    --env "MIUBOMZ_DEBIAN_MIRROR=${MIUBOMZ_DEBIAN_MIRROR:-http://deb.debian.org/debian}"
    --env "MIUBOMZ_ARCHIVE_AREAS=${MIUBOMZ_ARCHIVE_AREAS:-main non-free-firmware}"
    --env MIUBOMZ_CACHE_DIR=/cache
    --env "MIUBOMZ_LOCAL_UID=$(id -u)"
    --env "MIUBOMZ_LOCAL_GID=$(id -g)"
)

if [[ -n ${MIUBOMZ_REFERENCE_ROOT:-} ]]; then
    run_options+=(
        --mount "type=bind,src=$MIUBOMZ_REFERENCE_ROOT,dst=/reference,readonly"
        --env MIUBOMZ_REFERENCE_ROOT=/reference
    )
fi

"${docker_command[@]}" run "${run_options[@]}" "$builder_image" \
    bash /src/scripts/container-build.sh "$@" 2>&1 | tee .build/logs/build.log
