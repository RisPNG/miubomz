FROM debian:forky

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        apt-utils bzip2 ca-certificates cpio curl debian-archive-keyring \
        debootstrap desktop-file-utils dconf-cli dosfstools dpkg-dev dpkg-repack file \
        flatpak gpg grub-efi-amd64-bin grub-efi-amd64-signed grub-pc-bin \
        isolinux jq libglib2.0-bin live-build make mtools ostree \
        python3 python3-gi python3-yaml rsync shim-signed squashfs-tools \
        syslinux syslinux-common syslinux-utils systemd-container wget \
        xorriso xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
