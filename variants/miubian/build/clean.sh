#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)
builder_image=${MIUBOMZ_BUILDER_IMAGE:-$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["builder_image"])' "$project_dir/variants/miubian/release.json")}
docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    docker_command=(sudo -n docker)
fi
"${docker_command[@]}" run --rm --privileged \
    --mount "type=bind,src=$project_dir/.build/miubian,dst=/work" \
    "$builder_image" bash -eu -c '
        lb clean --purge
        rm -rf /work/config /work/auto /work/local-packages /work/integration
        rm -f /work/live-image-*.hybrid.iso /work/miubomz-*.deb /work/miubomz-settings_*
    '
