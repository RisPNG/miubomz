# Building Miubomz

Miubomz is an opinionated Debian Testing GNOME desktop. The installed operating system remains Debian, and users can change the supplied defaults after installation.

The first image is built from the documented reference workstation using Debian's native `live-build` and Calamares installer. It includes the selected Debian packages, vendor applications, Flatpaks and their runtimes, GNOME extensions, application defaults, shell configuration, and Btrfs recovery integration. ChatGPT and personal reference-machine data are excluded.

Live boot and installation require at least 6 GiB of RAM and a 64 GiB installation disk. The live session uses Debian's native RAM-backed overlay with a 90% size ceiling to accommodate the supplied user toolchains.

## Use

Open `artifacts/miubomz-0.1.0-amd64.iso` in GNOME Boxes or another virtual machine. Allocate at least 6 GiB of RAM; an 80 GiB virtual disk leaves room for the supplied software and snapshots. The tested VM configuration uses four virtual CPUs with 3D acceleration disabled. Start the live desktop and open **Install Miubomz**.

Choose your language, location, keyboard, and account normally. Automatic partitioning creates a GPT disk with an 8 MiB BIOS boot partition, a 1 GiB EFI partition, and Btrfs for the remaining space. Manual partitioning is also available. When installation finishes, shut down the live session, detach the ISO in the VM's settings, and start the installed system.

The first installed boot initializes native Timeshift scheduling and its initial snapshot. APT transactions create additional system snapshots before changing packages. Home stays outside system rollback.

The supplied development tools are available offline. Specific Python-version provisioning uses Mise's normal upstream refresh; use its native offline mode for a supplied version, for example `MISE_OFFLINE=1 venv create project 3.11 --yes`.

## Build

The host needs Docker and mise, access to the Docker daemon, and enough free disk space for the uncompressed system, software cache, and ISO. The builder runs in a disposable privileged Debian container so native live-build can mount its working filesystems. It has access to the project and the optional reference export through explicit bind mounts.

```sh
mise run build
```

The first build captures vetted software assets from a read-only export of the final reference snapshot. Point `MIUBOMZ_REFERENCE_ROOT` to that mounted export:

```sh
MIUBOMZ_REFERENCE_ROOT=/path/to/read-only-reference mise run build
```

The export is mounted read-only at `/reference` inside the builder. After asset preparation has populated `.cache/miubomz/`, later builds reuse the frozen assets and do not need the reference VM. Keep the manifests and cache together when transferring the build inputs.

`scripts/prepare-assets.py` prepares the frozen software inputs described by `manifests/`. Local packages are built from `packages/`. The builder then calls `lb config` and `lb build`, producing:

- `artifacts/miubomz-0.1.0-amd64.iso`
- `artifacts/miubomz-0.1.0-amd64.iso.sha256`
- `artifacts/miubomz-0.1.0-amd64.packages`
- `artifacts/miubomz-0.1.0-amd64.build.json`
- `artifacts/miubomz-0.1.0-amd64.inputs.json`

Build logs and native live-build state are stored in `.build/`. Downloaded software is cached in `.cache/miubomz/`. Those directories and release artifacts are generated files, outside the source implementation.

After a successful native build, the exact Debian package archives used by the live system and offline installer are also preserved in the frozen cache. The inputs manifest records every package's version and SHA-256 hash. Later builds resolve those archives through live-build's local package repository, so moving Debian Testing packages do not replace the first version's inputs.

Calamares is built from Debian's 3.4.2-1.1 source with one partition-module correction: the legacy BIOS boot flag applies only to non-GPT tables. This keeps the GPT Btrfs root partition's Linux type. `packages/calamares/` contains the source checksums, patch, and native Debian package recipe; the cache retains the patched source and package archive.

