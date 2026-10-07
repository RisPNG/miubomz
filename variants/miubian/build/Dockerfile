FROM debian:forky

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        apt-utils build-essential bzip2 ca-certificates cpio curl debian-archive-keyring \
        debootstrap debhelper desktop-file-utils dconf-cli dctrl-tools dh-python dosfstools dpkg-dev fakeroot file \
        flatpak fonts-dejavu-core git gpg grub-common grub-efi-amd64-bin grub-efi-amd64-signed \
        grub-efi-ia32-bin grub-pc-bin isolinux jq libglib2.0-bin librsvg2-bin live-build make mtools ostree \
        python3 python3-gi python3-yaml rsync shim-signed squashfs-tools \
        syslinux syslinux-common syslinux-utils systemd-container wget \
        xorriso xz-utils zstd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
