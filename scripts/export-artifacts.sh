#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

cd /work
iso_files=(/work/live-image-*.hybrid.iso)
if [[ ${#iso_files[@]} != 1 ]]; then
    printf 'Expected one native live-build ISO; found %s.\n' "${#iso_files[@]}" >&2
    exit 1
fi

artifact_name=miubomz-0.1.0-amd64
release_dir=$(mktemp -d /artifacts/.miubomz-release.XXXXXX)
trap 'rm -rf "$release_dir"' EXIT
trap 'exit 1' HUP INT TERM

python3 /src/scripts/freeze-inputs.py /work /cache "$release_dir/$artifact_name.inputs.json"
cp --reflink=auto "${iso_files[0]}" "$release_dir/$artifact_name.iso"
cp /work/binary/live/filesystem.packages "$release_dir/$artifact_name.packages"
python3 /src/scripts/validate-image.py "$release_dir/$artifact_name.iso" /work/chroot \
    > "$release_dir/$artifact_name.build.json"
(
    cd "$release_dir"
    sha256sum "$artifact_name.iso" > "$artifact_name.iso.sha256"
)
chown "${MIUBOMZ_LOCAL_UID:-0}:${MIUBOMZ_LOCAL_GID:-0}" "$release_dir/$artifact_name".*
mv "$release_dir/$artifact_name".* /artifacts/
printf 'Built /artifacts/%s.iso\n' "$artifact_name"
