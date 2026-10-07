#!/bin/sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cache_dir=${MIUBOMZ_CACHE_DIR:-$source_dir/../../../../.cache/miubian}/calamares
version=3.4.2-1.1+miubomz1
package=$cache_dir/calamares_${version}_amd64.deb
recipe=$(cat "$source_dir/sources.sha256" "$source_dir/gpt-root-boot-flag.patch" "$0" | sha256sum | cut -d ' ' -f 1)
mkdir -p "$cache_dir/sources" "$1"
if [ -f "$package" ] && [ -f "$cache_dir/recipe.sha256" ] && [ "$(cat "$cache_dir/recipe.sha256")" = "$recipe" ]; then
    (cd "$cache_dir" && sha256sum --check package.sha256)
    cp "$package" "$1/"
    exit 0
fi

cd "$cache_dir/sources"
while read -r hash filename; do
    if [ ! -f "$filename" ]; then
        curl --fail --location --silent --show-error \
            "https://deb.debian.org/debian/pool/main/c/calamares/$filename" --output "$filename"
    fi
done < "$source_dir/sources.sha256"
sha256sum --check "$source_dir/sources.sha256"

build_dir=$(mktemp -d "$cache_dir/build.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
cp calamares_3.4.2.orig.tar.xz "$build_dir/"
dpkg-source --no-check -x calamares_3.4.2-1.1.dsc "$build_dir/calamares"
cd "$build_dir/calamares"
mkdir -p debian/patches
cp "$source_dir/gpt-root-boot-flag.patch" debian/patches/
printf '%s\n' gpt-root-boot-flag.patch >> debian/patches/series
cat > "$build_dir/changelog" <<'CHANGELOG'
calamares (3.4.2-1.1+miubomz1) forky; urgency=medium

  * Preserve Linux GPT partition types when installing from BIOS firmware.

 -- Miubomz <noreply@miubomz.invalid>  Mon, 05 Oct 2026 02:00:00 +0800

CHANGELOG
cat debian/changelog >> "$build_dir/changelog"
mv "$build_dir/changelog" debian/changelog
export DEBIAN_FRONTEND=noninteractive
export DEB_BUILD_OPTIONS="parallel=${MIUBOMZ_BUILD_JOBS:-4} nocheck noautodbgsym"
export DEB_BUILD_PROFILES=nocheck
apt-get update
apt-get build-dep --no-install-recommends -y .
dpkg-buildpackage -us -uc
cp "$build_dir/calamares_${version}_amd64.deb" "$package"
mkdir -p "$cache_dir/patched-source"
cp "$build_dir"/calamares_${version}.* "$cache_dir/patched-source/"
cp "$build_dir"/calamares_${version}_amd64.buildinfo \
    "$build_dir"/calamares_${version}_amd64.changes "$cache_dir/patched-source/"
cp "$cache_dir/sources/calamares_3.4.2.orig.tar.xz" "$cache_dir/patched-source/"
printf '%s\n' "$recipe" > "$cache_dir/recipe.sha256"
(cd "$cache_dir" && sha256sum "calamares_${version}_amd64.deb" > package.sha256)
cp "$package" "$1/"
