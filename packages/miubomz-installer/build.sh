#!/bin/sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output_dir=$1
mkdir -p "$output_dir"
output_dir=$(CDPATH= cd -- "$output_dir" && pwd)
stage=$(mktemp -d "$output_dir/.miubomz-installer.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM

for component in installer recovery; do
    rsync -a --exclude=__pycache__/ --exclude='*.pyc' \
        "$source_dir/$component/root/" "$stage/$component/"
    find "$stage/$component" -type d -exec chmod 755 {} +
    find "$stage/$component" -type f -exec chmod 644 {} +
    (cd "$stage/$component" && find etc -type f -printf '/%p\n' | sort > DEBIAN/conffiles)
    chmod 755 "$stage/$component/DEBIAN/postinst"
    if [ "$component" = installer ]; then
        chmod 755 "$stage/$component/usr/bin/calamares-install-miubomz"
    else
        chmod 755 "$stage/$component/usr/bin/grub-btrfsd" \
            "$stage/$component/etc/grub.d/41_snapshots-btrfs" \
            "$stage/$component/usr/lib/miubomz/apt-pre-snapshot" \
            "$stage/$component/usr/lib/miubomz/recovery-start"
        chmod 440 "$stage/$component/etc/sudoers.d/99-miubomz-admin"
    fi
    dpkg-deb --build --root-owner-group "$stage/$component" "$output_dir"
done
