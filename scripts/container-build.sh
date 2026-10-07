#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

cd /work
if [[ -e chroot || -e binary || -e .build ]]; then
    lb clean
fi
rm -rf config auto
cp -a /src/auto /work/auto
cp -a /src/image/config /work/config
chmod +x auto/* config/hooks/live/*.hook.chroot

python3 /src/scripts/prepare-assets.py /work/config
mkdir -p /work/config/packages.chroot
rm -rf /work/local-packages
mkdir -p /work/local-packages

for package_dir in /src/packages/*; do
    if [[ -x $package_dir/build.sh ]]; then
        "$package_dir/build.sh" /work/local-packages
    elif [[ -f $package_dir/root/DEBIAN/control ]]; then
        dpkg-deb --build --root-owner-group "$package_dir/root" \
            /work/local-packages
    fi
done
cp /work/local-packages/*.deb /work/config/packages.chroot/
python3 - <<'CONFIGURE'
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("prepare_assets", "/src/scripts/prepare-assets.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.configure_packages(Path("/work/config"), Path("/work/local-packages"))
CONFIGURE

lb config "$@"
lb build
bash /src/scripts/export-artifacts.sh
