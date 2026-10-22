#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

profile_dir=${MIUBOMZ_PROFILE:-/src/variants/miubian}
export MIUBOMZ_PROFILE=$profile_dir
if [[ $(dpkg-parsechangelog -l "$profile_dir/integration/debian/changelog" -S Version) != $(jq -r .version "$profile_dir/release.json") ]]; then
    printf 'Release and native integration package versions must agree.\n' >&2
    exit 1
fi
cd /work
if [[ -e chroot || -e binary || -e .build ]]; then
    lb clean
fi
rm -rf config auto
cp -a "$profile_dir/live-build/auto" /work/auto
cp -a "$profile_dir/live-build/config" /work/config
chmod +x auto/* config/hooks/live/*.hook.chroot

python3 "$profile_dir/build/prepare-inputs.py" /work/config
mkdir -p /work/config/packages.chroot
rm -rf /work/local-packages
mkdir -p /work/local-packages

rm -rf /work/integration
rm -f /work/miubomz-*.deb /work/miubomz-settings_*
cp -a "$profile_dir/integration" /work/integration
(
    cd /work/integration
    dpkg-buildpackage -us -uc
)
cp /work/miubomz-*.deb /work/local-packages/
"$profile_dir/packages/calamares/build.sh" /work/local-packages
python3 "$profile_dir/build/prepare-inputs.py" /work/config --local-packages /work/local-packages

lb config "$@"
lb build
bash "$profile_dir/build/export-artifacts.sh"