Live boot uses the native `plymouth.enable=0` option. Cold BIOS testing reproduced the [GDM 50.3 Plymouth handoff timeout](https://github.com/GNOME/gdm/blob/50.3/daemon/gdm-manager.c): Plymouth returned to the initial console before GNOME's display was ready, and GDM opened a second login screen. Skipping Plymouth during live startup avoids that race. Installed systems use Debian's ordinary boot configuration.

The default build uses four CPUs, a 4 GiB container memory limit, and a 1 GiB Squashfs cache. Set `MIUBOMZ_BUILD_JOBS`, `MIUBOMZ_BUILD_MEMORY`, or `MIUBOMZ_SQUASHFS_MEMORY` to change these limits. `MIUBOMZ_DEBIAN_MIRROR` selects the build-time Debian archive; installed systems use Debian's ordinary Forky archive.

Squashfs compression uses the native `-no-duplicates` option to avoid the [Squashfs 4.7.5 duplicate-checking race](https://github.com/plougher/squashfs-tools/issues/362). Files and hard links retain their usual behavior; compression does not merge identical file contents.

```sh
mise run clean
```

This invokes native `lb clean --purge` for the generated working system. It preserves the downloaded asset cache, build logs, and exported release artifacts.

## Layout

- `auto/`: native live-build configuration, build, and clean entry points.
- `image/config/`: Debian package lists and final image hooks.
- `packages/`: maintained desktop defaults and installer/recovery integration.
- `manifests/`: reviewed reference inventory and frozen external software inputs.
- `scripts/`: asset preparation, container orchestration, and image validation.
- `builder/`: Debian builder dependencies.

GNOME and application defaults initialize a fresh user without repeatedly resetting later changes. Live conveniences and installer files are removed during installation. Calamares creates the Btrfs subvolumes natively, while Timeshift and grub-btrfs provide the configured system recovery behavior. Native binary package lists place the BIOS and UEFI GRUB packages and their dependencies on the ISO, so Calamares can install the appropriate Debian bootloader package offline.

## Validation

The first release's [QA report](artifacts/miubomz-0.1.0-amd64.qa.json) records ISO checksums, test scope, detailed reports, and screenshots. Tests used disposable VMs with 6 GiB RAM, four CPUs, 80 GiB installation disks, 2D Virtio graphics, and no network device.

- ISO checks passed for the complete Squashfs, Debian identity, all 2,906 exact reference package versions, five local packages, ChatGPT exclusion, BIOS/UEFI boot entries, and the offline GRUB repository.
- Both firmware modes booted directly into the live GNOME desktop. Native offline Calamares installations completed all 43 jobs and booted the installed system. GPT root typing, Btrfs subvolumes, account initialization, installer cleanup, and retained BIOS bootloader device were checked.
- Nine desktop checks passed: GNOME and all 13 extensions, Firefox, Vivaldi, interactive shell, qView, requested-version Python/easyvenv, other development tools, all 18 Flatpaks and 31 exact application/runtime commits, and qView/Gear Lever GUI integration.
- First-boot Timeshift scheduling, automatic GRUB snapshot entries, and an ordinary APT repository upgrade with a snapshot before the transaction passed. Installed APT policy was checked with unmodified official repository indexes transferred into the offline test guest after native media setup had pruned its index cache.

The final ISO rebuild changed the live boot menus and retained the exact tested filesystem hash. UEFI installation and desktop reports retain their original ISO identity and this filesystem linkage; the final ISO received fresh BIOS installation and both firmware cold-boot checks.

Kernel upgrade, GRUB snapshot preview, and permanent Timeshift restore were tested separately on an earlier disposable installation with the identical shipped recovery package contents. The component report preserves that lineage. Native Timeshift reported a temporary-directory cleanup error after a successful restore; the subsequent boot verified the restored root and old kernel, preserved home/log data, and had no failed units.

Secure Boot, encrypted installation, hibernation, the fail-safe boot entry, and physical display DDC were not tested. The supplied defaults remain editable after installation.
