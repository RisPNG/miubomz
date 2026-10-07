#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

cd /work
profile_dir=${MIUBOMZ_PROFILE:-/src/variants/miubian}
iso_files=(/work/live-image-*.hybrid.iso)
if [[ ${#iso_files[@]} != 1 ]]; then
    printf 'Expected one native live-build ISO; found %s.\n' "${#iso_files[@]}" >&2
    exit 1
fi

artifact_name=$(jq -r .artifact "$profile_dir/release.json")
release_dir=$(mktemp -d /artifacts/.miubomz-release.XXXXXX)
trap 'rm -rf "$release_dir"' EXIT
trap 'exit 1' HUP INT TERM

if [[ ${MIUBOMZ_RESOLVE_INPUTS:-0} == 1 ]]; then
    python3 "$profile_dir/build/freeze-inputs.py" /work /cache \
        "$release_dir/$artifact_name.inputs.candidate.json" "$release_dir/$artifact_name.apt-lock.candidate.json"
    chown "${MIUBOMZ_LOCAL_UID:-0}:${MIUBOMZ_LOCAL_GID:-0}" "$release_dir/$artifact_name".*
    mv "$release_dir/$artifact_name".* /artifacts/
    printf 'Exported candidate APT lock for review; install the reviewed lock and export its input bundle before building the release.\n'
    exit 0
fi

python3 "$profile_dir/build/freeze-inputs.py" /work /cache "$release_dir/$artifact_name.inputs.json"
cp --reflink=auto "${iso_files[0]}" "$release_dir/$artifact_name.iso"
cp /work/binary/live/filesystem.packages "$release_dir/$artifact_name.packages"
python3 "$profile_dir/tests/image/validate-image.py" "$release_dir/$artifact_name.iso" /work/chroot \
    > "$release_dir/$artifact_name.build.json"
(
    cd "$release_dir"
    sha256sum "$artifact_name.iso" > "$artifact_name.iso.sha256"
)
mkdir "$release_dir/sources" "$release_dir/packages"
cp --reflink=auto /work/miubomz-settings_* /cache/calamares/patched-source/* "$release_dir/sources/"
cp --reflink=auto /work/local-packages/*.deb "$release_dir/packages/"
perl "$profile_dir/build/verify-source-packages.pl" "$release_dir/packages" "$release_dir/sources"
(
    cd "$release_dir/sources"
    sha256sum * > SHA256SUMS
)
(
    cd "$release_dir/packages"
    sha256sum *.deb > SHA256SUMS
)
chown -R "${MIUBOMZ_LOCAL_UID:-0}:${MIUBOMZ_LOCAL_GID:-0}" "$release_dir"
mkdir -p "/artifacts/sources/$artifact_name" "/artifacts/packages/$artifact_name"
mv "$release_dir/sources/"* "/artifacts/sources/$artifact_name/"
mv "$release_dir/packages/"* "/artifacts/packages/$artifact_name/"
mv "$release_dir/$artifact_name".* /artifacts/
printf 'Built /artifacts/%s.iso\n' "$artifact_name"
