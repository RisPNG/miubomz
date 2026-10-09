#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
profile_dir=$project_dir/variants/miubian
cd "$project_dir"

builder_image=${MIUBOMZ_BUILDER_IMAGE:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["builder_image"])' "$profile_dir/release.json")}
container_name=${MIUBOMZ_BUILD_CONTAINER:-miubomz-build-$$}
mkdir -p .build/miubian/logs .cache/miubian artifacts/miubian

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_command=(sudo -n docker)
fi

if [[ -z ${MIUBOMZ_BUILDER_IMAGE:-} ]]; then
    "${docker_command[@]}" build --tag "$builder_image" "$profile_dir/build"
fi

run_options=(
    --rm --privileged --name "$container_name"
    --memory "${MIUBOMZ_BUILD_MEMORY:-4g}"
    --cpus "${MIUBOMZ_BUILD_JOBS:-4}"
    --mount "type=bind,src=$project_dir,dst=/src,readonly"
    --mount "type=bind,src=$project_dir/.build/miubian,dst=/work"
    --mount "type=bind,src=$project_dir/.cache/miubian,dst=/cache"
    --mount "type=bind,src=$project_dir/artifacts/miubian,dst=/artifacts"
    --env "MIUBOMZ_BUILD_JOBS=${MIUBOMZ_BUILD_JOBS:-4}"
    --env "MIUBOMZ_SQUASHFS_MEMORY=${MIUBOMZ_SQUASHFS_MEMORY:-1G}"
    --env MIUBOMZ_DEBIAN_MIRROR
    --env MIUBOMZ_ARCHIVE_AREAS
    --env MIUBOMZ_CACHE_DIR=/cache
    --env MIUBOMZ_PROFILE=/src/variants/miubian
    --env "MIUBOMZ_RESOLVE_INPUTS=${MIUBOMZ_RESOLVE_INPUTS:-0}"
    --env "MIUBOMZ_LOCAL_UID=$(id -u)"
    --env "MIUBOMZ_LOCAL_GID=$(id -g)"
)

if [[ -n ${MIUBOMZ_INPUT_BUNDLE:-} ]]; then
    input_bundle=$(realpath -- "$MIUBOMZ_INPUT_BUNDLE")
    run_options+=(--mount "type=bind,src=$input_bundle,dst=/input-bundle,readonly" --env MIUBOMZ_INPUT_BUNDLE=/input-bundle)
fi

trap '"${docker_command[@]}" container rm --force "$container_name" >/dev/null 2>&1 || true' EXIT
trap 'exit 1' HUP INT TERM
"${docker_command[@]}" run "${run_options[@]}" "$builder_image" \
    bash /src/variants/miubian/build/container-build.sh "$@" 2>&1 | tee .build/miubian/logs/build.log
